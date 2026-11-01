#!/usr/bin/env python3
"""Qualify measured resource-limit layouts, native values, and loader regressions."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tomllib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('contract', ROOT / 'scripts/irix-rlimit-records.py')
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources(manifest):
    for path, digest in manifest['sources'].items():
        assert sha(ROOT/path) == digest, path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('runs',nargs='+',type=Path)
    args = parser.parse_args()
    original = json.loads((args.reference/'result.json').read_text())
    assert original['status'] == 'observed' and original['clean_shutdown']
    manifest = original['manifest']
    sources(manifest)
    assert original['harness_sha256'] == sha(ROOT/'scripts/probe-irix-reference-rlimit.py')
    cases = {c['name']:c for c in manifest['cases']}
    oracle = {o['name']:o for o in original['observations']}
    assert set(oracle) == {c['name']+'-'+str(i) for c in cases.values() for i in c['identities']}
    ref_records = []
    for c in cases.values():
        for identity in c['identities']:
            name = c['name']+'-'+str(identity)
            actual = oracle[name]
            assert actual['exit'] == 0 and not actual['stderr']
            data = bytes.fromhex(actual['stdout_hex'])
            queries = c['name'].rsplit('-',1)[0]+'-queries-'+str(identity)
            limits = contract.wide_limits(bytes.fromhex(oracle[queries]['stdout_hex']))
            if c['symbols']['KIND'] == 3:
                limits[1] = (0x123456789,0x23456789a)
            elif c['symbols']['KIND'] == 4:
                limits[1] = (0x80000001,0xf1234567)
            checked = contract.check(data,c,manifest['identities'][identity][0],4096,limits)
            ref_records.append(dict(name=name,limits=limits,**checked))
    report = dict(schema=1,status='passed',qualifier_sha256=sha(Path(__file__)),
        contract_sha256=sha(ROOT/'scripts/irix-rlimit-records.py'),
        reference=dict(directory=str(args.reference),result_sha256=sha(args.reference/'result.json'),
                       observations=ref_records,manifest=manifest,clean_shutdown=True),runs=[])
    coverage = set()
    for directory in args.runs:
        result = json.loads((directory/'result.json').read_text())
        assert result['status'] == 'observed-uncompared' and result['clean_shutdown']
        sources(result)
        assert result['manifest'] == manifest
        sources(result['loader_manifest'])
        config = tomllib.loads((directory/'iris.toml').read_text())
        assert config['ci'] == (result['mode'] == 'ci')
        pin = json.loads((ROOT/'lab/irix-rlimit'/
            ('o32-baseline.json' if result['kernel_abi'] == 'o32' else 'baseline.json')).read_text())
        assert result['pin'] == pin and not pin['source_dirty']
        coverage.add((result['kernel_abi'],result['mode']))
        assert result['seed_result_sha256'] == sha(ROOT/result['seed']/'result.json')
        expected = {(c['name'],uid,policy) for c in cases.values() if not c['reference_only'] and
                    (result['kernel_abi']=='lp64' or c['abi']=='o32') for uid in [0,1234]
                    for policy in ([0,1,2] if c['symbols']['KIND']==0 else [0,1])}
        observed = {(o['case'],o['uid'],o['policy']) for o in result['observations']}
        assert observed == expected and len(result['observations']) == len(expected)
        checked = []
        for observation in result['observations']:
            c = cases[observation['case']]
            actual = observation['actual']
            assert all(actual[k] == 0 for k in ['errno_bytes','errno','exit','signal','killed'])
            lines = re.findall(r'^NATIVE_LIMIT resource=(\d+) soft=(\d+) hard=(\d+)$',actual['stderr'],re.M)
            assert len(lines)==9 and len(actual['stderr'].splitlines())==9
            limits = {int(r):(int(s),int(h)) for r,s,h in lines}
            assert set(limits)==set(range(9))
            if observation['policy']:
                assert limits[5]==(37,99) and limits[8]==(17,41)
                assert limits[1] == ((0x80000001,0xf1234567) if observation['policy']==2 else
                                     (0x123456789,0x23456789a))
            data = bytes.fromhex(actual['stdout_hex'])
            check = contract.check(data,c,observation['uid'],pin['page_bytes'],limits)
            checked.append(dict(name=observation['name'],uid=observation['uid'],policy=observation['policy'],
                                native_limits=limits,**check))
        loader = result['loader_manifest']['cases'] if result['kernel_abi']=='lp64' else []
        assert {x['name'] for x in result['loader']} == {c['name']+'-'+str(uid) for c in loader for uid in [0,1234]}
        assert len(result['loader']) == len(loader)*2
        success = dict(errno_bytes=0,errno=0,exit=37,signal=0,killed=0,
                       stdout_hex=b'XIRI_ABI_PROBE\n'.hex(),stderr='')
        rejection = dict(success,errno_bytes=4,errno=8,exit=126,stdout_hex='')
        loader_expected = {c['name']+'-'+str(uid):c['expect']
                           for c in loader for uid in [0,1234]}
        for observation in result['loader']:
            expectation = loader_expected[observation['name']]
            assert observation['expect'] == expectation
            assert observation['actual'] == (success if expectation=='output' else rejection),observation
        assert len(result['controls'])==8
        assert {(c['phase'],c['uid'],c['program']) for c in result['controls']} == {
            (phase,uid,program) for phase in ['before','after'] for uid in [0,1234]
            for program in ['native-o32','vendor-asa']}
        for control in result['controls']:
            native = control['program']=='native-o32'
            assert control['actual'] == dict(errno_bytes=0,errno=0,exit=37 if native else 0,
                signal=0,killed=0,stdout='XIRI_ABI_PROBE\n' if native else '',stderr='')
        report['runs'].append(dict(directory=str(directory),result_sha256=sha(directory/'result.json'),
            mode=result['mode'],kernel_abi=result['kernel_abi'],pin=pin,sources=result['sources'],
            observations=checked,loader=result['loader'],loader_manifest=result['loader_manifest'],
            controls=result['controls'],clean_shutdown=True))
    assert coverage=={('lp64','ci'),('lp64','ordinary'),('o32','ci')} and len(report['runs'])==3
    report['record_counts'] = dict(reference=sum(x['records'] for x in ref_records),
        netbsd=sum(x['records'] for r in report['runs'] for x in r['observations']),
        loader_executions=sum(len(r['loader']) for r in report['runs']))
    report['limits'] = [
        'Resource values are actual NetBSD limits, not fixed IRIX defaults; PTHREAD maps to native NTHR.',
        'No foreign setters or pthread creation/synchronization are implemented by this checkpoint.',
        'Queries expose native policy; native NTHR accounting is not a claim of equivalent IRIX thread accounting.',
        'The executable change accepts declared 4 KiB alignment only for page-aligned RW data; half-page addresses remain rejected.',
        'Application startup and window interaction are separately observed; no complete-desktop acceptance here.',
    ]
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Resource-limit and loader checks passed:',report['record_counts'])


if __name__ == '__main__':
    main()
