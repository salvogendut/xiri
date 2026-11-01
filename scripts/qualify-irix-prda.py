#!/usr/bin/env python3
"""Compare PRDA lifecycle records and native exec/fork policy controls."""
import argparse,hashlib,json,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def records(data,c,ids,page):
    kind=c['symbols']['KIND'];count=3 if kind==1 else 2
    assert len(data)==count*384
    rows=[list(struct.unpack_from('>96I',data,i*384)) for i in range(count)]
    assert [w[2] for w in rows]==([0,2,1] if kind==1 else [0,3 if kind==2 else 4 if kind==3 else 1])
    parent,ppid=rows[0][4:6];assert parent>1 and ppid>0
    for w in rows:
        stage=w[2];assert w[:2]==[0x58505244,kind] and w[3]==page and w[6:10]==ids
        assert w[32]==w[4] and w[4]>1 and w[5]>0
        if stage==2:assert w[4]!=parent and w[5]==parent
        else:assert w[4:6]==[parent,ppid]
        expected=[0]*96;expected[:10]=[0x58505244,kind,stage,page,w[4],w[5],*ids]
        expected[32]=w[4];expected[35]=4 if c['abi']=='n32' else 0;expected[36]=0x440
        if kind==0 and stage==1:expected[64]=0x55667788
        if kind==1:
            expected[64]=0x55667788 if stage==2 else 0x11223344
            if stage==2:expected[15]=1;expected[20]=0x11223344
            if stage==1:expected[14]=37<<8
        if kind==3 and stage==4:expected[16]=0x8000
        assert w==expected,(c['name'],stage,[(i,w[i],expected[i]) for i in range(96) if w[i]!=expected[i]])
    for w in rows:w[3]=4096;w[4]=w[5]=w[32]=0
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,required=True);p.add_argument('--export-reference',action='store_true');p.add_argument('runs',nargs='+',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    ref=json.loads((a.reference/'result.json').read_text());assert ref['status']=='observed' and ref['clean_shutdown'] and ref['scope']=='full'
    assert ref['harness_sha256']==sha(ROOT/'scripts/probe-irix-reference-prda.py')
    manifest=ref['manifest'];cases={c['name']+'-'+str(i):(c,i) for c in manifest['cases'] for i in c['identities']};oracle={o['name']:o for o in ref['observations']}
    assert len(cases)==len(ref['observations'])==32 and cases.keys()==oracle.keys()
    for path,h in manifest['sources'].items():assert sha(ROOT/path)==h,path
    exported=dict(reference='IRIX 6.5.22m',result_sha256=sha(a.reference/'result.json'),sources=manifest['sources'],harness_sha256=ref['harness_sha256'],cases=[])
    normalized={}
    for n,(c,i) in cases.items():
        o=oracle[n];assert o['exit']==0 and not o['stderr']
        normalized[n]=records(bytes.fromhex(o['stdout_hex']),c,manifest['identities'][i],4096)
        exported['cases'].append(dict(name=n,records=normalized[n]))
    rp=ROOT/'lab/irix-prda/reference.json'
    if a.export_reference:rp.write_text(json.dumps(exported,indent=2)+'\n')
    assert json.loads(rp.read_text())==exported
    result=dict(status='passed',reference=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),reference_records_sha256=sha(rp),qualifier_sha256=sha(Path(__file__)),executions=0,records=0,fork_policy_cases=0,controls=0,native_zero_controls=0,native_prda_controls=0,runs=[])
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());assert r['status']=='observed-uncompared' and r['clean_shutdown'] and not r['smoke'] and r['manifest']==manifest
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        for key in ['exec_manifest','fork_manifest']:
            for path,h in r[key]['sources'].items():assert sha(ROOT/path)==h,path
        assert r['pin']==json.loads((ROOT/'lab/irix-prda'/('o32-baseline.json' if r['kernel_abi']=='o32' else 'baseline.json')).read_text())
        page=r['pin']['page_bytes'];abis=['o32','n32'] if r['kernel_abi']=='lp64' else ['o32']
        want={n for n,(c,i) in cases.items() if c['abi'] in abis}
        assert len(r['observations'])==len(want) and {o['name'] for o in r['observations']}==want
        nrecords=0
        for item in r['observations']:
            n=item['name'];o=item['actual'];c,i=cases[n]
            assert o['errno_bytes']==o['errno']==o['exit']==o['signal']==o['killed']==0 and not o['stderr'],(n,o)
            actual=records(bytes.fromhex(o['stdout_hex']),c,manifest['identities'][i],page);assert actual==normalized[n];nrecords+=len(actual)
        expected_controls={(phase,name,uid) for phase in ['before','after'] for name,uid in [('session-descendant-cleanup',None),*[(exe,uid) for exe in ['/root/irix-desktop/native-o32','/root/irix-desktop/vendor-asa'] for uid in [0,1234]]]}
        assert len(r['controls'])==10 and {(c['phase'],c['name'],c.get('uid')) for c in r['controls']}==expected_controls
        for c in r['controls']:
            x=c['actual'];assert not x['stderr']
            if c['name']=='session-descendant-cleanup':assert x['exit']==x['signal']==0 and x['killed']==x['absent']==x['valid']==1 and x['elapsed_ms']>=2000 and not x['stdout']
            else:
                assert x['errno_bytes']==x['errno']==x['signal']==x['killed']==0
                assert (x['exit'],x['stdout'])==((37,'XIRI_ABI_PROBE\n') if c['name'].endswith('native-o32') else (0,''))
        expected_native={(phase,abi,uid) for phase in ['before','after'] for abi in ['native',*abis] for uid in [0,1234]}
        for key,text in [('native_zero_controls','NATIVE_ZERO page='+str(page)+' guard=1 errno=22\n'),('native_prda_controls','NATIVE_PRDA absent=1 errno=12 page='+str(page)+'\n')]:
            assert len(r[key])==len(expected_native) and {(c['phase'],c['abi'],c['uid']) for c in r[key]}==expected_native
            for c in r[key]:assert c['actual']==dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout=text,stderr='')
            result[key]+=len(expected_native)
        expected_fork={(abi,mode,uid) for abi in abis for mode in [0,1] for uid in [0,1234]}
        assert len(r['fork_errors'])==len(expected_fork) and {(c['abi'],c['mode'],c['uid']) for c in r['fork_errors']}==expected_fork
        for c in r['fork_errors']:
            x=c['actual'];assert x['errno_bytes']==x['errno']==x['exit']==x['signal']==x['killed']==0 and not x['stderr']
            assert struct.unpack('>8I',bytes.fromhex(x['stdout_hex']))==(0x58504645,c['mode'],0,0xfeedface,0,14,0xfeedface,1)
        result['executions']+=len(want);result['records']+=nrecords;result['controls']+=10;result['fork_policy_cases']+=len(expected_fork)
        result['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),kernel_abi=r['kernel_abi'],mode=r['mode'],pin=r['pin'],executions=len(want),records=nrecords,fork_policy_cases=len(expected_fork),controls=10,native_zero_controls=len(expected_native),native_prda_controls=len(expected_native),clean_shutdown=True))
    result['limits']=['Only single-process/fork/exec PRDA behavior; sproc share groups, threads, scheduling hints and user-managed PRDA signal holds remain unsupported.','FP flags are the measured initial ABI values (o32 0, n32 4); no general FP-control interface is implemented.','PRId uses native CPU identification; this qualification covers the configured R4400 value 0x440.','The native page is 8192 bytes on LP64; its extra half is verified zero.','Fork with the PID storage unmapped/read-only returns EFAULT before creating a child; this is an explicit native policy, not an original-IRIX parity claim.']
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['runs','limits']},indent=2))
if __name__=='__main__':main()
