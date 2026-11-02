#!/usr/bin/env python3
"""Collect checked high-address mapping matrices and original IRIX differences."""
import argparse
import importlib.util
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('matrix', ROOT/'scripts/probe-irix-elfmap-high.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs=3, type=Path)
    p.add_argument('--reference', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    ref = json.loads((a.reference/'result.json').read_text())
    assert ref['status']=='observed' and ref['clean_shutdown']
    oracle = {o['name']:o for o in ref['observations']}
    assert len(oracle)==280
    fixtures = ROOT/'.work/irix-elfmap-high/probes'
    manifest = json.loads((fixtures/'manifest.json').read_text())
    assert manifest['files']==ref['manifest']['files']
    assert all(m.p.sha256(fixtures/f)==info['sha256'] for f,info in manifest['files'].items())
    assert all(m.p.sha256(ROOT/f)==h for f,h in manifest['sources'].items())
    cases = {c['name']:c for c in manifest['cases']}; assert len(cases)==70
    layouts = {name:[struct.unpack_from('>8I', (fixtures/c['input']).read_bytes(), 52+i*32)
                    for i in range(2)] for name,c in cases.items()}
    # Positive high-address cases execute mapped code, check data/BSS and
    # preserve collision sentinels on the original OS as well as NetBSD.
    for name,o in oracle.items():
        c = cases[name.split('-',1)[1].rsplit('-',1)[0]]
        record = m.rt.elfmap_record(bytes.fromhex(o['stdout_hex']))
        assert record['magic']==0x58494531 and record['case']==c['number']
        if c['number']>=58:
            assert o['exit']==(139 if c['netbsd']['signal'] else 0), (name,o)
            assert record['a3']==0 and record['v1']==0xfeedface, (name,record)
            assert record['checks']==c['netbsd']['checks'], (name,record)
    report = dict(schema=1, status='qualified', reference_directory=str(a.reference),
                  reference_result_sha256=m.p.sha256(a.reference/'result.json'),
                  reference_executions=280, cases=70, runs=[], checks=0, controls=0,
                  qualifier_sha256=m.p.sha256(Path(__file__)),
                  limitations=[
                      'The four original no-bounded-space cases fail while establishing the 960 MiB occupant; they do not measure ELFMAP.',
                      'IRIX relocates the two above-user-limit requests; this bounded NetBSD subset rejects them with ENOEXEC.',
                      'NetBSD relocates the near-2GiB request because of its compat stack reservation; IRIX uses the requested address.',
                      'The first two native runs exposed an incorrect near-2GiB checker expectation; they are preserved and excluded.'])
    seen = set()
    for d in a.runs:
        r = json.loads((d/'result.json').read_text())
        assert r['status']=='passed' and r['clean_shutdown'] and r['manifest']==manifest
        key = (r['kernel_abi'],r['mode']); assert key not in seen; seen.add(key)
        pin = ROOT/'lab/irix-elfmap-high'/('o32-baseline.json' if key[0]=='o32' else 'baseline.json')
        assert r['pin']==json.loads(pin.read_text()) and not r['pin']['source_dirty']
        assert all(m.p.sha256(ROOT/f)==h for f,h in r['sources'].items())
        assert len(r['observations'])==(140 if key[0]=='o32' else 280)
        assert len(r['controls'])==(8 if key[0]=='o32' else 12)
        differences=[]
        for o in r['observations']:
            c=cases[o['name'].split('-',1)[1].rsplit('-',1)[0]]
            actual=o['actual']; sig=c['netbsd']['signal']
            assert actual['errno_bytes']==0 and actual['errno']==0 and actual['exit']==(-1 if sig else 0) and actual['signal']==sig and not actual['killed'] and not actual['stderr']
            record=m.rt.elfmap_record(bytes.fromhex(o['record_hex'])); assert record==o['record']
            layout=layouts[c['name']]
            expected=dict(c,block=layout[0][2]) if c.get('native_collision') else c
            m.qualify.expected(expected,record,layout)
            original=m.rt.elfmap_record(bytes.fromhex(oracle[o['name']]['stdout_hex']))
            diff={k:dict(netbsd=v,irix=original[k]) for k,v in record.items() if v!=original[k]}
            if diff:differences.append(dict(name=o['name'],fields=diff))
        report['runs'].append(dict(directory=str(d), result_sha256=m.p.sha256(d/'result.json'),
                                  kernel_abi=key[0], mode=key[1], pin=r['pin'], clean_shutdown=True,
                                  observations=len(r['observations']), controls=len(r['controls']),
                                  oracle_differences=differences))
        report['checks']+=len(r['observations']); report['controls']+=len(r['controls'])
    assert seen=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(report['checks'],'mapping checks and',report['controls'],'controls qualified')


if __name__ == '__main__':
    main()
