#!/usr/bin/env python3
"""Recheck saved fxstat runs, shared xstat regressions and Toolchest evidence."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent

def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/filename)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

NORMAL=dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout='',stderr='')

def checked_records(directory,kind,pins):
    directory=directory.resolve();r=json.loads((directory/'result.json').read_text())
    pair=r['kernel_abi'],r['mode'];assert r['pin']==pins[pair[0]]
    assert r['status']=='observed' and r['clean_shutdown'] and not r['failures']
    lab=ROOT/('lab/irix-'+kind);oracle=json.loads((lab/'reference.json').read_text())
    assert oracle['clean_shutdown']
    records=module(kind,'irix-'+kind+'-records.py')
    records.validate_reference(oracle['cases'],oracle['observations'])
    refs={o['name']:bytes.fromhex(o['stdout_hex']) for o in oracle['observations']}
    assert len(refs)==len(oracle['observations'])==len(oracle['cases'])*2
    assert all(o['exit']==0 and not o['stderr'] for o in oracle['observations'])
    assert r['reference_sha256']==digest(lab/'reference.json')
    assert r['manifest']['files']==oracle['files']
    for name,sha in r['sources'].items():assert digest(ROOT/name)==sha,name
    for name,sha in r['manifest']['sources'].items():assert digest(ROOT/name)==sha,name
    cases=[c for c in oracle['cases'] if pair[0]=='lp64' or c['abi']=='o32']
    actual={o['name']:o for o in r['observations']}
    assert len(actual)==2*len(cases)==len(r['observations'])
    for uid in [0,1234]:
        for c in cases:
            name=c['name']+'-'+str(uid);o=actual[name]
            path=records.descriptor(c) if kind=='fxstat' else c['path']
            native=r['native_metadata']['observations'][str(r['native_metadata']['paths'].index(path))+'-'+str(uid)]
            assert records.compare(c,uid,bytes.fromhex(o['record_hex']),refs[name],native)['passed'],name
            assert o['passed'] and o['actual']==dict(NORMAL,stdout=o['actual']['stdout']),name
    assert len(r['controls'])==(12 if pair[0]=='lp64' else 8)
    executables=['native-o32','vendor-asa']+(['vendor-echo'] if pair[0]=='lp64' else [])
    assert {c['name'] for c in r['controls']}=={f'{phase}-{exe}-{uid}' for phase in ['before','after'] for exe in executables for uid in [0,1234]}
    for control in r['controls']:
        name=control['name']
        expected=dict(NORMAL,exit=37,stdout='XIRI_ABI_PROBE\n') if 'native-o32' in name else dict(NORMAL,stdout='XIRI_VENDOR_O32\n' if 'vendor-asa' in name else 'XIRI_VENDOR_N32\n')
        assert control['actual']==expected,name
    compact=dict(kind=kind,kernel_abi=pair[0],mode=pair[1],status='passed',cases=len(actual),controls=len(r['controls']),clean_shutdown=True,directory=str(directory.relative_to(ROOT)),result_sha256=digest(directory/'result.json'),execution_sources=r['sources'])
    return r,compact

def trace_metadata(raw,tcp):
    """Follow successful opens/reads/closes; publish counts, never resource bytes."""
    opened={};pending=None;paths=[];reads={};ioctls=[]
    for block in re.split(r'(?m)(?=^\s*\d+\s+\d+\s+\S+\s+(?:MISC|NAMI))',raw):
        for line in tcp.trace_records(block,'irix_o32',True):
            pending={k:int(v,0) for k,v in re.findall(r'(\w+)=(0x[0-9a-f]+|[0-9]+)',line)}
            if pending['syscall']==1000:
                pending=dict(syscall=pending['a0'],a0=pending['a1'],a1=pending['a2'],a2=pending['a3'])
            paths=[]
        paths+=re.findall(r'NAMI\s+"([^"]+)"',block)
        for line in tcp.trace_records(block,'irix_ret',True):
            ret={k:int(v,0) for k,v in re.findall(r'(\w+)=(0x[0-9a-f]+|[0-9]+)',line)}
            assert pending and pending['syscall']==ret['syscall']
            call=pending['syscall']
            if call==1005 and not ret['a3'] and paths:opened[ret['v0']]=paths[-1]
            if call==1003 and pending['a0'] in opened:
                path=opened[pending['a0']]
                reads.setdefault(path,[]).append(dict(requested=pending['a2'],returned=None if ret['a3'] else ret['v0'],error=ret['v0'] if ret['a3'] else 0))
            if call==1054:
                ioctls.append(dict(fd=pending['a0'],command=pending['a1'],output=pending['a2'],v0=ret['v0'],a3=ret['a3']))
            if call==1006 and not ret['a3']:opened.pop(pending['a0'],None)
            pending=None;paths=[]
    return dict(resource_reads={path:items for path,items in reads.items() if path in ['/emul/irix/usr/lib/X11/app-defaults/Toolchest','/emul/irix/usr/lib/X11/system.chestrc']},ioctls=ioctls)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs=3,type=Path,help='LP64 CI, LP64 ordinary, o32 CI fxstat runs')
    p.add_argument('--xstat-runs',nargs=3,type=Path,required=True)
    p.add_argument('--select-run',type=Path,required=True)
    p.add_argument('--transport-runs',nargs=2,type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();lab=ROOT/'lab/irix-fxstat'
    pins={abi:json.loads((lab/name).read_text()) for abi,name in [('lp64','baseline.json'),('o32','o32-baseline.json')]}
    abi=json.loads((lab/'abi.json').read_text());tcp=module('tcp','probe-irix-tcp.py')
    expected=json.loads((lab/'toolchest.json').read_text())
    report=dict(schema=1,description='Measured IRIX fxstat subset and staged Toolchest observations',status='qualified-subset',source_revision=pins['lp64']['source_revision'],source_branch='xiri/irix-fxstat',reference_cases=520,window_or_event_loop_qualified=False,focused_runs=[],regression_runs=[],limits=abi['unqualified'],native_differences=abi['native_differences'],fixture_limits=abi['fixture_limits'])
    wanted={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    for kind,dirs,key in [('fxstat',args.runs,'focused_runs'),('xstat',args.xstat_runs,'regression_runs')]:
        seen=set()
        for directory in dirs:
            r,item=checked_records(directory,kind,pins);pair=r['kernel_abi'],r['mode'];assert pair not in seen;seen.add(pair)
            if kind=='xstat':
                assert r['kernel_checkpoint']=='fxstat' and r['fixtures_only'] and not r['toolchest']
            else:
                captures=[]
                for o in r['toolchest']:
                    raw=(directory/(o['name']+'.kdump')).read_text()
                    assert tcp.trace_records(raw,'irix_o32',True)==o['calls']
                    assert tcp.trace_records(raw,'irix_ret',True)==o['returns']
                    stage=o['name'].split('-')[0];actual=dict(o['actual']);counters=None
                    if 'stderr_counter_pattern' in expected[stage]:
                        pattern=expected[stage]['stderr_counter_pattern']
                        matches=re.findall(pattern,actual['stderr']);assert len(matches)==1
                        sent,processed,events=map(int,matches[0]);assert sent>=processed>250 and events==0
                        counters=dict(requests=sent,processed=processed,events=events)
                        actual['stderr']=re.sub(pattern,expected[stage]['stderr_counter_replacement'],actual['stderr'])
                    assert actual==expected[stage]['actual'] and o['passed'],o['name']
                    assert digest(directory/(o['name']+'.xwd'))==o['frame_sha256']
                    if 'frame_sha256' in expected[stage]:assert o['frame_sha256']==expected[stage]['frame_sha256']
                    errors=Counter();success=Counter()
                    for line in o['returns']:
                        words=dict(w.split('=',1) for w in line.split() if '=' in w)
                        if words.get('a3')=='0':success[words['syscall']]+=1
                        else:errors[words['syscall']+':'+words.get('v0','?')]+=1
                    for call in expected[stage]['required_successes']:assert success[str(call)]>0
                    for call in [1158,1160]:assert not errors.get(str(call)+':0x59',0)
                    for fragment in expected[stage].get('required_trace_fragments',[]):assert fragment in raw
                    metadata=trace_metadata(raw,tcp);reads=metadata['resource_reads'];boundary_ioctls=[]
                    if 'required_ioctl_command' in expected[stage]:
                        boundary_ioctls=[x for x in metadata['ioctls'] if x['command']==expected[stage]['required_ioctl_command']]
                        assert len(boundary_ioctls)==1 and boundary_ioctls[0]['v0']==89 and boundary_ioctls[0]['a3']==1
                    if stage=='resources':
                        assert reads['/emul/irix/usr/lib/X11/app-defaults/Toolchest']==[dict(requested=4281,returned=4281,error=0)]
                        assert reads['/emul/irix/usr/lib/X11/system.chestrc']==[dict(requested=4096,returned=n,error=0) for n in [4096,2364,0]]
                        assert not any(x.startswith('syscall=1003 ') and 'a2=0xffffffff ' in x for x in o['calls'])
                    captures.append(dict(boundary_ioctls=boundary_ioctls,x11_counters=counters,resource_reads=reads,name=o['name'],actual=o['actual'],successful_calls=dict(success),errors=dict(errors),window_tree=o['windows'],frame_sha256=o['frame_sha256']))
                if pair[0]=='lp64':
                    assert len(captures)==12 and r['native_x11_before'] and r['native_x11_after']
                    assert {c['name'] for c in captures}=={f'{stage}-{uid}-{i}' for stage in ['library','resources'] for uid in [0,1234] for i in range(3)}
                else:assert not captures
                item['toolchest']=captures
            report[key].append(item)
        assert seen==wanted
    transport_seen=set()
    assert len({p.resolve() for p in args.transport_runs})==2
    for directory in [args.select_run,*args.transport_runs]:
        directory=directory.resolve();r=json.loads((directory/'result.json').read_text())
        assert r['clean_shutdown'] and r['pin']==pins[r['kernel_abi']] and r['kernel_checkpoint']=='fxstat'
        if directory==args.select_run.resolve():
            assert r['status']=='observed' and r['fixtures_only'] and not r['failures']
            assert len(r['observations'])==552 and all(o['passed'] for o in r['observations'])
            for name,sha in r['sources'].items():assert digest(ROOT/name)==sha,name
            assert r['reference_sha256']==digest(ROOT/'lab/irix-select/reference.json')
            kind='select'
        else:
            assert r['kernel_abi'] not in transport_seen
            transport_seen.add(r['kernel_abi'])
            assert r['status']=='passed' and not r['x11'] and r['harness_sha256']==digest(ROOT/'scripts/probe-irix-tcp.py')
            assert len(r['observations'])==(1284 if r['kernel_abi']=='lp64' else 641)
            assert all(o['passed'] for o in r['observations'])
            if r['kernel_abi']=='lp64':assert r['expectations_sha256']==digest(lab/'desktop.json')
            kind='transport'
        report['regression_runs'].append(dict(kind=kind,kernel_abi=r['kernel_abi'],mode=r['mode'],status='passed',cases=len(r['observations']),clean_shutdown=True,directory=str(directory.relative_to(ROOT)),result_sha256=digest(directory/'result.json')))
    assert transport_seen=={'lp64','o32'}
    report['input_metadata_hashes']={str(p.relative_to(ROOT)):digest(p) for p in [lab/name for name in ['baseline.json','o32-baseline.json','reference.json','abi.json','toolchest.json','desktop.json']]}
    report['qualifier_sha256']=digest(Path(__file__).resolve());report['focused_cases']=sum(r['cases'] for r in report['focused_runs'])
    args.output.write_text(json.dumps(report,indent=2)+'\n');print('Qualified',report['focused_cases'],'fxstat records')

if __name__=='__main__':main()
