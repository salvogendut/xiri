#!/usr/bin/env python3
"""Build guarded IRIX record-lock fixtures for paired kernel observations."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('base', ROOT/'scripts/build-irix-tcp.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def main():
    if os.environ.get('XIRI_FILELOCKS_TOOLBOX') != '1':
        subprocess.run(['toolbox', 'run', '-c', 'xiri-iris', 'env',
            'XIRI_FILELOCKS_TOOLBOX=1', 'PYTHONDONTWRITEBYTECODE=1',
            'python3', str(Path(__file__).resolve())], check=True)
        return
    out = ROOT/'.work/irix-filelocks/probes'
    out.mkdir(parents=True, exist_ok=True)
    definitions=[]
    def case(name, **symbols): definitions.append((name,'',symbols))
    for command in [6,7,12,13,14]:
        for kind in [1,2,3]:case('cmd-'+str(command)+'-type-'+str(kind),COMMAND=command,TYPE=kind)
    for kind in [0,4,0xffff]:case('type-'+str(kind),TYPE=kind)
    for whence in [1,2,3,0xffff]:case('whence-'+str(whence),WHENCE=whence)
    for name,start,length in [('range',17,23),('negative-start',0xffffffff,0),('negative-len',17,0xfffffff8),('before-start',3,0xfffffff8),('overflow-end',0x7fffffff,0x7fffffff)]:case(name,START=start,LENGTH=length)
    for mode in [0,1]:
        for kind in [1,2,3]:case('mode-'+str(mode)+'-type-'+str(kind),OPEN_MODE=mode,TYPE=kind)
        for command in [6,7,12]:
            for kind in [1,2]:case('cmd-'+str(command)+'-mode-'+str(mode)+'-type-'+str(kind),COMMAND=command,OPEN_MODE=mode,TYPE=kind)
    for command in [6,7,12,14]:case('cmd-'+str(command)+'-negative-len',COMMAND=command,START=17,LENGTH=0xfffffff8)
    case('wide-start',START_HIGH=1,START=17,LENGTH=23)
    case('wide-overflow',START_HIGH=0x7fffffff,START=0xffffffff,LENGTH=2)
    for start,length in [(0xffffffff,1),(0xffffffff,2),(0xffffffff,3),(0xfffffffe,1),(0xfffffffe,2),(0xfffffffe,3),(0xfffffffe,4)]:
        case('negative-range-'+str(start)+'-'+str(length),START=start,LENGTH=length)
    for name,kind in [('pipe',1),('directory',2),('bad-fd',3),('closed',4)]:case(name,KIND=kind,OPEN_MODE=0)
    for name,kind in [('null',1),('high',2),('readonly',3)]:case(name,POINTER=kind)
    case('bad-fd-null',KIND=3,POINTER=1)
    case('bad-type-null',TYPE=0,POINTER=1)
    for align in [1,2,3,4,7]:case('align-'+str(align),ALIGN=align)
    for tail in [0,1,3,4,8,11,12,16,20,24,32,35,36,37,47,48]:case('tail-'+str(tail),POINTER=4,TAIL=tail)
    case('getlk-readonly',COMMAND=14,POINTER=3)
    case('getlk-tail-36',COMMAND=14,POINTER=4,TAIL=36)
    case('getlk-tail-48',COMMAND=14,POINTER=4,TAIL=48)
    sources = ['scripts/build-irix-filelocks.py', 'lab/irix-filelocks/probe.c',
               'lab/irix-prda/start.S', 'lab/irix-prda/call.S', 'lab/irix-prda/probe.ld',
               'lab/irix-filelocks/setup.sh']
    manifest = dict(schema=1, sources={n:base.digest(ROOT/n) for n in sources}, files={}, cases=[])
    for abi in ['o32', 'n32']:
        flags = ['-EB', '-mabi='+('n32' if abi=='n32' else '32'), '-mips3',
                 '-msoft-float', '-mno-abicalls', '-fno-pic', '-G0']
        start = out/(abi+'-start.o')
        base.run('gcc', *flags, '-c', ROOT/'lab/irix-prda/start.S', '-o', start)
        for indirect in [0, 1]:
            bridge = out/(abi+'-'+str(indirect)+'-call.o')
            base.run('gcc', *flags, '-DN32='+str(int(abi=='n32')), '-DINDIRECT='+str(indirect),
                     '-c', ROOT/'lab/irix-prda/call.S', '-o', bridge)
            for suffix, path, extra in definitions:
                name = abi+'-'+('indirect-' if indirect else 'direct-')+suffix
                syms = dict(CASE=len(manifest['cases'])+1, N32=int(abi=='n32'), COMMAND=13, TYPE=1, WHENCE=0,
                            START=0,LENGTH=0,OPEN_MODE=2,KIND=0,POINTER=0,TAIL=0,ALIGN=0)
                syms.update(extra)
                syms.setdefault('START_HIGH',0xffffffff if syms['START'] & 0x80000000 else 0)
                syms.setdefault('LENGTH_HIGH',0xffffffff if syms['LENGTH'] & 0x80000000 else 0)
                obj, elf = out/(name+'.o'), out/name
                base.run('gcc', *flags, '-O2', '-ffreestanding', '-fno-builtin',
                    '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                    *['-D'+k+'='+str(v)+'U' for k,v in syms.items()],
                    '-c', ROOT/'lab/irix-filelocks/probe.c', '-o', obj)
                base.run('ld', '-EB', '-m', 'elf32btsmipn32' if abi=='n32' else 'elf32btsmip',
                    '--build-id=none', '-z', 'max-page-size=8192', '-T', ROOT/'lab/irix-prda/probe.ld',
                    '-o', elf, start, bridge, obj)
                data = bytearray(elf.read_bytes()); data[7] = 0
                struct.pack_into('>I', data, 36, 0x20000021 if abi=='n32' else 0x20000101)
                elf.write_bytes(data); elf.chmod(0o755)
                manifest['files'][name] = dict(sha256=base.digest(elf), bytes=len(data))
                manifest['cases'].append(dict(name=name, abi=abi, path=path, symbols=syms, record_bytes=576))
    shutil.copyfile(ROOT/'lab/irix-filelocks/setup.sh', out/'setup.sh')
    manifest['files']['setup.sh'] = dict(sha256=base.digest(out/'setup.sh'), bytes=(out/'setup.sh').stat().st_size)
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(len(manifest['cases']), 'desktop query fixtures built')


if __name__ == '__main__':
    main()
