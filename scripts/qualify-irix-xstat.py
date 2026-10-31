#!/usr/bin/env python3
"""Recheck saved xstat runs and emit a compact qualification report."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('records',ROOT/'scripts/irix-xstat-records.py')
records=importlib.util.module_from_spec(spec);spec.loader.exec_module(records)

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs=3,type=Path,help='LP64 CI, LP64 ordinary and o32 CI run directories')
    p.add_argument('--transport-runs',nargs=2,type=Path,required=True)
    p.add_argument('--select-run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    ts=importlib.util.spec_from_file_location('tcp',ROOT/'scripts/probe-irix-tcp.py');tcp=importlib.util.module_from_spec(ts);ts.loader.exec_module(tcp)
    lab=ROOT/'lab/irix-xstat';oracle=json.loads((lab/'reference.json').read_text())
    records.validate_reference(oracle['cases'],oracle['observations'])
    refs={o['name']:bytes.fromhex(o['stdout_hex']) for o in oracle['observations']}
    normal=dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout='',stderr='')
    summary={'schema':1,'description':'Measured IRIX xstat subset and staged Toolchest observations','status':'qualified-subset','source_revision':json.loads((lab/'baseline.json').read_text())['source_revision'],'source_branch':'xiri/irix-xstat','reference_cases':len(refs),'window_or_event_loop_qualified':False,'focused_runs':[],'regression_runs':[],'limits':json.loads((lab/'abi.json').read_text())['unqualified'],'native_differences':json.loads((lab/'abi.json').read_text())['native_differences'],'input_metadata_hashes':{str(x.relative_to(ROOT)):digest(x) for x in [lab/'baseline.json',lab/'o32-baseline.json',lab/'abi.json',lab/'reference.json',lab/'desktop.json',ROOT/'lab/irix-desktop/manifest.json',ROOT/'lab/irix-reference/manifest.json']}}
    seen=set()
    for directory in args.runs:
        directory=directory.resolve();path=directory/'result.json';r=json.loads(path.read_text())
        pair=r['kernel_abi'],r['mode'];assert pair not in seen;seen.add(pair)
        assert r['status']=='observed' and r['clean_shutdown'] and not r['failures']
        pin=json.loads((lab/('baseline.json' if pair[0]=='lp64' else 'o32-baseline.json')).read_text());assert r['pin']==pin
        assert r['reference_sha256']==digest(lab/'reference.json')
        assert r['manifest']['files']==oracle['files']
        for name,sha in r['sources'].items():
            # The transport CLI gained an explicit expectation override during
            # these runs. Re-decode its only used helper from raw traces below.
            if name!='scripts/probe-irix-tcp.py':assert digest(ROOT/name)==sha,name
        cases=[c for c in oracle['cases'] if pair[0]=='lp64' or c['abi']=='o32']
        actual={o['name']:o for o in r['observations']}
        assert len(actual)==2*len(cases)==len(r['observations'])
        for uid in [0,1234]:
            for c in cases:
                n=c['name']+'-'+str(uid);o=actual[n]
                native=r['native_metadata']['observations'][str(r['native_metadata']['paths'].index(c['path']))+'-'+str(uid)]
                check=records.compare(c,uid,bytes.fromhex(o['record_hex']),refs[n],native)
                assert check['passed'] and o['passed'],n
                assert o['actual']==dict(normal,stdout=o['actual']['stdout']),n
        tc=[]
        for o in r['toolchest']:
            raw=(directory/(o['name']+'.kdump')).read_text()
            assert tcp.trace_records(raw,'irix_o32',True)==o['calls']
            assert tcp.trace_records(raw,'irix_ret',True)==o['returns']
            expected=dict(normal,exit=1,stderr='./vendor-toolchest: Cannot open configuration file /usr/lib/X11/system.chestrc\n') if o['name'].startswith('library-') else dict(normal,exit=-1,signal=11)
            assert o['actual']==expected and o['passed']
            assert not any(x.startswith('syscall=1158 ') and 'v0=0x59 ' in x for x in o['returns'])
            if o['name'].startswith('resources-'):
                assert any(x.startswith('syscall=1160 ') and 'v0=0x59 ' in x for x in o['returns'])
                assert any(x.startswith('syscall=1003 ') and 'a2=0xffffffff ' in x for x in o['calls'])
            errors=Counter();success=Counter()
            for line in o['returns']:
                words=dict(w.split('=',1) for w in line.split() if '=' in w)
                call=words['syscall']
                if words.get('a3')=='0':success[call]+=1
                else:errors[call+':'+words.get('v0','?')]+=1
            tc.append({'name':o['name'],'actual':o['actual'],'successful_calls':dict(success),'errors':dict(errors),'window_tree':o['windows']})
        if pair[0]=='lp64':assert len(tc)==12 and r['native_x11_before'] and r['native_x11_after']
        else:assert not tc
        summary['focused_runs'].append({'kernel_abi':pair[0],'mode':pair[1],'status':'passed','cases':len(actual),'native_controls':len(r['controls']),'toolchest':tc,'clean_shutdown':True,'directory':str(directory.relative_to(ROOT)),'result_sha256':digest(path),'execution_sources':r['sources']})
    assert seen=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    for directory in args.transport_runs+[args.select_run]:
        directory=directory.resolve();path=directory/'result.json';r=json.loads(path.read_text())
        assert r['clean_shutdown'] and r['status'] in ['passed','observed']
        assert r['pin']['source_revision']==summary['source_revision']
        if directory==args.select_run.resolve():
            assert r['kernel_checkpoint']=='xstat' and r['fixtures_only'] and not r['failures']
            assert len(r['observations'])==552 and all(x['passed'] for x in r['observations'])
            count=len(r['observations']);kind='select'
        else:
            assert r['status']=='passed' and r['kernel_checkpoint']=='xstat' and not r['x11']
            assert r['harness_sha256']==digest(ROOT/'scripts/probe-irix-tcp.py')
            if r['kernel_abi']=='lp64':assert r['expectations_sha256']==digest(lab/'desktop.json')
            count=len(r['observations']);kind='transport'
        summary['regression_runs'].append({'kind':kind,'kernel_abi':r['kernel_abi'],'mode':r['mode'],'status':'passed','cases':count,'clean_shutdown':True,'directory':str(directory.relative_to(ROOT)),'result_sha256':digest(path)})
    summary['qualifier_sha256']=digest(Path(__file__).resolve())
    summary['focused_cases']=sum(r['cases'] for r in summary['focused_runs'])
    args.output.write_text(json.dumps(summary,indent=2)+'\n')
    print(f"Qualified {summary['focused_cases']} xstat records; report: {args.output}")

if __name__=='__main__':main()
