#!/usr/bin/env python3
"""Build independent IRIX filesystem operation observers."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('base', ROOT/'scripts/build-irix-tcp.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


SUITES = {'rename': list(range(7))}


def build(suite):
    out = ROOT/('.work/irix-'+suite+'/probes')
    out.mkdir(parents=True, exist_ok=True)
    sources = ['scripts/build-irix-pathops.py', 'lab/irix-pathops/'+suite+'.c',
               'lab/irix-prda/start.S', 'lab/irix-prda/call.S', 'lab/irix-prda/probe.ld']
    manifest = dict(schema=1, record_bytes=1024,
                    modes=SUITES[suite],
                    sources={p: base.digest(ROOT/p) for p in sources}, files={})
    for abi in ['o32', 'n32']:
        flags = ['-EB', '-mabi='+('n32' if abi == 'n32' else '32'), '-mips3',
                 '-msoft-float', '-mno-abicalls', '-fno-pic', '-G0']
        start, obj = out/(abi+'-start.o'), out/(abi+'-'+suite+'.o')
        base.run('gcc', *flags, '-c', ROOT/'lab/irix-prda/start.S', '-o', start)
        base.run('gcc', *flags, '-O2', '-ffreestanding', '-fno-builtin',
                 '-fno-stack-protector', '-Wall', '-Wextra', '-Werror',
                 '-c', ROOT/('lab/irix-pathops/'+suite+'.c'), '-o', obj)
        for indirect in [0, 1]:
            name = abi+('-indirect' if indirect else '-direct')
            bridge, elf = out/(name+'-call.o'), out/name
            base.run('gcc', *flags, '-DN32='+str(int(abi == 'n32')), '-DINDIRECT='+str(indirect),
                     '-c', ROOT/'lab/irix-prda/call.S', '-o', bridge)
            base.run('ld', '-EB', '-m', 'elf32btsmipn32' if abi == 'n32' else 'elf32btsmip',
                     '--build-id=none', '-z', 'max-page-size=8192',
                     '-T', ROOT/'lab/irix-prda/probe.ld', '-o', elf, start, bridge, obj)
            data = bytearray(elf.read_bytes()); data[7] = 0
            struct.pack_into('>I', data, 36, 0x20000021 if abi == 'n32' else 0x20000101)
            elf.write_bytes(data); elf.chmod(0o755)
            manifest['files'][name] = dict(sha256=base.digest(elf), bytes=len(data))
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(out/'manifest.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=SUITES, action='append')
    args = parser.parse_args()
    if os.environ.get('XIRI_PATHOPS_TOOLBOX') != '1':
        subprocess.run(['toolbox', 'run', '-c', 'xiri-iris', 'env',
                        'XIRI_PATHOPS_TOOLBOX=1', 'PYTHONDONTWRITEBYTECODE=1',
                        'python3', str(Path(__file__).resolve()), *sys.argv[1:]], check=True)
        return
    for suite in args.suite or SUITES:
        build(suite)


if __name__ == '__main__':
    main()
