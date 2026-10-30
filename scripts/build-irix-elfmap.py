#!/usr/bin/env python3
"""Build an original direct-trap ELF-map probe and bounded mapping fixtures."""
import importlib.util
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-irix-probe.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
OUTPUT = ROOT / '.work/irix-o32-elfmap'


def main():
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / 'manifest.json').unlink(missing_ok=True)
    obj, elf = OUTPUT / 'elfmap.o', OUTPUT / 'elfmap'
    base.run('as', '-EB', '-mabi=32', '-mips3', '-G', '0', '-o', obj, base.SOURCE / 'elfmap.S')
    base.run('ld', '-EB', '-m', 'elf32btsmip', '--build-id=none', '-T', base.SOURCE / 'probe.ld', '-o', elf, obj)
    code = bytearray(elf.read_bytes())
    code[7] = 0
    struct.pack_into('>I', code, 36, 0x20000101)
    elf.write_bytes(code)
    elf.chmod(0o755)
    result = {'schema': 1, 'description': 'Original ELF-map probe and payloads; no vendor code',
              'builder_sha256': base.digest(Path(__file__).resolve()),
              'sources': {n: base.digest(base.SOURCE / n) for n in ['elfmap.S', 'probe.ld']},
              'tools': {n: base.run(n, '--version').splitlines()[0] for n in ['as', 'ld']},
              'files': {'elfmap': base.inspect(elf, ['Xiri'], False)}, 'cases': []}

    def case(name, *, action=0, count=2, pointer=0, fd=0, edits=(), filesz=4,
             truncate=None, mode=0o755, errno=8, checks=0, signal=0):
        number = len(result['cases']) + 1
        data = bytearray([0xa5]) * (0x4000 + max(filesz, 4) + 256)
        struct.pack_into('>16sHHIIIIIHHHHHH', data, 0,
                         b'\x7fELF\x01\x02\x01' + bytes(9), 2, 8, 1, 0x0e000100,
                         52, 0, 0x20000001, 52, 32, 2, 0, 0, 0)
        headers = [[1, 0, 0x0e000000, 0x0e000000, 0x1000, 0x1000, 5, 0x4000],
                   [1, 0x4000, 0x0e020000, 0x0e020000, filesz, filesz + 0x2011, 6, 0x4000]]
        for which, field, value in edits:
            headers[which][field] = value
        for i, header in enumerate(headers):
            struct.pack_into('>8I', data, 52 + i * 32, *header)
        # Executable function: return 0x13572468, independent of its address.
        struct.pack_into('>4I', data, 256, 0x3c021357, 0x34422468, 0x03e00008, 0)
        struct.pack_into('>5I', data, 384, number, action, count, pointer, fd)
        data[0x4000:0x4000 + filesz] = bytes([0x3c]) * filesz
        if truncate is not None:
            del data[truncate:]
        filename = 'elfmap-' + name
        path = OUTPUT / filename
        path.write_bytes(data)
        path.chmod(mode)
        result['files'][filename] = {'sha256': base.digest(path), 'bytes': len(data)}
        result['cases'].append({'name': filename, 'number': number, 'input': filename,
                                'mode': mode, 'action': action, 'netbsd': {
                                    'v0': errno if errno else 0x0e000000,
                                    'a3': 1 if errno else 0, 'checks': checks, 'signal': signal}})

    case('partial', action=1, errno=0, checks=1)
    case('pure-bss', action=1, filesz=0, errno=0, checks=1)
    case('full-and-tail', action=1, filesz=0x1004, errno=0, checks=1)
    case('repeat', action=2, errno=0, checks=3)
    case('rollback', action=5, errno=0, checks=7)
    case('rollback-tail', action=6, filesz=0x1004, errno=0, checks=7)
    case('text-fault', action=3, errno=0, checks=1, signal=11)
    case('gap-fault', action=4, errno=0, checks=1, signal=11)
    for name, count in [('zero', 0), ('one', 1), ('three', 3), ('negative', 0xffffffff), ('large', 10001)]:
        case('count-' + name, count=count, errno=22)
    case('bad-headers', pointer=1, errno=14)
    case('null-headers', pointer=2, errno=14)
    for name, fd, errno in [('bad', 1, 9), ('closed', 2, 9), ('write-only', 3, 9),
                            ('directory', 4, 22), ('device', 5, 22), ('read-write', 6, 26)]:
        case('fd-' + name, fd=fd, errno=errno)
    case('no-execute', mode=0o644, errno=13)
    for name, edits in {
        'nonload': [(1, 0, 4)], 'text-write': [(0, 6, 7)], 'data-exec': [(1, 6, 7)],
        'text-bss': [(0, 5, 0x1004)], 'zero-memory': [(1, 5, 0)],
        'file-over-memory': [(1, 5, 3)], 'unaligned-address': [(1, 2, 0x0e020001)],
        'unaligned-offset': [(1, 1, 0x4001)], 'nonpower-align': [(1, 7, 0x3000)],
        'small-align': [(1, 7, 4)], 'large-align': [(1, 7, 0x200000)],
        'incongruent': [(1, 2, 0x0e021000)], 'overlap': [(1, 2, 0x0e000000)],
        'reversed': [(1, 2, 0x0dff0000)], 'file-overlap': [(1, 1, 0)],
        'offset-wrap': [(1, 1, 0xffffc000)], 'address-wrap': [(1, 2, 0xffffc000)],
        'oversized': [(1, 5, 0x1000001)], 'large-span': [(1, 2, 0x11000000)],
    }.items():
        case(name, edits=edits)
    case('short-file', truncate=0x4003)
    (OUTPUT / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    (OUTPUT / 'elfmap.objdump.txt').write_text(base.run('objdump', '-d', elf))
    print(f'{len(result["cases"])} ELF-map cases, probe {base.digest(elf)}')


if __name__ == '__main__':
    main()
