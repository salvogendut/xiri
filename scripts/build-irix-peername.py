#!/usr/bin/env python3
"""Extend the frozen TCP fixtures with original paired getpeername probes."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('tcp', ROOT/'scripts/build-irix-tcp.py')
tcp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tcp)


def main():
    if os.environ.get('XIRI_TCP_TOOLBOX') != '1':
        subprocess.run(['toolbox', 'run', '-c', 'xiri-iris', 'env', 'XIRI_TCP_TOOLBOX=1',
                        'PYTHONDONTWRITEBYTECODE=1', 'python3', str(Path(__file__).resolve())], check=True)
        return
    source, output = ROOT/'.work/irix-sockname/probes', ROOT/'.work/irix-peername/probes'
    output.mkdir(parents=True, exist_ok=True)
    (output/'manifest.json').unlink(missing_ok=True)
    result = json.loads((source/'manifest.json').read_text())
    for path, sha in result['sources'].items():
        if tcp.digest(ROOT/path) != sha: raise RuntimeError('rebuild TCP fixtures: '+path)
    for name, info in result['files'].items():
        if tcp.digest(source/name) != info['sha256']: raise RuntimeError('changed TCP fixture: '+name)
        shutil.copy2(source/name, output/name)
    result['parent_manifest_sha256'] = tcp.digest(source/'manifest.json')
    result['builder_sha256'] = tcp.digest(Path(__file__))
    result['tools'] = {n:tcp.run(n,'--version').splitlines()[0] for n in ['as','ld']}
    for path in ['lab/irix-peername/probe.S', 'lab/irix-peername/reference-remote.S']:
        result['sources'][path] = tcp.digest(ROOT/path)
    definitions = [('length-'+str(n), {'LENGTH':n}) for n in [0,1,2,3,4,8,15,16,17,32,0x7fffffff,-1]]
    definitions += [
        ('bad-fd', {'FD':-1}), ('file-fd', {'FD':1}), ('closed', {'CLOSED':1, 'FD':3}),
        ('null', {'POINTER':0}), ('high', {'POINTER':0x80000000}), ('wrap', {'POINTER':0xfffffff8}),
        ('null-length', {'LEN_POINTER':0}), ('high-length', {'LEN_POINTER':0x80000000}),
        ('wrap-length', {'LEN_POINTER':0xfffffffe}),
        ('readonly-name', {'READONLY_NAME':1}), ('readonly-length', {'READONLY_LEN':1}),
        ('bad-fd-null-length', {'FD':-1, 'LEN_POINTER':0}),
        ('file-fd-null-length', {'FD':1, 'LEN_POINTER':0}),
        ('null-negative', {'POINTER':0, 'LENGTH':-1}),
        ('null-zero', {'POINTER':0, 'LENGTH':0}),
        ('unaligned-name', {'NAME_OFFSET':1}), ('unaligned-length', {'LEN_OFFSET':1}),
        ('overlap', {'OVERLAP':1}), ('bad-stack', {'BAD_STACK':0}), ('delay', {'DELAY':1}),
        ('unconnected', {'UNCONNECTED':1}), ('unconnected-zero', {'UNCONNECTED':1,'LENGTH':0}),
        ('unconnected-negative', {'UNCONNECTED':1,'LENGTH':-1}),
        ('unconnected-null', {'UNCONNECTED':1,'POINTER':0}),
        ('unconnected-null-length', {'UNCONNECTED':1,'LEN_POINTER':0}),
        ('unconnected-bad-fd', {'UNCONNECTED':1,'FD':-1,'LEN_POINTER':0}),
        ('refused', {'UNCONNECTED':1,'REFUSED':1})]

    def build(name, source_path, abi='o32', values=None):
        obj, elf = output/(name+'.o'), output/name
        flags = [x for k,v in (values or {}).items() for x in ['--defsym', f'{k}={v}']]
        tcp.run('as', '-EB', '-mabi='+('n32' if abi=='n32' else '32'), '-mips3', '-G', '0',
                *flags, '-o', obj, ROOT/source_path)
        tcp.run('ld', '-EB', '-m', 'elf32btsmipn32' if abi=='n32' else 'elf32btsmip',
                '--build-id=none', '-T', ROOT/'lab/irix-o32/probe.ld', '-o', elf, obj)
        data=bytearray(elf.read_bytes()); data[7]=0
        struct.pack_into('>I', data, 36, 0x20000021 if abi=='n32' else 0x20000101)
        elf.write_bytes(data); elf.chmod(0o755)
        result['files'][name]={'sha256':tcp.digest(elf), 'bytes':len(data)}

    for abi in ['o32','n32']:
        for indirect in [False,True]:
            for suffix, symbols in definitions:
                name=abi+'-'+('indirect-' if indirect else 'direct-')+'peername-'+suffix
                number=len(result['cases'])+1
                values=dict(CASE=number, KIND=7, INDIRECT=int(indirect), LENGTH=16,
                            NAME_OFFSET=0, LEN_OFFSET=0, TICKS=0, **({'N32':1} if abi=='n32' else {}))
                values.update(symbols)
                if 'UNCONNECTED' not in symbols: values['CONNECTED']=1
                build(name, 'lab/irix-peername/probe.S', abi, values)
                result['cases'].append({'name':name, 'number':number, 'abi':abi, 'symbols':values,
                                        'reference':True, 'record_bytes':96,
                                        'user':suffix in ['length-0','length-16','readonly-length','bad-fd','unconnected','unconnected-null-length']})
    count=sum(c['symbols']['KIND']==7 and 'CONNECTED' in c['symbols'] for c in result['cases'])
    build('reference-remote','lab/irix-peername/reference-remote.S',values={'COUNT':count})
    (output/'manifest.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'{len(result["cases"])} socket/address fixtures built', flush=True)


if __name__=='__main__':
    main()
