#!/usr/bin/env python3
"""Compare symlink and utimets results with original IRIX observations."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import tarfile


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def records(path):
    result = {}
    errors = set()
    with tarfile.open(path) as archive:
        for member in archive:
            name = member.name.removeprefix('./')
            if name.endswith('.err'):
                assert member.size == 0, name
                errors.add(name[:-4])
            elif name.endswith('.out'):
                data = archive.extractfile(member).read()
                assert len(data) == 512, (name, len(data))
                row = list(struct.unpack('>128I', data))
                assert row[0] == 0x58464d54 and row[1] in (1115, 1235)
                assert row[5] == 0 and row[3] == row[4] in (0, 1234)
                assert row[9] == 0xfeedface and row[10] in (0, 1)
                assert name not in result
                result[name] = row
    assert len(result) == 328 and errors == {name[:-4] for name in result}
    return result


def expected_record(name, original):
    row = original.copy()
    # IRIX stores malformed nanoseconds. Xiri deliberately rejects them,
    # avoiding native UTIME_NOW/UTIME_OMIT sentinel interpretation. Require
    # EINVAL and *all* original metadata unchanged for precisely these cases.
    # Native vattr also reserves seconds == -1 as VNOVAL, so that otherwise
    # valid IRIX timestamp must fail rather than succeed without changing it.
    if name.endswith(('-t-negative-nsec.out', '-t-large-nsec.out', '-t-negative-sec.out')):
        assert row[1] == 1235 and row[8:11] == [0, 0xfeedface, 0]
        row[8:11] = [22, 0xfeedface, 1]
        for which in range(3):
            before = 16 + which * 18
            after = before + 54
            row[after:after+18] = row[before:before+18]
            if row[before+1] == 0 and row[before+2] & 0o170000 != 0o120000:
                row[after+16] = 15
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native', type=Path, required=True)
    p.add_argument('--reference', type=Path, default=Path(__file__).resolve().parent.parent/'lab/irix-pathops/filemeta-reference.json')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--native-run', type=Path)
    p.add_argument('--diagnostic', action='store_true')
    args = p.parse_args()
    reference = json.loads(args.reference.read_text())
    assert reference['clean_shutdown'] and reference['status'] == 'observed'
    actual = records(args.native)
    assert set(actual) == set(reference['observations'])
    mismatches = []
    for name, row in actual.items():
        expected = expected_record(name, reference['observations'][name])
        differences = [dict(word=i, expected=value, actual=row[i])
                       for i, value in enumerate(expected) if value != row[i]]
        if differences:
            mismatches.append(dict(case=name, differences=differences))
    run = None
    if not args.diagnostic:
        assert args.native_run
        path = args.native_run/'result.json'
        run = json.loads(path.read_text())
        assert run['status'] == 'observed' and run['clean_shutdown'] and run['base_unchanged']
        assert not run.get('harness_note')
        assert run['archives']['filemeta.tar'] == digest(args.native)
        run = dict(directory=str(args.native_run), result_sha256=digest(path), module_sha256=run['module_sha256'])
    result = dict(schema=1, status='failed' if mismatches else ('diagnostic' if args.diagnostic else 'passed'),
        records=328, native_sha256=digest(args.native), reference_sha256=digest(args.reference),
        qualifier_sha256=digest(Path(__file__)), native_run=run, mismatches=mismatches,
        deliberate_difference='24 cases require EINVAL and unchanged metadata: noncanonical nanoseconds or native-vattr reserved seconds == -1. IRIX accepts these values.',
        limits=['Local filesystem, root and UID 1234, o32/n32 direct and indirect traps.',
                'No claim for remote filesystems, concurrent pathname replacement, immutable flags, or 64-bit time extensions.'])
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], records=328, mismatches=mismatches)))
    return bool(mismatches)


if __name__ == '__main__':
    raise SystemExit(main())
