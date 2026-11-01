#!/usr/bin/env python3
"""Build original damaged-PRDA fork policy controls."""
import importlib.util,json,os,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
def main():
    if os.environ.get('XIRI_PRDA_CONTROL_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_PRDA_CONTROL_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-prda/fork-controls';out.mkdir(parents=True,exist_ok=True)
    sources=['scripts/build-irix-prda-controls.py','lab/irix-prda/fork-error.c','lab/irix-prda/start.S','lab/irix-prda/call.S','lab/irix-prda/probe.ld']
    m=dict(sources={p:base.digest(ROOT/p) for p in sources},files={})
    for abi in ['o32','n32']:
        flags=['-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
        for mode in [0,1]:
            objects=[]
            for src in ['start.S','call.S','fork-error.c']:
                obj=out/(abi+'-'+src+'.o');objects.append(obj)
                base.run('gcc',*flags,'-DN32='+str(int(abi=='n32')),'-DINDIRECT=0','-DMODE='+str(mode),'-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror','-c',ROOT/'lab/irix-prda'/src,'-o',obj)
            elf=out/(abi+'-fork-error-'+str(mode))
            base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-prda/probe.ld','-o',elf,*objects)
            data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(data);elf.chmod(0o755)
            m['files'][elf.name]=dict(sha256=base.digest(elf),bytes=len(data))
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
