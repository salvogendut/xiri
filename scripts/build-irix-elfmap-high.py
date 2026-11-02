#!/usr/bin/env python3
"""Extend the existing original ELF-map fixtures with high library addresses."""
import copy
import importlib.util
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('relocation', ROOT/'scripts/build-irix-elfmap-relocation.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def main():
    base.OUTPUT = ROOT/'.work/irix-elfmap-high/probes'
    base.main()
    out = base.OUTPUT
    manifest = json.loads((out/'manifest.json').read_text())
    templates = {c['name']: c for c in manifest['cases']}
    # Preserve the lower-window regression cases unchanged. New fixtures use
    # the same position-independent RX function and checked data/BSS contents.
    for name, template, start, block in [
        ('high-preferred', 'partial', 0x60000000, 0),
        ('high-pure-bss', 'pure-bss', 0x60000000, 0),
        ('high-full-tail', 'full-and-tail', 0x60000000, 0),
        ('high-repeat', 'repeat', 0x60000000, 0),
        ('high-text-fault', 'text-fault', 0x60000000, 0),
        ('high-gap-fault', 'gap-fault', 0x60000000, 0),
        ('high-occupied-rx', 'occupied-rx', 0x60000000, 0x60000000),
        ('high-occupied-rw', 'occupied-rw', 0x60000000, 0x60020000),
        ('high-repeated-collision', 'repeated-collision', 0x60000000, 0x60000000),
        ('cross-1g', 'partial', 0x3fff0000, 0),
        ('near-2g', 'partial', 0x7f000000, 0),
        ('kernel-address', 'partial', 0x80000000, 0),
        ('cross-user-limit', 'partial', 0x7fff0000, 0),
    ]:
        c = copy.deepcopy(templates['elfmap-'+template])
        data = bytearray((out/c['input']).read_bytes())
        number = len(manifest['cases'])+1
        for i in range(2):
            struct.pack_into('>II', data, 52+32*i+8, start+i*0x20000, start+i*0x20000)
        struct.pack_into('>I', data, 24, start+256)
        struct.pack_into('>I', data, 384, number)
        struct.pack_into('>I', data, 404, block)
        c.update(name='elfmap-'+name, input='elfmap-'+name, number=number, block=block)
        c['netbsd']['v0'] = start
        if name == 'near-2g':
            # NetBSD reserves this part of the compat stack window. Unlike
            # the explicit occupant cases, do not replace any stack pages.
            c['native_collision'] = True
        if name in ['kernel-address', 'cross-user-limit']:
            struct.pack_into('>I', data, 388, 0)
            c['action'] = 0
            c['netbsd'].update(v0=8, a3=1, checks=0)
        f = out/c['input']; f.write_bytes(data); f.chmod(c['mode'])
        manifest['files'][f.name] = dict(sha256=base.base.digest(f), bytes=len(data))
        manifest['cases'].append(c)
    manifest['sources'][str(Path(__file__).resolve().relative_to(ROOT))] = base.base.digest(Path(__file__))
    manifest['description'] = 'High preferred library addresses and unchanged lower-window regressions'
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(len(manifest['cases']), 'high-address and regression cases')


if __name__ == '__main__':
    main()
