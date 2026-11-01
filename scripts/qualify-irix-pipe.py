#!/usr/bin/env python3
"""Independently verify IRIX pipe records and native/reference equivalence."""
import argparse,hashlib,json,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def expected(case,ids):
    s=case['symbols'];kind=s['KIND'];w=[0]*64
    w[:4]=[0x58504950,s['CASE'],kind,s['ARG']]
    w[48:52]=[0xa5a55a5a,0x12345678,0x87654321,0x5a5aa5a5]
    w[56:60]=ids;w[60:64]=[0xa5a55a5a,0x12345678,11,0]
    def ret(at,value,error=0,second=0xfeedface):w[at:at+3]=[value,second,error]
    if kind==5:
        w[4]=29;ret(5,24,1);ret(8,24,1);w[11]=31;ret(12,24,1)
        ret(15,31);w[18]=30;ret(19,30,second=31)
        return w
    ret(4,0 if kind==4 else 3,second=3 if kind==4 else 4)
    ret(7,0);ret(10,0);ret(13,0);ret(16,1)
    if kind in [0,4]:
        ret(19,11);ret(22,4);ret(25,7);w[28]=1;ret(29,0);ret(32,9,1)
    elif kind==1:
        ret(19,0);ret(22,0);ret(25,11,1);ret(28,9,1);ret(31,9,1)
        ret(34,1);ret(37,1);w[40]=ord('X')
    elif kind==2:
        ret(19,5);ret(22,11);ret(25,11);w[28]=1;ret(29,0)
    elif kind==6:
        ret(19,11);w[22]=1;ret(23,0);ret(26,0,second=37<<8);w[29:33]=[18,1,1,37]
    elif kind==7:
        ret(19,0);ret(22,32,1)
    else:raise AssertionError(kind)
    return w

def decode(o,case,ids,native=False):
    if native:
        x=o['actual'];assert x['errno_bytes']==x['errno']==x['exit']==x['signal']==x['killed']==0 and not x['stderr']
        assert o['group_absent'];data=bytes.fromhex(x['stdout_hex'])
    else:
        assert o['exit']==0 and not o['stderr'];data=bytes.fromhex(o['stdout_hex'])
    assert len(data)==256
    words=list(struct.unpack('>64I',data));want=expected(case,ids)
    assert words==want,(o['name'],[(i,a,b) for i,(a,b) in enumerate(zip(words,want)) if a!=b])
    return words

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True);p.add_argument('--export-reference',action='store_true')
    p.add_argument('runs',nargs='*',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    ref=json.loads((a.reference/'result.json').read_text());assert ref['status']=='observed' and ref['scope']=='full' and ref['clean_shutdown']
    assert ref['harness_sha256']==sha(ROOT/'scripts/probe-irix-reference-pipe.py')
    m=ref['manifest'];cases={c['name']+'-'+str(i):(c,i) for c in m['cases'] for i in c['identities']}
    assert len(cases)==len(ref['observations'])==88
    for path,h in m['sources'].items():assert sha(ROOT/path)==h,path
    oracle={}
    for o in ref['observations']:
        c,i=cases[o['name']];assert o['name'] not in oracle
        oracle[o['name']]=decode(o,c,m['identities'][i])
    exported=dict(reference='IRIX 6.5.22m',result_sha256=sha(a.reference/'result.json'),sources=m['sources'],records=oracle)
    rp=ROOT/'lab/irix-pipe/reference.json'
    if a.export_reference:rp.write_text(json.dumps(exported,indent=2)+'\n')
    assert json.loads(rp.read_text())==exported
    if not a.runs:assert a.export_reference;print('88 original pipe records validated');return
    assert a.output
    report=dict(schema=1,status='passed',qualifier_sha256=sha(Path(__file__)),reference_directory=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),reference_records_sha256=sha(rp),records=0,controls=0,runs=[],source_evidence=[])
    revision=json.loads((ROOT/'lab/irix-pipe/baseline.json').read_text())['source_revision']
    for path in ['sys/compat/irix_o32/irix_o32.c','sys/kern/sys_descrip.c','sys/kern/sys_pipe.c']:
        data=subprocess.check_output(['git','-C',str(ROOT.parent/'NetBSD-nixbench'),'show',revision+':'+path])
        report['source_evidence'].append(dict(repository='NetBSD-xiri',revision=revision,path=path,sha256=hashlib.sha256(data).hexdigest()))
    coverage=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());key=(r['kernel_abi'],r['mode']);assert key not in coverage;coverage.add(key)
        assert r['status']=='observed-uncompared' and r['clean_shutdown'] and r['manifest']==m
        pin=json.loads((ROOT/'lab/irix-pipe'/('o32-baseline.json' if key[0]=='o32' else 'baseline.json')).read_text());assert r['pin']==pin
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        assert sha(ROOT/r['seed']/'result.json')==r['seed_result_sha256']
        names={n for n,(c,i) in cases.items() if key[0]=='lp64' or c['abi']=='o32'}
        assert len(r['observations'])==len(names) and {o['name'] for o in r['observations']}==names
        for o in r['observations']:
            c,i=cases[o['name']];assert decode(o,c,m['identities'][i],True)==oracle[o['name']]
        controls=['native-o32','vendor-asa','native-pipe']+(['vendor-echo'] if key[0]=='lp64' else [])
        required={(phase,uid,name) for phase in ['before','after'] for uid in [0,1234] for name in controls}
        assert len(r['controls'])==len(required) and {(x['phase'],x['uid'],x['name']) for x in r['controls']}==required
        for x in r['controls']:
            name=x['name'];out={'native-o32':'XIRI_ABI_PROBE\n','vendor-asa':'XIRI_VENDOR_O32\n','vendor-echo':'XIRI_VENDOR_N32\n','native-pipe':f'NATIVE_PIPE uid={x["uid"]} io=1 fork=1 eof=1 nonblock=1 rollback=1\n'}[name]
            assert x['actual']==dict(errno_bytes=0,errno=0,exit=37 if name=='native-o32' else 0,signal=0,killed=0,stdout=out,stderr='')
            if name=='native-pipe':assert x['group_absent']
        report['records']+=len(names);report['controls']+=len(required)
        report['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),serial_sha256=sha(d/'serial.log'),fixtures_log_sha256=sha(d/'fixtures.log'),pin=pin,sources=r['sources'],kernel_abi=key[0],mode=key[1],records=len(names),controls=r['controls'],group_cleanup_passed=True,clean_shutdown=True))
    assert coverage=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    report['limits']=['Pipe ABI/lifecycle subset only; no STREAMS interfaces, poll adapter, asynchronous I/O, capacity/atomicity stress, signal-handler delivery or physical-hardware qualification.','All 64 words match the reference exactly; no descriptor/error normalization.','Blocked SIGPIPE yields EPIPE; this does not qualify foreign handlers or context restoration.']
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('Passed',report['records'],'pipe records and',report['controls'],'native/vendor controls')
if __name__=='__main__':main()
