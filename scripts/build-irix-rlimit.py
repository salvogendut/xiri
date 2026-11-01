#!/usr/bin/env python3
"""Build paired o32/n32 resource-limit query fixtures."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('base', ROOT / 'scripts/build-irix-tcp.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def main():
    if os.environ.get('XIRI_RLIMIT_TOOLBOX') != '1':
        subprocess.run(['toolbox', 'run', '-c', 'xiri-iris', 'env',
                        'XIRI_RLIMIT_TOOLBOX=1', 'PYTHONDONTWRITEBYTECODE=1',
                        'python3', str(Path(__file__).resolve())], check=True)
        return
    output = ROOT / '.work/irix-rlimit/probes'
    output.mkdir(parents=True, exist_ok=True)
    sources = ['scripts/build-irix-rlimit.py', 'lab/irix-rlimit/probe.c',
               'lab/irix-prda/start.S', 'lab/irix-prda/call.S', 'lab/irix-prda/probe.ld']
    manifest = dict(schema=1, identities=[[0,0,0,0], [1234,1234,1234,1234]],
                    sources={p: base.digest(ROOT / p) for p in sources}, files={}, cases=[])
    for abi in ['o32', 'n32']:
        flags = ['-EB', '-mabi=' + ('n32' if abi == 'n32' else '32'), '-mips3',
                 '-msoft-float', '-mno-abicalls', '-fno-pic', '-G0']
        for indirect in [0, 1]:
            for kind, suffix, records in [(0, 'queries', 18), (1, 'errors', 20),
                                           (2, 'inherit', 72), (3, 'large', 18), (4, 'highbit', 18)]:
                name = abi + ('-indirect-' if indirect else '-direct-') + suffix
                objects = []
                for source in sources[1:4]:
                    obj = output / (name + '-' + Path(source).name + '.o')
                    objects.append(obj)
                    base.run('gcc', *flags, '-DN32=' + str(int(abi == 'n32')),
                             '-DINDIRECT=' + str(indirect), '-DKIND=' + str(kind),
                             '-O2', '-ffreestanding', '-fno-builtin', '-fno-stack-protector',
                             '-Wall', '-Wextra', '-Werror', '-c', ROOT / source, '-o', obj)
                elf = output / name
                base.run('ld', '-EB', '-m', 'elf32btsmipn32' if abi == 'n32' else 'elf32btsmip',
                         '--build-id=none', '-z', 'max-page-size=8192', '-T',
                         ROOT / 'lab/irix-prda/probe.ld', '-o', elf, *objects)
                data = bytearray(elf.read_bytes())
                data[7] = 0
                struct.pack_into('>I', data, 36, 0x20000021 if abi == 'n32' else 0x20000101)
                elf.write_bytes(data)
                elf.chmod(0o755)
                manifest['files'][name] = dict(sha256=base.digest(elf), bytes=len(data))
                manifest['cases'].append(dict(name=name, abi=abi, indirect=indirect,
                                             symbols=dict(KIND=kind), records=records, identities=[0,1],
                                             reference_only=kind >= 3))
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print('Built 20 resource-limit fixtures', flush=True)


if __name__ == '__main__':
    main()
