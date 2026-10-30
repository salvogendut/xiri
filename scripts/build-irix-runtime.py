#!/usr/bin/env python3
"""Build original dynamic-loader fixtures; imports no vendor code."""
import importlib.util
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-irix-probe.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
OUTPUT = ROOT / '.work/irix-o32-runtime'


def code(source, address, name):
    obj, elf, raw = [OUTPUT / (name + suffix) for suffix in ['.o', '.elf', '.bin']]
    script = OUTPUT / (name + '.ld')
    script.write_text(f'ENTRY(_start)\nSECTIONS {{ . = {address}; '
                      '.text : { *(.text) *(.rodata) } '
                      '/DISCARD/ : { *(.reginfo) *(.MIPS.abiflags) *(.pdr) *(.gnu.attributes) } }\n')
    base.run('as', '-EB', '-mabi=32', '-mips3', '-G', '0', '-o', obj, source)
    base.run('ld', '-EB', '-m', 'elf32btsmip', '--build-id=none', '-T', script, '-o', elf, obj)
    base.run('objcopy', '-O', 'binary', '-j', '.text', elf, raw)
    return raw.read_bytes()


def image(text, interpreter=False):
    start = 0x0f900000 if interpreter else 0x00400000
    data_addr = 0x0f904000 if interpreter else 0x10004000
    path = b'/usr/lib/libc.so.1\0'
    # PHDR, INTERP, DYNAMIC, RX, RW for executable; DYNAMIC, RX, RW for DSO.
    headers = [] if interpreter else [
        (6, 52, start + 52, start + 52, 160, 160, 4, 4),
        (3, 0x200, start + 0x200, start + 0x200, len(path), len(path), 4, 1)]
    headers += [(2, 0x240, start + 0x240, start + 0x240, 8, 8, 4, 4),
                (1, 0, start, start, 0x2000, 0x2000, 5, 0x4000),
                (1, 0x4000, data_addr, data_addr, 4, 0x1010, 6, 0x4000)]
    data = bytearray(0x4100)
    struct.pack_into('>16sHHIIIIIHHHHHH', data, 0,
                     b'\x7fELF\x01\x02\x01' + bytes(9), 3 if interpreter else 2,
                     8, 1, start + 0x1000, 52, 0,
                     0x20000003 if interpreter else 0x20000005,
                     52, 32, len(headers), 0, 0, 0)
    for i, ph in enumerate(headers):
        struct.pack_into('>8I', data, 52 + i * 32, *ph)
    data[0x200:0x200 + len(path)] = path
    assert len(text) <= 0x1000
    data[0x1000:0x1000 + len(text)] = text
    struct.pack_into('>I', data, 0x4000, 0x12345678)
    data[0x4004:] = bytes([0xa5]) * (len(data) - 0x4004)
    return data


def main():
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / 'manifest.json').unlink(missing_ok=True)
    program = image(code(base.SOURCE / 'probe.S', 0x00401000, 'program-code'))
    interp = image(code(base.SOURCE / 'runtime-interp.S', 0x0f901000, 'interp-code'), True)
    result = {'schema': 1, 'description': 'Original synthetic loader fixtures, no vendor code',
              'sources': {n: base.digest(base.SOURCE / n) for n in ['probe.S', 'runtime-interp.S']},
              'builder_sha256': base.digest(Path(__file__).resolve()),
              'tools': {n: base.run(n, '--version').splitlines()[0] for n in ['as', 'ld']},
              'files': {}, 'cases': []}

    def save(name, data):
        path = OUTPUT / name
        path.write_bytes(data)
        path.chmod(0o755)
        result['files'][name] = {'sha256': base.digest(path), 'bytes': len(data)}

    save('dynamic', program)
    save('interpreter', interp)
    result['cases'].append({'name': 'dynamic', 'program': 'dynamic', 'interpreter': 'interpreter', 'expect': 'output'})
    # Exercise both executable and interpreter validation, not just branding.
    for prefix, original, rx, rw in [('exec', program, 52 + 3 * 32, 52 + 4 * 32),
                                      ('interp', interp, 52 + 32, 52 + 2 * 32)]:
        variants = {
            'n32': [(36, 0x20000024 if prefix == 'exec' else 0x20000022)],
            'flags': [(36, 0x20001005 if prefix == 'exec' else 0x20001003)],
            'entry-data': [(24, struct.unpack_from('>I', original, rw + 8)[0])],
            'phdr-count': [(44, 17, 'H')],
            'text-write': [(rx + 24, 7)],
            'data-wrap': [(rw + 8, 0xfffff000)],
            'data-overlap': [(rw + 8, struct.unpack_from('>I', original, rx + 8)[0])],
            'data-size': [(rw + 16, 0x1011)],
            'data-align': [(rw + 28, 0x3000)],
            'data-offset': [(rw + 4, 0x80000000)],
        }
        if prefix == 'exec':
            variants.update({'phdr-address': [(52 + 8, 0x00800034)],
                             'duplicate-interp': [(52 + 2 * 32, 3)],
                             'wrong-interp': [(0x200, 0x2f626164)]})
        else:
            variants.update({'type-exec': [(16, 2, 'H')],
                             'nested-interp': [(52, 3)],
                             'main-overlap': [(rw + 8, 0x10004000)]})
        for variant, edits in variants.items():
            data = bytearray(original)
            for position, value, *fmt in edits:
                struct.pack_into('>' + (fmt[0] if fmt else 'I'), data, position, value)
            name = f'bad-{prefix}-{variant}'
            save(name, data)
            result['cases'].append({'name': name, 'program': name if prefix == 'exec' else 'dynamic',
                                    'interpreter': name if prefix == 'interp' else 'interpreter', 'expect': 'reject'})
        name = f'bad-{prefix}-truncated'
        save(name, original[:0x4003])
        result['cases'].append({'name': name, 'program': name if prefix == 'exec' else 'dynamic',
                                'interpreter': name if prefix == 'interp' else 'interpreter', 'expect': 'reject'})
    result['cases'].append({'name': 'dynamic-repeat', 'program': 'dynamic', 'interpreter': 'interpreter', 'expect': 'output'})
    (OUTPUT / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'Built {len(result["files"])} files, {len(result["cases"])} cases in {OUTPUT}')


if __name__ == '__main__':
    main()
