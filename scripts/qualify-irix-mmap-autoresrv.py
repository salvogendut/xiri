#!/usr/bin/env python3
"""Compare AUTORESRV and private/fixed/local mmap records with original IRIX and native policy."""
import argparse,hashlib,json,struct,subprocess,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def words(o,c,ids,page):
    w=list(struct.unpack('>64I',bytes.fromhex(o['stdout_hex'])))
    s=c['symbols']
    assert w[:2]==[0x584d4c43,s['CASE']] and w[5]==page
    assert w[16:24]==[s[k] for k in ['ADDRESS','LENGTH','PROTECTION','FLAGS','FD_MODE','OFFSET','FILE_KIND','REPLACE']]
    assert w[56:60]==ids and w[60:]==[0,0,0,0]
    assert w[3]==0xfeedface and w[4] in [0,1]
    assert w[26:28]==[s['FORK'],s['PROTECT']]
    return w

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--export-reference',action='store_true')
    p.add_argument('runs',nargs='+',type=Path)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();ref=json.loads((a.reference/'result.json').read_text())
    assert ref['status']=='observed' and ref['clean_shutdown'] and ref['scope']=='full'
    assert ref['harness_sha256']==sha(ROOT/'scripts/probe-irix-reference-mmap-autoresrv.py')
    manifest=ref['manifest'];cases={c['name']+'-'+str(i):(c,i) for c in manifest['cases'] for i in c['identities']}
    oracle={o['name']:o for o in ref['observations']};assert len(cases)==len(ref['observations'])==464 and oracle.keys()==cases.keys()
    for path,h in manifest['sources'].items():assert sha(ROOT/path)==h,path
    records=[]
    for n,(c,i) in cases.items():
        o=oracle[n];w=words(o,c,manifest['identities'][i],4096)
        assert not o['stderr'] and o['exit']==(139 if c['symbols']['FAULT'] and not w[4] else 0)
        if not w[4]:
            assert w[2]<0x80000000 and w[2]%4096==0
            if c['symbols']['FLAGS']&0x10:assert w[2]==c['symbols']['ADDRESS']
            s=c['symbols']
            if s['LENGTH'] and s['LENGTH']<=0x200000:
                assert w[6]==((1 if s['PROTECTION']&1 else 0)|(2 if s['PROTECTION']&2 else 0)|(4 if s['REPLACE'] else 0))
                assert w[36:39]==([0,0,0] if s['FAULT'] else [0,0xfeedface,0])
            if s['FORK']:assert w[28:32]==[37,0x5a,0xa6,1]
            if s['PROTECT']:assert w[40:43]==[0,0xfeedface,0]
            if s['PROTECT']==2:assert w[43:46]==[0,0xfeedface,0]
        records.append(dict(name=n,exit=o['exit'],record=w))
    exported=dict(reference='IRIX 6.5.22m',result_sha256=sha(a.reference/'result.json'),harness_sha256=ref['harness_sha256'],manifest_sources=manifest['sources'],cases=records)
    record_path=ROOT/'lab/irix-mmap-autoresrv/reference.json'
    if a.export_reference:record_path.write_text(json.dumps(exported,indent=2)+'\n')
    assert json.loads(record_path.read_text())==exported
    result=dict(status='passed',reference=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),reference_records_sha256=sha(record_path),qualifier_sha256=sha(Path(__file__)),cases=0,oracle_equal=0,native_policy=0,controls=0,native_zero_controls=0,runs=[])
    policies={'fixed-local-bad-prot':22,'fixed-local-empty':22,'fixed-local-wrap':12,'flags-shared-local':22,**{n:22 for n in ['flags-autogrow','flags-anyaddr','flags-unknown','auto-empty','auto-shared','auto-only','auto-unknown','auto-autogrow']}}
    coverage=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());assert r['status']=='observed-uncompared' and r['clean_shutdown'] and not r['smoke'] and r['mapping_file_unchanged']
        assert r['manifest']==manifest
        coverage.add((r['kernel_abi'],r['mode']))
        assert tomllib.loads((d/'iris.toml').read_text())['ci']==(r['mode']=='ci')
        assert r['seed_result_sha256']==sha(ROOT/r['seed']/'result.json')
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        assert r['pin']==json.loads((ROOT/'lab/irix-mmap-autoresrv'/('o32-baseline.json' if r['kernel_abi']=='o32' else 'baseline.json')).read_text())
        for path,h in r['exec_manifest']['sources'].items():assert sha(ROOT/path)==h,path
        assert r['exec_manifest']==json.loads((ROOT/'.work/irix-mmap-local/exec-controls/manifest.json').read_text())
        page=r['pin']['page_bytes'];want={n for n,(c,i) in cases.items() if r['kernel_abi']=='lp64' or c['abi']=='o32'}
        assert len(r['observations'])==len(want) and {o['name'] for o in r['observations']}==want
        counts=dict(oracle_equal=0,native_policy=0)
        for item in r['observations']:
            n=item['name'];o=item['actual'];c,i=cases[n];s=c['symbols'];original=oracle[n]
            assert o['errno_bytes']==o['errno']==o['killed']==0 and not o['stderr'],(n,o)
            w=words(o,c,manifest['identities'][i],page);expected=words(original,c,manifest['identities'][i],4096)
            suffix=c['name'].split('-',2)[2];error=policies.get(suffix)
            if page==8192 and suffix in ['fixed-local-halfpage','fixed-local-halfpage-offset','auto-halfpage']:error=22
            policy=error is not None or suffix=='fixed-local-writeonly'
            if suffix=='fixed-local-writeonly':
                # Native /dev/zero is an anonymous-memory source before the
                # vnode FREAD test; ordinary file access checks are unchanged.
                expected[2:5]=[s['ADDRESS'],0xfeedface,0];expected[6]=3;expected[36:39]=[0,0xfeedface,0]
            elif error is not None:
                expected[2:5]=[error,0xfeedface,1];expected[6]=0;expected[36:39]=[0,0,0]
            else:
                if not w[4] and not (s['FLAGS']&0x10):
                    assert 0<w[2]<0x80000000 and not w[2]&(page-1)
                    w[2]=expected[2] # Non-fixed allocation address is host policy.
            assert (o['exit'],o['signal'])==((-1,11) if s['FAULT'] and not w[4] else (0,0)),(n,o)
            w[5]=4096 # Payload check covers the entire actual rounded page.
            assert w==expected,(n,[(i,w[i],expected[i]) for i in range(64) if w[i]!=expected[i]])
            counts['native_policy' if policy else 'oracle_equal']+=1
        expected_controls={(phase,name,uid) for phase in ['before','after'] for name,uid in [('session-descendant-cleanup',None),*[(exe,uid) for exe in ['/root/irix-desktop/native-o32','/root/irix-desktop/vendor-asa'] for uid in [0,1234]]]}
        assert len(r['controls'])==10 and {(c['phase'],c['name'],c.get('uid')) for c in r['controls']}==expected_controls
        for c in r['controls']:
            x=c['actual']
            assert not x['stderr']
            if c['name']=='session-descendant-cleanup':
                assert x['exit']==x['signal']==0 and x['killed']==x['absent']==x['valid']==1 and x['elapsed_ms']>=2000 and not x['stdout']
            else:
                assert x['errno_bytes']==x['errno']==x['signal']==x['killed']==0
                assert (x['exit'],x['stdout'])==((37,'XIRI_ABI_PROBE\n') if c['name'].endswith('native-o32') else (0,''))
        expected_zero={(phase,abi,uid) for phase in ['before','after'] for abi in ['native','o32']+(['n32'] if r['kernel_abi']=='lp64' else []) for uid in [0,1234]}
        assert len(r['native_zero_controls'])==len(expected_zero) and {(c['phase'],c['abi'],c['uid']) for c in r['native_zero_controls']}==expected_zero
        for c in r['native_zero_controls']:
            assert c['actual']==dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout='NATIVE_ZERO page='+str(page)+' guard=1 errno=22\n',stderr='')
        result['native_zero_controls']+=len(expected_zero)
        for k,v in counts.items():result[k]+=v
        result['cases']+=len(want);result['controls']+=10
        result['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),kernel_abi=r['kernel_abi'],mode=r['mode'],pin=r['pin'],counts=counts,controls=10,native_zero_controls=len(expected_zero),clean_shutdown=True,mapping_file_unchanged=True))
    assert coverage=={('lp64','ci'),('lp64','ordinary'),('o32','ci')} and len(result['runs'])==3
    revisions={run['pin']['source_revision'] for run in result['runs']}
    assert len(revisions)==1
    revision=revisions.pop()
    result['source_evidence']=[]
    for path in ['sys/compat/irix_o32/irix_o32.c','sys/uvm/uvm_mmap.c',
                 'sys/uvm/uvm_anon.c','sys/uvm/uvm_pdaemon.c']:
        data=subprocess.check_output(['git','-C',str(ROOT.parent/'NetBSD-nixbench'),
                                      'show',revision+':'+path])
        result['source_evidence'].append(dict(repository='NetBSD-xiri',revision=revision,
            path=path,sha256=hashlib.sha256(data).hexdigest()))
    result['limits']=['Only private mappings, optionally fixed/local/autoresrv; shared, autogrow, anyaddr and unknown flags remain EINVAL.','AUTORESRV uses native UVM demand allocation; IRIX logical-swap accounting, exhaustion behavior and mlock interactions are not established.','LOCAL requires one LWP and an unshared vmspace; sproc/share-group semantics are not implemented.','Native page alignment, file permissions and protections remain authoritative; LP64 rounds 4096 bytes to 8192.','Native /dev/zero permits mapping a write-only descriptor; original IRIX returns EACCES. Regular-file permission checks remain native.','Native bad-protection/empty-map EINVAL and wrap ENOMEM differ from original IRIX.','Only signed 32-bit file offsets are covered.','Validated IRIX executables permit page zero; native executables retain the default guard, including after foreign-to-native exec.']
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['runs','limits']},indent=2))
if __name__=='__main__':main()
