#!/usr/bin/env python3
"""Compare mkdir records with IRIX and verify independent native filesystem effects."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import struct
import subprocess

ROOT=Path(__file__).resolve().parent.parent
MODES=[0o755,0,0o7777,0o777,0o100755,0xffffffff,0x800001ed]+[0o755]*25
EFFECTS={0:'data/simple',1:'data/zero',2:'data/special',3:'data/perms',
    4:'data/typebits',5:'data/negative',6:'data/highbit',11:'data/parent/new',
    14:'data/nosearch/new',15:'data/nowrite/new',16:'data/group/new',
    17:'data/owner/new',18:'data/sgid/new',19:'data/trailing',28:'data/edge',
    30:'/tmp/xiri-mkdir-native/new',31:'/emul/irix/tmp/xiri-mkdir-shadow/new'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def decode(data,case,ids):
    assert len(data)==4096
    rows=[list(struct.unpack_from('>32I',data,i*128)) for i in range(32)]
    for i,w in enumerate(rows):
        assert w[:4]==[0x584d4b44,i,case['symbols']['MASK'],MODES[i]]
        assert w[4:8]==w[17:21]==ids
        assert w[9]==w[12]==0xfeedface
        assert w[10] in [0,1] and w[13] in [0,1]
        assert w[21:30]==[0]*9 and w[30:]==[0xa5a55a5a,0x12345678]
        if not w[10]:assert w[8]==0 and not w[13]
        if w[13]:assert w[14:17]==[0,0,0]
    return rows

def snapshot(text):
    result={}
    for line in text.splitlines():
        name,mode,uid,gid=line.split('|')
        assert name not in result
        result[name]=[int(mode,8),int(uid),int(gid)]
    assert len(result)>=17
    assert result['data']==[0o40777,0,0]
    assert result['data/group']==[0o40770,4567,5678]
    assert result['data/owner']==[0o40700,1234,5678]
    assert result['data/sgid']==[0o42777,4567,5678]
    assert result['/emul/irix/tmp/xiri-mkdir-shadow']==[0o40777,4567,2345]
    return result

def controls(result):
    names=['native-o32','vendor-asa','native-mkdir']+(['vendor-echo'] if result['kernel_abi']=='lp64' else [])
    expected={(phase,uid,name) for phase in ['before','after'] for uid in [0,1234] for name in names}
    assert len(result['controls'])==len(expected)
    assert {(c['phase'],c['uid'],c['name']) for c in result['controls']}==expected
    for c in result['controls']:
        name,uid=c['name'],c['uid']
        want={'native-o32':'XIRI_ABI_PROBE\n','vendor-asa':'XIRI_VENDOR_O32\n',
            'vendor-echo':'XIRI_VENDOR_N32\n','native-mkdir':f'NATIVE_MKDIR uid={uid} mode=755 exists=17 readonly={13 if uid else 30} removed=1\n'}[name]
        if name=='native-mkdir':
            want=c['actual']['stdout']
            assert re.fullmatch(f'NATIVE_MKDIR uid={uid} mode=755 exists=17 readonly='+('(13|30)' if uid else '(30)')+r' removed=1\n',want)
        assert c['actual']==dict(errno_bytes=0,errno=0,exit=37 if name=='native-o32' else 0,
            signal=0,killed=0,stdout=want,stderr='')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--export-reference',action='store_true')
    p.add_argument('runs',nargs='*',type=Path)
    p.add_argument('--output',type=Path)
    a=p.parse_args()
    ref=json.loads((a.reference/'result.json').read_text())
    assert ref['status']=='observed' and ref['clean_shutdown'] and ref['scope']=='full'
    assert ref['harness_sha256']==sha(ROOT/'scripts/probe-irix-reference-mkdir.py')
    manifest=ref['manifest']
    for path,h in manifest['sources'].items():assert sha(ROOT/path)==h,path
    cases={c['name']+'-'+str(i):(c,i) for c in manifest['cases'] for i in c['identities']}
    assert len(cases)==len(ref['observations'])==40
    oracle={}
    for o in ref['observations']:
        case,i=cases[o['name']];assert o['exit']==0 and not o['stderr']
        rows=decode(bytes.fromhex(o['stdout_hex']),case,manifest['identities'][i])
        for w in rows:
            if not w[10]:
                assert w[1] in EFFECTS and w[14:17]==[0o40000|(w[3]&0o777&~w[2]),w[5],w[7]]
        oracle[o['name']]=rows
    exported=dict(reference='IRIX 6.5.22m',result_sha256=sha(a.reference/'result.json'),
        sources=manifest['sources'],harness_sha256=ref['harness_sha256'],records=oracle)
    rp=ROOT/'lab/irix-mkdir/reference.json'
    if a.export_reference:rp.write_text(json.dumps(exported,indent=2)+'\n')
    assert json.loads(rp.read_text())==exported
    if not a.runs:
        assert a.export_reference;print('Exported 1280 mkdir reference records');return
    assert a.output
    report=dict(schema=1,status='passed',qualifier_sha256=sha(Path(__file__)),
        reference_directory=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),
        reference_records_sha256=sha(rp),executions=0,records=0,native_policy_records=0,
        created_directories=0,controls=0,runs=[])
    report['source_evidence']=[]
    revision=json.loads((ROOT/'lab/irix-mkdir/baseline.json').read_text())['source_revision']
    for path in ['sys/compat/irix_o32/irix_o32.c','sys/kern/vfs_syscalls.c','sys/kern/vfs_lookup.c','sys/ufs/ufs/ufs_vnops.c']:
        data=subprocess.check_output(['git','-C',str(ROOT.parent/'NetBSD-nixbench'),'show',revision+':'+path])
        report['source_evidence'].append(dict(repository='NetBSD-xiri',revision=revision,path=path,sha256=hashlib.sha256(data).hexdigest()))
    coverage=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text())
        key=(r['kernel_abi'],r['mode']);assert key not in coverage;coverage.add(key)
        assert r['status']=='observed-uncompared' and r['clean_shutdown'] and r['manifest']==manifest
        pin=json.loads((ROOT/'lab/irix-mkdir'/('o32-baseline.json' if key[0]=='o32' else 'baseline.json')).read_text())
        assert r['pin']==pin
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        assert sha(ROOT/r['seed']/'result.json')==r['seed_result_sha256']
        expected={n for n,(case,i) in cases.items() if key[0]=='lp64' or case['abi']=='o32'}
        assert len(r['observations'])==len(expected) and {o['name'] for o in r['observations']}==expected
        policies=[];created=0
        for o in r['observations']:
            x=o['actual'];assert x['errno_bytes']==x['errno']==x['exit']==x['signal']==x['killed']==0 and not x['stderr']
            case,i=cases[o['name']];rows=decode(bytes.fromhex(x['stdout_hex']),case,manifest['identities'][i])
            before,after=snapshot(o['before']),snapshot(o['after'])
            for path,metadata in before.items():assert after[path]==metadata,(o['name'],path)
            additions={}
            for j,(actual,original) in enumerate(zip(rows,oracle[o['name']])):
                want=original.copy()
                if not original[10]:
                    path=EFFECTS[j];assert path not in before
                    parent=before[str(Path(path).parent)]
                    # FFS supplies native parent-group ownership.
                    # Credentials and ordinary permissions must still match IRIX.
                    mode=0o40000|(original[3]&0o777&~original[2])
                    metadata=[mode,original[5],parent[2]]
                    want[14:17]=metadata
                    additions[path]=metadata
                    if want!=original:
                        policies.append(dict(execution=o['name'],case=j,reference=original[14:17],native=metadata))
                assert actual==want,(o['name'],j,[(k,actual[k],want[k]) for k in range(32) if actual[k]!=want[k]])
            assert after==dict(before,**additions),(o['name'],set(after)^set(dict(before,**additions)))
            assert '/tmp/xiri-mkdir-shadow/new' not in after
            created+=len(additions)
        controls(r)
        report['executions']+=len(expected);report['records']+=32*len(expected)
        report['native_policy_records']+=len(policies);report['created_directories']+=created
        report['controls']+=len(r['controls'])
        report['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),
            serial_sha256=sha(d/'serial.log'),fixtures_log_sha256=sha(d/'fixtures.log'),
            pin=pin,sources=r['sources'],kernel_abi=key[0],mode=key[1],executions=len(expected),
            records=32*len(expected),native_policy=policies,created_directories=created,
            controls=r['controls'],clean_shutdown=True))
    assert coverage=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    report['limits']=[
        'Native FFS parent-group ownership is retained; the reference creates tested directories with effective GID. Neither tested creation path retains special mode bits, including under the setgid parent.',
        'Absolute creation uses native TRYEMULROOT parent lookup and fallback; paired namespace fixtures verify the created location independently.',
        'Only mkdir is added: unlink, rename, fsync, broader waits and full desktop behavior remain separate work.',
        'No ACL, supplementary-group, concurrent namespace mutation, quota/full-filesystem or physical-hardware qualification.'
    ]
    a.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ['runs','limits','source_evidence']},indent=2))

if __name__=='__main__':main()
