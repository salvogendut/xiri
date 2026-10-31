#!/usr/bin/env python3
"""Recheck private breakpoint captures and publish only loader metadata/hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct

ROOT = Path(__file__).resolve().parent.parent
FIELDS = ['type', 'offset', 'vaddr', 'paddr', 'filesz', 'memsz', 'flags', 'align']
LIBRARIES = ['/lib32/rld', '/usr/lib32/libXaw.so.2', '/usr/lib32/libXmu.so']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def maps(raw):
    result, current = [], None
    for line in raw.splitlines():
        if line.startswith('CALL '):
            current = None
            values = dict(word.split('=') for word in line.split()[1:])
            if values['request'] == '68':
                require(values['count'] == '2' and values['fd'] == '3', 'unexpected ELF map call')
                current = dict(stub=values['stub'], before=[], after=[], memory=[])
                result.append(current)
        elif current is not None and line.startswith('RETURN '):
            values = dict(word.split('=') for word in line.split()[1:])
            require(values['request'] == '68', 'unexpected return')
            current['return'] = {key: int(values[key], 16) for key in ['v0', 'a3']}
        elif current is not None and line.startswith('PHDR '):
            values = dict(word.split('=') for word in line.split()[1:])
            header = {key: int(values[key], 10 if key in ['type', 'flags'] else 16) for key in FIELDS}
            phase = 'after' if 'return' in current else 'before'
            require(int(values['index']) == len(current[phase]), 'header order')
            current[phase].append(header)
        elif current is not None and line.startswith('MEM '):
            values = dict(word.split('=') for word in line.split()[2:])
            current['memory'].append(dict(address=int(values['address'], 16),
                                          error=int(values['error']), size=int(values['bytes']),
                                          data=bytes.fromhex(values['hex'])))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    directory = args.directory.resolve()
    result = json.loads((directory / 'result.json').read_text())
    require(result['status'] == 'observed' and result['clean_shutdown'], 'incomplete run')
    pin = json.loads((ROOT / 'lab/irix-xstat/baseline.json').read_text())
    require(result['pin'] == pin, 'kernel/emulator pin')
    require(set(result['sources']) == {'lab/irix-xclock/elfmap-trace.c',
                                      'scripts/probe-irix-xclock-elfmap.py',
                                      'scripts/probe-netbsd.py'}, 'source set')
    for name, expected_digest in result['sources'].items():
        require(digest(ROOT / name) == expected_digest, 'changed capture source: ' + name)
    manifest_path = ROOT / 'lab/irix-xclock/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    binaries, expected = {}, {}
    for name in LIBRARIES:
        path = ROOT / '.work/irix-xclock/root' / name.lstrip('/')
        require(digest(path) == manifest['files'][name]['sha256'], 'changed vendor file: ' + name)
        data = binaries[name] = path.read_bytes()
        phoff = struct.unpack_from('>I', data, 28)[0]
        entsize, count = struct.unpack_from('>HH', data, 42)
        require(entsize == 32, 'program header size')
        headers = [dict(zip(FIELDS, struct.unpack_from('>8I', data, phoff + i * entsize))) for i in range(count)]
        expected[name] = [h for h in headers if h['type'] == 1]
        require(len(expected[name]) == 2, 'program header count')
    require([c['name'] for c in result['captures']] == ['native-before', 'vendor-analog', 'vendor-digital', 'native-after'], 'case order')
    captures = []
    for capture in result['captures']:
        path = directory / (capture['name'] + '.txt')
        require(digest(path) == capture['raw_sha256'], 'capture digest')
        raw = path.read_text()
        records = re.findall(r'^(?:EXEC|NATIVE|CALL|RETURN|PHDR|RLD|END) .*$', raw, re.M)
        require(records == capture['records'], 'record decoding')
        if capture['name'].startswith('native-'):
            require(records == ['EXEC pc=0000000000400090 guard=intact',
                                'NATIVE breakpoint=00400090 restored=yes guard=intact',
                                'END exit=37 signal=0'], 'native breakpoint control')
            captures.append(capture)
            continue
        require(records[0] == 'EXEC pc=000000000faf15f8 guard=intact' and records[-1] == 'END exit=1 signal=0', 'vendor outcome')
        require("elfmap: couldn't map /usr/lib32/libXmu.so" in raw, 'loader diagnostic')
        observed = maps(raw)
        require(len(observed) == 3, 'ELF map count')
        clean = []
        for i, (name, item) in enumerate(zip(LIBRARIES, observed)):
            require(item['stub'] == ('libc' if i == 0 else 'rld'), 'syscall stub')
            require(item['before'] == expected[name] == item['after'], 'actual/unchanged headers: ' + name)
            outcome = {'v0': 12, 'a3': 1} if i == 2 else {'v0': expected[name][0]['vaddr'], 'a3': 0}
            require(item['return'] == outcome, 'ELF map return: ' + name)
            require(len(item['memory']) == 2, 'memory sample count')
            samples = []
            for header, memory in zip(item['before'], item['memory']):
                require(memory['address'] == header['vaddr'], 'memory sample address')
                sample = {key: memory[key] for key in ['address', 'error', 'size']}
                if i == 2:
                    offset = memory['address'] - expected[LIBRARIES[1]][0]['vaddr']
                    require(memory['error'] == 0 and memory['size'] == 128 and
                            memory['data'] == binaries[LIBRARIES[1]][offset:offset + 128], 'existing libXaw bytes')
                    sample.update(matches=LIBRARIES[1], file_offset=offset,
                                  sha256=hashlib.sha256(memory['data']).hexdigest())
                else:
                    require(memory['error'] != 0 and memory['size'] == 0 and not memory['data'], 'unexpected readable initial range')
                samples.append(sample)
            clean.append(dict(library=name, requested_headers=item['before'], headers_unchanged=True,
                              returned=item['return'], memory_before=samples))
        captures.append(dict(name=capture['name'], raw_sha256=capture['raw_sha256'], maps=clean, exit=1, signal=0))
    output = dict(schema=1, description='Actual original n32 xclock SGI_ELFMAP collision with libXaw',
                  run=str(directory.relative_to(ROOT)), result_sha256=digest(directory / 'result.json'),
                  mode=result['mode'], clean_shutdown=result['clean_shutdown'], pin=result['pin'],
                  sources=result['sources'], qualifier_sha256=digest(Path(__file__)),
                  manifest_sha256=digest(manifest_path), captures=captures,
                  scope='Root CI breakpoint observations on the pinned xstat kernel; no relocation implementation or GUI qualification')
    args.output.write_text(json.dumps(output, indent=2) + '\n')
    print('Qualified two native breakpoint controls and two matching libXmu collision captures.')


if __name__ == '__main__':
    main()
