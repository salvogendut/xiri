#!/usr/bin/env python3
"""Check terminal ABI observations against measured IRIX and bounded policies."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import tarfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def put(data, index, *values):
    struct.pack_into('>'+str(len(values))+'I', data, index*4, *values)


def expected(suite, mode, name, originals):
    """Keep successful reference records intact; spell out subset departures."""
    exe, _, uid = name.rsplit('-', 2)

    def reference(number):
        return bytearray.fromhex(originals[exe+'-'+str(number)+'-'+uid]['stdout_hex'])

    policy = None
    if suite == 'socketpair':
        data = reference(10 if mode == 11 else mode)
        if mode in [4, 11, 16]:
            error, policy = {
                4: (14, 'native EFAULT for read-only output; IRIX returns EACCES'),
                11: (121, 'datagram pairs unsupported'),
                16: (124, 'only AF_UNIX pairs supported'),
            }[mode]
            put(data, 11, error, 0xfeedface, 1)
    elif suite == 'ptm':
        data = reference(mode if mode <= 4 else 0)
        if mode > 4:
            policy = 'only exact zero-payload, zero-timeout master-check request supported'
            put(data, 11, 89, 0xfeedface, 1)
    else:
        if mode in [0, 6]:
            data = reference(mode)
        elif mode in [1, 2, 3, 4, 5, 10, 14]:
            data = reference(6)
            error = {1: 9, 2: 14}.get(mode, 122)
            policy = {1: 'invalid descriptor rejected without queuing data',
                      2: 'faulting descriptor input rejected without queuing data'}.get(
                          mode, 'only one complete descriptor with a non-null input is supported')
            put(data, 17, error, 0xfeedface, 1)
        else:
            data = reference(0)
            error = 14 if mode in [11, 15] else 122
            policy = ('fault closes the externalized descriptor' if error == 14 else
                      'unsupported receive capacity, null pointer or rights peek rejected before consumption')
            put(data, 23, error, 0xfeedface, 1)
            put(data, 26, 5)  # Only the two original sockets remain open.
            put(data, 29, 0, 0, 0, 0, 0, 0)
            put(data, 120, {7: 0, 8: 1, 9: 3, 12: 0xffffffff, 13: 65}.get(mode, 16))
            put(data, 128, 0xa5a5a5a5)
            if mode != 11:  # A rights-buffer fault follows successful data delivery.
                put(data, 144, 0)
            put(data, 152, 0, 0)
    put(data, 1, mode)
    return bytes(data), policy


def qualify(suite, reference, archive, manifest):
    originals = {o['name']: o for o in reference['suites'][suite]['observations']}
    observations = []
    with tarfile.open(archive) as tar:
        members = {m.name.removeprefix('./'): m for m in tar}
        for name, entry in manifest['files'].items():
            data = tar.extractfile(members['bin/'+name]).read()
            assert hashlib.sha256(data).hexdigest() == entry['sha256'], name
            assert len(data) == entry['bytes'], name
        names = {exe+'-'+str(mode)+'-'+str(uid)
                 for exe in manifest['files'] for mode in manifest['modes'] for uid in [0, 1234]}
        assert {n[:-4] for n in members if n.endswith('.log')} == names
        for name in sorted(names):
            log = tar.extractfile(members[name+'.log']).read().decode()
            assert 'errno_bytes=0 errno=0 exit=0 signal=0 killed=0\n' in log, name
            assert 'GROUP absent=1' in log and 'STDERR bytes=0 hex=\n' in log, name
            assert not tar.extractfile(members[name+'.err']).read(), name
            data = bytes.fromhex(re.search(r'^STDOUT bytes=1024 hex=([0-9a-f]+)$', log, re.M)[1])
            _, mode, uid = name.rsplit('-', 2)
            wanted, policy = expected(suite, int(mode), name, originals)
            assert data == wanted, (suite, name, [
                (i//4, data[i:i+4].hex(), wanted[i:i+4].hex())
                for i in range(0, 1024, 4) if data[i:i+4] != wanted[i:i+4]])
            observations.append(dict(name=name, uid=int(uid), mode=int(mode),
                                     contract='subset' if policy else 'IRIX parity',
                                     policy=policy, sha256=hashlib.sha256(data).hexdigest()))
    return observations


def qualify_peer(archive, manifest):
    """Check native-to-IRIX descriptor ownership, including rejected messages."""
    observations = []
    with tarfile.open(archive) as tar:
        members = {m.name.removeprefix('./'): m for m in tar}
        source = Path(__file__).resolve().parent.parent/'lab/irix-terminal/native-peer.c'
        assert tar.extractfile(members['bin/native-peer.c']).read() == source.read_bytes()
        for name, entry in manifest['files'].items():
            data = tar.extractfile(members['bin/'+name]).read()
            assert hashlib.sha256(data).hexdigest() == entry['sha256'], name
        names = {exe+'-'+str(mode)+'-'+str(uid)
                 for exe in manifest['files'] for mode in range(4) for uid in [0, 1234]}
        assert {n[:-4] for n in members if n.endswith('.log')} == names
        for name in sorted(names):
            log = tar.extractfile(members[name+'.log']).read().decode()
            assert 'errno_bytes=0 errno=0 exit=0 signal=0 killed=0\n' in log, name
            assert 'GROUP absent=1' in log and 'STDERR bytes=0 hex=\n' in log, name
            assert not tar.extractfile(members[name+'.err']).read(), name
            data = bytes.fromhex(re.search(r'^STDOUT bytes=1024 hex=([0-9a-f]+)$', log, re.M)[1])
            _, mode, uid = name.rsplit('-', 2)
            mode, uid = int(mode), int(uid)
            wanted = bytearray(1024)
            put(wanted, 0, 0x58525043, mode, uid, uid, 0, uid, uid, 0)
            put(wanted, 8, 3, 0xfeedface, 0)
            put(wanted, 11, 1 if mode == 0 else 122 if mode == 1 else 14,
                0xfeedface, int(mode != 0))
            put(wanted, 14, 4 if mode == 0 else 3, 0xfeedface, 0)
            put(wanted, 23, 3, 0xfeedface, 0)
            put(wanted, 120, 4 if mode == 0 else 16)
            put(wanted, 128, *([0xa5a5a5a5]*4))
            if mode != 3:
                wanted[144*4] = ord('D')
            if mode == 0:
                put(wanted, 128, 3)
                put(wanted, 17, 6, 0xfeedface, 0, 0, 0xfeedface, 0)
                wanted[152*4:152*4+6] = b'RIGHTS'
            assert data == wanted, (name, [
                (i//4, data[i:i+4].hex(), wanted[i:i+4].hex())
                for i in range(0, 1024, 4) if data[i:i+4] != wanted[i:i+4]])
            observations.append(dict(name=name, mode=mode, uid=uid,
                contract='native peer and descriptor cleanup',
                sha256=hashlib.sha256(data).hexdigest()))
    return observations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--native-dir', type=Path, required=True)
    parser.add_argument('--archive-suffix', default='native-v4')
    parser.add_argument('--peer-manifest', type=Path)
    parser.add_argument('--native-run', type=Path, required=True)
    parser.add_argument('--diagnostic', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text())
    assert reference['clean_shutdown'] and reference['status'] == 'observed'
    result = dict(status='diagnostic' if args.diagnostic else 'passed',
                  qualifier_sha256=sha(Path(__file__)), reference_sha256=sha(args.reference), suites={})
    for suite in ['socketpair', 'rights', 'ptm']:
        archive = args.native_dir/(suite+'-'+args.archive_suffix+'.tgz')
        manifest = reference['suites'][suite]['manifest']
        result['suites'][suite] = dict(archive_sha256=sha(archive),
            observations=qualify(suite, reference, archive, manifest))
    if args.peer_manifest:
        archive = args.native_dir/('rights-peer-'+args.archive_suffix+'.tgz')
        manifest = json.loads(args.peer_manifest.read_text())
        result['suites']['rights-peer'] = dict(archive_sha256=sha(archive),
            manifest=manifest, native_peer_source_sha256=sha(
                Path(__file__).resolve().parent.parent/'lab/irix-terminal/native-peer.c'),
            observations=qualify_peer(archive, manifest))
    record = json.loads((args.native_run/('initial.json' if args.diagnostic else 'result.json')).read_text())
    if not args.diagnostic:
        assert record['clean_shutdown'] and record['source_unchanged']
    result['native_run'] = str(args.native_run)
    result['candidate_module'] = record['candidate_module']
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(sum(len(s['observations']) for s in result['suites'].values()), 'observations qualified')


if __name__ == '__main__':
    main()
