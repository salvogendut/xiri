#!/usr/bin/env python3
"""Build independent IRIX sigaction, signal-frame and sigreturn observations."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('base', ROOT/'scripts/build-irix-tcp.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def main():
    if os.environ.get('XIRI_SIGNAL_TOOLBOX') != '1':
        subprocess.run(['toolbox', 'run', '-c', 'xiri-iris', 'env',
                        'XIRI_SIGNAL_TOOLBOX=1', 'PYTHONDONTWRITEBYTECODE=1',
                        'python3', str(Path(__file__).resolve())], check=True)
        return
    out = ROOT/'.work/irix-signal-v2/probes'
    out.mkdir(parents=True, exist_ok=True)
    (out/'manifest.json').unlink(missing_ok=True)
    definitions = [('action', {})]
    for number in [0, 1, 9, 18, 23, 31, 32, 33, 64, 65, 128, 0xffffffff]:
        definitions.append(('number-'+str(number), dict(SIGNUM=number)))
    for flags in [1, 2, 4, 8, 16, 0x10000, 0x20000, 0x3001f, 0x20, 0x80000000]:
        definitions.append(('flags-'+str(flags), dict(FLAGS=flags)))
    for handler in [0, 1, 2, 0x80000000, 0x400101]:
        definitions.append(('handler-'+str(handler), dict(HANDLER=handler)))
    for kind in range(1, 7):
        definitions.append(('set-'+str(kind), dict(SET_KIND=kind)))
        definitions.append(('old-'+str(kind), dict(OLD_KIND=kind)))
    definitions += [('bad-number-bad-set', dict(SIGNUM=65, SET_KIND=2)),
                    ('bad-set-bad-old', dict(SET_KIND=2, OLD_KIND=2)),
                    ('null-trampoline', dict(TRAMP=1)),
                    ('bad-trampoline', dict(TRAMP=2)),
                    ('mask-all', dict(MASK0=0xffffffff, MASK1=0xffffffff, MASK2=0xffffffff, MASK3=0xffffffff))]
    for name, extra in [('legacy', {}), ('siginfo', dict(FLAGS=8)),
                        ('nodefer', dict(FLAGS=24)), ('reset', dict(FLAGS=10)),
                        ('mask', dict(FLAGS=8, MASK0=0x10000))]:
        definitions.append(('deliver-'+name, dict(KIND=1, **extra)))
    for name, extra in [('legacy', {}), ('siginfo', dict(FLAGS=8)), ('reap', dict(FLAGS=8, REAP=1))]:
        definitions.append(('child-'+name, dict(KIND=2, SIGNUM=18, **extra)))
    definitions += [('fpu-legacy', dict(KIND=1,FPU=1)),
                    ('fpu-siginfo', dict(KIND=1,FLAGS=8,FPU=1)),
                    ('fpu-child', dict(KIND=2,FLAGS=8,FPU=1,SIGNUM=18,REAP=1))]
    for kind in range(1,5):
        definitions.append(('return-pointer-'+str(kind),dict(KIND=1,FLAGS=8,RETURN_TEST=kind)))
    sources = ['scripts/build-irix-signal-v2.py', 'lab/irix-signal/probe.c',
               'lab/irix-signal/start.S', 'lab/irix-signal/trampoline-v2.S', 'lab/irix-signal/fpu.S',
               'lab/irix-mmap-local/call.S', 'lab/irix-mmap-local/probe.ld']
    manifest = dict(schema=1, record_bytes=2048, identities=[[0]*4, [1234]*4],
                    sources={p: base.digest(ROOT/p) for p in sources},
                    tools={n: base.run(n, '--version').splitlines()[0] for n in ['gcc', 'ld']},
                    files={}, cases=[])
    for abi in ['o32', 'n32']:
        flags = ['-EB', '-mabi='+('n32' if abi == 'n32' else '32'), '-mips3',
                 '-msoft-float', '-mno-abicalls', '-fno-pic', '-G0']
        objects = []
        for name in ['start', 'fpu']:
            obj = out/(abi+'-'+name+'.o')
            base.run('gcc', *flags, '-c', ROOT/('lab/irix-signal/'+name+'.S'), '-o', obj)
            objects.append(obj)
        for indirect in [0, 1]:
            bridge = out/(abi+'-'+str(indirect)+'-call.o')
            trampoline = out/(abi+'-'+str(indirect)+'-trampoline.o')
            base.run('gcc', *flags, '-DINDIRECT='+str(indirect),
                     '-c', ROOT/'lab/irix-signal/trampoline-v2.S', '-o', trampoline)
            base.run('gcc', *flags, '-DN32='+str(int(abi == 'n32')), '-DINDIRECT='+str(indirect),
                     '-c', ROOT/'lab/irix-mmap-local/call.S', '-o', bridge)
            for suffix, extra in definitions:
                name = abi+'-'+('indirect-' if indirect else 'direct-')+suffix
                symbols = dict(CASE=len(manifest['cases'])+1, KIND=0, FLAGS=0, SIGNUM=16,
                               HANDLER=3, SET_KIND=0, OLD_KIND=0, TRAMP=0, REAP=0,FPU=0,RETURN_TEST=0,
                               MASK0=0, MASK1=0, MASK2=0, MASK3=0)
                symbols.update(extra)
                obj, elf = out/(name+'.o'), out/name
                base.run('gcc', *flags, '-O2', '-ffreestanding', '-fno-builtin',
                         '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                         *['-D'+k+'='+str(v)+'U' for k,v in symbols.items()],
                         '-c', ROOT/'lab/irix-signal/probe.c', '-o', obj)
                base.run('ld', '-EB', '-m', 'elf32btsmipn32' if abi == 'n32' else 'elf32btsmip',
                         '--build-id=none', '-z', 'max-page-size=8192',
                         '-T', ROOT/'lab/irix-mmap-local/probe.ld', '-o', elf, *objects, bridge, trampoline, obj)
                data = bytearray(elf.read_bytes())
                data[7] = 0
                struct.pack_into('>I', data, 36, 0x20000021 if abi == 'n32' else 0x20000101)
                elf.write_bytes(data)
                elf.chmod(0o755)
                manifest['files'][name] = dict(sha256=base.digest(elf), bytes=len(data))
                manifest['cases'].append(dict(name=name, abi=abi, symbols=symbols, identities=[0, 1]))
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(len(definitions), 'variants;', len(manifest['cases']), 'fixtures', flush=True)


if __name__ == '__main__':
    main()
