#!/usr/bin/env python3
"""Independently verify IRIX time records and native clock/ABI semantics."""
import datetime,argparse,hashlib,json,struct,subprocess,tarfile,re,tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

PIN_LABEL_NOTE = 'Initial captures retain a copied F_TIME descriptor-allocation description. Only this human-readable label is accepted as an alias; all source, configuration and binary fields must match the corrected pin exactly. Raw results are preserved.'

def check_pin(actual,expected):
    assert expected['description']=='Measured IRIX time and gettimeofday'
    assert actual==expected or actual==dict(expected,description='Measured IRIX F_TIME descriptor allocation')

def clock_bounds(run):
    values=[]
    for key in ['clock_before','clock_after']:
        dates=re.findall(r'^(\d{4} \d{2} \d{2} \d{2} \d{2} \d{2})$',run[key].replace('\r',''),re.M)
        assert len(dates)==1,(key,dates)
        values.append(int(datetime.datetime.strptime(dates[0],'%Y %m %d %H %M %S').replace(tzinfo=datetime.timezone.utc).timestamp()))
    assert 0<values[0]<=values[1]<0x80000000
    return values

def decode(o,case,ids,bounds,page,native=False):
    if native:
        x=o['actual'];assert x['errno_bytes']==x['errno']==x['exit']==x['signal']==x['killed']==0 and not x['stderr']
        assert o['group_absent'];data=bytes.fromhex(x['stdout_hex'])
    else:
        assert o['exit']==0 and not o['stderr'];data=bytes.fromhex(o['stdout_hex'])
    assert len(data)==256
    w=list(struct.unpack('>64I',data));s=case['symbols'];mode=s['MODE'];trap=s['TRAP']
    offset={0:8,1:0xffffffff,2:9,3:10,4:11,5:0xffffffff,6:0xffffffff,7:0xffffffff,8:8,9:28,10:31}[mode]
    assert w[:6]==[0x5854494d,s['CASE'],trap,mode,page,offset],o['name']
    assert w[28:32]==ids and w[23:28]==[0,s['SECOND'],0,0,0]
    assert w[7:9]==w[13:15]==[0xfeedface,0] and w[10]==0xfeedface
    assert w[17:19]==w[21:23]==[0xa5a5a5a5]*2
    early,late=w[15]*1000000+w[16],w[19]*1000000+w[20]
    assert 0<=w[16]<1000000 and 0<=w[20]<1000000
    assert bounds[0]<=w[15]<=w[6]<=w[12]<=w[19]<=bounds[1]
    assert 50000<=late-early<=10000000,(o['name'],'progression',late-early)
    assert w[12]-w[6]<=1
    buf=bytes(w[32:]);want=bytearray([0xa5]*32)
    if trap==1013:
        assert w[11]==0 and w[6]<=w[9]<=w[12]
    else:
        assert trap==1128
        success=mode in [0,2,3,4]
        assert (w[9],w[11])==((0,0) if success else (14,1)),o['name']
        if success:
            sec,usec=struct.unpack('>II',buf[offset:offset+8])
            assert w[6]<=sec<=w[12] and usec<1000000
            assert early<=sec*1000000+usec<=late
            want[offset:offset+8]=buf[offset:offset+8]
        elif mode==9:
            sec=struct.unpack('>I',buf[28:])[0]
            assert w[6]<=sec<=w[12]
            want[28:]=buf[28:]
        elif mode==10:
            assert buf[31] in {v>>24 for v in range(w[6],w[12]+1)}
            want[31]=buf[31]
    assert buf==want,(o['name'],'destination or guards',buf.hex(),want.hex())
    return w

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True);p.add_argument('--export-reference',action='store_true')
    p.add_argument('runs',nargs='*',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    ref=json.loads((a.reference/'result.json').read_text());assert ref['status']=='observed' and ref['scope']=='full' and ref['clean_shutdown']
    assert ref['harness_sha256']==sha(ROOT/'scripts/probe-irix-reference-time.py')
    assert sha(ROOT/ref['seed']/'result.json')==ref['seed_result_sha256']
    m=ref['manifest'];cases={c['name']+'-'+str(i):(c,i) for c in m['cases'] for i in c['identities']}
    assert len(cases)==len(ref['observations'])==192
    for path,h in m['sources'].items():assert sha(ROOT/path)==h,path
    assert {o['name'] for o in ref['observations']}==set(cases)
    assert len(m['cases'])==96 and m['identities']==[[0]*4,[1234]*4]
    assert set(ref['checked_files'])==set(m['files'])
    for name,info in m['files'].items():
        f=a.reference/'fixtures'/name
        assert sha(f)==info['sha256'] and f.stat().st_size==info['bytes']
    with tarfile.open(a.reference/'outputs.tgz') as archive:
        members={x.name.removeprefix('./'):x for x in archive.getmembers()}
        assert len(members)==len(archive.getmembers())
        def read(name):return archive.extractfile(members[name]).read()
        status=re.findall(r'^CASE (\S+) (\d+)$',read('status.txt').decode(),re.M)
        assert len(status)==192 and {n for n,_ in status}==set(cases) and all(v=='0' for _,v in status)
        for o in ref['observations']:
            assert read(o['name']+'.out').hex()==o['stdout_hex'] and read(o['name']+'.err')==b''
    oracle={}
    for o in ref['observations']:
        c,i=cases[o['name']];assert o['name'] not in oracle
        oracle[o['name']]=decode(o,c,m['identities'][i],clock_bounds(ref),4096)
    exported=dict(reference='IRIX 6.5.22m',result_sha256=sha(a.reference/'result.json'),sources=m['sources'],records=oracle)
    rp=ROOT/'lab/irix-time/reference.json'
    if a.export_reference:rp.write_text(json.dumps(exported,indent=2)+'\n')
    assert json.loads(rp.read_text())==exported
    if not a.runs:assert a.export_reference;print('192 original time records validated');return
    assert a.output
    report=dict(schema=1,status='passed',qualifier_sha256=sha(Path(__file__)),pin_label_note=PIN_LABEL_NOTE,reference_directory=str(a.reference),reference_result_sha256=sha(a.reference/'result.json'),reference_records_sha256=sha(rp),records=0,controls=0,runs=[],source_evidence=[])
    revision=json.loads((ROOT/'lab/irix-time/baseline.json').read_text())['source_revision']
    for path in ['sys/compat/irix_o32/irix_o32.c','sys/kern/kern_tc.c','sys/arch/mips/mips/copy.S']:
        data=subprocess.check_output(['git','-C',str(ROOT.parent/'NetBSD-nixbench'),'show',revision+':'+path])
        report['source_evidence'].append(dict(repository='NetBSD-xiri',revision=revision,path=path,sha256=hashlib.sha256(data).hexdigest()))
    coverage=set()
    for d in a.runs:
        r=json.loads((d/'result.json').read_text());key=(r['kernel_abi'],r['mode']);assert key not in coverage;coverage.add(key)
        assert tomllib.loads((d/'iris.toml').read_text())['ci']==(key[1]=='ci')
        assert r['status']=='observed-uncompared' and r['clean_shutdown'] and r['manifest']==m
        pin=json.loads((ROOT/'lab/irix-time'/('o32-baseline.json' if key[0]=='o32' else 'baseline.json')).read_text());check_pin(r['pin'],pin)
        for path,h in r['sources'].items():assert sha(ROOT/path)==h,path
        assert sha(ROOT/r['seed']/'result.json')==r['seed_result_sha256']
        names={n for n,(c,i) in cases.items() if key[0]=='lp64' or c['abi']=='o32'}
        assert len(r['observations'])==len(names) and {o['name'] for o in r['observations']}==names
        for c in m['cases']:
            if key[0]=='lp64' or c['abi']=='o32':assert sha(d/'media'/c['name'])==m['files'][c['name']]['sha256']
        for o in r['observations']:
            c,i=cases[o['name']];decode(o,c,m['identities'][i],clock_bounds(r),8192 if key[0]=='lp64' else 4096,True)
        controls=['native-o32','vendor-asa','native-time']+(['vendor-echo'] if key[0]=='lp64' else [])
        required={(phase,uid,name) for phase in ['before','after'] for uid in [0,1234] for name in controls}
        assert len(r['controls'])==len(required) and {(x['phase'],x['uid'],x['name']) for x in r['controls']}==required
        for x in r['controls']:
            name=x['name'];out={'native-o32':'XIRI_ABI_PROBE\n','vendor-asa':'XIRI_VENDOR_O32\n','vendor-echo':'XIRI_VENDOR_N32\n','native-time':f'NATIVE_TIME uid={x["uid"]} seconds=1 microseconds=1 progression=1 select=1\n'}[name]
            assert x['actual']==dict(errno_bytes=0,errno=0,exit=37 if name=='native-o32' else 0,signal=0,killed=0,stdout=out,stderr='')
            if name=='native-time':assert x['group_absent']
        report['records']+=len(names);report['controls']+=len(required)
        report['runs'].append(dict(directory=str(d),result_sha256=sha(d/'result.json'),serial_sha256=sha(d/'serial.log'),fixtures_log_sha256=sha(d/'fixtures.log'),pin=pin,sources=r['sources'],kernel_abi=key[0],mode=key[1],records=len(names),controls=r['controls'],group_cleanup_passed=True,clean_shutdown=True))
    assert coverage=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}
    report['limits']=['Raw time ignores all pointer arguments; libc is responsible for its optional output pointer.',
        'Gettimeofday has one destination, two signed32-bit fields, no kernel timezone argument; null is EFAULT.',
        'Absolute seconds differ between boots. Each record must match its own native date bounds and ordering; microseconds, progression, returns and guarded/partial writes are checked independently.',
        'Current positive signed32-bit dates only; pre-epoch, 2038 overflow, wall-clock adjustment, timezone/DST and physical hardware remain unqualified.']
    a.output.write_text(json.dumps(report,indent=2)+'\n');print('Passed',report['records'],'time records and',report['controls'],'native/vendor controls')
if __name__=='__main__':main()
