#!/usr/bin/env python3
"""Build original mask/fork/wait probes for paired IRIX and NetBSD runs."""
import importlib.util,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)

def main():
    if os.environ.get('XIRI_PROCESS_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_PROCESS_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-process/probes';out.mkdir(parents=True,exist_ok=True)
    definitions=[]
    def case(name,kind=0,**kw):definitions.append((name,kind,kw))
    for bit in range(1,65):case('mask-bit-'+str(bit),**{'MASK'+str((bit-1)//32):1<<((bit-1)%32)})
    case('mask-high-96',MASK2=0x80000000)
    case('mask-high-128',MASK3=0x80000000)
    case('mask-all',MASK0=0xffffffff,MASK1=0xffffffff,MASK2=0xffffffff,MASK3=0xffffffff)
    case('mask-empty',MASK0=0)
    for how in [1,2,3,0,4,256,0xffffffff]:
        case('how-'+str(how),HOW=how,MASK0=0x10000,MASK1=1)
        case('query-how-'+str(how),HOW=how,SET_KIND=1)
    for source in [1,2,3,4,5,6,7]:case('set-pointer-'+str(source),SET_KIND=source)
    for dest in [1,2,3,4,5,6,7]:case('old-pointer-'+str(dest),OLD_KIND=dest)
    case('bad-how-bad-set',HOW=0,SET_KIND=2)
    case('bad-set-bad-old',SET_KIND=2,OLD_KIND=2)
    case('query-bad-old',SET_KIND=1,OLD_KIND=2)
    for code in [0,37,255]:case('fork-exit-'+str(code),1,EXIT_CODE=code)
    case('fork-nohang',1,WAIT_OPTIONS=0x41)
    case('fork-nowait',1,WAIT_OPTIONS=0x81)
    for how in [0,0x10,0xff,0x100]:case('fork-options-'+str(how),1,WAIT_OPTIONS=how)
    for which in [1,7,0xffffffff]:case('fork-type-'+str(which),1,WAIT_TYPE=which)
    for dest in [1,2,3,4,5,6]:case('fork-info-'+str(dest),1,INFO_KIND=dest)
    case('fork-rusage',1,RUSAGE=0x80000000)
    sources=['scripts/build-irix-process.py','lab/irix-process/probe.c','lab/irix-process/start.S','lab/irix-process/call.S','lab/irix-process/probe.ld','lab/irix-process/setup.sh']
    m=dict(schema=1,record_bytes=256,identities=[[0,0,0,0],[1234,1234,1234,1234]],sources={p:base.digest(ROOT/p) for p in sources},files={},cases=[])
    for abi in ['o32','n32']:
        flags=['-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
        start=out/(abi+'-start.o');base.run('gcc',*flags,'-c',ROOT/'lab/irix-process/start.S','-o',start)
        for indirect in [0,1]:
            bridge=out/(abi+'-'+str(indirect)+'-call.o');base.run('gcc',*flags,'-DN32='+str(int(abi=='n32')),'-DINDIRECT='+str(indirect),'-c',ROOT/'lab/irix-process/call.S','-o',bridge)
            for suffix,kind,kw in definitions:
                name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix
                syms=dict(CASE=len(m['cases'])+1,KIND=kind,HOW=3,SET_KIND=0,OLD_KIND=0,MASK0=0,MASK1=0,MASK2=0,MASK3=0,EXIT_CODE=37,WAIT_TYPE=0,WAIT_OPTIONS=1,INFO_KIND=0,RUSAGE=0);syms.update(kw)
                obj=out/(name+'.o');elf=out/name
                base.run('gcc',*flags,'-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror',*['-D'+k+'='+str(v)+'U' for k,v in syms.items()],'-c',ROOT/'lab/irix-process/probe.c','-o',obj)
                base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-process/probe.ld','-o',elf,start,bridge,obj)
                data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(data);elf.chmod(0o755)
                m['files'][name]=dict(sha256=base.digest(elf),bytes=len(data))
                m['cases'].append(dict(name=name,abi=abi,symbols=syms,identities=[0,1],records=1 if kind==0 else 3))
    shutil.copyfile(ROOT/'lab/irix-process/setup.sh',out/'setup.sh')
    m['files']['setup.sh']=dict(sha256=base.digest(out/'setup.sh'),bytes=(out/'setup.sh').stat().st_size)
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(len(definitions),'variants;',len(m['cases']),'fixtures')
if __name__=='__main__':main()
