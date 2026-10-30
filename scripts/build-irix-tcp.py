#!/usr/bin/env python3
"""Build original TCP ABI fixtures for the NetBSD and original IRIX probes."""
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
import struct

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT/'scripts/build-irix-lp64.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
digest = builder.base.digest


def run(tool, *args):
    binary = ROOT/'.work/netbsd-irix64-build/tools/bin'/('mips64--netbsd-'+tool)
    return subprocess.check_output([str(binary), *map(str,args)], text=True)


def main():
    if os.environ.get('XIRI_TCP_TOOLBOX') != '1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_TCP_TOOLBOX=1',
                        'PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())], check=True)
        return
    output = ROOT/'.work/irix-tcp/probes'
    output.mkdir(parents=True, exist_ok=True)
    (output/'manifest.json').unlink(missing_ok=True)
    result = {'schema': 1, 'builder_sha256': digest(Path(__file__)),
              'sources': {p: digest(ROOT/p) for p in ['lab/irix-tcp/probe.S', 'lab/irix-tcp/reference-server.S', 'lab/irix-o32/probe.ld']},
              'tools': {n: run(n, '--version').splitlines()[0] for n in ['as','ld']},
              'files': {}, 'cases': []}
    definitions = []

    def case(name, kind, **symbols):
        definitions.append((name, kind, symbols))

    for name, symbols in [
        ('default', {}), ('tcp', {'PROTOCOL': 6}),
        ('bad-domain', {'DOMAIN': 255}), ('bad-type', {'TYPE': 255}),
        ('udp-type', {'TYPE': 1}), ('bad-protocol', {'PROTOCOL': 255}),
        ('tcp-udp-protocol', {'PROTOCOL': 17}),
        ('native-flags', {'TYPE': 0x10000002}), ('bad-stack', {'BAD_STACK': 0}),
        ('delay', {'DELAY': 1})]:
        case('socket-'+name, 0, **symbols)
    for name, symbols in [
        ('refused', {}), ('bad-fd', {'FD': -1}), ('file-fd', {'FD': 1}),
        ('null', {'POINTER': 0}), ('high', {'POINTER': 0x80000000}),
        ('wrap', {'POINTER': 0xfffffff8}), ('short', {'LENGTH': 15}),
        ('long', {'LENGTH': 17}), ('negative', {'LENGTH': -1}),
        ('family', {'FAMILY': 1}), ('bad-stack', {'BAD_STACK': 0}),
        ('delay', {'DELAY': 1})]:
        case('connect-'+name, 1, **symbols)
    for name, symbols in [
        ('nodelay', {}), ('nodelay-off', {'VALUE': 0}),
        ('keepalive', {'LEVEL': 0xffff, 'OPTION': 8}),
        ('bad-fd', {'FD': -1}), ('file-fd', {'FD': 1}),
        ('null', {'POINTER': 0}), ('high', {'POINTER': 0x80000000}),
        ('wrap', {'POINTER': 0xfffffffe}), ('short', {'LENGTH': 3}),
        ('long', {'LENGTH': 8}), ('negative', {'LENGTH': -1}),
        ('option', {'OPTION': 0x7fffffff}), ('level', {'LEVEL': 0x7fffffff}),
        ('bad-stack', {'BAD_STACK': 0}), ('wrap-stack', {'BAD_STACK': 0xfffffff0})]:
        case('setopt-'+name, 2, **symbols)
    for name, ticks in [('zero', 0), ('one', 1), ('retry', 101), ('negative', -1)]:
        case('nap-'+name, 3, TICKS=ticks)
    case('echo', 4, PORT=6111)
    case('borrow-nodelay', 2, BORROW=1)
    case('borrow-nodelay-off', 2, BORROW=1, VALUE=0)
    case('borrow-keepalive', 2, BORROW=1, LEVEL=0xffff, OPTION=8)
    def build(abi, indirect, suffix, kind, symbols):
        name = abi+'-'+('indirect-' if indirect else 'direct-')+suffix
        number = len(result['cases'])+1
        values = dict(CASE=number, KIND=kind, INDIRECT=int(indirect),
                      TRAP={0:1107,1:1091,2:1105,3:1082,4:1091,5:1040}[kind],
                      DOMAIN=2, TYPE=2, PROTOCOL=0, FAMILY=2, PORT=6099,
                      LEVEL=6, OPTION=1, VALUE=1, LENGTH=4 if kind==2 else 16,
                      TICKS=0, **({'N32':1} if abi=='n32' else {}))
        values.update(symbols)
        obj, elf = output/(name+'.o'), output/name
        flags = [x for k,v in values.items() for x in ['--defsym', f'{k}={v}']]
        run('as', '-EB', '-mabi='+('n32' if abi=='n32' else '32'), '-mips3', '-G','0',
            *flags, '-o', obj, ROOT/'lab/irix-tcp/probe.S')
        run('ld', '-EB', '-m', 'elf32btsmipn32' if abi=='n32' else 'elf32btsmip',
            '--build-id=none', '-T', ROOT/'lab/irix-o32/probe.ld', '-o', elf, obj)
        data=bytearray(elf.read_bytes()); data[7]=0
        struct.pack_into('>I', data, 36, 0x20000021 if abi=='n32' else 0x20000101)
        elf.write_bytes(data); elf.chmod(0o755)
        result['files'][name]={'sha256':digest(elf),'bytes':len(data)}
        result['cases'].append({'name':name,'number':number,'abi':abi,'symbols':values,
                                'reference': suffix != 'nap-negative' and 'BORROW' not in symbols})
    for abi in ['o32','n32']:
        for indirect in [False,True]:
            for suffix,kind,symbols in definitions:
                build(abi,indirect,suffix,kind,symbols)
    for abi in ['o32','n32']:
        for indirect in [False,True]:
            build(abi,indirect,'clock-rate',5,{})
    obj, elf = output/'reference-server.o', output/'reference-server'
    run('as','-EB','-mabi=32','-mips3','-G','0','-o',obj,ROOT/'lab/irix-tcp/reference-server.S')
    run('ld','-EB','-m','elf32btsmip','--build-id=none','-T',ROOT/'lab/irix-o32/probe.ld','-o',elf,obj)
    data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000101)
    elf.write_bytes(data);elf.chmod(0o755)
    result['files']['reference-server']={'sha256':digest(elf),'bytes':len(data)}
    (output/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'{len(result["cases"])} TCP fixtures built', flush=True)


if __name__=='__main__':
    main()
