"""Read-only export of Prismatic's raw disk and IRIS dirty-sector overlay."""
from contextlib import ExitStack
import fcntl
import hashlib
from pathlib import Path
import struct

SECTOR = 512
CHUNK = 1024 * 1024


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def dirty_sectors(data, size):
    """Include appended LBAs, not just the count at the last IRIS flush.

    Refuse incomplete metadata for an archival export, even though IRIS can
    recover a live overlay by ignoring an unfinished final append.
    """
    if len(data) < 8 or len(data) % 8:
        raise ValueError('dirty-sector map has an incomplete header or entry')
    count, = struct.unpack_from('<Q', data)
    entries = len(data) // 8 - 1
    if count > entries:
        raise ValueError('dirty-sector map is shorter than its recorded count')
    sectors = set()
    for sector, in struct.iter_unpack('<Q', memoryview(data)[8:]):
        if sector >= size // SECTOR:
            raise ValueError('dirty sector is outside the base disk')
        sectors.add(sector)
    return sorted(sectors), count, entries


def identity(stat):
    return (stat.st_dev, stat.st_ino, stat.st_size,
            stat.st_mtime_ns, stat.st_ctime_ns)


def export_raw(base, destination):
    """Export a stopped Prismatic raw disk; never write its source files.

    Require its existing frontend lease. Also hold the IRIS overlay lease when
    present. File identities and complete input hashes must remain unchanged.
    The caller must stop the guest cleanly first; locks do not prove a clean XFS.
    """
    base = Path(base).resolve(strict=True)
    destination = Path(destination).absolute()
    paths = [base, Path(str(base)+'.overlay'), Path(str(base)+'.overlay.dirty')]
    locks = [Path(str(base)+'.prismatic-lock')]
    overlay_lock = Path(str(paths[1])+'.lock')
    if overlay_lock.exists():
        locks.append(overlay_lock)
    created = False
    with ExitStack() as stack:
        for path in locks:
            stream = stack.enter_context(path.open('rb'))
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError('source disk is in use: '+str(path)) from error
        streams = [stack.enter_context(path.open('rb')) for path in paths]
        before = [identity(path.stat()) for path in paths]
        size = before[0][2]
        if not size or size % SECTOR:
            raise ValueError('base disk must contain whole 512-byte sectors')
        sectors, count, entries = dirty_sectors(streams[2].read(), size)
        if sectors and (sectors[-1]+1)*SECTOR > before[1][2]:
            raise ValueError('overlay is shorter than its last dirty sector')
        inputs = []
        for path, stream in zip(paths, streams):
            stream.seek(0)
            inputs.append({'path': str(path), 'bytes': path.stat().st_size,
                           'sha256': hashlib.file_digest(stream, 'sha256').hexdigest()})
        streams[0].seek(0)
        digest = hashlib.sha256()
        cursor = 0
        try:
            with destination.open('xb') as output:
                created = True
                for offset in range(0, size, CHUNK):
                    want = min(CHUNK, size-offset)
                    data = bytearray(streams[0].read(want))
                    if len(data) != want:
                        raise ValueError('base disk was truncated during export')
                    end_sector = (offset+want)//SECTOR
                    while cursor < len(sectors) and sectors[cursor] < end_sector:
                        first = last = sectors[cursor]
                        cursor += 1
                        while (cursor < len(sectors) and sectors[cursor] == last+1
                               and sectors[cursor] < end_sector):
                            last = sectors[cursor]
                            cursor += 1
                        length = (last-first+1)*SECTOR
                        streams[1].seek(first*SECTOR)
                        changed = streams[1].read(length)
                        if len(changed) != length:
                            raise ValueError('overlay was truncated during export')
                        start = first*SECTOR-offset
                        data[start:start+length] = changed
                    digest.update(data)
                    if data.strip(b'\0'):
                        output.write(data)
                    else:
                        output.seek(want, 1)
                output.truncate(size)
                output.flush()
                import os
                os.fsync(output.fileno())
            for path, stream, expected in zip(paths, streams, inputs):
                stream.seek(0)
                if hashlib.file_digest(stream, 'sha256').hexdigest() != expected['sha256']:
                    raise RuntimeError('source contents changed during export: '+str(path))
            if before != [identity(path.stat()) for path in paths]:
                raise RuntimeError('source files changed during export')
            exported_hash = digest.hexdigest()
            if sha256(destination) != exported_hash:
                raise RuntimeError('exported disk differs from the merged source view')
            return {'schema': 1, 'source_files': inputs, 'source_unchanged': True,
                    'locks': [str(p) for p in locks], 'logical_bytes': size,
                    'sector_bytes': SECTOR, 'dirty_header_count': count,
                    'dirty_entries': entries, 'unique_dirty_sectors': len(sectors),
                    'raw_sha256': exported_hash}
        except BaseException:
            if created:
                destination.unlink()
            raise
