#!/usr/bin/env python3
"""Recheck desktop ABI records from all three clean guest runs."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/name)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs=3, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    checkers = {name:module(filename) for name,filename in {
        'lxstat':'irix-lxstat-records.py', 'xstat':'irix-xstat-records.py',
        'desktop-queries':'irix-desktop-query-records.py',
        'poll':'irix-poll-records.py', 'dirent':'irix-dirent-records.py'}.items()}
    report = dict(schema=1, status='desktop-interfaces-qualified',
        qualifier_sha256=sha(Path(__file__).resolve()), runs=[], observations=0, controls=0,
        original_pipe_readiness_differences=0,
        limits=['Native pipe poll readiness retains the documented POLLOUT/POLLRDNORM differences.',
                'Directory padding is unspecified; native prevalidation avoids IRIX partial-byte writes on unmapped spans.',
                'Inodes, directory ordering/cookies and page sizes come from the native host.',
                'This syscall matrix alone does not qualify desktop services or application actions.'])
    modes = set()
    for run in args.runs:
        result = json.loads((run/'result.json').read_text())
        assert result['status']=='passed' and result['clean_shutdown'] and not result['failures']
        key = (result['kernel_abi'], result['mode']); assert key not in modes; modes.add(key)
        pin = json.loads((ROOT/'lab/irix-lxstat'/('o32-baseline.json' if key[0]=='o32' else 'baseline.json')).read_text())
        assert result['pin']==pin
        for path, digest in result['sources'].items(): assert sha(ROOT/path)==digest, path
        text = (run/'fixtures.txt').read_text()
        blocks = dict(re.findall(r'^STARTCASE (\S+)\n(.*?)^ENDCASE \1$', text, re.M|re.S))
        counts = {}; differences = 0
        assert set(result['suites']) == set(checkers)
        for kind,checker in checkers.items():
            oracle_path=ROOT/('lab/irix-'+kind+'/reference.json')
            oracle=json.loads(oracle_path.read_text()); suite=result['suites'][kind]
            assert suite['reference_sha256']==sha(oracle_path)
            checker.validate_reference(oracle['cases'], oracle['observations'])
            cases=[c for c in oracle['cases'] if key[0]!='o32' or c['abi']=='o32']
            paths=list(dict.fromkeys(c['path'] for c in cases))
            observations={o['name']:o for o in suite['observations']}
            assert len(observations)==len(cases)*2
            reference={o['name']:bytes.fromhex(o['stdout_hex']) for o in oracle['observations']}
            for case in cases:
                for uid in [0,1234]:
                    name=case['name']+'-'+str(uid); observation=observations[name]
                    data=bytes.fromhex(observation['record_hex'])
                    block=blocks[kind+'-'+name]
                    assert 'STDOUT bytes='+str(len(data))+' hex='+data.hex()+'\n' in block
                    actual=observation['actual']; assert actual==dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout=actual['stdout'],stderr='')
                    if kind=='desktop-queries':
                        assert data==checker.expected(case,uid,native=True,page_bytes=pin['page_bytes']), name
                    elif kind=='poll':
                        assert data==checker.expected(case,uid,native=True), name
                        differences+=data!=checker.expected(case,uid)
                    else:
                        native=suite['native_metadata'][str(paths.index(case['path']))+'-'+str(uid)]
                        assert checker.compare(case,uid,data,reference[name],native)['passed'],name
            counts[kind]=len(observations)
        controls=result['controls']; assert len(controls)==(8 if key[0]=='o32' else 12)
        for control in controls:
            actual=control['actual']; name=control['name']
            native=name.endswith('native-o32')
            stdout='XIRI_ABI_PROBE\n' if native else 'XIRI_VENDOR_O32\n' if name.endswith('vendor-asa') else 'XIRI_VENDOR_N32\n'
            assert actual==dict(errno_bytes=0,errno=0,exit=37 if native else 0,signal=0,killed=0,stdout=stdout,stderr='')
        report['runs'].append(dict(path=str(run),mode=key[1],kernel_abi=key[0],pin=pin,
            result_sha256=sha(run/'result.json'),fixtures_sha256=sha(run/'fixtures.txt'),
            counts=counts,controls=len(controls),original_pipe_readiness_differences=differences))
        report['observations']+=sum(counts.values()); report['controls']+=len(controls)
        report['original_pipe_readiness_differences']+=differences
    assert modes=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(report['observations'],'records and',report['controls'],'controls qualified')


if __name__=='__main__': main()
