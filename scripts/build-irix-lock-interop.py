#!/usr/bin/env python3
"""Build the foreign peers for native/IRIX locking interoperability."""
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
    out = ROOT/'.work/irix-lock-interop/probes'
    out.mkdir(parents=True, exist_ok=True)
    definitions=[]
    def case(name, **symbols): definitions.append((name,'',symbols))
    case('interop')
    sources = ['scripts/build-irix-lock-interop.py', 'lab/irix-filelocks/interop-irix.c',
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
                syms = dict(CASE=len(manifest['cases'])+1, N32=int(abi=='n32'), PTYPE=2,CTYPE=2,
                            CSTART=0,ACTION=0,BLOCK=0,PCMD=13,NCMD=12,BCMD=13)
                syms.update(extra)
                obj, elf = out/(name+'.o'), out/name
                base.run('gcc', *flags, '-O2', '-ffreestanding', '-fno-builtin',
                    '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                    *['-D'+k+'='+str(v)+'U' for k,v in syms.items()],
                    '-c', ROOT/'lab/irix-filelocks/interop-irix.c', '-o', obj)
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
