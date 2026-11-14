#!/usr/bin/env python3
"""Retain executable admission cases and test n32 half-page RW segments."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import struct
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'.work/irix-exec-subpage'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    OUT.mkdir(exist_ok=True)
    seed = ROOT/'.work/irix-acrobat-probes'
    old = json.loads((seed/'manifest.json').read_text())
    result = dict(schema=1, seed_sha256=sha(seed/'manifest.json'),
                  builder_sha256=sha(Path(__file__)), files={}, cases=copy.deepcopy(old['loader_cases']))
    def save(name, data):
        path=OUT/name;path.write_bytes(data);path.chmod(0o555)
        result['files'][name]=dict(sha256=sha(path), bytes=len(data))
    for name in {c[k] for c in result['cases'] for k in ('program','interpreter')} | {'loader-runner.c'}:
        assert sha(seed/name)==old['files'][name]['sha256'],name
        save(name,(seed/name).read_bytes())
    spec=importlib.util.spec_from_file_location('runtime',ROOT/'scripts/build-irix-runtime.py')
    rt=importlib.util.module_from_spec(spec);spec.loader.exec_module(rt);rt.OUTPUT=OUT
    def tool(name,*args):
        binary=ROOT/'.work/netbsd-wait-accounting-build/tools/bin'/('mips64--netbsd-'+name)
        return subprocess.check_output([str(binary),*map(str,args)],text=True)
    rt.base.run=tool
    source=(ROOT/'lab/irix-lp64/runtime-interp.S').read_text().replace('0x10004000','0x10005000')
    # Verify the first RW page's copied prefix, and that writing its private
    # alias does not change the corresponding RX bytes in the shared case.
    prefix='''    li $s0, 0x10004000
    lbu $12, 0($s0)
    li $13, 0xa5
    bne $12, $13, failed
    nop
    li $12, 0x5a
    sb $12, 0($s0)
'''
    alias='''    li $s0, 0x00402000
    lbu $12, 0($s0)
    bne $12, $13, failed
    nop
'''
    for suffix, extra in [('plain',''),('prefix',prefix),('alias',prefix+alias)]:
        asm=OUT/('interpreter-'+suffix+'.S');asm.write_text(source.replace('    /* Initialized data,',extra+'\n    /* Initialized data,',1))
        text=rt.code(asm,0x0f901000,'interpreter-'+suffix)
        data=rt.image(text,True)
        struct.pack_into('>I',data,36,0x20000022)
        struct.pack_into('>I',data,52+2*32+20,0x2010)
        save('subpage-interpreter-'+suffix,data)
    for case in result['cases']:
        if case['name']=='n32-bad-exec-data-half-page':
            case.update(name='n32-existing-exec-data-half-page',interpreter='subpage-interpreter-plain',expect='output',previous_expect='reject')
    rx,rw=52+3*32,52+4*32
    template=bytearray((seed/'n32-bad-exec-data-half-page').read_bytes())
    template[0x4000:0x5000]=b'\xa5'*4096
    variants=[
        ('prefix',[], 'output'),
        ('shared-file-page',[(rx+16,0x3000),(rx+20,0x3000),(rw+4,0x3000)],'output'),
        ('full-file-page',[(rw+16,0x2000)],'output'),
        ('pure-bss',[(rw+16,0)],'reject'),
        ('mismatched-prefix',[(rw+4,0x4000)],'reject'),
        ('unaligned-address',[(rw+8,0x10005001)],'reject'),
        ('native-alignment',[(rw+28,8192)],'reject'),
        ('small-alignment',[(rw+28,2048)],'reject'),
        ('offset-underflow',[(rw+4,0)],'reject'),
        ('virtual-overlap',[(rw+8,0x00401000)],'reject'),
        ('file-overlap',[(rx+16,0x6000),(rx+20,0x6000)],'reject'),
        ('readonly-data',[(rw+24,4)],'reject'),
    ]
    for suffix,edits,expected in variants:
        data=bytearray(template)
        for offset,value in edits:struct.pack_into('>I',data,offset,value)
        offset,size=struct.unpack_from('>I',data,rw+4)[0],struct.unpack_from('>I',data,rw+16)[0]
        data.extend(b'\xa5'*max(0,offset+size+256-len(data)))
        if suffix=='file-overlap':data.extend(b'\xa5'*max(0,0x6100-len(data)))
        if expected=='output':
            data[offset-4096:offset]=b'\xa5'*4096
            data[offset:offset+size]=b'\0'*size
            struct.pack_into('>I',data,offset,0x12345678)
        name='n32-subpage-'+suffix;save(name,data)
        result['cases'].append(dict(name=name,abi='n32',program=name,
            interpreter='subpage-interpreter-'+('alias' if suffix=='shared-file-page' else 'prefix'),expect=expected))
    lines=['set -eu','cd /tmp/xiri-exec-subpage','ulimit -c 0',
           'mkdir -p root/emul/irix/usr/lib root/emul/irix/lib32',': >input.txt']
    for case in result['cases']:
        dest='root/emul/irix/'+('lib32' if case['abi']=='n32' else 'usr/lib')+'/libc.so.1'
        for src,target in [(case['program'],'root/program'),(case['interpreter'],dest)]:
            lines.append('cp '+shlex.quote(src)+' '+target+'.new; chmod 555 '+target+'.new; mv '+target+'.new '+target)
        lines.append('before=$(sha256 -q root/program)')
        for uid in (0,1234):
            lines.append('./loader-runner /program '+' '.join([str(uid)]*4)+' >'+shlex.quote(case['name']+'-'+str(uid)+'.log'))
        lines.append('test "$before" = "$(sha256 -q root/program)"')
    lines.append('echo EXEC_SUBPAGE_DONE');save('run.sh',('\n'.join(lines)+'\n').encode())
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    with tarfile.open(OUT/'probes.tgz','w:gz') as archive:
        for name in result['files']:archive.add(OUT/name,arcname=name)
        archive.add(OUT/'manifest.json',arcname='manifest.json')
    print(len(result['cases']),'executable cases')

if __name__=='__main__':main()
