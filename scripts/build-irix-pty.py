#!/usr/bin/env python3
"""Build libc-free PTY interface and permission probes for both IRIX ABIs."""
import importlib.util,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)

def main():
    if os.environ.get('XIRI_TCP_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_TCP_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-pty/probes';out.mkdir(parents=True,exist_ok=True)
    definitions=[]
    def case(name,kind,path='owned',**kw):definitions.append((name,kind,path,kw))
    for mode in [0,1,2,4,6,128,130,132,134,2048,2054,2178,2182,3,7,16,0xffffffff]:case('open-'+str(mode),0,MODE=mode)
    for mode in [0,4,128,132,8,12,136,16,0xffffffff]:case('setfl-'+str(mode),1,MODE=mode)
    for mode in [0,384,420,448]:case('chmod-'+str(mode),2,MODE=mode)
    case('chmod-root',2,'root',MODE=384)
    for path in ['missing','']:case('chmod-'+('missing' if path else 'empty'),2,path,MODE=384)
    for pointer in [0,0x80000000,0xfffffffe]:case('chmod-pointer-'+str(pointer),2,POINTER=pointer,MODE=384)
    for uid,gid in [(0,0),(1234,1234),(2345,2345),(0xffffffff,0xffffffff),(1234,0xffffffff),(0xffffffff,1234)]:case('chown-'+str(uid)+'-'+str(gid),3,OWNER=uid,GROUP=gid)
    case('chown-root',3,'root',OWNER=1234,GROUP=1234)
    case('chown-missing',3,'missing',OWNER=1234,GROUP=1234)
    for pointer in [0,0x80000000,0xfffffffe]:case('chown-pointer-'+str(pointer),3,POINTER=pointer)
    case('unlock',4,'/dev/ptc')
    case('unlock-file',4)
    case('unlock-bad-fd',4,'/dev/ptc',BAD_FD=0xffffffff)
    for pointer in [0,0x80000000,0xfffffffe]:case('unlock-pointer-'+str(pointer),4,'/dev/ptc',POINTER=pointer)
    for name,kw in [('command',dict(COMMAND=0x5003)),('timeout',dict(TIMEOUT=1)),('negative-timeout',dict(TIMEOUT=0xffffffff)),('length',dict(LENGTH=1)),('data',dict(DATA=0x00400000))]:case('unlock-'+name,4,'/dev/ptc',**kw)
    sources=['scripts/build-irix-pty.py','lab/irix-pty/probe.c','lab/irix-pty/start.S','lab/irix-access/probe.ld','lab/irix-pty/record-setup.sh']
    manifest=dict(schema=1,identities=[[0,0,0,0],[1234,1234,1234,1234]],sources={p:base.digest(ROOT/p) for p in sources},files={},cases=[])
    for abi in ['o32','n32']:
        for indirect in [0,1]:
            flags=['-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
            start=out/(abi+'-start.o');base.run('gcc',*flags,'-c',ROOT/'lab/irix-pty/start.S','-o',start)
            for suffix,kind,path,kw in definitions:
                name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix
                syms=dict(CASE=len(manifest['cases'])+1,KIND=kind,N32=int(abi=='n32'),VERSION=3 if abi=='n32' else 2,INDIRECT=indirect,MODE=2,OWNER=1234,GROUP=1234,COMMAND=0x5002,TIMEOUT=0,LENGTH=0,DATA=0);syms.update(kw)
                obj=out/(name+'.o');elf=out/name
                base.run('gcc',*flags,'-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror',*['-D'+k+'='+str(v)+'U' for k,v in syms.items()],'-DPATH='+json.dumps(path),'-c',ROOT/'lab/irix-pty/probe.c','-o',obj)
                base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-access/probe.ld','-o',elf,start,obj)
                b=bytearray(elf.read_bytes());b[7]=0;struct.pack_into('>I',b,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(b);elf.chmod(0o755)
                manifest['files'][name]=dict(sha256=base.digest(elf),bytes=len(b))
                manifest['cases'].append(dict(name=name,abi=abi,path=path,symbols=syms,identities=[0,1]))
    shutil.copyfile(ROOT/'lab/irix-pty/record-setup.sh',out/'setup.sh')
    manifest['files']['setup.sh']=dict(sha256=base.digest(out/'setup.sh'),bytes=(out/'setup.sh').stat().st_size)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(len(definitions),'variants;',len(manifest['cases']),'fixtures')
if __name__=='__main__':main()
