#!/usr/bin/env python3
"""Compare rename outcomes and filesystem effects with original IRIX."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(reference, native):
    original = json.loads(reference.read_text())
    assert original['status'] == 'observed' and original['clean_shutdown']
    observations = original['observations']
    assert len({o['name'] for o in observations}) == len(observations) == 256
    results = []
    with tarfile.open(native) as tar:
        files = {m.name.removeprefix('./'): m for m in tar if m.isfile()}
        for name, item in original['manifest']['files'].items():
            data = tar.extractfile(files[name]).read()
            assert len(data) == item['bytes']
            assert hashlib.sha256(data).hexdigest() == item['sha256']
        logs = {n for n in files if n.endswith('.log')}
        assert logs == {o['name']+'.log' for o in observations}
        for observation in observations:
            name = observation['name']
            assert observation['exit'] == 0
            assert not tar.extractfile(files[name+'.err']).read(), name
            log = tar.extractfile(files[name+'.log']).read().decode()
            assert re.search(r'^OBS .* errno_bytes=0 errno=0 exit=0 signal=0 killed=0$', log, re.M), name
            assert 'STDERR bytes=0 hex=' in log and 'GROUP absent=1' in log, name
            match = re.search(r'^STDOUT bytes=1024 hex=([0-9a-f]+)$', log, re.M)
            assert match, name
            actual = bytes.fromhex(match[1])
            expected = bytes.fromhex(observation['stdout_hex'])
            differences = [(i, actual[i:i+4].hex(), expected[i:i+4].hex())
                           for i in range(0, 1024, 4) if actual[i:i+4] != expected[i:i+4]]
            results.append(dict(name=name, passed=not differences,
                                differences=differences, record_sha256=hashlib.sha256(actual).hexdigest()))
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, default=Path('lab/irix-pathops/rename-reference.json'))
    p.add_argument('--native', type=Path, required=True)
    p.add_argument('--native-run', type=Path, required=True)
    p.add_argument('--diagnostic', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    run = json.loads((args.native_run/('initial.json' if args.diagnostic else 'result.json')).read_text())
    if not args.diagnostic:
        assert run['clean_shutdown'] and run['source_unchanged']
    observations = qualify(args.reference, args.native)
    passed = all(o['passed'] for o in observations)
    result = dict(schema=1, status=('diagnostic' if args.diagnostic else 'passed') if passed else 'mismatch',
                  reference_sha256=sha(args.reference), native_sha256=sha(args.native),
                  native_run=str(args.native_run), candidate_module=run['candidate_module'],
                  qualifier_sha256=sha(Path(__file__)), observations=observations)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(sum(o['passed'] for o in observations), '/', len(observations), 'rename records match')
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
