#!/usr/bin/env python3
"""Build original descriptor/session and argv/envp exec probes."""
import importlib.util,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)

def main():
    if os.environ.get('XIRI_MMAP_LOCAL_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_MMAP_LOCAL_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-mmap-local/probes';out.mkdir(parents=True,exist_ok=True)
    definitions=[]
    def case(name,**kw):definitions.append((name,kw))
    case('private')
    case('local',FLAGS=0x82)
    case('fixed-zero',FLAGS=0x12)
    case('fixed-local-zero',FLAGS=0x92)
    case('fixed-local-page',FLAGS=0x92,ADDRESS=0x0e100000,LENGTH=8192)
    case('fixed-local-one-byte',FLAGS=0x92,LENGTH=1)
    case('fixed-local-replace',FLAGS=0x92,ADDRESS=0x0e100000,LENGTH=8192,REPLACE=1)
    case('replace-invalid-fd',FLAGS=0x92,ADDRESS=0x0e100000,LENGTH=8192,REPLACE=1,FD_MODE=1)
    case('fixed-local-invalid-fd',FLAGS=0x92,FD_MODE=1)
    case('fixed-local-writeonly',FLAGS=0x92,FD_MODE=2)
    case('fixed-local-closed',FLAGS=0x92,FD_MODE=3)
    case('fixed-local-file',FLAGS=0x92,ADDRESS=0x0e100000,FILE_KIND=1)
    case('fixed-local-directory',FLAGS=0x92,FILE_KIND=2)
    case('fixed-local-readonly',FLAGS=0x92,PROTECTION=1)
    case('fixed-local-readonly-fault',FLAGS=0x92,PROTECTION=1,FAULT=1)
    case('fixed-local-no-access',FLAGS=0x92,PROTECTION=0)
    case('fixed-local-bad-prot',FLAGS=0x92,PROTECTION=8)
    case('fixed-local-empty',FLAGS=0x92,LENGTH=0)
    case('fixed-local-wrap',FLAGS=0x92,ADDRESS=0x0e100000,LENGTH=0xffffffff)
    case('fixed-local-high',FLAGS=0x92,ADDRESS=0x80000000)
    case('fixed-local-unaligned',FLAGS=0x92,ADDRESS=0x0e100001)
    case('fixed-local-halfpage',FLAGS=0x92,ADDRESS=0x0e101000)
    case('fixed-local-negative-offset',FLAGS=0x92,OFFSET=0xffffffff)
    case('fixed-local-byte-offset',FLAGS=0x92,OFFSET=1)
    case('fixed-local-halfpage-offset',FLAGS=0x92,ADDRESS=0x0e100000,FILE_KIND=1,OFFSET=4096)
    for name,flags in [('none',0),('local-only',0x80),('shared-local',0x81),('both',3),('autogrow',0xd2),('autoreserve',0x192),('anyaddr',0x1092),('unknown',0x10000092)]:case('flags-'+name,FLAGS=flags)
    sources=['scripts/build-irix-mmap-local.py','lab/irix-mmap-local/probe.c','lab/irix-mmap-local/start.S','lab/irix-mmap-local/call.S','lab/irix-mmap-local/probe.ld','lab/irix-mmap-local/setup.sh']
    m=dict(schema=1,identities=[[0,0,0,0],[1234,1234,1234,1234]],sources={p:base.digest(ROOT/p) for p in sources},files={},cases=[])
    for abi in ['o32','n32']:
        flags=['-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
        start=out/(abi+'-start.o');base.run('gcc',*flags,'-c',ROOT/'lab/irix-mmap-local/start.S','-o',start)
        for indirect in [0,1]:
            bridge=out/(abi+'-'+str(indirect)+'-call.o');base.run('gcc',*flags,'-DN32='+str(int(abi=='n32')),'-DINDIRECT='+str(indirect),'-c',ROOT/'lab/irix-mmap-local/call.S','-o',bridge)
            for suffix,kw in definitions:
                name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix
                syms=dict(CASE=len(m['cases'])+1,ADDRESS=0,LENGTH=4096,PROTECTION=3,FLAGS=2,OFFSET=0,FD_MODE=0,FILE_KIND=0,REPLACE=0,FAULT=0);syms.update(kw)
                obj=out/(name+'.o');elf=out/name
                base.run('gcc',*flags,'-O2','-fno-delete-null-pointer-checks','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror',*['-D'+k+'='+str(v)+'U' for k,v in syms.items()],'-c',ROOT/'lab/irix-mmap-local/probe.c','-o',obj)
                base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-mmap-local/probe.ld','-o',elf,start,bridge,obj)
                data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(data);elf.chmod(0o755)
                m['files'][name]=dict(sha256=base.digest(elf),bytes=len(data));m['cases'].append(dict(name=name,abi=abi,symbols=syms,identities=[0,1]))
    shutil.copyfile(ROOT/'lab/irix-mmap-local/setup.sh',out/'setup.sh');m['files']['setup.sh']=dict(sha256=base.digest(out/'setup.sh'),bytes=(out/'setup.sh').stat().st_size)
    (out/'mapping').write_bytes(bytes([0x3c])*32768);m['files']['mapping']=dict(sha256=base.digest(out/'mapping'),bytes=32768)
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(len(definitions),'variants;',len(m['cases']),'fixtures')
if __name__=='__main__':main()
