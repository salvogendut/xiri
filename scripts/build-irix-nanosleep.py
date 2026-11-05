#!/usr/bin/env python3
"""Build the same independent nanosleep observers for original IRIX and NetBSD."""
import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('builder', ROOT/'scripts/build-irix-tcp.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def main():
    if os.environ.get('XIRI_SLEEP_TOOLBOX') != '1':
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_SLEEP_TOOLBOX=1',
            'PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True)
        return
    out = ROOT/'.work/irix-job-control/nanosleep'
    out.mkdir(parents=True,exist_ok=True)
    sources = ['scripts/build-irix-nanosleep.py','lab/irix-job-control/nanosleep.c',
        'lab/irix-signal/start.S','lab/irix-signal/trampoline-v2.S',
        'lab/irix-job-control/call.S','lab/irix-mmap-local/probe.ld']
    names = ['zero','one-ns','one-ms','twenty-ms','negative-sec','negative-ns',
        'billion-ns','over-billion-ns','request-null','request-high','request-boundary',
        'request-unaligned','request-readonly','remaining-null','remaining-high',
        'remaining-unaligned','remaining-readonly','remaining-boundary','alias',
        'invalid-time-and-remaining','interrupt','interrupt-restart','interrupt-null',
        'interrupt-high','interrupt-unaligned','interrupt-readonly','interrupt-boundary',
        'interrupt-alias','interrupt-overlap','interrupt-max-sec','minimum-sec',
        'maximum-ns','both-high']
    manifest = dict(schema=1,record_bytes=512,
        sources={s:builder.digest(ROOT/s) for s in sources},
        tools={n:builder.run(n,'--version').splitlines()[0] for n in ['gcc','ld']},
        cases=[dict(number=i,name=name) for i,name in enumerate(names)],files={})
    for abi in ['o32','n32']:
        flags=['-EB','-mabi='+('32' if abi=='o32' else 'n32'),'-mips3',
            '-msoft-float','-mno-abicalls','-fno-pic','-G0']
        start=out/(abi+'-start.o')
        builder.run('gcc',*flags,'-c',ROOT/'lab/irix-signal/start.S','-o',start)
        for indirect in [0,1]:
            name=abi+('-indirect' if indirect else '-direct')
            objects=[start]
            for source,part in [('lab/irix-job-control/call.S','call'),
                                ('lab/irix-signal/trampoline-v2.S','trampoline')]:
                obj=out/(name+'-'+part+'.o')
                builder.run('gcc',*flags,'-DINDIRECT='+str(indirect),
                    '-DN32='+str(int(abi=='n32')),'-c',ROOT/source,'-o',obj)
                objects.append(obj)
            obj,elf=out/(name+'.o'),out/name
            builder.run('gcc',*flags,'-O2','-ffreestanding','-fno-builtin',
                '-fno-stack-protector','-Wall','-Wextra','-Werror','-c',
                ROOT/'lab/irix-job-control/nanosleep.c','-o',obj)
            builder.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip',
                '--build-id=none','-z','max-page-size=8192',
                '-T',ROOT/'lab/irix-mmap-local/probe.ld','-o',elf,*objects,obj)
            data=bytearray(elf.read_bytes());data[7]=0
            struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101)
            elf.write_bytes(data);elf.chmod(0o755)
            manifest['files'][name]=dict(sha256=builder.digest(elf),bytes=len(data),
                abi=abi,indirect=bool(indirect))
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(out)


if __name__=='__main__':
    main()
