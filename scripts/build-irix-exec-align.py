#!/usr/bin/env python3
"""Retain LP64 loader regressions and add the measured executable alignment."""
import hashlib
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    seed = ROOT / '.work/irix-lp64-probes'
    old = json.loads((seed / 'manifest.json').read_text())
    out = ROOT / '.work/irix-exec-align/probes'
    out.mkdir(parents=True, exist_ok=True)
    result = dict(schema=1, sources={'scripts/build-irix-exec-align.py': sha(Path(__file__))},
                  seed_manifest_sha256=sha(seed / 'manifest.json'), files={}, cases=old['loader_cases'])

    def save(name, data):
        path = out / name
        path.write_bytes(data)
        path.chmod(0o755)
        result['files'][name] = dict(sha256=sha(path), bytes=len(data))

    for name in sorted({c[k] for c in old['loader_cases'] for k in ['program','interpreter']}):
        assert sha(seed / name) == old['files'][name]['sha256']
        save(name, (seed / name).read_bytes())
    for abi in ['o32', 'n32']:
        for suffix, interpreter, index, alignment, expect in [
            ('exec-data-4k', False, 4, 4096, 'output'),
            ('exec-data-2k', False, 4, 2048, 'reject'),
            ('exec-data-zero-align', False, 4, 0, 'reject'),
            ('exec-text-4k', False, 3, 4096, 'reject-lp64'),
            ('interp-data-4k', True, 2, 4096, 'reject-lp64'),
        ]:
            name = abi + '-' + suffix
            data = bytearray((seed / (abi + ('-interpreter' if interpreter else '-dynamic'))).read_bytes())
            struct.pack_into('>I', data, 52 + index*32 + 28, alignment)
            save(name, data)
            result['cases'].append(dict(name=name, abi=abi, program=abi+'-dynamic' if interpreter else name,
                                       interpreter=name if interpreter else abi+'-interpreter', expect=expect))
    (out / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(len(result['cases']), 'loader cases prepared')


if __name__ == '__main__':
    main()
