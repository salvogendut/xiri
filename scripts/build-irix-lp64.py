#!/usr/bin/env python3
"""Build paired o32/n32 probes and bounded LP64 loader fixtures."""
import importlib.util
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-irix-probe.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def run(tool, *args):
    binary = ROOT / '.work/netbsd-irix64-build/tools/bin' / ('mips64--netbsd-' + tool)
    result = subprocess.run(['toolbox', 'run', '-c', 'xiri-iris', str(binary), *map(str, args)],
                            capture_output=True, text=True, check=True)
    return result.stdout


base.run = run


def main():
    directory = ROOT / '.work/irix-lp64-probes'
    directory.mkdir(exist_ok=True)
    (directory / 'manifest.json').unlink(missing_ok=True)
    result = {'schema': 1, 'description': 'Original o32/n32 probes; 8 KiB kernel, no vendor code',
              'builder_sha256': base.digest(Path(__file__).resolve()),
              'sources': {str(p.relative_to(ROOT)): base.digest(p) for p in [ROOT / 'lab/irix-lp64/dispatch.S', ROOT / 'lab/irix-o32/probe.ld', ROOT / 'lab/irix-lp64/runtime-interp.S', ROOT / 'lab/irix-lp64/fp.S', ROOT / 'lab/irix-lp64/heap.S', ROOT / 'lab/irix-lp64/heap.ld', ROOT / 'lab/irix-o32/probe.S', ROOT / 'scripts/build-irix-runtime.py']},
              'files': {}, 'cases': [], 'record_bytes': 32,
              'tools': {n: base.run(n, '--version').splitlines()[0] for n in ['as', 'ld']}}

    def case(name, trap, *, indirect=True, arguments=(), v0=0, v1=0xfeedface,
             error=False, checks=0, mapping=False, exit_status=0, **symbols):
        name = abi + '-' + name
        number = len(result['cases']) + 1
        definitions = dict(CASE=number, TRAP=trap, INDIRECT=int(indirect),
                           **{f'ARG{i}': arguments[i] if i < len(arguments) else 0 for i in range(4)},
                           **symbols)
        definitions['PAGE_BYTES'] = 8192
        if abi == 'n32': definitions['N32'] = 1
        obj, elf = directory / (name + '.o'), directory / name
        flags = [x for key, value in definitions.items() for x in ['--defsym', f'{key}={value}']]
        base.run('as', '-EB', '-mabi=' + ('n32' if abi == 'n32' else '32'), '-mips3', '-G', '0', *flags,
                 '-o', obj, ROOT / 'lab/irix-lp64/dispatch.S')
        base.run('ld', '-EB', '-m', 'elf32btsmipn32' if abi == 'n32' else 'elf32btsmip', '--build-id=none',
                 '-T', base.SOURCE / 'probe.ld', '-o', elf, obj)
        data = bytearray(elf.read_bytes())
        data[7] = 0
        struct.pack_into('>I', data, 36, 0x20000021 if abi == 'n32' else 0x20000101)
        elf.write_bytes(data)
        elf.chmod(0o755)
        assert data[:6] == b'\x7fELF\x01\x02'
        result['files'][name] = {'sha256': base.digest(elf), 'bytes': len(data),
                                 'abi': abi, 'flags': hex(struct.unpack_from('>I', data, 36)[0])}
        result['cases'].append({'name': name, 'abi': abi, 'number': number, 'symbols': definitions,
                                'mapping': mapping, 'netbsd': {'v0': v0, 'v1': v1,
                                    'a3': int(error), 'checks': checks, 'exit': exit_status}})

    for abi in ['o32', 'n32']:
        for indirect in [False, True]:
            prefix = 'indirect-' if indirect else 'direct-'
            case(prefix + 'pagesize-bad-stack', 1056, indirect=indirect, arguments=[14],
                 v0=8192 if abi == 'n32' else 14, error=abi != 'n32', BAD_STACK=0)
            case(prefix + 'sysmp-unknown', 1056, indirect=indirect, arguments=[0x7fffffff],
                 v0=89, error=True)
        case('uid', 1024, v1=0, BAD_STACK=0)
        case('gid', 1047, v1=0, BAD_STACK=0)
        case('close-bad', 1006, arguments=[-1], v0=9, error=True, BAD_STACK=0)
        case('write-bad-fd', 1004, arguments=[-1, 0, 1], v0=9, error=True, BAD_STACK=0)
        case('write-bad-pointer', 1004, arguments=[1, 0, 1], v0=14, error=True, BAD_STACK=0)
        case('write-zero', 1004, arguments=[1, 0, 0], BAD_STACK=0)
        case('open-read-close', 1005, OPEN_READ=1, v0=3, checks=1)
        case('four-args', 1040, FOUR_ARGS=1, v0=22, error=True)
        case('four-args-bad-stack', 1040, FOUR_ARGS=1, BAD_STACK=0, v0=22 if abi == 'n32' else 14, error=True)
        case('delay-success', 1004, arguments=[1, 0, 0], DELAY=1)
        case('delay-error', 1006, arguments=[-1], DELAY=1, v0=9, error=True)
        case('exit', 1001, arguments=[37], exit_status=37)
        for name, stack in [('null', 0), ('home-wrap', 0xfffffff8), ('span-wrap', 0xffffffe8)]:
            case('stack-' + name, 1134, arguments=[0, 8192, 3, 2], BAD_STACK=stack, v0=9 if abi == 'n32' else 14, error=True, BAD_MMAP=1)
        if abi == 'o32': case('stack-guard', 1000, indirect=False, ZERO_MAP=1, GUARD=1, v0=14, error=True)
        for number in [0, 1, 999, 1000, 1255, 1256, 0x7fffffff, 0xffffffff]:
            case('unknown-' + str(number), number, BAD_STACK=0, v0=89, error=True)
        for indirect in [False, True]:
            prefix = 'indirect-' if indirect else 'direct-'
            for name, hint, extra, checks in [
                    ('zero', 0, {}, 1), ('free', 0x10000000, {}, 1),
                    ('occupied', 0x10000000, {'OCCUPIED': 1}, 3),
                    ('text', 0x00400000, {'TEXT_HINT': 1}, 3),
                    ('unaligned', 0x10000001, {}, 1)]:
                case(prefix + 'hint-' + name, 1134, indirect=indirect, ZERO_MAP=1,
                     MAPPING=1, HINT=hint, OFFSET=0, BYTE=0, mapping=True, checks=checks, **extra)
            case(prefix + 'hint-high', 1134, indirect=indirect, ZERO_MAP=1,
                 MAPPING=1, HINT=0xfffff000, OFFSET=0, BYTE=0, v0=22, error=True)
            case(prefix + 'file-offset-private', 1134, indirect=indirect, FILE_MAP=1,
                 MAPPING=1, HINT=0x10000000, OFFSET=8192, BYTE=0x22, mapping=True, checks=5)
        for indirect in [False, True]:
            case(('indirect-' if indirect else 'direct-') + 'pagesize-valid-stack',
                 1056, indirect=indirect, arguments=[14], v0=8192)
    path = directory / 'dispatch-input'
    path.write_bytes(bytes([0x11]) * 8192 + bytes([0x22]) * 8192)
    result['files'][path.name] = {'sha256': base.digest(path), 'bytes': path.stat().st_size}
    result['page_bytes'] = 8192
    result['asa_cases'] = []
    for name, stdin, stdout in [
            ('lines', ' Alpha\n Beta\n', 'Alpha\nBeta\n'),
            ('double', ' Alpha\n0Beta\n', 'Alpha\n\nBeta\n'),
            ('page', ' Alpha\n1Beta\n', 'Alpha\n\fBeta\n'),
            ('overprint', ' Alpha\n+Beta\n', 'Alpha\rBeta\n'),
            ('unterminated', ' Tail', 'Tail\n'),
            ('empty', '', '')]:
        path = directory / ('asa-input-' + name)
        path.write_bytes(stdin.encode())
        result['files'][path.name] = {'sha256': base.digest(path), 'bytes': path.stat().st_size}
        result['asa_cases'].append({'name': 'asa-' + name, 'input': path.name,
                                    'stdin': stdin, 'stdout': stdout})
    add_heap_fixtures(directory, result)
    add_loader_fixtures(directory, result)
    (directory / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(result["cases"])} dispatch fixtures built')



def add_heap_fixtures(directory, result):
    result['heap_cases'] = []
    for abi in ['o32', 'n32']:
        for indirect in [False, True]:
            for kind, symbols in [
                    ('cycle', {'CYCLE': 1}), ('shrink-fault', {'CYCLE': 1, 'FAULT': 1}),
                    ('null', {'END': 0}), ('below-data', {'END': 0x007fe000}),
                    ('high', {'END': 0x80000000}), ('wrap', {'END': 0xffffffff}),
                    ('limit', {'END': 0x10802000}),
                    ('collision', {'END': 0x00806000, 'COLLISION': 1})]:
                name = abi + '-heap-' + ('indirect-' if indirect else 'direct-') + kind
                number = 200 + len(result['heap_cases'])
                definitions = dict(CASE=number, INDIRECT=int(indirect), **symbols)
                obj, elf = directory / (name + '.o'), directory / name
                flags = [x for k,v in definitions.items() for x in ['--defsym', f'{k}={v}']]
                base.run('as', '-EB', '-mabi=' + ('n32' if abi == 'n32' else '32'),
                         '-mips3', '-G', '0', *flags, '-o', obj, ROOT / 'lab/irix-lp64/heap.S')
                base.run('ld', '-EB', '-m', 'elf32btsmipn32' if abi == 'n32' else 'elf32btsmip',
                         '--build-id=none', '-T', ROOT / 'lab/irix-lp64/heap.ld', '-o', elf, obj)
                data = bytearray(elf.read_bytes()); data[7] = 0
                struct.pack_into('>I', data, 36, 0x20000021 if abi == 'n32' else 0x20000101)
                elf.write_bytes(data); elf.chmod(0o755)
                result['files'][name] = {'sha256': base.digest(elf), 'bytes': len(data)}
                result['heap_cases'].append({'name': name, 'abi': abi, 'number': number,
                    'symbols': definitions, 'mapping': False, 'signal': 11 if 'FAULT' in symbols else 0,
                    'netbsd': {'v0': 0 if 'CYCLE' in symbols else 12, 'v1': 0xfeedface,
                              'a3': 0 if 'CYCLE' in symbols else 1,
                              'checks': int('CYCLE' in symbols or 'COLLISION' in symbols), 'exit': 0}})


def add_loader_fixtures(directory, result):
    spec = importlib.util.spec_from_file_location('runtime_builder', ROOT / 'scripts/build-irix-runtime.py')
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    runtime.OUTPUT = directory
    runtime.base.run = run
    text = runtime.code(base.SOURCE / 'probe.S', 0x00401000, 'program-code')
    interp_text = runtime.code(ROOT / 'lab/irix-lp64/runtime-interp.S', 0x0f901000, 'interp-code')
    result['loader_cases'] = []

    def save(name, data):
        path = directory / name
        path.write_bytes(data)
        path.chmod(0o755)
        result['files'][name] = {'sha256': base.digest(path), 'bytes': len(data)}

    for abi in ['o32', 'n32']:
        program, interp = runtime.image(text), runtime.image(interp_text, True)
        struct.pack_into('>I', program, 52 + 4 * 32 + 20, 0x2010)
        struct.pack_into('>I', interp, 52 + 2 * 32 + 20, 0x2010)
        if abi == 'n32':
            struct.pack_into('>I', program, 36, 0x20000024)
            struct.pack_into('>I', interp, 36, 0x20000022)
            path = b'/lib32/libc.so.1\0'
            program[0x200:0x200+len(path)] = path
            for offset in [16,20]: struct.pack_into('>I', program, 52+32+offset, len(path))
        save(abi + '-dynamic', program)
        save(abi + '-interpreter', interp)
        result['loader_cases'].append({'name': abi+'-dynamic', 'abi':abi, 'program':abi+'-dynamic',
                                      'interpreter':abi+'-interpreter', 'expect':'output'})
        for prefix, original, rx, rw in [('exec',program,52+3*32,52+4*32),('interp',interp,52+32,52+2*32)]:
            variants = {
                'mixed-abi': [(36, (0x20000005 if prefix=='exec' else 0x20000003) if abi=='n32' else (0x20000024 if prefix=='exec' else 0x20000022))],
                'flags':[(36,0x20001005)], 'entry-data':[(24,struct.unpack_from('>I',original,rw+8)[0])],
                'phdr-count':[(44,17,'H')], 'text-write':[(rx+24,7)], 'data-wrap':[(rw+8,0xffffe000)],
                'data-overlap':[(rw+8,struct.unpack_from('>I',original,rx+8)[0])],
                'data-half-page':[(rw+4,0x5000),(rw+8,0x10005000 if prefix=='exec' else 0xf905000),(rw+28,4096)],
                'data-size':[(rw+16,0x2011)], 'data-align':[(rw+28,0x3000)], 'data-offset':[(rw+4,0x80000000)],
            }
            if prefix=='exec': variants.update({'phdr-address':[(52+8,0x00800034)], 'duplicate-interp':[(52+2*32,3)], 'wrong-interp':[(0x200,0x2f626164)]})
            else: variants.update({'type-exec':[(16,2,'H')], 'nested-interp':[(52,3)], 'main-overlap':[(rw+8,0x10004000)]})
            for variant, edits in variants.items():
                data=bytearray(original)
                for position,value,*fmt in edits: struct.pack_into('>'+(fmt[0] if fmt else 'I'),data,position,value)
                name=abi+'-bad-'+prefix+'-'+variant
                if variant == 'data-half-page':
                    data.extend(bytes([0xa5]) * (0x5100 - len(data)))
                    struct.pack_into('>I', data, 0x5000, 0x12345678)
                save(name,data)
                result['loader_cases'].append({'name':name,'abi':abi,'program':name if prefix=='exec' else abi+'-dynamic',
                                              'interpreter':name if prefix=='interp' else abi+'-interpreter','expect':'reject'})
        result['loader_cases'].append({'name':abi+'-dynamic-repeat','abi':abi,'program':abi+'-dynamic','interpreter':abi+'-interpreter','expect':'output'})
    obj, elf = directory/'n32-fp.o', directory/'n32-fp'
    base.run('as','-EB','-mabi=n32','-mips3','-G','0','-o',obj,ROOT/'lab/irix-lp64/fp.S')
    base.run('ld','-EB','-m','elf32btsmipn32','--build-id=none','-T',base.SOURCE/'probe.ld','-o',elf,obj)
    data=bytearray(elf.read_bytes());data[7]=0
    struct.pack_into('>I',data,36,0x20000021)
    save('n32-fp',data)


if __name__ == '__main__':
    main()
