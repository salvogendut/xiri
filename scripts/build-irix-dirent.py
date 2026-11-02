#!/usr/bin/env python3
"""Build identical o32/n32 readlink and desktop feature-query observers."""
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
    if os.environ.get('XIRI_DIRENT_TOOLBOX') != '1':
        subprocess.run(['toolbox', 'run', '-c', 'xiri-iris', 'env',
            'XIRI_DIRENT_TOOLBOX=1', 'PYTHONDONTWRITEBYTECODE=1',
            'python3', str(Path(__file__).resolve())], check=True)
        return
    out = ROOT/'.work/irix-dirent/probes'
    out.mkdir(parents=True, exist_ok=True)
    definitions=[]
    for trap in [1081,1205,1207,1208]:
        variants=[('normal',{}),('empty',{}),('regular',{}),('bad-fd',dict(FD_KIND=1))]
        variants += [('count-'+str(n),dict(COUNT=n)) for n in [0,1,11,12,15,16,23,24,32,64,65536,0xffffffff]]
        variants += [('null',dict(POINTER=1)),('high',dict(POINTER=2)),
            ('readonly',dict(POINTER=3)),('unaligned',dict(ALIGN=1)),
            ('tail-1',dict(POINTER=4,TAIL=1)),('tail-16',dict(POINTER=4,TAIL=16))]
        variants += [('eof-'+str(n),dict(EOF_KIND=n)) for n in [0,2,3]]
        for name,extra in variants:
            path='tree/empty' if name=='empty' else 'tree/file' if name=='regular' else 'tree/directory'
            definitions.append((str(trap)+'-'+name,path,dict(TRAP=trap,**extra)))
    sources = ['scripts/build-irix-dirent.py', 'lab/irix-dirent/probe.c',
               'lab/irix-prda/start.S', 'lab/irix-prda/call.S', 'lab/irix-prda/probe.ld',
               'lab/irix-dirent/setup.sh']
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
                syms = dict(CASE=len(manifest['cases'])+1, TRAP=1081, COUNT=1024,
                            POINTER=0, FD_KIND=0, EOF_KIND=1, ALIGN=0, TAIL=0)
                syms.update(extra)
                obj, elf = out/(name+'.o'), out/name
                base.run('gcc', *flags, '-O2', '-ffreestanding', '-fno-builtin',
                    '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                    *['-D'+k+'='+str(v)+'U' for k,v in syms.items()],
                    '-DPATHNAME='+json.dumps(path), '-c', ROOT/'lab/irix-dirent/probe.c', '-o', obj)
                base.run('ld', '-EB', '-m', 'elf32btsmipn32' if abi=='n32' else 'elf32btsmip',
                    '--build-id=none', '-z', 'max-page-size=8192', '-T', ROOT/'lab/irix-prda/probe.ld',
                    '-o', elf, start, bridge, obj)
                data = bytearray(elf.read_bytes()); data[7] = 0
                struct.pack_into('>I', data, 36, 0x20000021 if abi=='n32' else 0x20000101)
                elf.write_bytes(data); elf.chmod(0o755)
                manifest['files'][name] = dict(sha256=base.digest(elf), bytes=len(data))
                manifest['cases'].append(dict(name=name, abi=abi, path=path, symbols=syms, record_bytes=4096))
    shutil.copyfile(ROOT/'lab/irix-dirent/setup.sh', out/'setup.sh')
    manifest['files']['setup.sh'] = dict(sha256=base.digest(out/'setup.sh'), bytes=(out/'setup.sh').stat().st_size)
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(len(manifest['cases']), 'desktop query fixtures built')


if __name__ == '__main__':
    main()
