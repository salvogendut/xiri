#!/usr/bin/env python3
"""Extend retained loader/map fixtures for measured legacy Acrobat layouts."""
import copy
import hashlib
import json
from pathlib import Path
import shlex
import struct
import tarfile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'.work/irix-acrobat-probes'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    OUT.mkdir(exist_ok=True)
    result = dict(schema=1, sources={'scripts/build-irix-acrobat-probes.py': sha(Path(__file__))},
                  files={}, loader_cases=[], mapping_cases=[])

    def save(name, data):
        path = OUT/name
        path.write_bytes(data)
        path.chmod(0o755)
        result['files'][name] = dict(sha256=sha(path), bytes=len(data))

    for directory, key, target in [('.work/irix-exec-align/probes', 'cases', 'loader_cases'),
                                   ('.work/irix-elfmap-subpage/probes', 'cases', 'mapping_cases')]:
        seed = ROOT/directory
        manifest = json.loads((seed/'manifest.json').read_text())
        result.setdefault('seeds', {})[directory] = sha(seed/'manifest.json')
        result[target] = copy.deepcopy(manifest[key])
        for name, entry in manifest['files'].items():
            assert sha(seed/name) == entry['sha256']
            save(name, (seed/name).read_bytes())

    rx, rw = 52+3*32, 52+4*32
    legacy = bytearray((OUT/'o32-dynamic').read_bytes())
    struct.pack_into('>I', legacy, 36, 4)
    for header in [rx, rw]:
        struct.pack_into('>I', legacy, header+28, 4096)
    legacy.extend(bytes([0xa5]) * (0x5100-len(legacy)))
    struct.pack_into('>I', legacy, rw+4, 0x5000)
    struct.pack_into('>I', legacy, 0x5000, 0x12345678)
    variants = [
        ('legacy-copy-data', [], 'output'),
        ('legacy-zero-phdr-memsz', [(52+20,0)], 'output'),
        ('legacy-bad-phdr-memsz', [(52+20,4)], 'reject'),
        ('legacy-bad-phdr-filesz', [(52+16,0)], 'reject'),
        ('legacy-shared-file-page', [(rx+16,0x3000),(rx+20,0x3000),(rw+4,0x3000),(0x3000,0x12345678)], 'output'),
        ('legacy-page-aligned-data', [(rw+4,0x4000)], 'output'),
        ('legacy-no-cpic', [(36,0)], 'reject'),
        ('legacy-unknown-flags', [(36,0x1004)], 'reject'),
        ('legacy-n32-flags', [(36,0x24)], 'reject'),
        ('legacy-unknown-isa', [(36,0x60000004)], 'reject'),
        ('legacy-small-alignment', [(rx+28,2048)], 'reject'),
        ('legacy-invalid-alignment', [(rw+28,0x3000)], 'reject'),
        ('legacy-incongruent-8k', [(rw+28,8192)], 'reject'),
        ('legacy-virtual-half-page', [(rw+8,0x10005000)], 'reject'),
        ('legacy-file-overlap', [(rx+16,0x6000),(rx+20,0x6000)], 'reject'),
        ('legacy-writable-text', [(rx+24,7)], 'reject'),
        ('legacy-wrapped-data', [(rw+4,0xfffff000)], 'reject'),
    ]
    for name, edits, expected in variants:
        data = bytearray(legacy)
        for offset, value in edits:
            struct.pack_into('>I', data, offset, value)
        if name == 'legacy-file-overlap':
            data.extend(bytes([0xa5]) * (0x6100-len(data)))
        save(name, data)
        result['loader_cases'].append(dict(name=name, abi='o32', program=name,
                                           interpreter='o32-interpreter', expect=expected))

    cases = {c['name']:c for c in result['mapping_cases']}
    for source in ['partial','pure-bss','full-and-tail','repeat','rollback','rollback-tail',
                   'text-fault','gap-fault','occupied-rx','occupied-rw','repeated-collision']:
        original = cases['elfmap-'+source]
        case = copy.deepcopy(original)
        name = 'elfmap-legacy-'+source
        data = bytearray((OUT/original['input']).read_bytes())
        offset, size = struct.unpack_from('>I',data,52+32+4)[0], struct.unpack_from('>I',data,52+32+16)[0]
        payload = data[offset:offset+size]
        data.extend(bytes([0xa5])*max(0,0x5000+size+256-len(data)))
        data[0x5000:0x5000+size] = payload
        struct.pack_into('>I',data,52+28,4096)
        struct.pack_into('>I',data,52+32+28,4096)
        struct.pack_into('>I',data,52+32+4,0x5000)
        number = len(result['mapping_cases'])+1
        struct.pack_into('>I',data,384,number)
        case.update(name=name,input=name,number=number)
        save(name,data)
        result['mapping_cases'].append(case)

    runner = (ROOT/'lab/irix-process/runner.c').read_text()
    needle = '        if (with_ids && (setgroups(0, NULL) ||'
    assert runner.count(needle) == 1
    isolated = runner.replace(needle, '        if (chroot("root") || chdir("/")) _exit(125);\n'+needle)
    save('loader-runner.c',isolated.encode())
    save('runner.c',runner.encode())
    result['sources']['lab/irix-process/runner.c'] = sha(ROOT/'lab/irix-process/runner.c')
    loaders = ['set -eu', 'cd /tmp/xiri-acrobat-tests', 'ulimit -c 0',
               'mkdir -p root/emul/irix/usr/lib root/emul/irix/lib32',
               'test ! -L root', ': >input.txt']
    for case in result['loader_cases']:
        destination = 'root/emul/irix/'+('lib32' if case['abi'] == 'n32' else 'usr/lib')+'/libc.so.1'
        for source, target in [(case['program'], 'root/program'), (case['interpreter'], destination)]:
            loaders.append('cp '+shlex.quote(source)+' '+target+'.new; chmod 555 '+target+'.new; mv '+target+'.new '+target)
        for uid in [0, 1234]:
            loaders.append('./loader-runner /program '+' '.join([str(uid)]*4)+
                           ' >'+shlex.quote('loader-'+case['name']+'-'+str(uid)+'.log'))
    loaders.append('echo LOADER_DONE')
    save('loaders.sh', ('\n'.join(loaders)+'\n').encode())
    mappings = ['set -eu', 'cd /tmp/xiri-acrobat-tests', 'ulimit -c 0', ': >input.txt']
    for case in result['mapping_cases']:
        mappings += ['cp '+shlex.quote(case['input'])+' elfmap-input',
                     'chmod '+('666' if case['mode'] & 0o111 == 0 else '777')+' elfmap-input',
                     'before=$(sha256 -q elfmap-input)']
        for abi in ['o32', 'n32']:
            for uid in [0, 1234]:
                mappings.append('./runner ./elfmap-'+abi+' '+' '.join([str(uid)]*4)+
                                ' >'+shlex.quote('map-'+abi+'-'+case['name']+'-'+str(uid)+'.log'))
        mappings.append('test "$before" = "$(sha256 -q elfmap-input)"')
    mappings.append('echo MAPPING_DONE')
    save('mapping.sh', ('\n'.join(mappings)+'\n').encode())
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    with tarfile.open(OUT/'probes.tgz','w:gz') as archive:
        for name in result['files']:
            archive.add(OUT/name,arcname=name)
        archive.add(OUT/'manifest.json',arcname='manifest.json')
    print(len(result['loader_cases']), 'loader cases;',len(result['mapping_cases']),'mapping cases')


if __name__ == '__main__':
    main()
