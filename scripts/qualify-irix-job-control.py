#!/usr/bin/env python3
"""Compare independently observed IRIX sleep/child records with a candidate.

Only defined child-event fields are compared: the reference copies unspecified
padding/accounting and no-event status bytes. The candidate must zero unused
fields. P_PGID/0 exit selection is recorded as a specific native-policy delta.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import tarfile

ROOT=Path(__file__).resolve().parent.parent
CANARY=0xfeedface
FILL=0xa5a5a5a5


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def archive(path):
    with tarfile.open(path) as stream:
        result = {}
        for member in stream.getmembers():
            if not member.isfile():
                continue
            name = member.name.removeprefix('./')
            assert name not in result, (path, 'duplicate member', name)
            result[name] = stream.extractfile(member).read()
        return result


def reference(path,prefix,length):
    data=archive(path);result={}
    for name,value in data.items():
        if not(name.startswith(prefix+'-') and name.endswith('.out')):
            continue
        stem=name[:-4]
        assert data[stem+'.guard'].strip()==b'GUARD reaped=1 exit=0 signal=0 timeout=0 absent=1',stem
        assert data[stem+'.err']==b'',stem
        assert len(value)==length,(stem,len(value))
        parts=stem[len(prefix)+1:].split('-')
        exe='-'.join(parts[:2]);uid=1234 if parts[2]=='1' else 0
        key=(exe,uid,*map(int,parts[3:]))
        assert key not in result,key
        result[key]=value
    return result,data


def native(data,expected_length=None):
    result={}
    chunks=re.split(r'^CASE:([^\n]+)\n',data.decode(),flags=re.M)
    assert chunks[0]=='',chunks[0]
    for i in range(1,len(chunks),2):
        label,chunk=chunks[i:i+2];parts=label.split(':')
        key=(parts[0],int(parts[1]),*[int(p) if p.isdigit() else p for p in parts[2:]])
        assert re.search(r'^OBS path=\S+ errno_bytes=0 errno=0 exit=0 signal=0 killed=0$',chunk,re.M),label+': '+chunk[:180]
        assert re.search(r'^STDERR bytes=0 hex=$',chunk,re.M),label
        assert re.search(r'^GROUP absent=1$',chunk,re.M),label
        m=re.search(r'^STDOUT bytes=(\d+) hex=([0-9a-f]*)$',chunk,re.M)
        assert m,label
        value=bytes.fromhex(m[2]);assert len(value)==int(m[1]),label
        if expected_length is not None:assert len(value)==expected_length,(label,len(value))
        assert key not in result,key
        result[key]=value
    return result


def words(data):
    return list(struct.unpack('>'+str(len(data)//4)+'I',data))


def sleep_record(data,key):
    r=words(data);exe,uid,case=key
    assert r[:6]==[0x584e4150,case,uid,uid,uid,uid],key
    assert r[13]==CANARY,key
    assert r[24:30]==[0,CANARY,0,0,CANARY,0],key
    elapsed=r[82]+r[83]/1e6-r[80]-r[81]/1e6
    assert 0<=elapsed<4.5,(key,elapsed)
    detail=dict(reply=r[12:15],signals=r[15],elapsed=round(elapsed,6))
    output=bytearray(data)
    if 20<=case<=29:
        assert r[15]==1 and r[16:20]==[0,0,0,0] and r[20:23]==[0,CANARY,0],key
        if case==21:assert 2<=elapsed<4.5,(key,elapsed)
        else:assert .03<=elapsed<1.5,(key,elapsed)
        position={20:164,21:164,24:165,27:132,28:136,29:164}.get(case)
        if position is not None:
            sec,ns=struct.unpack_from('>II',data,position)
            assert ns<1000000000 and ns%10000000==0,(key,sec,ns)
            remaining=sec+ns/1e9
            duration=21474836.47 if case==29 else 2
            assert 0<=remaining<=duration,(key,remaining)
            if case==21:assert 1<=remaining<2,(key,remaining)
            else:assert abs(duration-remaining-elapsed)<.08,(key,remaining,elapsed)
            detail['remaining']=[sec,ns]
            output[position:position+8]=bytes(8)
        if case==26:
            assert r[51]==1,(key,r[51])
    else:
        assert r[15]==0,key
    output[320:336]=bytes(16)
    return bytes(output),detail


def child_record(data,key,reference_system):
    r=words(data);exe,uid,mode,selector=key
    assert r[:8]==[0x5843484c,mode,selector,(8 if mode<2 else 0)|(0x20000 if mode&1 else 0),uid,uid,uid,uid],key
    assert r[8]>0 and r[9]>0 and r[10]>0,key
    assert r[24:27]==[0,CANARY,0],key
    complete=selector<5
    assert r[13]==(0 if complete else 2),key
    if complete:
        assert r[16:19]==([0,0,1] if mode&1 else [1,2,3]),(key,r[16:19])
        assert r[20]==r[18],key
    else:
        assert r[16:20]==[0,0,0,0] and r[44:47]==[0,9,0],(key,r[16:20],r[44:47])
        assert r[20]==1,key
    summary=dict(counts=r[16:21],waits=[],signals=[],pgid_zero_exit_delta=False)
    for slot in range(9):
        at=64+36*slot;reply=r[at:at+3];info=r[at+4:at+36]
        if not complete:
            if slot==0:
                assert reply==[10 if selector==5 else 22,CANARY,1],(key,reply)
                assert info==[FILL]*32,key
            else:assert r[at:at+36]==[0]*36,key
            continue
        anomalous=reference_system and selector==2 and slot in [6,7]
        if slot==8 or anomalous:
            assert reply==[10,CANARY,1] and info==[FILL]*32,(key,slot,reply)
        else:
            assert reply==[0,9472 if slot==7 else CANARY,0],(key,slot,reply)
            if slot in [2,5]:
                assert info[:5]==[0]*5,(key,slot,info[:6])
                if not reference_system:assert info[5:]==[0xffffffff]+[0]*26,(key,slot)
            else:
                code,status=(5,23) if slot<2 else (6,25) if slot<5 else (1,37)
                assert info[:6]==[18,code,0,r[10],0,status],(key,slot,info[:6])
                if not reference_system:assert info[6:]==[0]*26,(key,slot)
        summary['waits'].append(dict(reply=reply,info=info[:6] if slot not in [2,5] else info[:5]))
    if complete:
        if reference_system and selector==2:
            assert r[19]==0 and r[44:47]==[0,9472,0],key
            summary['pgid_zero_exit_delta']=True
        else:assert r[19]==1 and r[44:47]==[0,0,0],key
    for n in range(r[20]):
        at=400+36*n;info=r[at+4:at+36]
        assert r[at]==(18|(0x80000000 if mode<2 else 0)),(key,r[at])
        if mode<2:
            if complete:
                code,status=(1,37) if mode&1 else [(5,23),(6,25),(1,37)][n]
                assert info[:6]==[18,code,0,r[10],0,status],(key,n,info[:6])
            else:
                assert info[:5]==[18,2 if mode&1 else info[1],0,r[10],0],(key,n,info[:6])
                assert (info[1],info[5]) in [(5,23),(2,9)],(key,n,info[:6])
            if not reference_system:assert info[6:]==[0]*26,(key,n)
        summary['signals'].append(info[:6] if mode<2 else [18])
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sleep-reference',type=Path,default=ROOT/'.work/job-control/sleep-reference-v3.tar')
    p.add_argument('--child-reference',type=Path,default=ROOT/'.work/job-control/children-reference-v3.tar')
    p.add_argument('--baseline',type=Path,default=ROOT/'.work/job-control/baseline-matrices.tgz')
    p.add_argument('--candidate',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();result=dict(schema=1,status='failed',sleep=[],children=[])
    try:
        sr,sd=reference(a.sleep_reference,'sleep',512)
        cr,cd=reference(a.child_reference,'child',2560)
        assert len(sr)==264 and len(cr)==256,(len(sr),len(cr))
        assert sd['timeout.guard'].strip()==b'GUARD reaped=1 exit=-1 signal=9 timeout=1 absent=1'
        candidate=archive(a.candidate);baseline=archive(a.baseline)
        for group,original in [('nanosleep',sd),('children',cd)]:
            manifest=json.loads(candidate[group+'/manifest.json'])
            assert manifest==json.loads(original['manifest.json']),group
            for source,wanted in manifest['sources'].items():
                assert digest(ROOT/source)==wanted,source
            for name,info in manifest['files'].items():
                assert hashlib.sha256(original[name]).hexdigest()==info['sha256'],(group,name,'reference ELF')
                match=re.search(r'^SHA256 \('+re.escape(group+'/'+name)+r'\) = ([0-9a-f]{64})$',
                                candidate['digests.txt'].decode(),re.M)
                assert match and match[1]==info['sha256'],(group,name)
        sn=native(candidate['sleep.txt'],512);cn=native(candidate['children.txt'],2560)
        assert sr.keys()==sn.keys() and cr.keys()==cn.keys()
        for key,old in sr.items():
            before,ro=sleep_record(old,key);after,no=sleep_record(sn[key],key)
            assert before==after,(key,'sleep bytes differ',[i for i,(x,y) in enumerate(zip(before,after)) if x!=y])
            result['sleep'].append(dict(case=list(key),reference=ro,candidate=no,passed=True))
        for key,old in cr.items():
            ro=child_record(old,key,True);no=child_record(cn[key],key,False)
            result['children'].append(dict(case=list(key),reference=ro,candidate=no,passed=True))
        bn=native(baseline['native.txt']);nn=native(candidate['native.txt']);assert bn==nn
        result['native_controls']={':'.join(map(str,k)):v.decode().strip() for k,v in nn.items()}
        bs=native(baseline['sleep.txt'],512);bc=native(baseline['children.txt'],2560)
        assert len(bs)==24 and all(words(v)[12:15]==[89,CANARY,1] for v in bs.values())
        assert len(bc)==16 and all(words(v)[64:67]==[22,CANARY,1] for v in bc.values())
        result['baseline']=dict(nanosleep_enosys=len(bs),stop_wait_einval=len(bc))
        result['scope']=dict(sleep_comparisons=264,child_event_contracts=256,
            pgid_zero_exit_policy_differences=32,native_controls=4,
            undefined_reference_siginfo_bytes_excluded=True,
            candidate_unused_siginfo_bytes_required_zero=True)
        result['inputs']={k:dict(path=str(getattr(a,k)),sha256=digest(getattr(a,k))) for k in ['sleep_reference','child_reference','baseline','candidate']}
        compared_sources = ['nanosleep.c', 'children.c', 'call.S', 'native-children.c']
        result['sources']={str(f.relative_to(ROOT)):digest(f) for f in
            [Path(__file__).resolve(),*[ROOT/'lab/irix-job-control'/name for name in compared_sources]]}
        result['reference_instrumentation']={group:hashlib.sha256(data['guardian.c']).hexdigest()
            for group,data in [('sleep',sd),('children',cd)]}
        result['status']='passed'
    except Exception as error:
        result['error']=repr(error)
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k in ['status','error','baseline']}))
    return result['status']!='passed'


if __name__=='__main__':
    raise SystemExit(main())
