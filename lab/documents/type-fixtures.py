#!/usr/bin/env python3
"""Generate inert ELF headers for the original IRIX classifier; never execute them."""
import io
import json
from pathlib import Path
import struct
import sys
import tarfile


def fixtures():
    cases = {}
    def elf(slot=0, count=1, kind=3, interpreter=b'/usr/libexec/ld.elf_so\0'):
        data = bytearray(4096)
        data[:16] = b'\x7fELF\x01\x02\x01' + bytes(9)
        struct.pack_into('>HHIIIIIHHHHHH', data, 16,
                         kind, 8, 1, 0, 52, 0, 0x1007, 52, 32, count, 0, 0, 0)
        offset = 52 + count * 32
        struct.pack_into('>IIIIIIII', data, 52 + slot * 32,
                         3, offset, 0, 0, len(interpreter), len(interpreter), 4, 1)
        data[offset:offset+len(interpreter)] = interpreter
        return data
    for slot in (0, 1, 7, 15, 31):
        cases[f'pie-slot-{slot}'] = (elf(slot, slot+1), 0o555, True)
    cases['exec'] = (elf(kind=2), 0o555, True)
    cases['irix-interpreter'] = (elf(interpreter=b'/lib32/rld\0'), 0o555, False)
    cases['no-execute-mode'] = (elf(), 0o444, False)
    mutations = {
        'little-endian': (5, b'\x01'), 'elf64': (4, b'\x02'),
        'wrong-machine': (18, b'\x00\x03'), 'relocatable': (16, b'\x00\x01'),
        'no-interpreter': (52, b'\x00\x00\x00\x01'),
        'zero-headers': (44, b'\x00\x00'), 'wrong-entry-size': (42, b'\x00\x10'),
        'offset-outside-file': (56, b'\xff\xff\xff\xf0'),
        'header-table-outside-file': (28, b'\xff\xff\xff\xf0'),
        'wrong-interpreter-size': (68, b'\x00\x00\x00\x14'),
        'unterminated-interpreter': (104, b'X'),
        'wrong-interpreter': (84, b'/tmp/libexec/ld.elf_so'),
    }
    for name, (offset, value) in mutations.items():
        data = elf(); data[offset:offset+len(value)] = value
        cases[name] = (data, 0o555, False)
    cases['too-many-headers'] = (elf(32, 33), 0o555, False)
    for size in (0, 4, 20, 51, 60, 84, 100):
        cases[f'truncated-{size}'] = (elf()[:size], 0o555, False)
    return cases


def main():
    destination = Path(sys.argv[1]); destination.mkdir(parents=True, exist_ok=True)
    expected = {}
    with tarfile.open(destination/'type-fixtures.tgz', 'w:gz') as tar:
        for name, (data, mode, native) in fixtures().items():
            info = tarfile.TarInfo(name); info.mode=mode; info.size=len(data)
            tar.addfile(info, io.BytesIO(data)); expected[name]=native
    (destination/'type-fixtures.json').write_text(json.dumps(expected, indent=2)+'\n')


if __name__ == '__main__':
    main()
