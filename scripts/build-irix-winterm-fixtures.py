#!/usr/bin/env python3
"""Build bounded, libc-free PTY and SIGCHLD fixtures for o32/n32."""
import importlib.util,json,os,struct,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('base',ROOT/'scripts/build-irix-tcp.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
def main():
    if os.environ.get('XIRI_WINTERM_TOOLBOX')!='1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_WINTERM_TOOLBOX=1','python3',str(Path(__file__).resolve())],check=True);return
    out=ROOT/'.work/irix-winterm-reliability/probes';out.mkdir(parents=True,exist_ok=True)
    sources=['scripts/build-irix-winterm-fixtures.py','lab/irix-winterm-reliability/winsize-raw.c',
             'lab/irix-signal/probe.c','lab/irix-signal/start.S','lab/irix-signal/trampoline-v2.S',
             'lab/irix-signal/fpu.S','lab/irix-mmap-local/call.S','lab/irix-mmap-local/probe.ld']
    result=dict(schema=1,sources={s:base.digest(ROOT/s) for s in sources},files={})
    for abi in ('o32','n32'):
        flags=['-EB','-mabi='+('32' if abi=='o32' else abi),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
        fixed=[]
        for part in ('start','fpu'):
            obj=out/(abi+'-'+part+'.o');base.run('gcc',*flags,'-c',ROOT/('lab/irix-signal/'+part+'.S'),'-o',obj);fixed.append(obj)
        for indirect in (0,1):
            prefix=abi+('-indirect' if indirect else '-direct')
            objects=[]
            for src,part in [('lab/irix-mmap-local/call.S','call'),('lab/irix-signal/trampoline-v2.S','trampoline')]:
                obj=out/(prefix+'-'+part+'.o');base.run('gcc',*flags,'-DN32='+str(abi=='n32' and 1 or 0),'-DINDIRECT='+str(indirect),'-c',ROOT/src,'-o',obj);objects.append(obj)
            for name,symbols in [('winsize',None),('child-legacy',dict(KIND=2,FLAGS=0x20000)),
                                 ('child-siginfo',dict(KIND=2,FLAGS=0x20008)),('child-signal',dict(KIND=2,FLAGS=0x20012))]:
                source=ROOT/'lab/irix-winterm-reliability/winsize-raw.c';defines=[]
                if symbols is not None:
                    source=ROOT/'lab/irix-signal/probe.c'
                    defaults=dict(CASE=1,SIGNUM=18,HANDLER=3,SET_KIND=0,OLD_KIND=0,TRAMP=0,REAP=0,FPU=0,RETURN_TEST=0,MASK0=0,MASK1=0,MASK2=0,MASK3=0)
                    defaults.update(symbols);defines=['-D'+k+'='+str(v)+'U' for k,v in defaults.items()]
                elf=out/(prefix+'-'+name);obj=elf.with_suffix('.o')
                base.run('gcc',*flags,'-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror',*defines,'-c',source,'-o',obj)
                linked = [fixed[0], objects[0]] if symbols is None else fixed + objects
                base.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/'lab/irix-mmap-local/probe.ld','-o',elf,*linked,obj)
                data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(data);elf.chmod(0o755)
                result['files'][elf.name]=dict(sha256=base.digest(elf),bytes=len(data))
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(out)
if __name__=='__main__':main()
