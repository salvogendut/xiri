#!/usr/bin/env python3
"""Build an original o32 query probe for both IRIX and Xiri."""
import importlib.util
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-irix-probe.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def main():
    directory = ROOT / '.work/irix-o32-queries'
    directory.mkdir(exist_ok=True)
    (directory / 'manifest.json').unlink(missing_ok=True)
    obj, elf = directory / 'queries.o', directory / 'queries'
    base.run('as', '-EB', '-mabi=32', '-mips3', '-G', '0', '-o', obj, base.SOURCE / 'queries.S')
    base.run('ld', '-EB', '-m', 'elf32btsmip', '--build-id=none', '-T', base.SOURCE / 'probe.ld', '-o', elf, obj)
    data = bytearray(elf.read_bytes())
    data[7] = 0
    struct.pack_into('>I', data, 36, 0x20000101)
    elf.write_bytes(data)
    elf.chmod(0o755)
    result = {'schema': 1, 'description': 'Original direct-trap queries; no vendor code',
              'builder_sha256': base.digest(Path(__file__).resolve()),
              'sources': {n: base.digest(base.SOURCE / n) for n in ['queries.S', 'probe.ld']},
              'files': {'queries': base.inspect(elf, ['Xiri'], False)},
              'tools': {n: base.run(n, '--version').splitlines()[0] for n in ['as', 'ld']},
              'record_bytes': 64, 'magic': '0x58495131', 'cases': [
                  'cap-mode', 'page-size', 'unknown-sysconf', 'cap-get', 'unknown-attribute',
                  'null-name', 'null-buffer', 'uid-euid', 'gid-egid', 'unknown-syssgi',
                  'bad-name', 'bad-buffer', 'readonly-buffer', 'long-name', 'name-79', 'name-80']}
    (directory / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    (directory / 'queries.readelf.txt').write_text(base.run('readelf', '-h', '-l', '-n', elf))
    (directory / 'queries.objdump.txt').write_text(base.run('objdump', '-d', elf))
    print(f'{base.digest(elf)} {len(data)} bytes, {len(result["cases"])} queries')


if __name__ == '__main__':
    main()
