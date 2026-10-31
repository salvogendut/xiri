#!/usr/bin/env python3
"""Build original guarded fxstat fixtures, identical on IRIX and NetBSD."""
import importlib.util,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)

def main():
    if os.environ.get('XIRI_TCP_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_TCP_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-fxstat/probes';out.mkdir(parents=True,exist_ok=True)
    defs=[]
    def case(name,path='tree/file',**symbols):defs.append((name,path,symbols))
    case('file')
    case('write-only',OPEN_FLAGS=1)
    case('read-write',OPEN_FLAGS=2)
    for name in ['empty','dir','large']:case(name,path='tree/'+name)
    case('null-device',path='/dev/null')
    case('fifo',path='tree/fifo',OPEN_FLAGS=2)
    case('stdin-unreadable',path='input.txt',FD=0)
    case('closed',CLOSED=1)
    case('reused',REOPEN=1)
    for fd in [-1,31,1024,2147483647,-2147483648]:case('fd-'+str(fd),FD=fd)
    for name,symbols in [('null-out',dict(BUFPTR=0)),('high-out',dict(BUFPTR=0x80000000)),('wrap-out',dict(BUFPTR=0xfffffff0)),('readonly-out',dict(READONLY=1)),('align-1',dict(ALIGN=1)),('align-2',dict(ALIGN=2)),('align-4',dict(ALIGN=4)),('align-7',dict(ALIGN=7)),('bad-stack',dict(BAD_STACK=0))]:case(name,**symbols)
    for tail in [0,1,4,8,64,128,135,136,137,148,151,152,153]:case('tail-'+str(tail),TAIL=tail)
    case('bad-fd-bad-out',FD=-1,BUFPTR=0)
    for version in [0,1,3,4,-1]:
        case('version-'+str(version),VERSION=version)
        case('version-'+str(version)+'-bad-fd',VERSION=version,FD=-1)
        case('version-'+str(version)+'-bad-out',VERSION=version,BUFPTR=0)
        case('version-'+str(version)+'-bad-both',VERSION=version,FD=-1,BUFPTR=0)
    for name,symbols in [('align-1',dict(ALIGN=1)),('readonly',dict(READONLY=1)),('tail-1',dict(TAIL=1)),('tail-151',dict(TAIL=151)),('tail-152',dict(TAIL=152))]:case('v3-'+name,VERSION=3,**symbols)
    case('v3-large',path='tree/large',VERSION=3)
    result={'schema':1,'sources':{n:base.digest(ROOT/n) for n in ['scripts/build-irix-fxstat.py','lab/irix-fxstat/probe.S','lab/irix-fxstat/probe.ld','lab/irix-fxstat/setup.sh']},'files':{},'cases':[]}
    for abi in ['o32','n32']:
      for indirect in [0,1]:
       for suffix,path,extra in defs:
        name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix
        syms=dict(CASE=len(result['cases'])+1,VERSION=2,INDIRECT=indirect,ALIGN=0,OPEN_FLAGS=0);syms.update(extra)
        if abi=='n32':syms['N32']=1
        (out/'path.inc').write_text('.asciz '+json.dumps(path)+'\n')
        obj,elf=out/(name+'.o'),out/name
        flags=[x for k,v in syms.items() for x in ['--defsym',f'{k}={v}']]
        base.run('as','-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-G','0','-I',out,*flags,'-o',obj,ROOT/'lab/irix-fxstat/probe.S')
        base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-fxstat/probe.ld','-o',elf,obj)
        b=bytearray(elf.read_bytes());b[7]=0;struct.pack_into('>I',b,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(b);elf.chmod(0o755)
        result['files'][name]={'sha256':base.digest(elf),'bytes':len(b)}
        result['cases'].append({'name':name,'path':path,'abi':abi,'symbols':syms,'record_bytes':576})
    shutil.copyfile(ROOT/'lab/irix-fxstat/setup.sh',out/'setup.sh')
    result['files']['setup.sh']={'sha256':base.digest(out/'setup.sh'),'bytes':(out/'setup.sh').stat().st_size}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(len(defs),'variants;',len(result['cases']),'fxstat fixtures built')
if __name__=='__main__':main()
