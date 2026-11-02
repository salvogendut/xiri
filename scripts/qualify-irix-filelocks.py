#!/usr/bin/env python3
"""Qualify retained raw lock observations without rerunning the guests."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('records',ROOT/'scripts/irix-filelock-records.py')
records=importlib.util.module_from_spec(spec);spec.loader.exec_module(records)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--original-harness',type=Path)
    p.add_argument('--output',required=True,type=Path)
    args=p.parse_args();summaries=[]
    for run in args.runs:
        r=json.loads((run/'result.json').read_text())
        assert r['status'] in ['passed','different'] and r['clean_shutdown']
        o32=r['kernel_abi']=='o32'
        pin=ROOT/'lab/irix-filelocks'/('o32-baseline.json' if o32 else 'baseline.json')
        assert r['pin']==json.loads(pin.read_text())
        for source,h in r['sources'].items():
            source_path=ROOT/source
            if source=='scripts/probe-irix-filelocks.py' and args.original_harness:
                source_path=args.original_harness
            assert sha(source_path)==h, source
        total=0;setup=[]
        for kind,suite in r['suites'].items():
            oracle=ROOT/'lab/irix-filelocks'/('reference.json' if kind=='filelocks' else 'behavior-reference.json')
            assert sha(oracle)==suite['reference_sha256']
            ref=json.loads(oracle.read_text())
            cases={c['name']:c for c in ref['cases'] if not o32 or c['abi']=='o32'}
            expected={o['name']:bytes.fromhex(o['stdout_hex']) for o in ref['observations']}
            assert {o['name'] for o in suite['observations']}=={n+'-'+str(uid) for n in cases for uid in [0,1234]}
            for o in suite['observations']:
                case=cases[o['name'].rsplit('-',1)[0]]
                comparison=records.compare(case,bytes.fromhex(o['record_hex']),expected[o['name']])
                assert comparison['passed'],(kind,o['name'])
                if comparison['documented_setup_differences']:setup.append(o['name'])
                total+=1
        assert len(r['interop'])==(4 if o32 else 8)
        assert all(x['stdout']=='native/IRIX lock interoperability passed\n' and
                   not any(x[k] for k in ['exit','signal','killed','errno','stderr']) for x in r['interop'].values())
        assert len(r['controls'])==(8 if o32 else 12)
        summaries.append(dict(run=str(run),result_sha256=sha(run/'result.json'),
            pin=r['pin'],records=total,interop=len(r['interop']),controls=len(r['controls']),
            documented_directory_setup_differences=setup,clean_shutdown=True))
    report=dict(status='qualified',runs=summaries,qualifier_sha256=sha(Path(__file__)),
        comparator_sha256=sha(ROOT/'scripts/irix-filelock-records.py'))
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Qualified',sum(x['records'] for x in summaries),'lock records and',sum(x['interop'] for x in summaries),'native/IRIX interoperability executions')

if __name__=='__main__':main()
