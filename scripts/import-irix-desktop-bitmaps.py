#!/usr/bin/env python3
"""Import observed SGI toolbar resources from the read-only reference image.

Vendor data stays in .work. The public ledger records source/destination
paths and hashes; the existing qualified desktop payload is left intact.
"""
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT/'.work/irix-desktop-bitmaps'
REFERENCE = ROOT/'.work/irix-reference'
SOURCE = '/usr/include/X11/bitmaps/sgidesktop'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    raw = REFERENCE/'media/irix65.raw'
    pin = ROOT/'lab/irix-reference/manifest.json'
    assert raw.stat().st_size == json.loads(pin.read_text())['logical_disk_bytes']
    env = dict(os.environ, LIBGUESTFS_BACKEND='direct',
               LIBGUESTFS_CACHEDIR=str(REFERENCE/'guestfs-cache'),
               LIBGUESTFS_TMPDIR=str(REFERENCE/'tmp'))
    listener = subprocess.check_output(['guestfish', '--ro', '-a', str(raw), '--listen'],
                                       env=env, text=True, timeout=30)
    pid = re.search(r'GUESTFISH_PID=(\d+)', listener)[1]
    def guest(*args):
        subprocess.run(['guestfish', '--remote='+pid, *args], check=True, timeout=180)
    archive = WORK/'sgidesktop.tar'
    try:
        guest('run')
        guest('mount-options', 'ro,norecovery', '/dev/sda1', '/')
        guest('tar-out', SOURCE, str(archive))
    finally:
        guest('exit')
    rows = []
    # Preserve the six original resource aliases inside the guest payload.
    # No original absolute link is materialized on the host.
    with tarfile.open(archive) as source, tarfile.open(WORK/'payload.tgz', 'w:gz') as out:
        for member in source:
            relative = PurePosixPath(member.name)
            assert not relative.is_absolute() and '..' not in relative.parts
            assert member.isdir() or member.isfile() or member.issym(), member.name
            path = str(PurePosixPath(SOURCE)/relative)
            dest = '/emul/irix'+path
            entry = tarfile.TarInfo(dest.lstrip('/'))
            entry.uid = entry.gid = 0
            entry.mode = 0o755 if member.isdir() else 0o444
            entry.type = tarfile.DIRTYPE if member.isdir() else tarfile.SYMTYPE if member.issym() else tarfile.REGTYPE
            row = dict(source=path, netbsd_destination=dest,
                       type='directory' if member.isdir() else 'symlink' if member.issym() else 'file',
                       source_mode=oct(member.mode), installed_mode=oct(entry.mode))
            if member.isfile():
                data = source.extractfile(member).read()
                entry.size = len(data)
                row.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
                out.addfile(entry, io.BytesIO(data))
            elif member.issym():
                target = PurePosixPath(member.linkname)
                assert target.parent == PurePosixPath(SOURCE) and '..' not in target.parts
                entry.linkname = member.linkname
                row['target'] = member.linkname
                out.addfile(entry)
            else:
                out.addfile(entry)
            rows.append(row)
    result = dict(schema=1, source_manifest_sha256=sha(pin),
                  extraction='guestfish --ro; XFS ro,norecovery',
                  purpose='Observed fm toolbar bitmap lookups; filetype icon artwork is separate.',
                  script_sha256=sha(Path(__file__)), files=rows,
                  payload_sha256=sha(WORK/'payload.tgz'))
    (WORK/'copy-ledger.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'Imported {len(rows)} resource paths into {WORK}')


if __name__ == '__main__':
    main()
