#!/usr/bin/env python3
"""Compare paired raw window-size and NOCLDSTOP observations."""
import argparse,importlib.util,json,struct
from pathlib import Path
from xiri_lab import ROOT,sha256
spec=importlib.util.spec_from_file_location('signal_reference',ROOT/'scripts/qualify-irix-signal-reference-v2.py')
signal=importlib.util.module_from_spec(spec);spec.loader.exec_module(signal)

def decode_child(data,name,uid,elf,page):
    w=list(struct.unpack('>512I',data));flags=w[3]
    assert flags in (0x20000,0x20008,0x20012)
    assert w[13]==page and w[65]==0
    assert w[481]==flags and w[56]==flags
    # Reuse the independent full signal-frame validator. Check NOCLDSTOP
    # explicitly above, then remove only that bit from its older low-flag
    # contract. Normalize only measured page size and inherited disposition.
    normalized=bytearray(data)
    for word in (3,56,481):struct.pack_into('>I',normalized,word*4,flags&0x1f)
    struct.pack_into('>I',normalized,13*4,4096)
    struct.pack_into('>I',normalized,65*4,0x20000)
    symbols=dict(CASE=1,KIND=2,FLAGS=flags&0x1f,SIGNUM=18,HANDLER=3,SET_KIND=0,
                 OLD_KIND=0,TRAMP=0,REAP=0,FPU=0,RETURN_TEST=0,MASK0=0,MASK1=0,MASK2=0,MASK3=0)
    decoded=signal.decode(bytes(normalized),dict(name=name,abi=name.split('-')[0],symbols=symbols),uid,elf)
    decoded['nocldstop_retained']=True
    return decoded

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--native',type=Path)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    fixtures=ROOT/'.work/irix-winterm-reliability/probes'
    manifest=json.loads((fixtures/'manifest.json').read_text())
    for source,digest in manifest['sources'].items():assert sha256(ROOT/source)==digest
    result=dict(status='original-reference' if not args.native else 'passed',fixtures=manifest,
                reference=str(args.reference),native=str(args.native) if args.native else None,
                winsize_observations=0,child_executions=0,records={})
    for name,item in manifest['files'].items():
        assert sha256(fixtures/name)==item['sha256']
        for identity in (0,1):
            uid=1234 if identity else 0
            key=name+'-'+str(identity)
            ref=args.reference/(key+'.bin');raw=ref.read_bytes()
            assert (args.reference/(key+'.err')).read_bytes()==b''
            entry=dict(reference_sha256=sha256(ref))
            if name.endswith('winsize'):
                assert len(raw)==31*32
                rows=list(struct.iter_unpack('>8I',raw))
                assert [r[0] for r in rows]==list(range(1,32))
                entry['observations']=[list(r) for r in rows]
                result['winsize_observations']+=31
            else:
                entry['reference']=decode_child(raw,name,uid,(fixtures/name).read_bytes(),4096)
                result['child_executions']+=1
            if args.native:
                native=args.native/(key+'.bin');data=native.read_bytes()
                assert (args.native/(key+'.err')).read_bytes()==b''
                entry['native_sha256']=sha256(native)
                if name.endswith('winsize'):assert data==raw,key
                else:entry['native']=decode_child(data,name,uid,(fixtures/name).read_bytes(),8192)
            result['records'][key]=entry
    assert result['winsize_observations']==248 and result['child_executions']==24
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],result['winsize_observations'],'ioctl observations;',result['child_executions'],'child signal/frame controls')
if __name__=='__main__':main()
