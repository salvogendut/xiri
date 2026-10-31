#!/usr/bin/env python3
"""Build guarded SIOCNREAD fixtures for both original IRIX and Xiri."""
import importlib.util,json,os,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('tcp',ROOT/'scripts/build-irix-tcp.py')
tcp=importlib.util.module_from_spec(spec);spec.loader.exec_module(tcp)

def main():
    if os.environ.get('XIRI_TCP_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_TCP_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-siocnread/probes';out.mkdir(parents=True,exist_ok=True)
    defs=[]
    def case(name,**s):defs.append((name,s))
    for state,label in [(0,'unconnected'),(1,'empty'),(2,'queued'),(3,'partial'),(4,'eof')]:
        case(label,STATE=state)
    for label,extra in [
        ('repeat',dict(REPEAT=1)),('nonblocking',dict(NONBLOCK=1)),
        ('unaligned',dict(ALIGN=1)),('null',dict(BUFPTR=0)),
        ('high',dict(BUFPTR=0x80000000)),('wrap',dict(BUFPTR=0xfffffffe)),
        ('readonly',dict(READONLY=1)),('tail1',dict(TAIL=1)),
        ('tail2',dict(TAIL=2)),('tail3',dict(TAIL=3)),('tail4',dict(TAIL=4)),
        ('bad-stack',dict(BAD_STACK=0)),('wrap-stack',dict(BAD_STACK=0xfffffff0)),
        ('unknown',dict(COMMAND=0x4004730b)),('wrong-size',dict(COMMAND=0x4008730a)),
        ('native-selector',dict(COMMAND=0x4004667f)),('tcgeta',dict(COMMAND=0x5401))]:
        case(label,**extra)
    case('empty-nonblocking',STATE=1,NONBLOCK=1)
    case('eof-null',STATE=4,BUFPTR=0)
    case('eof-nonblocking',STATE=4,NONBLOCK=1)
    case('empty-null',STATE=1,BUFPTR=0)
    for label,extra in [
        ('regular',{}),('regular-partial',dict(PRE_READ=1)),
        ('write-only',dict(OPEN_FLAGS=1)),('read-write',dict(OPEN_FLAGS=2)),
        ('regular-null',dict(BUFPTR=0)),('regular-unknown',dict(COMMAND=0x4004730b)),
        ('closed',dict(CLOSED=1)),('closed-null',dict(CLOSED=1,BUFPTR=0)),
        ('devnull',dict(PATH='/dev/null')),('directory',dict(PATH='.')),
        ('fifo',dict(PATH='fifo',OPEN_FLAGS=0x80))]:
        case(label,KIND=1,**extra)
    for fd,label in [(-1,'negative'),(65535,'large')]:
        case(label,KIND=2,FD=fd)
        case(label+'-null',KIND=2,FD=fd,BUFPTR=0)
    case('bad-fd-unknown',KIND=2,FD=-1,COMMAND=0x4004730b,BUFPTR=0)
    result={'schema':1,'files':{},'cases':[], 'sources':{p:tcp.digest(ROOT/p) for p in ['lab/irix-siocnread/probe.S','lab/irix-siocnread/probe.ld','lab/irix-siocnread/reference-peer.S','lab/irix-siocnread/peer.c','scripts/build-irix-siocnread.py']}}
    for abi in ['o32','n32']:
      for indirect in [0,1]:
       for suffix,extra in defs:
        name=f'{abi}-'+('indirect-' if indirect else 'direct-')+suffix
        s=dict(CASE=len(result['cases'])+1,INDIRECT=indirect,KIND=0,STATE=2,COMMAND=0x4004730a,ALIGN=0,OPEN_FLAGS=0)
        s.update({k:v for k,v in extra.items() if k!='PATH'})
        (out/'path.inc').write_text('.asciz '+json.dumps(extra.get('PATH','input.txt'))+'\n')
        if abi=='n32':s['N32']=1
        flags=[v for k,n in s.items() for v in ['--defsym',f'{k}={n}']]
        obj,elf=out/(name+'.o'),out/name
        tcp.run('as','-I',out,'-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-G','0',*flags,'-o',obj,ROOT/'lab/irix-siocnread/probe.S')
        tcp.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-siocnread/probe.ld','-o',elf,obj)
        b=bytearray(elf.read_bytes());b[7]=0;struct.pack_into('>I',b,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(b);elf.chmod(0o755)
        result['files'][name]={'sha256':tcp.digest(elf),'bytes':len(b)}
        result['cases'].append({'name':name,'abi':abi,'symbols':s,'reference':True,'record_bytes':160,'path':extra.get('PATH','input.txt')})
    peer=out/'reference-peer'
    count=2*sum(c['symbols']['KIND']==0 and c['symbols']['STATE']>0 for c in result['cases'])
    tcp.run('as','-EB','-mabi=32','-mips3','-G','0','--defsym',f'COUNT={count}','-o',str(peer)+'.o',ROOT/'lab/irix-siocnread/reference-peer.S')
    tcp.run('ld','-EB','-m','elf32btsmip','--build-id=none','-T',ROOT/'lab/irix-o32/probe.ld','-o',peer,str(peer)+'.o')
    b=bytearray(peer.read_bytes());b[7]=0;struct.pack_into('>I',b,36,0x20000101);peer.write_bytes(b);peer.chmod(0o755)
    result['sources']['lab/irix-o32/probe.ld']=tcp.digest(ROOT/'lab/irix-o32/probe.ld')
    result['files']['reference-peer']={'sha256':tcp.digest(peer),'bytes':len(b)}
    import shutil
    shutil.copyfile(ROOT/'lab/irix-siocnread/setup.sh',out/'setup.sh')
    result['files']['setup.sh']={'sha256':tcp.digest(out/'setup.sh'),'bytes':(out/'setup.sh').stat().st_size}
    result['sources']['lab/irix-siocnread/setup.sh']=tcp.digest(ROOT/'lab/irix-siocnread/setup.sh')
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(len(result['cases']),'siocnread fixtures built')
if __name__=='__main__':main()
