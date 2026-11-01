#!/usr/bin/env python3
"""Build original IRIX-to-native exec controls for the per-personality VM minimum."""
import importlib.util,json,os,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py');base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
def main():
    if os.environ.get('XIRI_MMAP_EXEC_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_MMAP_EXEC_TOOLBOX=1','PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-mmap-local/exec-controls';out.mkdir(parents=True,exist_ok=True)
    sources=['scripts/build-irix-mmap-exec.py','lab/irix-mmap-local/native-exec.c','lab/irix-mmap-local/start.S','lab/irix-mmap-local/call.S','lab/irix-mmap-local/probe.ld']
    m=dict(sources={p:base.digest(ROOT/p) for p in sources},files={})
    for abi in ['o32','n32']:
        flags=['-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
        objects=[]
        for src in ['start.S','call.S','native-exec.c']:
            obj=out/(abi+'-'+src+'.o');objects.append(obj)
            base.run('gcc',*flags,'-DN32='+str(int(abi=='n32')),'-DINDIRECT=0','-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror','-c',ROOT/'lab/irix-mmap-local'/src,'-o',obj)
        elf=out/(abi+'-native-exec')
        base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-mmap-local/probe.ld','-o',elf,*objects)
        data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(data);elf.chmod(0o755)
        m['files'][elf.name]=dict(sha256=base.digest(elf),bytes=len(data))
    (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
if __name__=='__main__':main()
