#!/usr/bin/env python3
"""Build guarded select fixtures for both original IRIX and Xiri."""
import importlib.util,json,os,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('tcp',ROOT/'scripts/build-irix-tcp.py')
tcp=importlib.util.module_from_spec(spec);spec.loader.exec_module(tcp)

def main():
    if os.environ.get('XIRI_TCP_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_TCP_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-select/probes';out.mkdir(parents=True,exist_ok=True)
    defs=[]
    def case(name,**s):defs.append((name,s))
    for n in [0,1,3,4,31,32,33,63,64,65,127,128,1024]:case('nfds-'+str(n),ND=n)
    for name,s in [
        ('read',dict(R=1)),('write',dict(W=1)),('except',dict(E=1)),
        ('two-reads',dict(R=1,OPEN_FD=4,BIT=4,ND=5,SECOND_FD=1)),
        ('two-read-write',dict(R=1,W=1,OPEN_FD=4,BIT=4,ND=5,SECOND_FD=1)),
        ('read-write',dict(R=1,W=1)),('all-sets',dict(R=1,W=1,E=1)),
        ('null-sets',dict(RP=0,WP=0,EP=0)),('negative-nfds',dict(ND=-1)),
        ('negative-nfds-bad-time',dict(ND=-1,TP=0x80000000)),
        ('negative-nfds-bad-set',dict(ND=-1,RP=0x80000000)),
        ('bad-read-set',dict(RP=0x80000000)),('wrap-read-set',dict(RP=0xfffffffe)),
        ('bad-write-set',dict(WP=0x80000000)),('bad-except-set',dict(EP=0x80000000)),
        ('zero-nfds-bad-set',dict(ND=0,RP=0x80000000)),
        ('null-time-ready',dict(R=1,TP=0)),('bad-time',dict(TP=0x80000000)),
        ('wrap-time',dict(TP=0xfffffffc)),('negative-seconds',dict(R=1,SEC=-1)),
        ('negative-useconds',dict(R=1,USEC=-1)),('million-useconds',dict(R=1,USEC=1000000)),
        ('large-useconds',dict(R=1,USEC=0x7fffffff)),
        ('bad-time-bad-set',dict(TP=0x80000000,RP=0x80000000)),
        ('invalid-time-bad-set',dict(SEC=-1,RP=0x80000000)),
        ('closed-read',dict(R=1,CLOSED=1)),('closed-write',dict(W=1,CLOSED=1)),
        ('closed-except',dict(E=1,CLOSED=1)),('closed-bad-time',dict(R=1,CLOSED=1,TP=0x80000000)),
        ('closed-bad-write',dict(R=1,CLOSED=1,WP=0x80000000)),
        ('ignored-bit31',dict(R=1,ND=31,BIT=31)),('bad-bit31',dict(R=1,ND=32,BIT=31)),
        ('bit31',dict(R=1,ND=32,BIT=31,OPEN_FD=31)),
        ('bit32',dict(R=1,ND=33,BIT=32,OPEN_FD=32)),
        ('bit63',dict(R=1,ND=64,BIT=63,OPEN_FD=63)),
        ('unaligned-read',dict(R=1,ROFF=1)),('unaligned-write',dict(W=1,WOFF=1)),
        ('unaligned-except',dict(E=1,EOFF=1)),('unaligned-time',dict(R=1,TOFF=1)),
        ('readonly-read',dict(R=1,READONLY_R=1)),('readonly-write',dict(R=1,W=1,READONLY_W=1)),
        ('readonly-r-before-except',dict(R=1,E=1,READONLY_R=1)),
        ('readonly-w-before-except',dict(R=1,W=1,E=1,READONLY_W=1)),
        ('readonly-time',dict(R=1,READONLY_T=1)),
        ('alias-read-write',dict(R=1,ALIAS_RW=1)),('alias-read-except',dict(R=1,ALIAS_RE=1)),
        ('timeout',dict(USEC=100000)),('bad-stack',dict(R=1,BAD_STACK=0)),
        ('wrap-stack',dict(R=1,BAD_STACK=0xfffffff0)),
        ('limit-policy',dict(ND=1025,POLICY=1)),
        ('socket-delayed-data',dict(SOCKET=1,MODE=0,R=1,SEC=2)),
        ('socket-delayed-eof',dict(SOCKET=1,MODE=1,R=1,SEC=2)),
        ('socket-null-time',dict(SOCKET=1,MODE=0,R=1,TP=0)),
        ('socket-timeout',dict(SOCKET=1,MODE=2,R=1,USEC=100000)),
        ('socket-writable',dict(SOCKET=1,MODE=2,W=1)),
        ('socket-read-write',dict(SOCKET=1,MODE=2,R=1,W=1))]:case(name,**s)
    result={'schema':1,'files':{},'cases':[], 'sources':{p:tcp.digest(ROOT/p) for p in ['lab/irix-select/probe.S','lab/irix-select/probe.ld','lab/irix-select/reference-peer.S','lab/irix-select/peer.c','scripts/build-irix-select.py']}}
    for abi in ['o32','n32']:
      for indirect in [0,1]:
       for suffix,extra in defs:
        name=f'{abi}-'+('indirect-' if indirect else 'direct-')+suffix
        s=dict(CASE=len(result['cases'])+1,INDIRECT=indirect,ND=4,OPEN_FD=3,BIT=3,R=0,W=0,E=0,SEC=0,USEC=0,ROFF=0,WOFF=0,EOFF=0,TOFF=0,SOCKET=0,MODE=0)
        s.update(extra)
        if abi=='n32':s['N32']=1
        flags=[v for k,n in s.items() for v in ['--defsym',f'{k}={n}']]
        obj,elf=out/(name+'.o'),out/name
        tcp.run('as','-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-G','0',*flags,'-o',obj,ROOT/'lab/irix-select/probe.S')
        tcp.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-select/probe.ld','-o',elf,obj)
        b=bytearray(elf.read_bytes());b[7]=0;struct.pack_into('>I',b,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(b);elf.chmod(0o755)
        result['files'][name]={'sha256':tcp.digest(elf),'bytes':len(b)}
        result['cases'].append({'name':name,'abi':abi,'symbols':s,'reference':True,'record_bytes':512})
    peer=out/'reference-peer'
    count=sum(c['symbols']['SOCKET'] for c in result['cases'])
    tcp.run('as','-EB','-mabi=32','-mips3','-G','0','--defsym',f'COUNT={count}','-o',str(peer)+'.o',ROOT/'lab/irix-select/reference-peer.S')
    tcp.run('ld','-EB','-m','elf32btsmip','--build-id=none','-T',ROOT/'lab/irix-o32/probe.ld','-o',peer,str(peer)+'.o')
    b=bytearray(peer.read_bytes());b[7]=0;struct.pack_into('>I',b,36,0x20000101);peer.write_bytes(b);peer.chmod(0o755)
    result['sources']['lab/irix-o32/probe.ld']=tcp.digest(ROOT/'lab/irix-o32/probe.ld')
    result['files']['reference-peer']={'sha256':tcp.digest(peer),'bytes':len(b)}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(len(result['cases']),'select fixtures built')
if __name__=='__main__':main()
