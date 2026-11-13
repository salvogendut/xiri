#!/usr/bin/env python3
"""Compare removal results and surviving file metadata with measured IRIX."""
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
    with tarfile.open(path) as archive:
        for member in archive:
            if member.name.endswith('.err'):
                assert member.size == 0, member.name
            elif member.name.endswith('.out'):
                data = archive.extractfile(member).read()
                assert len(data) == 512, (member.name, len(data))
                row = list(struct.unpack('>128I', data))
                assert row[0] == 0x58524d56 and row[1] in (1010, 1079)
                assert row[5] == 0 and row[3] == row[4] in (0, 1234)
                assert member.name not in result
                result[member.name] = row
    assert len(result) == 336, len(result)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native', type=Path, required=True)
    p.add_argument('--reference', type=Path, default=Path(__file__).resolve().parent.parent/'lab/irix-pathops/remove-reference.json')
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--native-run', type=Path)
    p.add_argument('--reference-run', type=Path)
    p.add_argument('--diagnostic', action='store_true')
    args = p.parse_args()
    ref = json.loads(args.reference.read_text())
    observed = records(args.native)
    assert set(observed) == set(ref['observations'])
    mismatches = []
    for name, row in observed.items():
        expected = ref['observations'][name]
        differences = [i for i, value in enumerate(row) if value != expected[i]]
        if differences:
            mismatches.append(dict(case=name, words=differences,
                expected_result=expected[8:11], actual_result=row[8:11]))
    runs = {}
    if not args.diagnostic:
        assert args.native_run and args.reference_run
        for kind, directory in [('native', args.native_run), ('reference', args.reference_run)]:
            path = directory/'result.json'
            result = json.loads(path.read_text())
            assert result['status'] == 'observed' and result['clean_shutdown']
            assert not result.get('harness_note'), 'Diagnostic owner recovery is not qualification'
            if kind == 'native':
                assert result['base_unchanged']
            runs[kind] = dict(directory=str(directory), result_sha256=digest(path))
    result = dict(schema=1, status='diagnostic' if args.diagnostic else 'passed',
        native_sha256=digest(args.native), reference_sha256=digest(args.reference),
        records=336, mismatches=mismatches, runs=runs,
        qualifier_sha256=digest(Path(__file__)),
        limits=['Local filesystem, root and UID 1234, o32/n32 direct and indirect traps.',
                'No claim for concurrent pathname replacement, remote filesystems or immutable flags.'])
    if mismatches:
        result['status'] = 'failed'
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(dict(status=result['status'], records=336, mismatches=mismatches)))
    return bool(mismatches)


if __name__ == '__main__':
    raise SystemExit(main())
