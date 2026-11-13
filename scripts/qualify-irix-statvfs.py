#!/usr/bin/env python3
"""Compare paired filesystem-statistics records without equating two disks."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tarfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_records(path):
    result = {}
    with tarfile.open(path) as archive:
        for abi in ('o32', 'n32'):
            for dispatch in ('direct', 'indirect'):
                for user in ('root', 'user'):
                    name = f'{abi}-{dispatch}-{user}'
                    data = archive.extractfile('results/'+name+'.out').read()
                    assert len(data) == 48*512, (name, len(data))
                    assert not archive.extractfile('results/'+name+'.err').read(), name
                    records = []
                    offset = 0
                    for trap, count in ((1174, 16), (1175, 8), (1201, 16), (1202, 8)):
                        for case in range(count):
                            block = data[offset:offset+512]
                            header = struct.unpack_from('>8I', block)
                            assert header[:2] == (trap, case), (name, header)
                            assert header[5] == 0, (name, 'fixture open', header)
                            error = header[4] != 0
                            wide = abi == 'n32' or trap in (1201, 1202)
                            size = 184 if wide else 156
                            unaligned = case == (6 if count == 8 else 12)
                            begin = 80 + int(unaligned)
                            memory = block[64:320]
                            if error:
                                assert memory == b'\xa5'*256, (name, trap, case, 'error clobber')
                            else:
                                assert block[64:begin] == b'\xa5'*(begin-64)
                                assert block[begin+size:320] == b'\xa5'*(320-begin-size)
                            item = dict(trap=trap, case=case, result=list(header[2:5]),
                                        layout_bytes=size, guards=True)
                            if not error:
                                buf = block[begin:begin+size]
                                values = struct.unpack_from('>2I6Q' if wide else '>8I', buf)
                                assert values[0] and values[1] and values[2], (name, values)
                                assert values[3] <= values[2], (name, values)
                                # Some filesystems use -1 for unknown inode
                                # counts; record these rather than inventing them.
                                tail = 56 if wide else 32
                                fsid, = struct.unpack_from('>I', buf, tail)
                                flags, namemax = struct.unpack_from('>2I', buf, tail+20)
                                kind = buf[tail+4:tail+20].split(b'\0', 1)[0].decode('ascii')
                                assert kind and namemax > 0
                                item['filesystem'] = dict(bsize=values[0], frsize=values[1],
                                    blocks=values[2], bfree=values[3], bavail=values[4],
                                    files=values[5], ffree=values[6], favail=values[7],
                                    fsid=fsid, type=kind, flags=flags, namemax=namemax)
                                item['reserved_zero'] = not any(buf[tail+60:])
                            records.append(item)
                            offset += 512
                    result[name] = records
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--native', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--diagnostic', action='store_true')
    p.add_argument('--native-run', type=Path)
    p.add_argument('--reference-run', type=Path)
    a = p.parse_args()
    reference_path = Path(__file__).resolve().parent.parent/'lab/irix-pathops/statvfs-reference.json'
    reference_pin = json.loads(reference_path.read_text())
    assert digest(a.reference) == reference_pin['archive_sha256'], 'Use the retained IRIX reference archive'
    reference, native = read_records(a.reference), read_records(a.native)
    mismatches = []
    for name, records in native.items():
        for index, item in enumerate(records):
            expected = reference[name][index]
            if item['result'] != expected['result']:
                mismatches.append(dict(name=name, trap=item['trap'], case=item['case'],
                                       expected=expected['result'], actual=item['result']))
            if 'filesystem' in item:
                assert item['reserved_zero'], (name, item)
        # All four call forms address the same filesystem. Its identity,
        # geometry and total capacity must agree; free counts can change.
        stable = ('bsize', 'frsize', 'blocks', 'fsid', 'type', 'flags', 'namemax')
        seen = {tuple(r['filesystem'][k] for k in stable)
                for r in records if 'filesystem' in r}
        assert len(seen) == 1, (name, seen)
    runs = {}
    if not a.diagnostic:
        assert a.native_run and a.reference_run, 'Supply halted owning runs for qualification'
        for kind, directory in [('native', a.native_run), ('reference', a.reference_run)]:
            path = directory/'result.json'
            result = json.loads(path.read_text())
            assert result['status'] == 'observed' and result['clean_shutdown'], (kind, result)
            assert not result.get('harness_note'), 'Diagnostic owner recovery is not qualification'
            if kind == 'native':
                assert result['base_unchanged']
            runs[kind] = dict(directory=str(directory), result_sha256=digest(path))
    result = dict(schema=1, status='diagnostic' if a.diagnostic else 'passed',
                  reference_sha256=digest(a.reference), native_sha256=digest(a.native),
                  reference_manifest_sha256=digest(reference_path),
                  qualifier_sha256=digest(Path(__file__)),
                  records=384, mismatches=mismatches, runs=runs,
                  observations=native,
                  limits=['Filesystem capacity and IDs differ between XFS and FFS.',
                          'No claim of large-filesystem overflow or concurrent unmount qualification.'])
    if mismatches:
        result['status'] = 'failed'
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], records=384, mismatches=mismatches)))
    return bool(mismatches)


if __name__ == '__main__':
    raise SystemExit(main())
