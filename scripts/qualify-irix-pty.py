#!/usr/bin/env python3
"""Qualify PTY interface records against the original oracle and explicit policy."""
import argparse
import hashlib
import importlib.util
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/filename)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+', type=Path)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--export-reference', type=Path)
    a = p.parse_args()
    contract = module('contract', 'irix-pty-records.py')
    ref = json.loads((a.reference/'result.json').read_text())
    assert ref['status'] == 'observed' and ref['clean_shutdown']
    assert ref['harness_sha256'] == sha(ROOT/'scripts/probe-irix-reference-pty-records.py')
    assert ref['decoder_sha256'] == sha(ROOT/'scripts/probe-irix-runtime.py')
    manifest = ref['manifest']
    for path, h in manifest['sources'].items():
        assert sha(ROOT/path) == h
    cases = {c['name']: c for c in manifest['cases']}
    names = {c['name']+'-'+str(i) for c in cases.values() for i in c['identities']}
    oracle = {o['name']: o for o in ref['observations']}
    assert len(oracle) == len(ref['observations']) and set(oracle) == names

    def checked_words(name, data):
        case_name, identity = name.rsplit('-', 1)
        w = struct.unpack('>21I', data)
        c = cases[case_name]
        assert w[:2] == (0x58505459, c['symbols']['CASE'])
        assert w[3] == 0xfeedface and w[4] in [0, 1]
        assert w[11:15] == tuple(manifest['identities'][int(identity)])
        assert w[15:17] == (0xa5a5a5a5, 0x5a5a5a5a)
        assert w[17:] == tuple(c['symbols'][k] for k in ['COMMAND', 'TIMEOUT', 'LENGTH', 'DATA'])
        return w

    for name, o in oracle.items():
        assert not o['exit'] and not o['stderr']
        checked_words(name, bytes.fromhex(o['stdout_hex']))
    report = dict(schema=1, status='qualified-subset', reference_directory=str(a.reference),
                  reference_result_sha256=sha(a.reference/'result.json'), reference_checks=len(names),
                  checks=0, controls=0, runs=[], fixture_files=manifest['files'], identities=manifest['identities'])
    seen = set()
    for d in a.runs:
        r = json.loads((d/'result.json').read_text())
        key = r['kernel_abi'], r['mode']
        assert key not in seen
        seen.add(key)
        assert r['status'] == 'observed-uncompared' and r['clean_shutdown'] and not r['failures']
        assert r['manifest'] == manifest
        for path, h in r['sources'].items():
            assert sha(ROOT/path) == h
        pin = 'o32-baseline.json' if key[0] == 'o32' else 'baseline.json'
        assert r['pin'] == json.loads((ROOT/'lab/irix-pty'/pin).read_text())
        want = {n for n in names if key[0] == 'lp64' or n.startswith('o32-')}
        assert len(r['observations']) == len(want) and {o['name'] for o in r['observations']} == want
        policies = []
        for o in r['observations']:
            name = o['name']
            checked_words(name, bytes.fromhex(o['record_hex']))
            c = cases[name.rsplit('-', 1)[0]]
            expected, policy = contract.expected(c, bytes.fromhex(oracle[name]['stdout_hex']))
            assert o['record_hex'] == expected.hex(), (name, o['record_hex'], expected.hex())
            assert o['expected_hex'] is None and o['passed'] is None and o['contract_policy'] is None
            actual = o['actual']
            assert actual == dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stdout=actual['stdout'], stderr='')
            if policy:
                policies.append(dict(name=name, policy=policy, irix=oracle[name]['stdout_hex'],
                                     netbsd=expected.hex(), differs=oracle[name]['stdout_hex'] != expected.hex()))
        control_names = {(phase, uid, name) for phase in ['before', 'after'] for uid in [0, 1234]
                         for name in (['native-o32', 'vendor-asa', 'vendor-echo'] if key[0] == 'lp64' else ['native-o32', 'vendor-asa'])}
        assert len(r['controls']) == len(control_names)
        assert {(c['phase'], c['uid'], c['name']) for c in r['controls']} == control_names
        for c in r['controls']:
            code, text = {'native-o32': (37, 'XIRI_ABI_PROBE\n'), 'vendor-asa': (0, 'XIRI_VENDOR_O32\n'),
                          'vendor-echo': (0, 'XIRI_VENDOR_N32\n')}[c['name']]
            assert c['actual'] == dict(errno_bytes=0, errno=0, exit=code, signal=0, killed=0, stdout=text, stderr='')
        differing = sum(x['differs'] for x in policies)
        report['checks'] += len(want)
        report['controls'] += len(control_names)
        report['runs'].append(dict(directory=str(d), kernel_abi=key[0], mode=key[1], checks=len(want),
            controls=len(control_names), clean_shutdown=True, result_sha256=sha(d/'result.json'),
            oracle_identical_records=len(want)-differing, oracle_different_records=differing,
            contract_policy_cases=policies, sources=r['sources']))
    assert seen == {('lp64', 'ci'), ('lp64', 'ordinary'), ('o32', 'ci')}
    report['contract_sha256'] = sha(ROOT/'scripts/irix-pty-records.py')
    report['qualifier_sha256'] = sha(Path(__file__))
    if a.export_reference:
        exported = dict(schema=1, description='Original IRIX 6.5.22m PTY interface records; empty supplementary groups',
                        reference_directory=str(a.reference), reference_result_sha256=sha(a.reference/'result.json'),
                        files=manifest['files'], identities=manifest['identities'], sources=manifest['sources'], observations=ref['observations'])
        a.export_reference.write_text(json.dumps(exported, indent=2)+'\n')
        report['exported_reference_sha256'] = sha(a.export_reference)
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(report['checks'], 'PTY interface checks qualified;', report['controls'], 'native/vendor controls')


if __name__ == '__main__':
    main()
