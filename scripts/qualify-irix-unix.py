#!/usr/bin/env python3
"""Compare pathname-stream observations with original IRIX records."""
import argparse
import contextlib
import hashlib
import json
from pathlib import Path
import re
import struct
import tarfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify(reference, native):
    observations = []
    published = json.loads(reference.read_text()) if reference.suffix == '.json' else None
    if published:
        assert published['status'] == 'observed' and published['clean_shutdown']
        original = {o['name']: o for o in published['observations']}
        assert len(original) == len(published['observations']) == 68
    with (contextlib.nullcontext() if published else tarfile.open(reference)) as ref, tarfile.open(native) as net:
        names = {m.name.removeprefix('./'): m for m in net.getmembers()}
        if published:
            for name, expected in published['manifest']['files'].items():
                fixture = net.extractfile(names['bin/'+name]).read()
                assert len(fixture) == expected['bytes'], name
                assert hashlib.sha256(fixture).hexdigest() == expected['sha256'], name
        modes = [0, 1, 2, 3, 4, 10, 11, 12, *range(20, 29)]
        logs = {abi+'-'+form+'-'+str(mode)+'-'+str(uid)+'.log'
                for abi in ['o32', 'n32'] for form in ['direct', 'indirect']
                for mode in modes for uid in [0, 1234]}
        assert {n for n in names if n.endswith('.log')} == logs
        statuses = ({name: str(o['exit']) for name, o in original.items()} if published else
                    dict(re.findall(r'^(\S+) (\d+)$', ref.extractfile('status.txt').read().decode(), re.M)))
        for name in sorted(logs):
            exe, mode, uid = name[:-4].rsplit('-', 2)
            mode, uid = int(mode), int(uid)
            log = net.extractfile(names[name]).read().decode()
            assert re.search(r'errno_bytes=0 errno=0 exit=0 signal=0 killed=0\n', log), name
            assert 'GROUP absent=1' in log and 'STDERR bytes=0 hex=\n' in log, name
            data = bytes.fromhex(re.search(r'^STDOUT bytes=2048 hex=([0-9a-f]+)$', log, re.M)[1])
            refname = exe+'-'+str(mode)
            assert statuses[refname] == '0'
            if published:
                assert not original[refname]['stderr']
                expected = bytearray.fromhex(original[refname]['stdout_hex'])
            else:
                assert not ref.extractfile(refname+'.err').read()
                expected = bytearray(ref.extractfile(refname+'.out').read())
            assert len(data) == len(expected) == 2048
            for index in [2, 3, 5, 6]:
                struct.pack_into('>I', expected, index*4, uid)
            # Explicit bounded-subset policies, not original-IRIX parity.
            policy = {11: 'datagrams unsupported', 21: 'short family rejected',
                      24: 'oversize address rejected', 25: 'null input returns EFAULT',
                      28: 'native pathname capacity enforced'}.get(mode)
            if mode == 11:
                struct.pack_into('>3I', expected, 8*4, 121, 0xfeedface, 1)
                struct.pack_into('>3I', expected, 56*4, 0, 0, 0)
            elif mode in [21, 24, 25, 28]:
                struct.pack_into('>3I', expected, 11*4,
                                 {21: 22, 24: 22, 25: 14, 28: 78}[mode], 0xfeedface, 1)
            assert data == expected, (name, [(i, data[i:i+4].hex(), expected[i:i+4].hex())
                                             for i in range(0, len(data), 4) if data[i:i+4] != expected[i:i+4]])
            observations.append(dict(name=name[:-4], uid=uid, mode=mode,
                                     contract='subset' if policy else 'IRIX parity',
                                     policy=policy, sha256=hashlib.sha256(data).hexdigest()))
    assert len(observations) == 136, len(observations)
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--native', type=Path, required=True)
    parser.add_argument('--native-run', type=Path, required=True)
    parser.add_argument('--reference-run', type=Path,
                        help='Required for an unpublished reference tar archive')
    parser.add_argument('--diagnostic', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    observations = qualify(args.reference, args.native)
    if args.reference_run:
        original = json.loads((args.reference_run/'result.json').read_text())
        assert original['clean_shutdown']
    else:
        assert args.reference.suffix == '.json', 'unpublished reference needs its shutdown record'
    if not args.diagnostic:
        current = json.loads((args.native_run/'result.json').read_text())
        assert current['clean_shutdown'] and current['source_unchanged']
    else:
        current = json.loads((args.native_run/'initial.json').read_text())
    result = dict(status='diagnostic' if args.diagnostic else 'passed',
                  reference_sha256=sha(args.reference), native_sha256=sha(args.native),
                  reference_run=str(args.reference_run), native_run=str(args.native_run),
                  candidate_module=current['candidate_module'], observations=observations,
                  qualifier_sha256=sha(Path(__file__)))
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(len(observations), 'observations match their declared contracts')


if __name__ == '__main__':
    main()
