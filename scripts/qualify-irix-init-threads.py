#!/usr/bin/env python3
"""Compare pthread initialization with IRIX and verify native signal delivery."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT=Path(__file__).resolve().parent.parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def records(data,case,ids):
    kind=case['symbols']['KIND']
    stages={3:[0,1,3,4,2],4:[0,1,5,6],6:[0,1,8,2],9:[0,1],10:[0,1],
            11:[0,1,8,2],12:[0,1,8,2]}.get(kind,[0,1,2])
    assert len(data)==len(stages)*384,(case['name'],len(data))
    rows=[list(struct.unpack_from('>96I',data,i*384)) for i in range(len(stages))]
    assert [w[2] for w in rows]==stages
    parent,ppid=rows[0][3:5];assert parent>1 and ppid>0
    child=rows[2][3] if kind==3 else 0
    for w in rows:
        stage=w[2]
        assert w[:2]==[0x58505449,kind] and w[5:9]==ids
        assert w[32]==w[3] and w[35]==(4 if case['abi']=='n32' else 0) and w[36]==0x440
        if stage in [3,4]:assert w[3]==child and child!=parent and w[4]==parent
        else:assert w[3:5]==[parent,ppid]
        assert w[22]==(parent if kind==3 and stage in [2,3,4] else 0)
        assert w[23]==(child if kind==3 and stage==2 else 0)
        assert w[24]==(37 if kind==3 and stage==2 else 0)
        for i in [3,4,22,23,32]:w[i]=0
    return rows

def native_expectation(oracle,case):
    rows=[w.copy() for w in oracle]
    for w in rows:
        # Share-group queries were measured alongside initialization but
        # are still outside this adapter; do not count them as parity.
        assert w[25:31]==[0,0xfeedface,0,22,0xfeedface,1]
        w[25:31]=[89,0xfeedface,1,89,0xfeedface,1]
        if case['symbols']['KIND'] in [9,10] and w[2]==1:
            assert w[9:12]==[0,0xfeedface,0] and w[59:62]==[1,0,0x8000]
            w[9:12]=[14,0xfeedface,1]
            w[59:62]=[0,0,0]
    return rows

def check_controls(result):
    abis=['o32','n32'] if result['kernel_abi']=='lp64' else ['o32']
    page=result['pin']['page_bytes']
    expected={(phase,name,uid) for phase in ['before','after'] for name,uid in
        [('session-descendant-cleanup',None),*[(exe,uid) for exe in
        ['/root/irix-desktop/native-o32','/root/irix-desktop/vendor-asa'] for uid in [0,1234]]]}
    controls=result['controls'];assert len(controls)==len(expected)
    assert {(c['phase'],c['name'],c.get('uid')) for c in controls}==expected
    for c in controls:
        x=c['actual'];assert not x['stderr']
        if c['name']=='session-descendant-cleanup':
            assert x['exit']==x['signal']==0 and x['killed']==x['absent']==x['valid']==1
            assert x['elapsed_ms']>=2000 and not x['stdout']
        else:
            assert x['errno_bytes']==x['errno']==x['signal']==x['killed']==0
            assert (x['exit'],x['stdout'])==((37,'XIRI_ABI_PROBE\n') if c['name'].endswith('native-o32') else (0,''))
    expected_native={(phase,abi,uid) for phase in ['before','after'] for abi in ['native',*abis] for uid in [0,1234]}
    for key,text in [('native_zero_controls',f'NATIVE_ZERO page={page} guard=1 errno=22\n'),
                     ('native_prda_controls',f'NATIVE_PRDA absent=1 errno=12 page={page}\n')]:
        assert len(result[key])==len(expected_native)
        assert {(c['phase'],c['abi'],c['uid']) for c in result[key]}==expected_native
        for c in result[key]:assert c['actual']==dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout=text,stderr='')
    expected_fork={(abi,mode,uid) for abi in abis for mode in [0,1] for uid in [0,1234]}
    assert len(result['fork_errors'])==len(expected_fork)
    assert {(c['abi'],c['mode'],c['uid']) for c in result['fork_errors']}==expected_fork
    for c in result['fork_errors']:
        x=c['actual'];assert x['errno_bytes']==x['errno']==x['exit']==x['signal']==x['killed']==0 and not x['stderr']
        assert struct.unpack('>8I',bytes.fromhex(x['stdout_hex']))==(0x58504645,c['mode'],0,0xfeedface,0,14,0xfeedface,1)
    expected_signals={(abi,mode,uid) for abi in ['native',*abis] for mode in [0,1] for uid in [0,1234]}
    assert len(result['signal_controls'])==len(expected_signals)
    assert {(c['abi'],c['mode'],c['uid']) for c in result['signal_controls']}==expected_signals
    for c in result['signal_controls']:
        lines=re.findall(r'^SIGNAL (.+)$',c['output'],re.M);assert len(lines)==1
        f=dict(re.findall(r'(\w+)=(\S+)',lines[0]))
        assert int(f['uid'])==c['uid'] and int(f['mode'])==c['mode']
        assert f['observed']==f['absent']==f['valid']=='1' and 1<=int(f['tries'])<=50
        assert [int(x,16) for x in f['mask'].split(',')]==[0x10000000|(0 if c['mode'] else 0x4000),1,0,0]
        pending=[int(x,16) for x in f['pending'].split(',')]
        assert f['exit']=='-1' and int(f['signal'])==(15 if c['mode'] else 9)
        assert pending==([0]*4 if c['mode'] else [0x4000,0,0,0])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--export-reference',action='store_true')
    p.add_argument('runs',nargs='*',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--exec-runs',nargs=2,type=Path)
    a=p.parse_args()
    ref=json.loads((a.reference/'result.json').read_text())
    assert ref['status']=='observed' and ref['clean_shutdown'] and ref['scope']=='full'
    assert ref['harness_sha256']==sha(ROOT/'scripts/probe-irix-reference-init-threads.py')
    manifest=ref['manifest'];cases={c['name']+'-'+str(i):(c,i) for c in manifest['cases'] for i in c['identities']}
    oracle={o['name']:o for o in ref['observations']}
    assert len(cases)==len(ref['observations'])==104 and cases.keys()==oracle.keys()
    for path,h in manifest['sources'].items():assert sha(ROOT/path)==h,path
    exported=dict(reference='IRIX 6.5.22m',result_sha256=sha(a.reference/'result.json'),
        sources=manifest['sources'],harness_sha256=ref['harness_sha256'],cases=[])
    normalized={}
    for name,(case,i) in cases.items():
        o=oracle[name];assert o['exit']==0 and not o['stderr']
        normalized[name]=records(bytes.fromhex(o['stdout_hex']),case,manifest['identities'][i])
        exported['cases'].append(dict(name=name,records=normalized[name]))
    rp=ROOT/'lab/irix-init-threads/reference.json'
    if a.export_reference:rp.write_text(json.dumps(exported,indent=2)+'\n')
    assert json.loads(rp.read_text())==exported
    if not a.runs:
        assert a.export_reference
        print('Exported 104 reference executions');return
    assert a.output
    report=dict(status='passed',reference=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),
        reference_records_sha256=sha(rp),qualifier_sha256=sha(Path(__file__)),executions=0,records=0,
        prda_protection_policy_cases=0,controls=0,signal_controls=0,
        native_zero_controls=0,native_prda_controls=0,fork_policy_cases=0,runs=[])
    modes=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text())
        assert r['status']=='observed-uncompared' and r['clean_shutdown'] and not r['smoke'] and r['manifest']==manifest
        key=(r['kernel_abi'],r['mode']);assert key not in modes;modes.add(key)
        source_paths={}
        for path,h in r['sources'].items():
            checked=ROOT/path
            if sha(checked)!=h:checked=d/'sources'/path
            assert sha(checked)==h,path
            source_paths[path]=dict(checked=str(checked),sha256=h)
        for key in ['exec_manifest','fork_manifest','signal_manifest']:
            for path,h in r[key]['sources'].items():assert sha(ROOT/path)==h,path
        assert r['pin']==json.loads((ROOT/'lab/irix-init-threads'/('o32-baseline.json' if r['kernel_abi']=='o32' else 'baseline.json')).read_text())
        abis=['o32','n32'] if r['kernel_abi']=='lp64' else ['o32']
        want={n for n,(c,i) in cases.items() if c['abi'] in abis}
        assert len(r['observations'])==len(want) and {o['name'] for o in r['observations']}==want
        nrecords=0;policies=0
        for item in r['observations']:
            name=item['name'];o=item['actual'];case,i=cases[name]
            assert o['errno_bytes']==o['errno']==o['exit']==o['signal']==o['killed']==0 and not o['stderr'],(name,o)
            actual=records(bytes.fromhex(o['stdout_hex']),case,manifest['identities'][i])
            expected=native_expectation(normalized[name],case)
            assert actual==expected,(name,[(j,[(k,x[k],y[k]) for k in range(96) if x[k]!=y[k]]) for j,(x,y) in enumerate(zip(actual,expected)) if x!=y])
            nrecords+=len(actual);policies+=case['symbols']['KIND'] in [9,10]
        check_controls(r)
        report['executions']+=len(want);report['records']+=nrecords;report['prda_protection_policy_cases']+=policies
        report['controls']+=len(r['controls']);report['signal_controls']+=len(r['signal_controls'])
        report['native_zero_controls']+=len(r['native_zero_controls'])
        report['native_prda_controls']+=len(r['native_prda_controls'])
        report['fork_policy_cases']+=len(r['fork_errors'])
        report['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),pin=r['pin'],
            kernel_abi=r['kernel_abi'],mode=r['mode'],executions=len(want),records=nrecords,sources=source_paths,
            signal_controls=r['signal_controls'],clean_shutdown=True))
    assert modes=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    report['initialized_native_exec_controls']=0
    report['initialized_native_exec_runs']=[]
    if a.exec_runs:
        coverage=set()
        for d in a.exec_runs:
            r=json.loads((d/'result.json').read_text())
            assert r['status']=='passed' and r['clean_shutdown']
            abi=r['kernel_abi'];assert abi not in coverage;coverage.add(abi)
            assert r['pin']==json.loads((ROOT/'lab/irix-init-threads'/('o32-baseline.json' if abi=='o32' else 'baseline.json')).read_text())
            for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
            seed=ROOT/r['seed'];assert sha(seed/'result.json')==r['seed_result_sha256']
            assert str(seed.resolve()) in {str(d.resolve()) for d in a.runs}
            abis=['o32','n32'] if abi=='lp64' else ['o32']
            expected={(c['name'],uid) for c in manifest['cases'] if c['abi'] in abis and c['symbols']['KIND']==4 for uid in [0,1234]}
            assert len(r['cases'])==len(expected) and {(c['name'],c['uid']) for c in r['cases']}==expected
            for c in r['cases']:
                x=c['actual'];assert x['errno_bytes']==x['errno']==x['exit']==x['signal']==x['killed']==0 and not x['stderr']
                data=bytes.fromhex(x['stdout_hex'])
                rows=[list(struct.unpack_from('>96I',data,i*384)) for i in range(2)]
                assert rows[0][3]>1 and rows[0][4]>0
                assert rows[0][3:5]==rows[1][3:5]
                for w in rows:
                    assert w[32]==w[3] and w[22:24]==[0,0]
                    for i in [3,4,22,23,32]:w[i]=0
                identity=next(i for i,ids in enumerate(manifest['identities']) if ids==[c['uid']]*4)
                name=c['name']+'-'+str(identity);case,_=cases[name]
                assert rows==native_expectation(normalized[name],case)[:2]
                native=f"NATIVE_AFTER_INIT uid={c['uid']} mask=30000000,00000001,00000000,00000000 prda_absent=1 fork=37\n"
                assert data[768:].decode()==c['native']==native
            report['initialized_native_exec_controls']+=len(expected)
            report['initialized_native_exec_runs'].append(dict(directory=str(d),
                result_sha256=sha(d/'result.json'),serial_sha256=sha(d/'serial.log'),
                sources=r['sources'],pin=r['pin'],cases=r['cases'],clean_shutdown=True))
        assert coverage=={'lp64','o32'} and report['initialized_native_exec_controls']==12
    report['limits']=[
        'Single native LWP initialization only; thread creation, scheduling, foreign signal handlers and realtime signals remain unsupported.',
        'Only traditional IRIX signals 1..31 are translated; native-only mask bits are preserved.',
        'PR_GETNSHARE and PR_GETSHMASK remain ENOSYS and are excluded from parity; their measured reference returns are retained.',
        'PRDA protections remain authoritative: initial read-only/inaccessible holds return EFAULT instead of the reference success.',
        'After initialization an unreadable PRDA hold terminates the process with SIGSEGV; reserved PRDA remapping is not implemented.',
        'The new e_sigmask hook is a core-kernel dependency to resolve for stock-kernel module deployment.'
    ]
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['runs','limits','initialized_native_exec_runs']},indent=2))

if __name__=='__main__':main()
