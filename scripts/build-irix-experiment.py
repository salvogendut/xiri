#!/usr/bin/env python3
"""Build the o32 execution/error fixtures and deliberately rejected ELF variants."""

import argparse
import importlib.util
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-irix-probe.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--basics', action='store_true', help='add static argument, file, and memory checks')
    args = parser.parse_args()
    base.OUTPUT = ROOT / ('.work/irix-o32-basics' if args.basics else '.work/irix-o32-experiment')
    base.main()
    output = base.OUTPUT
    manifest = json.loads((output / 'manifest.json').read_text())
    # A failed extended build must not leave a usable three-fixture manifest.
    (output / 'manifest.json').unlink()
    manifest['experiment_version'] = 2 if args.basics else 1
    manifest['source_sha256']['checks.S'] = base.digest(base.SOURCE / 'checks.S')
    manifest['fixtures']['native-o32']['expect'] = 'output'
    manifest['fixtures']['irix-o32-marked']['expect'] = 'output'
    manifest['fixtures']['irix-o32-unbranded']['expect'] = 'reject'
    checks = [('irix-errors', 'ERRORS', 'quiet', 'checks.S'),
              ('irix-numbers', 'NUMBERS', 'quiet', 'checks.S'),
              ('irix-delay', 'DELAY', 'output', 'checks.S'),
              ('irix-loop', 'LOOP', 'timeout', 'checks.S'),
              ('irix-fault', 'FAULT', 'signal', 'checks.S')]
    if args.basics:
        manifest['source_sha256']['basics.S'] = base.digest(base.SOURCE / 'basics.S')
        checks += [(name, symbol, expected, 'basics.S') for name, symbol, expected in [
            ('irix-args', 'ARGS', 'quiet'), ('irix-args-empty', 'ARGS_EMPTY', 'quiet'),
            ('irix-files', 'FILES', 'quiet'), ('irix-file-errors', 'FILE_ERRORS', 'quiet'),
            ('irix-partial', 'PARTIAL', 'quiet'), ('irix-memory', 'MEMORY', 'quiet'),
            ('irix-file-map', 'FILE_MAP', 'quiet'), ('irix-mem-errors', 'MEM_ERRORS', 'quiet'),
            ('irix-stack-args', 'STACK_ARGS', 'quiet'), ('irix-readonly', 'READONLY', 'signal'),
            ('irix-unmapped', 'UNMAPPED', 'signal')]]
    for name, symbol, expected, source in checks:
        obj, elf = output / f'{name}.o', output / name
        base.run('as', '-EB', '-mabi=32', '-mips3', '-G', '0',
                 '--defsym', f'{symbol}=1', '-o', obj, base.SOURCE / source)
        base.run('ld', '-EB', '-m', 'elf32btsmip', '--build-id=none',
                 '-T', base.SOURCE / 'probe.ld', '-o', elf, obj)
        data = bytearray(elf.read_bytes())
        data[7] = 0
        struct.pack_into('>I', data, 36, struct.unpack_from('>I', data, 36)[0] & ~0xf030)
        elf.write_bytes(data)
        elf.chmod(0o755)
        manifest['fixtures'][name] = {**base.inspect(elf, ['Xiri'], False), 'expect': expected}
        (output / f'{name}.objdump.txt').write_text(base.run('objdump', '-d', elf))

    marked = (output / 'irix-o32-marked').read_bytes()
    phoff = struct.unpack_from('>I', marked, 28)[0]
    note_ph = phoff + 32
    note = struct.unpack_from('>I', marked, note_ph + 4)[0]
    # Each mutation targets a different recognition boundary.
    variants = {
        'bad-note-name': (note + 12, b'Fake'),
        'bad-note-version': (note + 20, struct.pack('>I', 2)),
        'bad-note-size': (note + 4, struct.pack('>I', 0xffffffff)),
        'bad-note-offset': (note_ph + 4, struct.pack('>I', 0xfffffff0)),
        'bad-osabi': (7, bytes([2])),
        'bad-n32': (36, struct.pack('>I', 0x20000121)),
        'bad-n64': (4, bytes([2])),
        'bad-endian': (5, bytes([1])),
        'bad-pie': (16, struct.pack('>H', 3)),
        'bad-interp': (note_ph, struct.pack('>I', 3)),
        'bad-dynamic': (note_ph, struct.pack('>I', 2)),
        'bad-entry': (24, struct.pack('>I', 0x1000)),
        'bad-load-size': (phoff + 16, struct.pack('>I', 0xffffffff)),
        'bad-phnum': (44, struct.pack('>H', 0xffff)),
    }
    for name, (offset, replacement) in variants.items():
        data = bytearray(marked)
        data[offset:offset + len(replacement)] = replacement
        (output / name).write_bytes(data)
        manifest['fixtures'][name] = {'sha256': base.digest(output / name),
                                      'bytes': len(data), 'expect': 'reject'}
    name = 'bad-truncated'
    (output / name).write_bytes(marked[:note + 15])
    manifest['fixtures'][name] = {'sha256': base.digest(output / name),
                                  'bytes': note + 15, 'expect': 'reject'}
    for name in manifest['fixtures']:
        (output / name).chmod(0o755)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f"Built {len(manifest['fixtures'])} fixtures in {output}")


if __name__ == '__main__':
    main()
