#!/usr/bin/env python3
"""Recheck saved SIOCNREAD records, X observations and transport regressions."""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parent.parent
NORMAL=dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout='',stderr='')


def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/filename)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sources(items):
    for path,sha in items.items():assert digest(ROOT/path)==sha,path


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',nargs=3,type=Path)
    p.add_argument('--select-run',type=Path,required=True)
    p.add_argument('--transport-runs',nargs=2,type=Path,required=True)
    p.add_argument('--window-run',type=Path)
    p.add_argument('--xclock-run',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();lab=ROOT/'lab/irix-siocnread'
    pins={abi:json.loads((lab/name).read_text()) for abi,name in [('lp64','baseline.json'),('o32','o32-baseline.json')]}
    oracle=json.loads((lab/'reference.json').read_text());records=module('records','irix-siocnread-records.py')
    assert oracle['clean_shutdown'] and records.validate_reference(oracle['cases'],oracle['observations'])==336
    sources(oracle['sources'])
    assert oracle['harness_sha256']==digest(ROOT/'scripts/probe-irix-reference-siocnread.py')
    refs={o['name']:bytes.fromhex(o['stdout_hex']) for o in oracle['observations']}
    contract=json.loads((lab/'abi.json').read_text())
    tc=json.loads((lab/'toolchest.json').read_text())
    tcp=module('tcp','probe-irix-tcp.py');fxstat=module('fxstat','qualify-irix-fxstat.py')
    report=dict(schema=1,status='qualified-subset',source_revision=pins['lp64']['source_revision'],source_branch='xiri/irix-siocnread',reference_cases=336,focused_runs=[],regression_runs=[],native_differences=contract['native_differences'],limits=contract['unqualified'],fixture_limits=contract['fixture_limits'])
    seen=set()
    for directory in args.runs:
        directory=directory.resolve();r=json.loads((directory/'result.json').read_text())
        pair=r['kernel_abi'],r['mode'];assert pair not in seen;seen.add(pair)
        assert r['status']=='observed' and r['clean_shutdown'] and not r['failures']
        assert r['pin']==pins[pair[0]] and r['reference_sha256']==digest(lab/'reference.json')
        assert r['manifest']['files']==oracle['files'] and not r['fixtures_only']
        sources(r['sources']);sources(r['manifest']['sources'])
        cases=[c for c in oracle['cases'] if pair[0]=='lp64' or c['abi']=='o32']
        obs={o['name']:o for o in r['observations']};assert len(obs)==len(r['observations'])==2*len(cases)
        for uid in [0,1234]:
            for case in cases:
                name=case['name']+'-'+str(uid);o=obs[name]
                assert o['passed'] and o['actual']==dict(NORMAL,stdout=o['actual']['stdout']),name
                assert records.compare(case,uid,bytes.fromhex(o['record_hex']),refs[name])['passed'],name
        expected=b'RDY\n'+b''.join(struct.pack('>II',c['symbols']['CASE'],c['symbols']['STATE']) for uid in [0,1234] for c in cases if c['symbols']['KIND']==0 and c['symbols']['STATE']>0)
        assert r['peer_stdout_hex']==expected.hex()
        controls=r['controls'];executables=['native-o32','vendor-asa']+(['vendor-echo'] if pair[0]=='lp64' else [])
        names={f'{phase}-{exe}-{uid}' for phase in ['before','after'] for exe in executables for uid in [0,1234]}
        assert len(controls)==len(names) and {x['name'] for x in controls}==names
        for o in controls:
            want=dict(NORMAL,exit=37,stdout='XIRI_ABI_PROBE\n') if 'native-o32' in o['name'] else dict(NORMAL,stdout='XIRI_VENDOR_O32\n' if 'vendor-asa' in o['name'] else 'XIRI_VENDOR_N32\n')
            assert o['actual']==want,o['name']
        captures=[]
        for o in r['toolchest']:
            name=o['name'];stage=name.split('-')[0];raw=(directory/(name+'.kdump')).read_text()
            assert o['actual']==tc[stage]['actual'] and o['passed'],name
            assert tcp.trace_records(raw,'irix_o32',True)==o['calls']
            assert tcp.trace_records(raw,'irix_ret',True)==o['returns']
            assert digest(directory/(name+'.xwd'))==o['frame_sha256']
            metadata=fxstat.trace_metadata(raw,tcp)
            boundary=[x for x in metadata['ioctls'] if x['command']==0x4004730a]
            if stage=='resources':assert boundary and all(x['a3']==0 and x['v0']==0 for x in boundary),name
            if 'frame_sha256' in tc[stage]:assert o['frame_sha256']==tc[stage]['frame_sha256'],name
            captures.append(dict(name=name,actual=o['actual'],siocnread=boundary,resource_reads=metadata['resource_reads'],window_tree=o['windows'],frame_sha256=o['frame_sha256']))
        if pair[0]=='lp64':
            assert r['native_x11_before'] and r['native_x11_after'] and len(captures)==12
            assert {c['name'] for c in captures}=={f'{stage}-{uid}-{i}' for stage in ['library','resources'] for uid in [0,1234] for i in range(3)}
        else:assert not captures
        report['focused_runs'].append(dict(kernel_abi=pair[0],mode=pair[1],cases=len(obs),controls=len(controls),clean_shutdown=True,toolchest=captures,directory=str(directory.relative_to(ROOT)),result_sha256=digest(directory/'result.json'),execution_sources=r['sources']))
    assert seen=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    regression_seen=set()
    for kind,directory in [('select',args.select_run),*[('transport',d) for d in args.transport_runs]]:
        directory=directory.resolve();r=json.loads((directory/'result.json').read_text())
        pair=kind,r['kernel_abi'];assert pair not in regression_seen;regression_seen.add(pair)
        assert r['clean_shutdown'] and r['pin']==pins[r['kernel_abi']] and r['kernel_checkpoint']=='siocnread'
        if kind=='select':
            sources(r['sources'])
            assert r['status']=='observed' and r['fixtures_only'] and not r['failures'] and not r['toolchest']
            assert len(r['observations'])==552 and all(o['passed'] for o in r['observations'])
            assert r['reference_sha256']==digest(ROOT/'lab/irix-select/reference.json')
            count=len(r['observations'])
        else:
            assert r['status']=='passed' and not r['x11']
            assert r['harness_sha256']==digest(ROOT/'scripts/probe-irix-tcp.py')
            assert len(r['observations'])==(1284 if r['kernel_abi']=='lp64' else 641)
            assert all(o['passed'] for o in r['observations'])
            if r['kernel_abi']=='lp64':assert r['expectations_sha256']==digest(ROOT/'lab/irix-fxstat/desktop.json')
            count=len(r['observations'])
        report['regression_runs'].append(dict(kind=kind,kernel_abi=r['kernel_abi'],mode=r['mode'],cases=count,clean_shutdown=True,directory=str(directory.relative_to(ROOT)),result_sha256=digest(directory/'result.json')))
    assert regression_seen=={('select','lp64'),('transport','lp64'),('transport','o32')}
    if args.window_run:
        directory=args.window_run.resolve();r=json.loads((directory/'result.json').read_text())
        assert r['status']=='observed' and r['clean_shutdown'] and r['native_x11_after'] and r['pin']==pins['lp64']
        sources(r['sources'])
        expected=re.search(r'^([0-9a-f]{128})  sgimips/binary/sets/xcomp.tgz$',(ROOT/'lab/netbsd-11.0/SHA512SUMS').read_text(),re.M)[1]
        assert r['xcomp_sha512']==expected
        def redraw(log):
            m=re.search(r'REDRAW visible=(\d+) before=(\w+) cleared=(\w+) after=(\w+)',log)
            assert m
            return dict(visible_windows=int(m[1]),before=m[2],cleared=m[3],after=m[4],restored=int(m[1])>0 and m[2]==m[4] and m[2]!=m[3])
        assert len(r['controls'])==2 and {c['phase'] for c in r['controls']}=={'before','after'}
        assert all(redraw(c['log'])['restored'] for c in r['controls'])
        assert len(r['toolchest'])==2 and {o['uid'] for o in r['toolchest']}=={0,1234}
        observations=[]
        for o in r['toolchest']:
            assert o['actual']==tc['resources']['actual']
            name='toolchest-'+str(o['uid']);raw=(directory/(name+'.kdump')).read_text()
            assert tcp.trace_records(raw,'irix_o32',True)==o['calls'] and tcp.trace_records(raw,'irix_ret',True)==o['returns']
            assert digest(directory/(name+'.xwd'))==o['frame_sha256']
            state=redraw(o['redraw'])
            observations.append(dict(uid=o['uid'],actual=o['actual'],window_tree=o['window_tree'],redraw=state,frame_sha256=o['frame_sha256']))
        report['sustained_window_check']=dict(clean_shutdown=True,seconds_per_client=60,native_expose_controls=2,all_redraws_restored=all(o['redraw']['restored'] for o in observations),observations=observations,directory=str(directory.relative_to(ROOT)),result_sha256=digest(directory/'result.json'),execution_sources=r['sources'])
    if args.xclock_run:
        directory=args.xclock_run.resolve();r=json.loads((directory/'result.json').read_text())
        assert r['status']=='observed' and r['clean_shutdown'] and r['native_x11_before'] and r['native_x11_after']
        assert r['pin']==pins['lp64'] and r['kernel_checkpoint']=='siocnread' and not r['faults']
        assert r['xclock_manifest_sha256']==digest(ROOT/'lab/irix-xclock/manifest.json')
        sources(r['sources'])
        assert 'Map State: IsViewable' in r['native_clock_window'] and len(r['cases'])==13
        assert r['native_trace_controls']['guard_intact']
        assert len(r['xclock'])==4 and {o['name'] for o in r['xclock']}=={f'clock-{style}-{uid}' for style in ['analog','digital'] for uid in [0,1234]}
        serial=(directory/'serial.log').read_text()
        assert serial.count("rld: Error: elfmap: couldn't map /usr/lib32/libXmu.so")==4
        cases=[]
        for o in r['xclock']:
            assert o['actual']==dict(NORMAL,exit=1)
            assert '0 children.' in o['window_tree'] and 'Map State: IsViewable' not in o['window']
            raw=(directory/(o['name']+'.kdump')).read_text()
            assert tcp.trace_records(raw,'irix_o32',True)==o['calls'] and tcp.trace_records(raw,'irix_ret',True)==o['returns']
            assert not any(c.startswith(('syscall=1107 ','syscall=1091 ')) for c in o['calls'])
            assert 'syscall=1040 v0=0xc a3=1' in o['returns']
            assert o['frames']['before']==o['frames']['after']
            for phase,sha in o['frames'].items():assert digest(directory/(o['name']+'-'+phase+'.xwd'))==sha
            cases.append(dict(name=o['name'],actual=o['actual'],elfmap_errno=12,socket_or_connect_calls=0,frame_sha256=o['frames']['before']))
        report['xclock_recheck']=dict(status='loader-boundary-observed',native_clock_viewable=True,clean_shutdown=True,native_controls=13,cases=cases,directory=str(directory.relative_to(ROOT)),result_sha256=digest(directory/'result.json'),execution_sources=r['sources'])
    report['input_metadata_hashes']={str((lab/name).relative_to(ROOT)):digest(lab/name) for name in ['baseline.json','o32-baseline.json','reference.json','abi.json','toolchest.json']}
    report['qualifier_sha256']=digest(Path(__file__).resolve())
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print('Qualified',sum(r['cases'] for r in report['focused_runs']),'SIOCNREAD records and',sum(r['cases'] for r in report['regression_runs']),'regression observations')

if __name__=='__main__':main()
