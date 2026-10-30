#!/usr/bin/env python3
"""Build original direct/indirect o32 call and non-fixed mapping probes."""
import importlib.util
import json
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT / 'scripts/build-irix-probe.py')
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)


def main():
    directory = ROOT / '.work/irix-o32-dispatch'
    directory.mkdir(exist_ok=True)
    (directory / 'manifest.json').unlink(missing_ok=True)
    result = {'schema': 1, 'description': 'Original o32 dispatch probes; no vendor code',
              'builder_sha256': base.digest(Path(__file__).resolve()),
              'sources': {n: base.digest(base.SOURCE / n) for n in ['dispatch.S', 'probe.ld']},
              'files': {}, 'cases': [], 'record_bytes': 32,
              'tools': {n: base.run(n, '--version').splitlines()[0] for n in ['as', 'ld']}}

    def case(name, trap, *, indirect=True, arguments=(), v0=0, v1=0xfeedface,
             error=False, checks=0, mapping=False, exit_status=0, **symbols):
        name = 'dispatch-' + name
        number = len(result['cases']) + 1
        definitions = dict(CASE=number, TRAP=trap, INDIRECT=int(indirect),
                           **{f'ARG{i}': arguments[i] if i < len(arguments) else 0 for i in range(4)},
                           **symbols)
        obj, elf = directory / (name + '.o'), directory / name
        flags = [x for key, value in definitions.items() for x in ['--defsym', f'{key}={value}']]
        base.run('as', '-EB', '-mabi=32', '-mips3', '-G', '0', *flags,
                 '-o', obj, base.SOURCE / 'dispatch.S')
        base.run('ld', '-EB', '-m', 'elf32btsmip', '--build-id=none',
                 '-T', base.SOURCE / 'probe.ld', '-o', elf, obj)
        data = bytearray(elf.read_bytes())
        data[7] = 0
        struct.pack_into('>I', data, 36, 0x20000101)
        elf.write_bytes(data)
        elf.chmod(0o755)
        result['files'][name] = base.inspect(elf, ['Xiri'], False)
        result['cases'].append({'name': name, 'number': number, 'symbols': definitions,
                                'mapping': mapping, 'netbsd': {'v0': v0, 'v1': v1,
                                    'a3': int(error), 'checks': checks, 'exit': exit_status}})

    for indirect in [False, True]:
        prefix = 'indirect-' if indirect else 'direct-'
        case(prefix + 'pagesize-bad-stack', 1056, indirect=indirect, arguments=[14],
             v0=14, error=True, BAD_STACK=0)
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
    case('four-args-bad-stack', 1040, FOUR_ARGS=1, BAD_STACK=0, v0=14, error=True)
    case('delay-success', 1004, arguments=[1, 0, 0], DELAY=1)
    case('delay-error', 1006, arguments=[-1], DELAY=1, v0=9, error=True)
    case('exit', 1001, arguments=[37], exit_status=37)
    for name, stack in [('null', 0), ('home-wrap', 0xfffffff8), ('span-wrap', 0xffffffe8)]:
        case('stack-' + name, 1134, arguments=[0, 4096, 3, 2], BAD_STACK=stack, v0=14, error=True)
    case('stack-guard', 1000, indirect=False, ZERO_MAP=1, GUARD=1, v0=14, error=True)
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
             MAPPING=1, HINT=0x10000000, OFFSET=4096, BYTE=0x22, mapping=True, checks=5)
    for indirect in [False, True]:
        case(('indirect-' if indirect else 'direct-') + 'pagesize-valid-stack',
             1056, indirect=indirect, arguments=[14], v0=4096)
    path = directory / 'dispatch-input'
    path.write_bytes(bytes([0x11]) * 4096 + bytes([0x22]) * 4096)
    result['files'][path.name] = {'sha256': base.digest(path), 'bytes': path.stat().st_size}
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
    (directory / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(result["cases"])} dispatch fixtures built')


if __name__ == '__main__':
    main()
