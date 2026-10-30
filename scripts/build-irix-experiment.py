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


def add_segments(output, manifest):
    for source in ['segments.S', 'segments.ld']:
        manifest['source_sha256'][source] = base.digest(base.SOURCE / source)
    specs = [('irix-segments', None, 'output'),
             ('irix-segments-short', 'SHORT_BSS', 'output'),
             ('irix-segments-aligned', 'ALIGNED_DATA', 'output'),
             ('irix-segments-bss', 'PURE_BSS', 'output'),
             ('irix-segments-adjacent', 'ADJACENT', 'output'),
             ('irix-text-write', 'TEXT_WRITE', 'fault-output'),
             ('irix-segment-gap', 'GAP_READ', 'fault-output'),
             ('irix-segment-end', 'END_READ', 'fault-output')]
    for name, symbol, expected in specs:
        obj, elf = output / f'{name}.o', output / name
        symbols = ['--defsym', f'{symbol}=1'] if symbol else []
        base.run('as', '-EB', '-mabi=32', '-mips3', '-G', '0', *symbols,
                 '-o', obj, base.SOURCE / 'segments.S')
        script = base.SOURCE / 'segments.ld'
        if symbol == 'ADJACENT':
            script = output / 'adjacent.ld'
            script.write_text((base.SOURCE / 'segments.ld').read_text().replace('0x00600000', '0x00401000'))
        base.run('ld', '-EB', '-m', 'elf32btsmip', '--build-id=none',
                 '-z', 'max-page-size=4096', '-T', script, '-o', elf, obj)
        data = bytearray(elf.read_bytes())
        data[7] = 0
        struct.pack_into('>I', data, 36, struct.unpack_from('>I', data, 36)[0] & ~0xf030)
        elf.write_bytes(data)
        metadata = base.inspect(elf, ['Xiri'], False)
        phoff = struct.unpack_from('>I', data, 28)[0]
        assert struct.unpack_from('>H', data, 44)[0] == 3
        headers = [struct.unpack_from('>8I', data, phoff + i * 32) for i in range(3)]
        text, rw, note = headers
        assert [h[0] for h in headers] == [1, 1, 4]
        assert text[6] == 5 and rw[6] == 6 and rw[7] == 4096
        assert text[4] == text[5] and rw[5] > rw[4]
        assert rw[2] >= ((text[2] + text[5] + 4095) & ~4095)
        assert rw[2] % 4096 == rw[1] % 4096 == 0
        if symbol == 'PURE_BSS':
            assert rw[4] == 0
        else:
            end = rw[1] + rw[4]
            assert data[end:end + 32] == bytes([0xa5]) * 32, 'missing BSS poison sentinel'
        manifest['fixtures'][name] = {**metadata, 'segments': headers, 'expect': expected}
        (output / f'{name}.readelf.txt').write_text(base.run('readelf', '-h', '-l', '-n', elf))
        (output / f'{name}.objdump.txt').write_text(base.run('objdump', '-d', elf))

    marked = (output / 'irix-segments').read_bytes()
    phoff = struct.unpack_from('>I', marked, 28)[0]
    rw = phoff + 32
    offset, addr, filesz, memsz = [struct.unpack_from('>I', marked, rw + n)[0] for n in [4, 8, 16, 20]]
    variants = {
        'bad-data-filesz': [(rw + 16, memsz + 1)],
        'bad-data-empty': [(rw + 16, 0), (rw + 20, 0)],
        'bad-data-large': [(rw + 20, 0x100001)],
        'bad-data-wrap': [(rw + 8, 0xfffff000)],
        'bad-data-kernel': [(rw + 8, 0x80000000)],
        'bad-data-window': [(rw + 8, 0x00fff000)],
        'bad-data-overlap': [(rw + 8, 0x00400000)],
        'bad-data-unaligned': [(rw + 8, addr + 1)],
        'bad-data-offset-align': [(rw + 4, offset + 1)],
        'bad-data-align-small': [(rw + 28, 1)],
        'bad-data-align-power': [(rw + 28, 0x3000)],
        'bad-data-align-large': [(rw + 28, 0x200000)],
        'bad-data-congruence': [(rw + 28, 0x100000)],
        'bad-data-file-overlap': [(rw + 4, 0)],
        'bad-data-eof': [(rw + 4, (len(marked) + 8191) & ~4095)],
        'bad-data-offset-wrap': [(rw + 4, 0xfffff000)],
        'bad-data-wx': [(rw + 24, 7)],
        'bad-data-readonly': [(rw + 24, 4)],
        'bad-data-executable': [(rw + 24, 5)],
        'bad-data-flags': [(rw + 24, 0x100006)],
        'bad-data-type': [(rw, 2)],
        'bad-data-duplicate-note': [(rw, 4)],
        'bad-entry-data': [(24, addr)],
        'bad-entry-bss': [(24, addr + filesz)],
        'bad-entry-gap': [(24, 0x00500000)],
        'bad-text-writable': [(phoff + 24, 7)],
        'bad-text-bss': [(phoff + 20, struct.unpack_from('>I', marked, phoff + 16)[0] + 16)],
    }
    for name, edits in variants.items():
        data = bytearray(marked)
        for position, value in edits:
            struct.pack_into('>I', data, position, value)
        (output / name).write_bytes(data)
        manifest['fixtures'][name] = {'sha256': base.digest(output / name),
                                      'bytes': len(data), 'expect': 'reject'}
    name = 'bad-data-truncated'
    (output / name).write_bytes(marked[:offset + filesz - 1])
    manifest['fixtures'][name] = {'sha256': base.digest(output / name),
                                  'bytes': offset + filesz - 1, 'expect': 'reject'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    suites = parser.add_mutually_exclusive_group()
    suites.add_argument('--basics', action='store_true', help='add static argument, file, and memory checks')
    suites.add_argument('--segments', action='store_true', help='include basics and static data/BSS segment checks')
    args = parser.parse_args()
    basics = args.basics or args.segments
    directory = 'irix-o32-segments' if args.segments else 'irix-o32-basics' if basics else 'irix-o32-experiment'
    base.OUTPUT = ROOT / '.work' / directory
    base.main()
    output = base.OUTPUT
    manifest = json.loads((output / 'manifest.json').read_text())
    # A failed extended build must not leave a usable three-fixture manifest.
    (output / 'manifest.json').unlink()
    manifest['experiment_version'] = 3 if args.segments else 2 if basics else 1
    manifest['source_sha256']['checks.S'] = base.digest(base.SOURCE / 'checks.S')
    manifest['fixtures']['native-o32']['expect'] = 'output'
    manifest['fixtures']['irix-o32-marked']['expect'] = 'output'
    manifest['fixtures']['irix-o32-unbranded']['expect'] = 'reject'
    checks = [('irix-errors', 'ERRORS', 'quiet', 'checks.S'),
              ('irix-numbers', 'NUMBERS', 'quiet', 'checks.S'),
              ('irix-delay', 'DELAY', 'output', 'checks.S'),
              ('irix-loop', 'LOOP', 'timeout', 'checks.S'),
              ('irix-fault', 'FAULT', 'signal', 'checks.S')]
    if basics:
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
    if args.segments:
        add_segments(output, manifest)
    for name in manifest['fixtures']:
        (output / name).chmod(0o755)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f"Built {len(manifest['fixtures'])} fixtures in {output}")


if __name__ == '__main__':
    main()
