#!/usr/bin/env python3
"""Independently check the complete original-IRIX sproc reference matrix."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import tarfile

ROOT = Path(__file__).resolve().parent.parent
FEED = 0xfeedface
VARIANTS = {'unblock', 'exit', 'exec-release', 'exec-fail', 'exit-release-armed',
            'exec-no-release', 'no-block', 'no-share', 'share-fds', 'local',
            'new-mapping', 'explicit-stack', 'short-stack', 'bad-entry'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def qualify_case(case, identity, data, status, guard, stderr, cleanup):
    """Check every word; only validated runtime PIDs and addresses vary."""
    s = case['symbols']
    variant = case['name'].split('-', 2)[2]
    assert variant in VARIANTS
    timed = variant in {'exit', 'exec-no-release', 'bad-entry'}
    assert guard == ('1' if timed else '0') and status == (137 if timed else 0)
    assert stderr == b'' and cleanup == 'clear'
    roles = ([] if variant == 'bad-entry' else [0] if variant == 'short-stack'
             else [1, 2] if variant == 'exec-no-release'
             else [1] if variant == 'exit'
             else [1, 2, 0] if variant == 'exec-release' else [1, 0])
    assert len(data) == 256*len(roles), (variant, len(data), roles)
    records = [list(struct.unpack('>64I', data[i:i+256])) for i in range(0, len(data), 256)]
    assert [w[2] for w in records] == roles
    by_role = {w[2]: w for w in records}
    child, parent = by_role.get(1), by_role.get(0)
    pp = parent[6] if parent else child[7] if child else 0
    cp = child[6] if child else 0
    if pp:
        assert 1 < pp < 0x80000000
    if cp:
        assert 1 < cp < 0x80000000 and cp != pp
    argument = parent[47] if parent else child[8] if child else 0
    if argument:
        assert 0x10000 <= argument < 0x80000000 and argument % 4 == 0
    top = parent[37] if parent else child[37] if child else 0
    if variant == 'explicit-stack':
        assert 0x10000 <= top < 0x80000000 and top % 4096 == 0
        assert child[14] == top-64
    if child:
        assert 0x10000 <= child[14] < 0x80000000 and child[14] % 16 == 0
        assert abs(child[14]-argument) > 8192
    mapped = child[48] if variant == 'new-mapping' else 0
    local = parent[38] if variant == 'local' else 0
    for addr in [mapped, local]:
        if addr:
            assert 0x10000 <= addr < 0x80000000 and addr % 4096 == 0
    if variant in {'new-mapping', 'local'}:
        assert mapped or local

    for actual in records:
        role = actual[2]
        expected = [0]*64
        expected[0:6] = [0x58535052, s['CASE'], role, s['FLAGS'], s['ACTION'], s['TRAP']]
        expected[56:60] = identity
        if role == 1:
            expected[6:9] = [cp, pp, argument]
            expected[13:20] = [1, actual[14], 0, 0x11220001, 0x11220002, 0x11220003, 0x11220004]
            expected[20:24] = [cp, 0xbabababa, 0x11223344, 0x98765432]
            expected[24:27] = [int(bool(s['FLAGS'] & 0x01000000)), FEED, 0]
            expected[27:30] = [2, FEED, 0]
            expected[30:33] = [1 | (s['FLAGS'] & 0x42), FEED, 0]
            expected[33:36] = [0, FEED, 0]
            expected[36:38] = [0x12345678 if s['LOCAL'] else 0, top]
            if s['ACTION'] in [2, 3, 4]:
                expected[38:41] = [0, FEED, 0]
            if s['ACTION'] == 3:
                expected[41:47] = [2, FEED, 1, 1, FEED, 0]
            if s['ACTION'] == 6:
                expected[48:51] = [mapped, FEED, 0]
        elif role == 0:
            failed = variant == 'short-stack'
            shared = bool(s['FLAGS'] & 0x40) and not failed
            expected[6] = pp
            expected[8:11] = [22, FEED, 1] if failed else [cp, 0, 0]
            expected[20:24] = [pp, 0xbabababa, 0x55667788 if shared else 0x11223344,
                               0xabcdef01 if shared else 0x98765432]
            if not failed:
                expected[24:30] = [0, 37 << 8, 0, 1, 37, cp]
            expected[30:33] = [0, FEED, 0]
            expected[33:36] = [9, FEED, 1] if s['FLAGS'] & 2 else [1, FEED, 0]
            expected[36:38] = [0x12345678 if s['LOCAL'] else 0, top]
            if s['LOCAL']:
                expected[38:41] = [local, FEED, 0]
            expected[41:44] = [0 if failed else 1, FEED, 0]
            expected[47] = argument
            if s['ACTION'] == 6:
                expected[48:50] = [mapped, 0xdecaf123]
        else:
            expected[0:6] = [0x58535052, 0, 2, 0, 0, 0]
            expected[6] = expected[20] = cp
            expected[27:30] = [0, FEED, 0]
        assert actual == expected, (case['name'], role,
            [(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(actual, expected)) if a != b])
    return records


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--reference-output', type=Path)
    a = p.parse_args()
    directory = a.run.resolve()
    run = json.loads((directory/'result.json').read_text())
    assert run['status'] == 'observed' and run['scope'] == 'full' and run['clean_shutdown']
    assert run['harness_sha256'] == sha(ROOT/'scripts/probe-irix-reference-sproc.py')
    assert run['seed_result_sha256'] == sha(ROOT/run['seed']/'result.json')
    seed = json.loads((ROOT/run['seed']/'result.json').read_text())
    media = json.loads((ROOT/'lab/irix-reference/manifest.json').read_text())
    assert seed['status'] == 'observed' and seed['clean_shutdown']
    assert run['emulator_sha256'] == seed['emulator_sha256'] == sha(ROOT/'.work/target/release/iris')
    assert run['firmware_sha256'] == seed['firmware_sha256'] == media['firmware']['sha256']
    assert '6.5 6.5.22m' in run['identity']
    m = run['manifest']
    assert m['identities'] == [[0]*4, [1234]*4]
    for name, digest in m['sources'].items():
        assert sha(ROOT/name) == digest, name
    assert len(m['cases']) == 56 and len(m['files']) == 56
    assert set(run['checked_files']) == set(m['files'])
    for name, info in m['files'].items():
        f = directory/'fixtures'/name
        assert sha(f) == info['sha256'] and f.stat().st_size == info['bytes']
    expected_names = {abi+'-'+dispatch+'-'+v for abi in ['o32', 'n32']
                      for dispatch in ['direct', 'indirect'] for v in VARIANTS}
    assert {c['name'] for c in m['cases']} == expected_names
    assert all(c['identities'] == [0, 1] for c in m['cases'])
    expected_runs = {n+'-'+str(i) for n in expected_names for i in [0, 1]}
    archive = directory/'outputs.tgz'
    observations, total, timed = [], 0, 0
    recorded = {o['name']: o for o in run['observations']}
    assert len(recorded) == len(run['observations']) == 112 and set(recorded) == expected_runs
    with tarfile.open(archive) as tar:
        members = {x.name.removeprefix('./'): x for x in tar.getmembers()}
        assert len(members) == len(tar.getmembers())
        def read(name): return tar.extractfile(members[name]).read()
        statuses = re.findall(r'^CASE (\S+) (\d+)$', read('status.txt').decode(), re.M)
        assert len(statuses) == 112 and {n for n, _ in statuses} == expected_runs
        statuses = {n: int(v) for n, v in statuses}
        for case in m['cases']:
            for identity in [0, 1]:
                name = case['name']+'-'+str(identity)
                data, stderr = read(name+'.out'), read(name+'.err')
                guard, cleanup = read(name+'.guard').decode().strip(), read(name+'.cleanup').decode().strip()
                records = qualify_case(case, m['identities'][identity], data,
                                       statuses[name], guard, stderr, cleanup)
                assert recorded[name] == dict(name=name, identity=identity, exit=statuses[name],
                    stdout_hex=data.hex(), stderr='', watchdog=guard=='1', cleanup=cleanup)
                total += len(records)
                timed += guard == '1'
                observations.append(dict(name=name, exit=statuses[name], watchdog=guard=='1',
                                         roles=[r[2] for r in records], stdout_hex=data.hex()))
    assert total == 200 and timed == 24
    reference = dict(schema=1, manifest=m, observations=observations)
    report = dict(schema=1, status='passed', scope='original IRIX reference only; no NetBSD sproc implementation',
                  run=str(directory.relative_to(ROOT)), executions=112, records=total,
                  checked_words=total*64, watchdog_groups=timed, groups_absent=112,
                  clean_shutdown=True, emulator_sha256=run['emulator_sha256'],
                  firmware_sha256=run['firmware_sha256'],
                  hashes={str(f.relative_to(ROOT)): sha(f) for f in [directory/'result.json', archive,
                          ROOT/'scripts/qualify-irix-sproc.py', ROOT/'scripts/probe-irix-reference-sproc.py']},
                  observations=[{k: v for k, v in o.items() if k != 'stdout_hex'} for o in observations])
    if a.reference_output:
        a.reference_output.write_text(json.dumps(reference, indent=2)+'\n')
        report['reference_sha256'] = sha(a.reference_output)
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print('112 executions; 200 records / 12800 words; 24 bounded watchdogs; all groups absent')


if __name__ == '__main__':
    main()
