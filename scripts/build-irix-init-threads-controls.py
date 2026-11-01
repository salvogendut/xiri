#!/usr/bin/env python3
"""Build syscall-free PRDA signal-mask spin controls for native observation."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def main():
    if os.environ.get('XIRI_INIT_THREADS_CONTROLS_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_INIT_THREADS_CONTROLS_TOOLBOX=1',
            'PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True)
        return
    out=ROOT/'.work/irix-init-threads/signal-controls';out.mkdir(parents=True,exist_ok=True)
    sources=['scripts/build-irix-init-threads-controls.py','lab/irix-init-threads/signal-spin.c',
        'lab/irix-prda/start.S','lab/irix-prda/call.S','lab/irix-prda/probe.ld']
    manifest=dict(sources={p:base.digest(ROOT/p) for p in sources},files={})
    for abi in ['o32','n32']:
        flags=['-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
        start=out/(abi+'-start.o');bridge=out/(abi+'-call.o')
        base.run('gcc',*flags,'-c',ROOT/'lab/irix-prda/start.S','-o',start)
        base.run('gcc',*flags,'-DN32='+str(int(abi=='n32')),'-DINDIRECT=0','-c',ROOT/'lab/irix-prda/call.S','-o',bridge)
        for mode in [0,1]:
            name=abi+'-signal-spin-'+str(mode);obj=out/(name+'.o');elf=out/name
            base.run('gcc',*flags,'-DMODE='+str(mode),'-O2','-ffreestanding','-fno-builtin',
                '-fno-stack-protector','-Wall','-Wextra','-Werror','-c',ROOT/'lab/irix-init-threads/signal-spin.c','-o',obj)
            base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip',
                '--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-prda/probe.ld','-o',elf,start,bridge,obj)
            data=bytearray(elf.read_bytes());data[7]=0
            struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101)
            elf.write_bytes(data);elf.chmod(0o555)
            manifest['files'][name]=dict(sha256=base.digest(elf),bytes=len(data))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Built four asynchronous signal controls')

if __name__=='__main__':main()
