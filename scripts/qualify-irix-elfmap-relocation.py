#!/usr/bin/env python3
"""Check relocation evidence against the bounded contract and the IRIX oracle."""
import argparse,collections,hashlib,importlib.util,json,re,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('runtime',ROOT/'scripts/probe-irix-runtime.py');rt=importlib.util.module_from_spec(s);s.loader.exec_module(rt)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def expected(case,record,layout):
    assert record is not None
    ph=layout;want=dict(magic=0x58494531,case=case['number'],v1=0xfeedface,second_v0=0,second_a3=0,third_v0=0,third_a3=0,preserved_word=0,reserved=0)
    want.update({k:case['netbsd'][k] for k in ['v0','a3','checks']})
    start=ph[0][2];align=max(ph[0][7],ph[1][7]);span=ph[1][2]+((ph[1][5]+8191)&~8191)-start
    def relocated(value,original=start,span=span):
        assert 0x04000000<=value<=0x40000000-span and value!=original
        assert (value-original)%align==0
        return value
    if not want['a3']:
        want['v0']=relocated(record['v0']) if case['block'] and case['name']!='elfmap-occupied-gap' else start
    if case['action']==2:want['second_v0']=start
    if case['action'] in [5,6]:
        want.update(second_v0=relocated(record['second_v0'],start+0x10000),checks=3,preserved_word=0x12345678)
    if case['action']==7:
        want.update(second_v0=relocated(record['second_v0']),third_v0=relocated(record['third_v0']),checks=3,preserved_word=0x12345678)
        values=sorted([want['v0'],want['second_v0'],want['third_v0']])
        assert len(set(values))==3 and all(b>=a+span for a,b in zip(values,values[1:]))
    if case['fallback'] and not want['a3']:
        assert not(want['v0']<case['fallback']+8192 and want['v0']+span>case['fallback'])
    assert record==want,(case['name'],record,want)

def clock_summary(directory,case):
    unsupported=collections.Counter()
    addresses=set()
    for line in case['returns']:
        m=re.fullmatch(r'syscall=(\d+) v0=(0x[0-9a-f]+|\d+) a3=(\d+)',line)
        assert m,line
        number,value,error=int(m[1]),int(m[2],0),int(m[3])
        if error and value==89:unsupported[str(number)]+=1
        if number==1040 and not error and value>=0x00400000:addresses.add(value)
    return {**{k:case[k] for k in ['name','uid','style','actual','frames']},
            'window_viewable':True,'socket_calls':1,'connect_calls':1,
            'sampled_frames_identical':True,
            'successful_syssgi_address_returns':[hex(v) for v in sorted(addresses)],
            'unsupported_syscall_counts':dict(sorted(unsupported.items())),
            'private_trace_sha256':sha(directory/(case['name']+'.kdump'))}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('runs',nargs='+',type=Path);p.add_argument('--limits',nargs=2,type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    ref=json.loads((a.reference/'result.json').read_text());assert ref['status']=='observed' and ref['clean_shutdown']
    manifest=ref['manifest'];cases={c['name']:c for c in manifest['cases']}
    assert len(cases)==57 and len(ref['observations'])==228
    layouts={}
    for n,c in cases.items():
        f=ROOT/'.work/irix-elfmap-relocation/probes'/c['input'];assert sha(f)==manifest['files'][c['input']]['sha256']
        b=f.read_bytes();layouts[n]=[struct.unpack_from('>8I',b,52+32*i) for i in range(2)]
    oracle={o['name']:o for o in ref['observations']}
    assert len(oracle)==228
    # Positive validation actions assert code/data/BSS and sentinels; all
    # completed mapper calls check headers. Action zero records only returns.
    # Mixed alignment records the residue rather than assuming a contract.
    for n,o in oracle.items():
        case=cases[n.split('-',1)[1].rsplit('-',1)[0]];record=rt.elfmap_record(bytes.fromhex(o['stdout_hex']))
        if case['name']=='elfmap-no-bounded-space':
            # The original guest cannot establish this 960 MiB /dev/zero
            # occupant. No SGI_ELFMAP conclusion follows from that setup exit.
            assert o['exit']==99 and record['v0']==0 and record['v1']==0
            continue
        assert o['exit']==(139 if case['netbsd']['signal'] else 0),(n,o)
        assert record['magic']==0x58494531 and record['case']==case['number']
        assert record['v1']==0xfeedface
        if case['name']=='elfmap-mixed-align':assert record['reserved']==0xc000
        else:assert record['reserved']==0
    report=dict(schema=1,status='qualified',reference_directory=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),fixture_files=manifest['files'],runs=[],oracle_differences=[],reference_setup_limit='The four no-bounded-space cases exit 99 while establishing a 960 MiB occupant, before SGI_ELFMAP; these are native-only exhaustion checks.')
    seen=set();total=0
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());key=(r['kernel_abi'],r['mode']);assert key not in seen;seen.add(key)
        assert r['status']=='observed' and r['clean_shutdown']
        assert r['manifest']==manifest
        pin=ROOT/'lab/irix-elfmap-relocation'/('o32-baseline.json' if r['kernel_abi']=='o32' else 'baseline.json');assert r['pin']==json.loads(pin.read_text())
        assert len(r['observations'])==(114 if r['kernel_abi']=='o32' else 228)
        diffs=[]
        for o in r['observations']:
            c=cases[o['name'].split('-',1)[1].rsplit('-',1)[0]];actual=o['actual'];sig=c['netbsd']['signal']
            assert actual['errno_bytes']==0 and actual['errno']==0 and actual['exit']==(-1 if sig else 0) and actual['signal']==sig and not actual['killed'] and not actual['stderr'],(o['name'],actual)
            assert rt.elfmap_record(bytes.fromhex(o['record_hex']))==o['record']
            expected(c,o['record'],layouts[c['name']])
            irix=rt.elfmap_record(bytes.fromhex(oracle[o['name']]['stdout_hex']))
            # Retain every difference, including allowed address placement.
            fields={k:dict(netbsd=v,irix=irix[k]) for k,v in o['record'].items() if v!=irix[k]}
            if fields:diffs.append(dict(name=o['name'],fields=fields))
        # The initial 8 MiB limit was below the reserved stack span:
        # these setup exits are excluded, and replaced by focused reruns.
        for o in r['limits']:
            if o['actual']['exit']==99:assert o['record']['v1']==0
            else:assert o['actual']['exit']==0 and o['record']['v0']==12 and o['record']['a3']==1
        assert len(r['limits'])==(2 if r['kernel_abi']=='o32' else 4)
        if r['kernel_abi']=='lp64':
            assert r['native_x11_before'] and r['native_x11_after'] and len(r['xclock'])==4
            assert {(c['uid'],c['style']) for c in r['xclock']}=={(uid,style) for uid in [0,1234] for style in ['analog','digital']}
            for c in r['xclock']:
                assert c['actual']==dict(errno_bytes=0,errno=0,exit=-1,signal=9,killed=1,stdout='',stderr='Warning: Color name \"sgilightgray\" is not defined\nWarning: Color name \"sgislateblue\" is not defined\n')
                assert 'Map State: IsViewable' in c['window'] and 'Xiri_IRIX_clock' in c['tree']
                assert c['frames']['before']==c['frames']['after']
                for phase,h in c['frames'].items():assert sha(d/(c['name']+'-'+phase+'.xwd'))==h
                assert 'syscall=1040 v0=0x4000000 a3=0' in c['returns']
                assert 'syscall=1013 v0=0x59 a3=1' in c['returns'] and 'syscall=1128 v0=0x59 a3=1' in c['returns']
                assert sum(x.startswith('syscall=1107 ') for x in c['calls'])==1
                assert sum(x.startswith('syscall=1091 ') for x in c['calls'])==1
        report['runs'].append(dict(directory=str(d),mode=r['mode'],kernel_abi=r['kernel_abi'],result_sha256=sha(d/'result.json'),clean_shutdown=True,cases=len(r['observations']),excluded_limit_setup_attempts=len(r['limits']),controls=len(r['controls']),xclock=[clock_summary(d,c) for c in r['xclock']],oracle_differences=diffs))
        total+=len(r['observations'])
    assert seen=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    report['limit_runs']=[]
    limit_abis=set()
    for d in a.limits:
        r=json.loads((d/'result.json').read_text());assert r['status']=='observed' and r['clean_shutdown'] and r['limits_only']
        assert r['kernel_abi'] not in limit_abis;limit_abis.add(r['kernel_abi'])
        assert r['manifest']==manifest and not r['observations'] and not r['xclock']
        pin=ROOT/'lab/irix-elfmap-relocation'/('o32-baseline.json' if r['kernel_abi']=='o32' else 'baseline.json');assert r['pin']==json.loads(pin.read_text())
        for o in r['limits']:
            assert o['actual']['exit']==0 and o['actual']['signal']==0 and not o['actual']['killed'] and not o['actual']['stderr'],o
            assert o['record']['v1']==0xfeedface and o['record']['v0']==12 and o['record']['a3']==1 and o['record']['checks']==0,o
        assert len(r['limits'])==(2 if r['kernel_abi']=='o32' else 4)
        total+=len(r['limits'])
        report['limit_runs'].append(dict(directory=str(d),kernel_abi=r['kernel_abi'],result_sha256=sha(d/'result.json'),clean_shutdown=True,checks=len(r['limits']),controls=len(r['controls'])))
    assert limit_abis=={'lp64','o32'}
    report['checks']=total;report['qualifier_sha256']=sha(Path(__file__))
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(total,'mapping and limit checks qualified')
if __name__=='__main__':main()
