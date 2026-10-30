#!/usr/bin/env python3
"""Build original native n32/n64 ABI probes for the isolated 64-bit kernel."""
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'lab/netbsd64'
OUTPUT = ROOT / '.work/netbsd64-probes'
TOOLS = ROOT / '.work/netbsd64-build/tools/bin'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(tool, *args):
    return subprocess.check_output(['toolbox', 'run', '-c', 'xiri-iris',
                                    str(TOOLS / f'mips64--netbsd-{tool}'), *map(str, args)], text=True)


def main():
    OUTPUT.mkdir(exist_ok=True)
    (OUTPUT / 'manifest.json').unlink(missing_ok=True)
    manifest = {'schema': 1, 'builder_sha256': digest(Path(__file__).resolve()),
                'sources': {n: digest(SOURCE / n) for n in ['native.S', 'native.ld']},
                'tools': {n: run(n, '--version').splitlines()[0] for n in ['as', 'ld']},
                'files': {}, 'cases': [], 'page_bytes': 8192}
    for abi, flag, emulation in [('n32', 'n32', 'elf32btsmipn32'), ('n64', '64', 'elf64btsmip')]:
        for kind, symbols in [('registers', ['REGISTERS']), ('fp', ['FP']),
                              ('seek64', ['FILE', 'SEEK']), ('mmap', ['FILE', 'MMAP']),
                              ('indirect-mmap', ['FILE', 'MMAP', 'INDIRECT']),
                              ('errors', ['ERRORS']), ('delay', ['DELAY']), ('text-fault', ['TEXT_FAULT'])]:
            name = abi + '-' + kind
            obj, elf = OUTPUT / (name + '.o'), OUTPUT / name
            flags = [x for s in symbols for x in ['--defsym', s + '=1']]
            run('as', '-EB', '-mabi=' + flag, '-mips3', '-G', '0', '--defsym',
                f'PAGE_BYTES={manifest["page_bytes"]}', *flags, '-o', obj, SOURCE / 'native.S')
            run('ld', '-EB', '-m', emulation, '--build-id=none', '-T', SOURCE / 'native.ld', '-o', elf, obj)
            data = bytearray(elf.read_bytes())
            data[7] = 2  # ELFOSABI_NETBSD, with a matching NetBSD note.
            elf.write_bytes(data)
            elf.chmod(0o755)
            assert data[:6] == b'\x7fELF' + bytes([1 if abi == 'n32' else 2, 2])
            flags = struct.unpack_from('>I', data, 36 if abi == 'n32' else 48)[0]
            assert flags & 0xf020 == (0x20 if abi == 'n32' else 0)
            manifest['files'][name] = {'sha256': digest(elf), 'bytes': len(data),
                                       'abi': abi, 'elf_class': data[4], 'flags': hex(flags)}
            manifest['cases'].append({'name': name, 'signal': 11 if kind == 'text-fault' else 0})
            (OUTPUT / (name + '.readelf.txt')).write_text(run('readelf', '-h', '-l', '-n', elf))
    path = OUTPUT / 'map-input.bin'
    path.write_bytes(bytes([0x11]) * manifest['page_bytes'] + bytes([0x22]) * manifest['page_bytes'])
    manifest['files'][path.name] = {'sha256': digest(path), 'bytes': path.stat().st_size}
    (OUTPUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(f'{len(manifest["cases"])} native n32/n64 probes built')


if __name__ == '__main__':
    main()
