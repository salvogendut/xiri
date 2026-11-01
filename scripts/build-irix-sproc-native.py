#!/usr/bin/env python3
"""Build native sproc guard, LOCAL replacement and repeated-creation checks."""
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
    if os.environ.get('XIRI_SPROC_NATIVE_TOOLBOX') != '1':
        subprocess.run(['toolbox', 'run', '-c', 'xiri-iris', 'env',
                        'XIRI_SPROC_NATIVE_TOOLBOX=1', 'PYTHONDONTWRITEBYTECODE=1',
                        'python3', str(Path(__file__).resolve())], check=True)
        return
    out = ROOT/'.work/irix-sproc/native-probes'
    out.mkdir(parents=True, exist_ok=True)
    (out/'manifest.json').unlink(missing_ok=True)
    definitions = [('guards', {'KIND': 0}), ('local-replace', {'KIND': 1}), ('repeat', {'KIND': 2})]
    sources = ['scripts/build-irix-sproc-native.py', 'lab/irix-sproc/probe.c', 'lab/irix-sproc/native-lifecycle.c',
               'lab/irix-sproc/entry.S', 'lab/irix-sproc/spawn.S', 'lab/irix-mmap-local/start.S',
               'lab/irix-mmap-local/call.S', 'lab/irix-mmap-local/probe.ld']
    manifest = dict(schema=1, identities=[[0, 0, 0, 0], [1234]*4],
                    sources={p: base.digest(ROOT/p) for p in sources},
                    tools={n: base.run(n, '--version').splitlines()[0] for n in ['gcc', 'ld']},
                    files={}, cases=[])
    for abi in ['o32', 'n32']:
        flags = ['-EB', '-mabi='+('n32' if abi == 'n32' else '32'),
                 '-mips3', '-msoft-float', '-mno-abicalls', '-fno-pic', '-G0']
        start, entry = out/(abi+'-start.o'), out/(abi+'-entry.o')
        base.run('gcc', *flags, '-c', ROOT/'lab/irix-mmap-local/start.S', '-o', start)
        base.run('gcc', *flags, '-c', ROOT/'lab/irix-sproc/entry.S', '-o', entry)
        for indirect in [0, 1]:
            bridge = out/(abi+'-'+str(indirect)+'-call.o')
            spawn = out/(abi+'-'+str(indirect)+'-spawn.o')
            base.run('gcc', *flags, '-DN32='+str(int(abi == 'n32')),
                     '-DINDIRECT='+str(indirect), '-c', ROOT/'lab/irix-mmap-local/call.S', '-o', bridge)
            base.run('gcc', *flags, '-DN32='+str(int(abi == 'n32')),
                     '-DINDIRECT='+str(indirect), '-c', ROOT/'lab/irix-sproc/spawn.S', '-o', spawn)
            for suffix, extra in definitions:
                name = abi+'-'+('indirect-' if indirect else 'direct-')+suffix
                symbols = dict(CASE=len(manifest['cases'])+1, FLAGS=0x03000040,
                               ACTION=0, TRAP=1129, STACK_LEN=0, LOCAL=0, BAD_ENTRY=0)
                symbols.update(extra)
                obj, elf = out/(name+'.o'), out/name
                base.run('gcc', *flags, '-O2', '-ffreestanding', '-fno-builtin',
                         '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                         *['-D'+k+'='+str(v)+'U' for k, v in symbols.items()],
                         '-DHELPER="./'+abi+'-direct-unblock"',
                         '-c', ROOT/'lab/irix-sproc/native-lifecycle.c', '-o', obj)
                base.run('ld', '-EB', '-m', 'elf32btsmipn32' if abi == 'n32' else 'elf32btsmip',
                         '--build-id=none', '-z', 'max-page-size=8192',
                         '-T', ROOT/'lab/irix-mmap-local/probe.ld', '-o', elf, start, bridge, spawn, entry, obj)
                data = bytearray(elf.read_bytes())
                data[7] = 0
                struct.pack_into('>I', data, 36, 0x20000021 if abi == 'n32' else 0x20000101)
                elf.write_bytes(data)
                elf.chmod(0o755)
                manifest['files'][name] = dict(sha256=base.digest(elf), bytes=len(data))
                manifest['cases'].append(dict(name=name, abi=abi, symbols=symbols, identities=[0, 1]))
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(len(manifest['cases']), 'sproc fixtures built', flush=True)


if __name__ == '__main__':
    main()
