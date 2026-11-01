#!/usr/bin/env python3
"""Build an original direct-trap ELF-map probe and bounded mapping fixtures."""
import importlib.util
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-irix-probe.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)
OUTPUT = ROOT / '.work/irix-elfmap-subpage/probes'
SOURCE = ROOT / 'lab/irix-elfmap-subpage'

def run(tool,*args):
    return subprocess.check_output(['toolbox','run','-c','xiri-iris',str(ROOT/'.work/netbsd-irix64-build/tools/bin'/('mips64--netbsd-'+tool)),*map(str,args)],text=True)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / 'manifest.json').unlink(missing_ok=True)
    result = {'schema': 1, 'description': 'Original subpage mapping probes and relocation regressions; no vendor code',
              'sources': {str(p.relative_to(ROOT)): base.digest(p) for p in
                          [Path(__file__).resolve(), SOURCE/'probe.S', SOURCE/'probe.ld']},
              'files': {}, 'cases': []}
    for abi in ['o32','n32']:
        name = 'elfmap-' + abi
        obj, elf = OUTPUT/(name+'.o'), OUTPUT/name
        run('as', '-EB', '-mabi='+('n32' if abi=='n32' else '32'), '-mips3', '-G', '0',
                 '--defsym', 'N32='+str(int(abi=='n32')), '-o', obj, SOURCE/'probe.S')
        run('ld', '-EB', '-m', 'elf32btsmipn32' if abi=='n32' else 'elf32btsmip',
                 '--build-id=none', '-T', SOURCE/'probe.ld', '-o', elf, obj)
        data=bytearray(elf.read_bytes()); data[7]=0
        struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101)
        elf.write_bytes(data);elf.chmod(0o755)
        result['files'][name]={'sha256':base.digest(elf),'bytes':len(data)}

    def case(name, *, action=0, count=2, pointer=0, fd=0, edits=(), filesz=4, data_offset=0x4000,
             truncate=None, mode=0o755, errno=8, checks=0, signal=0, block=0, fallback=0, block_length=8192):
        number = len(result['cases']) + 1
        data = bytearray([0xa5]) * (data_offset + max(filesz, 4) + 256)
        struct.pack_into('>16sHHIIIIIHHHHHH', data, 0,
                         b'\x7fELF\x01\x02\x01' + bytes(9), 2, 8, 1, 0x0e000100,
                         52, 0, 0x20000001, 52, 32, 2, 0, 0, 0)
        headers = [[1, 0, 0x0e000000, 0x0e000000, 0x1000, 0x1000, 5, 0x4000],
                   [1, data_offset, 0x0e020000, 0x0e020000, filesz, filesz + 0x2011, 6, 0x4000]]
        for which, field, value in edits:
            headers[which][field] = value
        for i, header in enumerate(headers):
            struct.pack_into('>8I', data, 52 + i * 32, *header)
        # Executable function: return 0x13572468, independent of its address.
        struct.pack_into('>4I', data, 256, 0x3c021357, 0x34422468, 0x03e00008, 0)
        struct.pack_into('>5I', data, 384, number, action, count, pointer, fd)
        struct.pack_into('>3I', data, 404, block, fallback, block_length)
        data[data_offset:data_offset + filesz] = bytes([0x3c]) * filesz
        if truncate is not None:
            del data[truncate:]
        filename = 'elfmap-' + name
        path = OUTPUT / filename
        path.write_bytes(data)
        path.chmod(mode)
        result['files'][filename] = {'sha256': base.digest(path), 'bytes': len(data)}
        result['cases'].append({'name': filename, 'number': number, 'input': filename,
                                'mode': mode, 'action': action, 'block':block, 'fallback':fallback, 'netbsd': {
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
    for name, block in [('rx',0x0e000000),('rw',0x0e020000),('bss',0x0e022000),('gap',0x0e010000)]:
        case('occupied-'+name,action=1,block=block,errno=0,checks=1)
    case('repeated-collision',action=7,block=0x0e000000,errno=0,checks=3)
    case('occupied-fallback',action=7,block=0x0e000000,fallback=0x04000000,errno=0,checks=3)
    case('mixed-align',action=1,block=0x0e004000,edits=[(0,2,0x0e004000),(1,2,0x0e024000),(1,7,0x10000)],errno=0,checks=1)
    case('mixed-align-zero-residue',action=1,block=0x0e000000,edits=[(1,2,0x0e024000),(1,7,0x10000)],errno=0,checks=1)
    case('occupied-pure-bss',action=1,filesz=0,block=0x0e020000,errno=0,checks=1)
    case('occupied-full-tail',action=1,filesz=0x1004,block=0x0e022000,errno=0,checks=1)
    case('upper-edge',action=1,block=0x3ffd0000,edits=[(0,2,0x3ffd0000),(1,2,0x3fff0000)],errno=0,checks=1)
    case('no-bounded-space',action=1,block=0x04000000,block_length=0x3c000000,errno=12)
    case('as-limit-payload',action=0,block=0x0e000000,edits=[(1,5,0x1000000)],errno=0)
    case('relocated-text-fault',action=3,block=0x0e000000,errno=0,checks=1,signal=11)
    case('relocated-gap-fault',action=4,block=0x0e000000,errno=0,checks=1,signal=11)
    # Same four-byte aligned ELF headers, but data begins halfway through an
    # LP64 native page. Keep active payloads independent of native padding.
    sub=[(1,2,0x0e021000),(1,7,0x1000)]
    for name,size in [('partial',4),('full-4k',0x1000),('full-8k',0x2000),('full-tail',0x2004),('pure-bss',0)]:
        case('subpage-'+name,action=8,data_offset=0x5000,filesz=size,edits=sub,errno=0,checks=1)
    case('subpage-file-page-alias',action=9,data_offset=0x5000,filesz=0x2000,edits=sub+[(0,4,0x5000),(0,5,0x5000)],errno=0,checks=1)
    case('subpage-prefix-collision',action=8,data_offset=0x5000,edits=sub,block=0x0e020000,block_length=0x1000,errno=0,checks=1)
    case('subpage-bss-collision',action=8,data_offset=0x5000,edits=sub,block=0x0e022000,errno=0,checks=1)
    case('subpage-repeat-collision',action=7,data_offset=0x5000,edits=sub,block=0x0e020000,errno=0,checks=3)
    case('subpage-text-fault',action=3,data_offset=0x5000,edits=sub,errno=0,checks=1,signal=11)
    case('subpage-gap-fault',action=4,data_offset=0x5000,edits=sub,errno=0,checks=1,signal=11)
    case('subpage-native-incongruent',data_offset=0x4000,edits=sub)
    case('subpage-native-overlap',data_offset=0x5000,edits=[(1,2,0x0e001000),(1,7,0x1000)])
    case('subpage-file-overlap',data_offset=0x1000,edits=sub+[(0,4,0x2000),(0,5,0x2000)])
    case('subpage-byte-offset',data_offset=0x5000,edits=sub+[(1,1,0x5001),(1,2,0x0e021001)])
    case('subpage-short-file',data_offset=0x5000,edits=sub,truncate=0x5003)
    case('subpage-upper-edge',action=8,data_offset=0x5000,edits=sub+[(0,2,0x3ffd0000),(1,2,0x3fff1000)],errno=0,checks=1)
    (OUTPUT / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(result["cases"])} ELF-map cases, probe {base.digest(elf)}')


if __name__ == '__main__':
    main()
