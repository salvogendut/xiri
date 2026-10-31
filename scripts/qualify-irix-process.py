#!/usr/bin/env python3
"""Qualify the process matrix against original IRIX and native observations."""
import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', type=Path, nargs='+')
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--export-reference', type=Path)
    a = p.parse_args()
    spec = importlib.util.spec_from_file_location('contract', ROOT/'scripts/irix-process-records.py')
    contract = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(contract)
    ref = json.loads((a.reference/'result.json').read_text())
    assert ref['status'] == 'observed' and ref['clean_shutdown'] and ref['scope'] == 'full'
    assert ref['harness_sha256'] == sha(ROOT/'scripts/probe-irix-reference-process.py')
    assert ref['decoder_sha256'] == sha(ROOT/'scripts/probe-irix-runtime.py')
    manifest = ref['manifest']
    for path, digest in manifest['sources'].items():
        assert sha(ROOT/path) == digest, path
    cases = {c['name']: c for c in manifest['cases']}
    names = {c['name']+'-'+str(i) for c in cases.values() for i in c['identities']}
    oracle = {o['name']: o for o in ref['observations']}
    assert len(oracle) == len(ref['observations']) == 944 and set(oracle) == names
    expected = {}
    exported = []
    for name, o in oracle.items():
        assert o['exit'] == 0 and not o['stderr']
        cn, identity = name.rsplit('-', 1)
        ids = manifest['identities'][int(identity)]
        raw = bytes.fromhex(o['stdout_hex'])
        expected[name] = contract.expected(cases[cn], raw, ids)
        normalized = contract.canonical(cases[cn], raw, ids, oracle=True)
        exported.append(dict(name=name, raw_sha256=hashlib.sha256(raw).hexdigest(),
            canonical_hex=b''.join(struct.pack('>64I', *w) for w in normalized).hex()))
    report = dict(schema=1, status='qualified-subset', reference_directory=str(a.reference),
        reference_result_sha256=sha(a.reference/'result.json'), reference_checks=len(names),
        checks=0, records=0, controls=0, native_process_controls=0, runs=[],
        sources=manifest['sources'], fixture_files=manifest['files'], identities=manifest['identities'])
    seen = set()
    for directory in a.runs:
        r = json.loads((directory/'result.json').read_text())
        key = r['kernel_abi'], r['mode']
        assert key not in seen
        seen.add(key)
        assert r['status'] == 'observed-uncompared' and r['clean_shutdown'] and r['scope'] == 'full'
        assert r['manifest'] == manifest
        for path, digest in r['sources'].items():
            assert sha(ROOT/path) == digest, path
        pin = 'o32-baseline.json' if key[0] == 'o32' else 'baseline.json'
        assert r['pin'] == json.loads((ROOT/'lab/irix-process'/pin).read_text())
        want = {n for n in names if key[0] == 'lp64' or n.startswith('o32-')}
        assert len(r['observations']) == len(want) and {o['name'] for o in r['observations']} == want
        policies, differing, count = {}, 0, 0
        for o in r['observations']:
            name = o['name']
            cn, identity = name.rsplit('-', 1)
            c, ids = cases[cn], manifest['identities'][int(identity)]
            actual = contract.canonical(c, bytes.fromhex(o['actual']['stdout_hex']), ids, actual=o['actual'])
            exp, policy = expected[name]
            assert actual == exp, (name, [(ri, j, x, y) for ri, (ew, aw) in enumerate(zip(exp, actual))
                                         for j, (x, y) in enumerate(zip(ew, aw)) if x != y])
            original = contract.canonical(c, bytes.fromhex(oracle[name]['stdout_hex']), ids, oracle=True)
            differing += actual != original
            count += c['records']
            for item in policy:
                policies[item] = policies.get(item, 0) + 1
        control_names = {(phase, uid, name) for phase in ['before', 'after'] for uid in [0, 1234]
            for name in (['native-o32', 'vendor-asa', 'vendor-echo'] if key[0] == 'lp64' else ['native-o32', 'vendor-asa'])}
        assert len(r['controls']) == len(control_names)
        assert {(c['phase'], c['uid'], c['name']) for c in r['controls']} == control_names
        for c in r['controls']:
            code, output = {'native-o32': (37, 'XIRI_ABI_PROBE\n'), 'vendor-asa': (0, 'XIRI_VENDOR_O32\n'),
                            'vendor-echo': (0, 'XIRI_VENDOR_N32\n')}[c['name']]
            assert c['actual'] == dict(errno_bytes=0, errno=0, exit=code, signal=0, killed=0, stdout=output, stderr='')
        controls = r['native_process_controls']
        assert len(controls) == 8 and {(c['phase'], c['uid'], c['kind']) for c in controls} == {
            (phase, uid, kind) for phase in ['before', 'after'] for uid in [0, 1234] for kind in [0, 1]}
        for c in controls:
            obs = c['actual']
            assert {k: obs[k] for k in ['exit', 'signal', 'timeout', 'valid', 'released', 'group_absent']} == dict(exit=0, signal=0, timeout=0, valid=1, released=1, group_absent=1)
            assert not obs['stderr_hex']
            data = bytes.fromhex(obs['stdout_hex'])
            assert len(data) == (768 if c['kind'] else 256)
            rows = sorted([struct.unpack('>64I', data[i:i+256]) for i in range(0, len(data), 256)], key=lambda w: w[55])
            assert [w[55] for w in rows] == ([0, 1, 2] if c['kind'] else [0])
            assert len(obs['snapshots']) == (2 if c['kind'] else 1)
            assert sorted(s['role'] for s in obs['snapshots']) == ([0, 1] if c['kind'] else [0])
            for s in obs['snapshots']:
                w = rows[s['role']]
                assert w[0] == contract.MAGIC and w[56:60] == (c['uid'],)*4
                assert [s['pid'], s['ppid']] == list(w[60:62])
                assert s['pgid'] == obs['pid'] and s['ids'] == [c['uid']]*4 and s['groups'] == 0
                assert s['mask'] == contract.native_mask(0x20000 if s['role'] else 0x28000)
            assert rows[0][60] == obs['pid']
            if c['kind']:
                assert rows[1][61] == rows[0][60] and rows[2][60:62] == rows[0][60:62]
                assert rows[1][33] == 0x87654321 and rows[1][47] == 65
                assert rows[2][51:53] == (66, 0x12345678) and rows[2][63] == rows[1][60]
        report['checks'] += len(want)
        report['records'] += count
        report['controls'] += len(control_names)
        report['native_process_controls'] += len(controls)
        report['runs'].append(dict(directory=str(directory), kernel_abi=key[0], mode=key[1],
            checks=len(want), records=count, canonical_oracle_equal=len(want)-differing,
            canonical_oracle_different=differing, policy_counts=policies, controls=len(control_names),
            native_process_controls=len(controls), clean_shutdown=True,
            result_sha256=sha(directory/'result.json'), sources=r['sources'], pin=r['pin']))
    assert seen == {('lp64', 'ci'), ('lp64', 'ordinary'), ('o32', 'ci')}
    report['contract_sha256'] = sha(ROOT/'scripts/irix-process-records.py')
    report['qualifier_sha256'] = sha(Path(__file__))
    if a.export_reference:
        payload = dict(schema=1, description='IRIX 6.5.22m process records with checked PID relationships canonicalized and undefined siginfo padding removed; raw data stays private',
            reference_directory=str(a.reference), reference_result_sha256=sha(a.reference/'result.json'),
            sources=manifest['sources'], files=manifest['files'], identities=manifest['identities'], observations=exported)
        a.export_reference.write_text(json.dumps(payload, indent=2)+'\n')
        report['exported_reference_sha256'] = sha(a.export_reference)
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(report['checks'], 'process cases;', report['records'], 'records;', report['controls'],
          'native/vendor controls;', report['native_process_controls'], 'native process controls')


if __name__ == '__main__':
    main()
