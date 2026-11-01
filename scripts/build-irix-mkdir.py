#!/usr/bin/env python3
"""Build paired mkdir filesystem fixtures."""
import importlib.util,json,os,shutil,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)

def main():
    if os.environ.get('XIRI_MKDIR_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_MKDIR_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-mkdir/probes';out.mkdir(parents=True,exist_ok=True)
    definitions=[('umask-'+format(mask,'03o'),dict(MASK=mask)) for mask in [0o22,0o77]]
    sources=['scripts/build-irix-mkdir.py','lab/irix-mkdir/probe.c','lab/irix-prda/start.S','lab/irix-prda/call.S','lab/irix-prda/probe.ld','lab/irix-mkdir/setup.sh']
    m=dict(schema=1,identities=[[0,0,0,0],[1234,1234,1234,1234],[0,1234,0,1234],[1234,0,1234,0],[1234,1234,5678,5678]],sources={p:base.digest(ROOT/p) for p in sources},files={},cases=[])
    for abi in ['o32','n32']:
        flags=['-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
        start=out/(abi+'-start.o');base.run('gcc',*flags,'-c',ROOT/'lab/irix-prda/start.S','-o',start)
        for indirect in [0,1]:
            bridge=out/(abi+'-'+str(indirect)+'-call.o');base.run('gcc',*flags,'-DN32='+str(int(abi=='n32')),'-DINDIRECT='+str(indirect),'-c',ROOT/'lab/irix-prda/call.S','-o',bridge)
            for suffix,kw in definitions:
                name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix
                syms=dict(MASK=kw['MASK'],N32=int(abi=='n32'))
                obj=out/(name+'.o');elf=out/name
                base.run('gcc',*flags,'-O2','-fno-delete-null-pointer-checks','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror',*['-D'+k+'='+str(v)+'U' for k,v in syms.items()],'-c',ROOT/'lab/irix-mkdir/probe.c','-o',obj)
                base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-prda/probe.ld','-o',elf,start,bridge,obj)
                data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(data);elf.chmod(0o755)
                m['files'][name]=dict(sha256=base.digest(elf),bytes=len(data));m['cases'].append(dict(name=name,abi=abi,symbols=syms,identities=list(range(5))))
    shutil.copyfile(ROOT/'lab/irix-mkdir/setup.sh',out/'setup.sh')
    m['files']['setup.sh']=dict(sha256=base.digest(out/'setup.sh'),bytes=(out/'setup.sh').stat().st_size)
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n');print(len(definitions),'variants;',len(m['cases']),'fixtures')
if __name__=='__main__':main()
