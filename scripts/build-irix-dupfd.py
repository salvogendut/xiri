#!/usr/bin/env python3
"""Build F_DUPFD ABI/lifecycle fixtures."""
import importlib.util,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)

def main():
    if os.environ.get('XIRI_DUPFD_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_DUPFD_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-dupfd/probes';out.mkdir(parents=True,exist_ok=True)
    (out/'manifest.json').unlink(missing_ok=True)
    definitions=[('min-'+str(arg),dict(KIND=0,ARG=arg)) for arg in [0,1,2,3,4,8,31,32,0xffffffff,0x80000000,0x7fffffff]]
    definitions += [('holes',dict(KIND=1,ARG=0))]
    definitions += [('bad-'+str(arg),dict(KIND=2,ARG=arg)) for arg in [0,32,0xffffffff]]
    definitions += [('closed-'+str(arg),dict(KIND=3,ARG=arg)) for arg in [0,32]]
    definitions += [('exhaust',dict(KIND=4,ARG=0)),('stdout',dict(KIND=5,ARG=1)),('stderr',dict(KIND=5,ARG=2)),('exec',dict(KIND=6,ARG=0))]
    sources=['scripts/build-irix-dupfd.py','lab/irix-dupfd/probe.c','lab/irix-prda/start.S','lab/irix-prda/call.S','lab/irix-prda/probe.ld','lab/irix-dupfd/setup.sh']
    m=dict(schema=1,identities=[[0,0,0,0],[1234,1234,1234,1234]],sources={p:base.digest(ROOT/p) for p in sources},files={},cases=[])
    for abi in ['o32','n32']:
        flags=['-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
        start=out/(abi+'-start.o');base.run('gcc',*flags,'-c',ROOT/'lab/irix-prda/start.S','-o',start)
        for indirect in [0,1]:
            bridge=out/(abi+'-'+str(indirect)+'-call.o');base.run('gcc',*flags,'-DN32='+str(int(abi=='n32')),'-DINDIRECT='+str(indirect),'-c',ROOT/'lab/irix-prda/call.S','-o',bridge)
            for suffix,kw in definitions:
                name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix
                syms=dict(CASE=len(m['cases'])+1,N32=int(abi=='n32'),**kw)
                obj=out/(name+'.o');elf=out/name
                base.run('gcc',*flags,'-O2','-fno-delete-null-pointer-checks','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror',*['-D'+k+'='+str(v)+'U' for k,v in syms.items()],'-DHELPER="./'+name+'"','-c',ROOT/'lab/irix-dupfd/probe.c','-o',obj)
                base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-prda/probe.ld','-o',elf,start,bridge,obj)
                data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(data);elf.chmod(0o755)
                m['files'][name]=dict(sha256=base.digest(elf),bytes=len(data));m['cases'].append(dict(name=name,abi=abi,symbols=syms,identities=list(range(2))))
    shutil.copyfile(ROOT/'lab/irix-dupfd/setup.sh',out/'setup.sh')
    m['files']['setup.sh']=dict(sha256=base.digest(out/'setup.sh'),bytes=(out/'setup.sh').stat().st_size)
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(len(definitions),'variants;',len(m['cases']),'fixtures')
if __name__=='__main__':main()
