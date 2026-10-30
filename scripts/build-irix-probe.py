#!/usr/bin/env python3
"""Build synthetic static o32 fixtures with the qualified NetBSD cross-tools."""

import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'lab/irix-o32'
OUTPUT = ROOT / '.work/irix-o32'
TOOLS = ROOT / '.work/netbsd-build/tools/bin'
PREFIX = ['toolbox', 'run', '-c', 'xiri-iris']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(tool, *args):
    command = PREFIX + [str(TOOLS / f'mipseb--netbsd-{tool}'), *map(str, args)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f'{tool} exited {result.returncode}: {result.stderr}\n{result.stdout}')
    return result.stdout


def inspect(path, expected_note, native):
    data = path.read_bytes()
    eh = struct.unpack_from('>16sHHIIIIIHHHHHH', data)
    ident, kind, machine, _, entry, phoff, _, flags, _, phentsize, phnum, *_ = eh
    assert ident[:7] == b'\x7fELF\x01\x02\x01', 'expected ELF32, MSB, version 1'
    assert kind == 2 and machine == 8, 'expected MIPS ET_EXEC'
    assert flags & 0xf0000000 == 0x20000000, 'expected MIPS III'
    assert flags & 0xf030 == (0x1000 if native else 0), 'wrong ABI flags'
    assert ident[7] == (2 if native else 0), 'wrong OSABI'
    headers = [struct.unpack_from('>8I', data, phoff + i * phentsize)
               for i in range(phnum)]
    assert all(h[0] not in (2, 3) for h in headers), 'dynamic/interpreted fixture'
    assert any(h[0] == 1 and h[6] & 1 and h[2] <= entry < h[2] + h[4]
               for h in headers), 'entry not in executable file-backed LOAD'
    notes = []
    for kind, offset, _, _, filesz, *_ in headers:
        if kind != 4 or not filesz:
            continue
        end = offset + filesz
        while offset < end:
            namesz, descsz, ntype = struct.unpack_from('>III', data, offset)
            offset += 12
            name = data[offset:offset + namesz]
            offset += (namesz + 3) & ~3
            desc = data[offset:offset + descsz]
            offset += (descsz + 3) & ~3
            notes.append({'name': name.rstrip(b'\0').decode(),
                          'type': ntype, 'descriptor_hex': desc.hex()})
    assert [n['name'] for n in notes] == expected_note, 'unexpected branding'
    return {'sha256': digest(path), 'bytes': len(data), 'entry': hex(entry),
            'flags': hex(flags), 'osabi': ident[7], 'notes': notes}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'manifest.json').unlink(missing_ok=True)
    result = {'description': 'Synthetic fixtures, not vendor IRIX binaries',
              'source_sha256': {n: digest(SOURCE / n) for n in ['probe.S', 'probe.ld']},
              'tools': {}, 'fixtures': {}}
    for tool in ['as', 'ld']:
        result['tools'][tool] = run(tool, '--version').splitlines()[0]
    for name, symbols, notes in [('native-o32', ['NATIVE=1'], ['NetBSD']),
                                 ('irix-o32-marked', ['MARKED=1'], ['Xiri']),
                                 ('irix-o32-unbranded', [], [])]:
        obj, elf = OUTPUT / f'{name}.o', OUTPUT / name
        options = [part for symbol in symbols for part in ['--defsym', symbol]]
        run('as', '-EB', '-mabi=32', '-mips3', '-G', '0', *options,
            '-o', obj, SOURCE / 'probe.S')
        script = SOURCE / 'probe.ld'
        if not notes:
            script = OUTPUT / 'unbranded.ld'
            script.write_text((SOURCE / 'probe.ld').read_text()
                              .replace('    note PT_NOTE FLAGS(4);\n', '')
                              .replace(':image :note', ':image'))
        run('ld', '-EB', '-m', 'elf32btsmip', '--build-id=none',
            '-T', script, '-o', elf, obj)
        data = bytearray(elf.read_bytes())
        native = name == 'native-o32'
        # Set identity explicitly: NetBSD for the positive control; System V
        # and legacy IRIX o32 ABI bits for the two synthetic foreign fixtures.
        data[7] = 2 if native else 0
        flags = struct.unpack_from('>I', data, 36)[0]
        struct.pack_into('>I', data, 36, flags if native else flags & ~0xf030)
        elf.write_bytes(data)
        elf.chmod(0o755)
        result['fixtures'][name] = inspect(elf, notes, native)
        (OUTPUT / f'{name}.readelf.txt').write_text(run('readelf', '-h', '-l', '-n', elf))
        (OUTPUT / f'{name}.objdump.txt').write_text(run('objdump', '-d', elf))
        print(name, result['fixtures'][name], flush=True)
    (OUTPUT / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
