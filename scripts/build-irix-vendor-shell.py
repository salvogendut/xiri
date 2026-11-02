#!/usr/bin/env python3
"""Build original static n32 admission fixtures and shell behavior cases."""
import copy
import hashlib
import json
from pathlib import Path
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT/'.work/irix-vendor-shell/probes'


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tool(name, *args):
    subprocess.run(['toolbox', 'run', '-c', 'xiri-iris',
        str(ROOT/'.work/netbsd-irix64-build/tools/bin'/('mips64--netbsd-'+name)),
        *map(str,args)], check=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sources=['scripts/build-irix-vendor-shell.py','lab/irix-vendor-shell/static.S',
             'lab/irix-vendor-shell/process.c','lab/irix-vendor-shell/reference-exec.c',
             'lab/irix-shell/start.S','lab/irix-shell/call.S','lab/irix-shell/probe.ld']
    result=dict(schema=1, sources={f:sha(ROOT/f) for f in sources}, files={}, loader_cases=[])
    ld=OUT/'code.ld'
    ld.write_text('ENTRY(_start)\nSECTIONS { . = 0x00401000; .text : { *(.text) } /DISCARD/ : { *(.reginfo) *(.MIPS.abiflags) *(.pdr) *(.gnu.attributes) } }\n')
    def image(native=False):
        name='native' if native else 'foreign'
        tool('as','-EB','-mabi=n32','-mips3','-G','0','--defsym','SYS_WRITE='+str(4 if native else 1004),
             '--defsym','SYS_EXIT='+str(1 if native else 1001),'-o',OUT/(name+'.o'),ROOT/sources[1])
        tool('ld','-EB','-m','elf32btsmipn32','--build-id=none','-T',ld,'-o',OUT/(name+'.elf'),OUT/(name+'.o'))
        tool('objcopy','-O','binary','-j','.text',OUT/(name+'.elf'),OUT/(name+'.bin'))
        code=(OUT/(name+'.bin')).read_bytes(); assert len(code)<4096
        data=bytearray(0x4100)
        ph=[(0x70000002,0x200,0x00400200,0,40,40,4,8),
            (0x70000000,0x240,0x00400240,0,24,24,4,4),
            (1,0,0x00400000,0,0x2000,0x2000,5,0x4000),
            (1,0x4000,0x10004000,0,4,0x2010,6,0x4000)]
        if native:
            ph.append((4,0x280,0x00400280,0,24,24,4,4))
            struct.pack_into('>III8sI',data,0x280,7,4,1,b'NetBSD\0\0',1100000000)
        ident=b'\x7fELF\x01\x02\x01'+bytes([2 if native else 0])+bytes(8)
        struct.pack_into('>16sHHIIIIIHHHHHH',data,0,ident,2,8,1,0x00401000,52,0,0x20000020,52,32,len(ph),0,0,0)
        for i,h in enumerate(ph):struct.pack_into('>8I',data,52+32*i,*h)
        # ODK_REGINFO with an original empty register-use mask and GP value.
        struct.pack_into('>BBHI',data,0x200,1,40,0,0)
        data[0x1000:0x1000+len(code)]=code
        struct.pack_into('>I',data,0x4000,0x12345678)
        data[0x4004:]=bytes([0xa5])*(len(data)-0x4004)
        return data
    def save(name,data,expect):
        p=OUT/name;p.write_bytes(data);p.chmod(0o755)
        result['files'][name]=dict(sha256=sha(p),bytes=len(data))
        result['loader_cases'].append(dict(name=name,expect=expect))
    valid=image();save('static-n32',valid,'output')
    save('native-n32',image(True),'native-output')
    rx=52+64;rw=52+96;options=52;reginfo=84
    variants={
        'machine':[(18,3,'H')], 'abi-o32':[(36,0x20000000)],
        'arch-mips2':[(36,0x10000020)], 'dynamic-flags':[(36,0x20000024)],
        'phnum':[(44,5,'H')], 'phoff':[(28,56)],
        'entry-data':[(24,0x10004000)], 'entry-gap':[(24,0x00408000)],
        'entry-unaligned':[(24,0x00401001)],
        'text-write':[(rx+24,7)], 'text-bss':[(rx+20,0x2004)],
        'data-exec':[(rw+24,7)], 'data-over-memory':[(rw+16,0x2011)],
        'data-overlap':[(rw+8,0x00400000)], 'data-wrap':[(rw+8,0xffffc000)],
        'data-offset-wrap':[(rw+4,0xffffc000)], 'data-align':[(rw+28,0x3000)],
        'data-unaligned':[(rw+8,0x10004004)], 'data-zero':[(rw+20,0)],
        'data-large':[(rw+20,0x1000001)], 'file-overlap':[(rw+4,0)],
        'options-missing':[(options,0)], 'options-duplicate':[(reginfo,0x70000002)],
        'options-address':[(options+8,0x00400300)], 'options-size':[(options+16,7)],
        'options-align':[(options+28,4)], 'options-write':[(options+24,6)],
        'reginfo-missing':[(reginfo,0)], 'reginfo-size':[(reginfo+16,20)],
        'reginfo-address':[(reginfo+8,0x00400300)], 'reginfo-align':[(reginfo+28,8)],
        'metadata-dynamic':[(options,2)], 'metadata-interp':[(options,3)],
        'metadata-note':[(options,4)], 'metadata-rtproc':[(options,0x70000001)],
    }
    for name,edits in variants.items():
        b=copy.copy(valid)
        for offset,value,*fmt in edits:struct.pack_into('>'+(fmt[0] if fmt else 'I'),b,offset,value)
        save('bad-static-'+name,b,'reject')
    save('bad-static-short-file',valid[:0x4003],'reject')
    result['process_cases']=[]
    for abi in ['o32','n32']:
        flags=['-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-msoft-float','-mno-abicalls','-fno-pic','-G0']
        start=OUT/(abi+'-start.o');tool('gcc',*flags,'-c',ROOT/sources[4],'-o',start)
        for indirect in [0,1]:
            bridge=OUT/(abi+'-'+str(indirect)+'-call.o')
            tool('gcc',*flags,'-DN32='+str(int(abi=='n32')),'-DINDIRECT='+str(indirect),'-c',ROOT/sources[5],'-o',bridge)
            for kind in range(5):
                name=abi+'-'+('indirect-' if indirect else 'direct-')+str(kind)
                obj=OUT/(name+'.o');elf=OUT/name
                tool('gcc',*flags,'-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror','-DKIND='+str(kind),'-c',ROOT/sources[2],'-o',obj)
                tool('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-T',ROOT/sources[6],'-o',elf,start,bridge,obj)
                b=bytearray(elf.read_bytes());b[7]=0;struct.pack_into('>I',b,36,0x20000021 if abi=='n32' else 0x20000101);elf.write_bytes(b);elf.chmod(0o755)
                result['files'][name]=dict(sha256=sha(elf),bytes=len(b))
                result['process_cases'].append(dict(name=name,abi=abi,indirect=indirect,kind=kind))
            if abi=='n32' and indirect==0:
                obj=OUT/'reference-exec.o';elf=OUT/'reference-exec'
                tool('gcc',*flags,'-O2','-ffreestanding','-fno-builtin','-fno-stack-protector','-Wall','-Wextra','-Werror','-c',ROOT/sources[3],'-o',obj)
                tool('ld','-EB','-m','elf32btsmipn32','--build-id=none','-T',ROOT/sources[6],'-o',elf,start,bridge,obj)
                b=bytearray(elf.read_bytes());b[7]=0;struct.pack_into('>I',b,36,0x20000021);elf.write_bytes(b);elf.chmod(0o755)
                result['files'][elf.name]=dict(sha256=sha(elf),bytes=len(b))
    result['shell_cases']=[
        dict(name='exit',command='exit 37'),
        dict(name='echo',command='echo XIRI_VENDOR_SH_OK'),
        dict(name='quote',command='v="two words"; echo "$v"; echo "a*b"'),
        dict(name='arguments',command='echo "$0|$1|$2"',arguments=['xiri argv0','two words','']),
        dict(name='environment',command='echo "$XIRI_TEST_ENV"'),
        dict(name='status',command='false; echo $?; true; echo $?'),
        dict(name='redirect',command='echo first > shell-output; echo second >> shell-output; read v < shell-output; echo "$v"'),
        dict(name='substitution',command='v=`echo SUBSTITUTION_OK`; echo "$v"'),
        dict(name='subshell',command='(echo SUBSHELL_OK); echo PARENT_OK'),
        dict(name='pipeline',command='echo PIPE_OK | (read v; echo "$v")'),
        dict(name='background',command='(echo BACKGROUND_OK) & p=$!; wait "$p"; echo WAIT=$?'),
        dict(name='cd',command='cd /usr/people; pwd; cd /; pwd'),
        dict(name='cd-missing',command='cd /xiri-no-such-directory 2>/dev/null; echo CD=$?'),
        dict(name='absolute-exec',command='/tmp/xiri-vendor-shell/vendor-echo EXTERNAL_OK'),
        dict(name='path-exec',command='PATH=/tmp/xiri-vendor-shell; vendor-echo PATH_OK'),
        dict(name='nested-shell',command="/bin/sh -c 'echo NESTED_OK'"),
        dict(name='exec-replace',command='exec /tmp/xiri-vendor-shell/vendor-echo EXEC_OK'),
        dict(name='script',command='/bin/sh ./shell-script'),
    ]
    (OUT/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(len(result['loader_cases']),'loader cases;',len(result['shell_cases']),'shell cases')


if __name__=='__main__':main()
