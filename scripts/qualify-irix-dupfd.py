#!/usr/bin/env python3
"""Independently verify IRIX dupfd records and native/reference equivalence."""
import argparse,hashlib,json,struct,subprocess,tarfile,re,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def expected(case,ids):
    s=case['symbols'];kind=s['KIND'];arg=s['ARG'];w=[0]*64
    w[:4]=[0x58445550,s['CASE'],kind,arg];w[56:60]=ids
    w[60:62]=[0xa5a55a5a,0x12345678]
    def ret(at,value,error=0,second=0xfeedface):w[at:at+3]=[value,second,error]
    def read(at,byte):ret(at,1 if byte else 0);w[at+3]=byte
    if kind==0:
        ret(4,3);ret(7,0)
        if arg>=32:
            ret(10,22,1);ret(13,1);read(19,ord('0'));ret(23,4)
        else:
            ret(10,max(4,arg));ret(13,1);ret(16,0)
            read(19,ord('0'));read(23,ord('1'));read(27,ord('2'))
            ret(31,0);ret(34,10);ret(37,0);ret(40,0);ret(43,1);ret(46,0);read(49,ord('3'))
    elif kind==1:
        ret(4,3);ret(7,4);ret(10,0);read(13,ord('0'));read(17,ord('1'))
    elif kind==2:
        ret(4,9,1);ret(7,3)
    elif kind==3:
        ret(4,3);ret(7,9,1);ret(10,3)
    elif kind==4:
        ret(4,3);w[7]=28;ret(8,24,1);ret(11,22,1);ret(14,9,1)
        w[17]=31;ret(18,31);read(21,ord('0'));ret(25,3)
    elif kind==5:
        ret(4,4,second=5);ret(7,0);ret(10,arg);ret(13,0);ret(16,1)
        ret(19,1);read(22,ord('Q'));read(26,0)
    elif kind==6:
        ret(4,9,1);ret(7,0);read(10,ord('0'));ret(14,2)
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
    assert ref['harness_sha256']==sha(ROOT/'scripts/probe-irix-reference-dupfd.py')
    assert sha(ROOT/ref['seed']/'result.json')==ref['seed_result_sha256']
    m=ref['manifest'];cases={c['name']+'-'+str(i):(c,i) for c in m['cases'] for i in c['identities']}
    assert len(cases)==len(ref['observations'])==168
    for path,h in m['sources'].items():assert sha(ROOT/path)==h,path
    assert {o['name'] for o in ref['observations']}==set(cases)
    assert len(m['cases'])==84 and m['identities']==[[0]*4,[1234]*4]
    assert set(ref['checked_files'])==set(m['files'])
    for name,info in m['files'].items():
        f=a.reference/'fixtures'/name
        assert sha(f)==info['sha256'] and f.stat().st_size==info['bytes']
    with tarfile.open(a.reference/'outputs.tgz') as archive:
        members={x.name.removeprefix('./'):x for x in archive.getmembers()}
        assert len(members)==len(archive.getmembers())
        def read(name):return archive.extractfile(members[name]).read()
        status=re.findall(r'^CASE (\S+) (\d+)$',read('status.txt').decode(),re.M)
        assert len(status)==168 and {n for n,_ in status}==set(cases) and all(v=='0' for _,v in status)
        for o in ref['observations']:
            assert read(o['name']+'.out').hex()==o['stdout_hex'] and read(o['name']+'.err')==b''
    oracle={}
    for o in ref['observations']:
        c,i=cases[o['name']];assert o['name'] not in oracle
        oracle[o['name']]=decode(o,c,m['identities'][i])
    exported=dict(reference='IRIX 6.5.22m',result_sha256=sha(a.reference/'result.json'),sources=m['sources'],records=oracle)
    rp=ROOT/'lab/irix-dupfd/reference.json'
    if a.export_reference:rp.write_text(json.dumps(exported,indent=2)+'\n')
    assert json.loads(rp.read_text())==exported
    if not a.runs:assert a.export_reference;print('168 original dupfd records validated');return
    assert a.output
    report=dict(schema=1,status='passed',qualifier_sha256=sha(Path(__file__)),reference_directory=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),reference_records_sha256=sha(rp),records=0,controls=0,runs=[],source_evidence=[])
    revision=json.loads((ROOT/'lab/irix-dupfd/baseline.json').read_text())['source_revision']
    for path in ['sys/compat/irix_o32/irix_o32.c','sys/kern/sys_descrip.c','sys/kern/kern_descrip.c']:
        data=subprocess.check_output(['git','-C',str(ROOT.parent/'NetBSD-nixbench'),'show',revision+':'+path])
        report['source_evidence'].append(dict(repository='NetBSD-xiri',revision=revision,path=path,sha256=hashlib.sha256(data).hexdigest()))
    coverage=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());key=(r['kernel_abi'],r['mode']);assert key not in coverage;coverage.add(key)
        assert tomllib.loads((d/'iris.toml').read_text())['ci']==(key[1]=='ci')
        assert r['status']=='observed-uncompared' and r['clean_shutdown'] and r['manifest']==m
        pin=json.loads((ROOT/'lab/irix-dupfd'/('o32-baseline.json' if key[0]=='o32' else 'baseline.json')).read_text());assert r['pin']==pin
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        assert sha(ROOT/r['seed']/'result.json')==r['seed_result_sha256']
        names={n for n,(c,i) in cases.items() if key[0]=='lp64' or c['abi']=='o32'}
        assert len(r['observations'])==len(names) and {o['name'] for o in r['observations']}==names
        for c in m['cases']:
            if key[0]=='lp64' or c['abi']=='o32':assert sha(d/'media'/c['name'])==m['files'][c['name']]['sha256']
        for o in r['observations']:
            c,i=cases[o['name']];assert decode(o,c,m['identities'][i],True)==oracle[o['name']]
        controls=['native-o32','vendor-asa','native-dupfd']+(['vendor-echo'] if key[0]=='lp64' else [])
        required={(phase,uid,name) for phase in ['before','after'] for uid in [0,1234] for name in controls}
        assert len(r['controls'])==len(required) and {(x['phase'],x['uid'],x['name']) for x in r['controls']}==required
        for x in r['controls']:
            name=x['name'];out={'native-o32':'XIRI_ABI_PROBE\n','vendor-asa':'XIRI_VENDOR_O32\n','vendor-echo':'XIRI_VENDOR_N32\n','native-dupfd':f'NATIVE_DUPFD uid={x["uid"]} allocation=1 flags=1 offset=1 fork=1 eof=1 rollback=1\n'}[name]
            assert x['actual']==dict(errno_bytes=0,errno=0,exit=37 if name=='native-o32' else 0,signal=0,killed=0,stdout=out,stderr='')
            if name=='native-dupfd':assert x['group_absent']
        report['records']+=len(names);report['controls']+=len(required)
        report['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),serial_sha256=sha(d/'serial.log'),fixtures_log_sha256=sha(d/'fixtures.log'),pin=pin,sources=r['sources'],kernel_abi=key[0],mode=key[1],records=len(names),controls=r['controls'],group_cleanup_passed=True,clean_shutdown=True))
    assert coverage=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    report['limits']=['F_DUPFD selector0 only; no new locking commands, foreign close-on-fork flag or broad fcntl command forwarding.',
        'All64 words match the reference without descriptor/error normalization. Exhaustion is a per-process32-descriptor test, not system-wide pressure.',
        'No additional core kernel hook; native descriptor allocation owns references, limits and publication.']
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('Passed',report['records'],'dupfd records and',report['controls'],'native/vendor controls')
if __name__=='__main__':main()
