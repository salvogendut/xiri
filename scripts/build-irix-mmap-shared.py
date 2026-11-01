#!/usr/bin/env python3
"""Build SHARED mappings and the existing private/fixed/local regression cases."""
import importlib.util,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)

def main():
    if os.environ.get('XIRI_MMAP_SHARED_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_MMAP_SHARED_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-mmap-shared/probes';out.mkdir(parents=True,exist_ok=True)
    definitions=[]
    def case(name,**kw):definitions.append((name,kw))
    case('installer',LENGTH=0x100000)
    for name,flags in [('shared',1),('shared-auto',0x101),('shared-grow',0x41),('private',2),('private-grow',0x142),('shared-local',0x181)]:
        case(name,FLAGS=flags)
        case(name+'-fork',FLAGS=flags,ACTION=1)
    case('installer-fork',LENGTH=0x100000,ACTION=1)
    case('installer-close',CLOSE_EARLY=1)
    case('installer-close-fork',CLOSE_EARLY=1,ACTION=1)
    case('installer-alias',FILE_KIND=3)
    case('installer-second-map',ACTION=2)
    case('shared-file',FILE_KIND=1,FLAGS=1)
    case('shared-file-fork',FILE_KIND=1,FLAGS=1,ACTION=1)
    case('shared-file-second-map',FILE_KIND=1,FLAGS=1,ACTION=2)
    case('private-file-fork',FILE_KIND=1,FLAGS=2,ACTION=1)
    case('shared-file-offset',FILE_KIND=1,FLAGS=0x101,OFFSET=8192)
    case('shared-fixed',FLAGS=0x111,ADDRESS=0x0e100000)
    case('installer-fixed',FLAGS=0x151,ADDRESS=0x0e100000)
    case('installer-local',FLAGS=0x1c1)
    for name,kind,flags in [('shared',1,0x141),('private',1,0x142),('shared-no-grow',1,1),('private-no-grow',1,2),('zero-name-file',4,0x141)]:
        case(name+'-past-eof-store',FILE_KIND=kind,FLAGS=flags,FILE_SIZE=17,LENGTH=16384,TARGET=8192,ACTION=3)
        case(name+'-past-eof-read',FILE_KIND=kind,FLAGS=flags,FILE_SIZE=17,LENGTH=16384,TARGET=8192,ACTION=4)
    case('shared-grow-empty-store',FILE_KIND=1,FILE_SIZE=0,LENGTH=16384,TARGET=8192,ACTION=3)
    case('shared-grow-within-file',FILE_KIND=1)
    case('shared-grow-file-readonly',FILE_KIND=1,OPEN_MODE=0)
    case('shared-file-readonly-fd',FILE_KIND=1,FLAGS=1,OPEN_MODE=0)
    case('shared-file-writeonly-fd',FILE_KIND=1,FLAGS=1,OPEN_MODE=1)
    case('installer-readonly-fd',OPEN_MODE=0)
    case('installer-writeonly-fd',OPEN_MODE=1)
    case('installer-readonly-map',PROTECTION=1)
    case('shared-readonly-store',FLAGS=1,PROTECTION=1,ACTION=3,TARGET=0)
    case('shared-no-access-read',FLAGS=1,PROTECTION=0,ACTION=4,TARGET=0)
    case('installer-invalid-fd',BADFD=1)
    case('installer-closed-fd',BADFD=2)
    case('installer-directory',FILE_KIND=2,OPEN_MODE=0)
    case('installer-negative-offset',OFFSET=0xffffffff)
    case('installer-byte-offset',OFFSET=1)
    case('installer-page-offset',OFFSET=8192)
    case('installer-empty',LENGTH=0)
    case('installer-both-types',FLAGS=0x143)
    case('installer-no-type',FLAGS=0x140)
    case('installer-unknown',FLAGS=0x10000141)
    case('installer-bad-protection',PROTECTION=8)
    case('installer-fixed-unaligned',FLAGS=0x151,ADDRESS=0x0e100001)
    case('installer-fixed-halfpage',FLAGS=0x151,ADDRESS=0x0e101000)
    sources=['scripts/build-irix-mmap-shared.py','lab/irix-mmap-shared/probe.c','lab/irix-mmap-local/start.S','lab/irix-mmap-local/call.S','lab/irix-mmap-local/probe.ld','lab/irix-mmap-shared/setup.sh']
    m=dict(schema=1,identities=[[0,0,0,0],[1234,1234,1234,1234]],sources={p:base.digest(ROOT/p) for p in sources},files={},cases=[])
    for abi in ['o32','n32']:
        flags=['-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
        start=out/(abi+'-start.o');base.run('gcc',*flags,'-c',ROOT/'lab/irix-mmap-local/start.S','-o',start)
        for indirect in [0,1]:
            bridge=out/(abi+'-'+str(indirect)+'-call.o');base.run('gcc',*flags,'-DN32='+str(int(abi=='n32')),'-DINDIRECT='+str(indirect),'-c',ROOT/'lab/irix-mmap-local/call.S','-o',bridge)
            for suffix,kw in definitions:
                name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix
                syms=dict(CASE=len(m['cases'])+1,ADDRESS=0,LENGTH=8192,PROTECTION=3,FLAGS=0x141,OFFSET=0,OPEN_MODE=2,FILE_KIND=0,ACTION=0,BADFD=0,FILE_SIZE=32768,TARGET=8192,CLOSE_EARLY=0);syms.update(kw)
                obj=out/(name+'.o');elf=out/name
                base.run('gcc',*flags,'-O2','-fno-delete-null-pointer-checks','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror',*['-D'+k+'='+str(v)+'U' for k,v in syms.items()],'-c',ROOT/'lab/irix-mmap-shared/probe.c','-o',obj)
                base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-mmap-local/probe.ld','-o',elf,start,bridge,obj)
                data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(data);elf.chmod(0o755)
                m['files'][name]=dict(sha256=base.digest(elf),bytes=len(data));m['cases'].append(dict(name=name,abi=abi,symbols=syms,identities=[0,1]))
    shutil.copyfile(ROOT/'lab/irix-mmap-shared/setup.sh',out/'setup.sh');m['files']['setup.sh']=dict(sha256=base.digest(out/'setup.sh'),bytes=(out/'setup.sh').stat().st_size)
    (out/'mapping').write_bytes(bytes([0x3c])*32768);m['files']['mapping']=dict(sha256=base.digest(out/'mapping'),bytes=32768)
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(len(definitions),'variants;',len(m['cases']),'fixtures')
if __name__=='__main__':main()
