#!/usr/bin/env python3
"""Build original legacy recvmsg ABI probes."""
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
        subprocess.run(['toolbox','run','-c','xiri-iris','env','XIRI_TCP_TOOLBOX=1',
                        'PYTHONDONTWRITEBYTECODE=1','python3',str(Path(__file__).resolve())],check=True)
        return
    source, output = ROOT/'.work/irix-xconnect/probes', ROOT/'.work/irix-recvmsg/probes'
    output.mkdir(parents=True,exist_ok=True)
    (output/'manifest.json').unlink(missing_ok=True)
    result=json.loads((source/'manifest.json').read_text())
    for path,sha in result['sources'].items():
        if tcp.digest(ROOT/path)!=sha:raise RuntimeError('stale parent: '+path)
    for name,info in result['files'].items():
        if tcp.digest(source/name)!=info['sha256']:raise RuntimeError('changed parent fixture: '+name)
        shutil.copy2(source/name,output/name)
    result['parent_manifest_sha256']=tcp.digest(source/'manifest.json')
    result['builder_sha256']=tcp.digest(Path(__file__))
    result['tools']={n:tcp.run(n,'--version').splitlines()[0] for n in ['as','ld']}
    for p in ['lab/irix-recvmsg/probe.S','lab/irix-recvmsg/probe.ld','lab/irix-recvmsg/reference-receive.S']:
        result['sources'][p]=tcp.digest(ROOT/p)
    definitions=[]
    def case(name,**s):definitions.append(('recvmsg-'+name,s))
    for n in [0,1,3,8,16]:case('length-'+str(n),LENGTH=n)
    for name,s in [('two',{'TWO':1}),('sixteen',{'IOVCNT':16}),('empty',{'IOVCNT':0}),
        ('negative-count',{'IOVCNT':-1}),('too-many',{'IOVCNT':17}),
        ('null-message',{'POINTER':0}),('high-message',{'POINTER':0x80000000}),('wrap-message',{'POINTER':0xfffffff0}),
        ('readonly-message',{'READONLY_MSG':1}),('unaligned-message',{'OFFSET':1}),
        ('null-iov',{'IOVP':0}),('high-iov',{'IOVP':0x80000000}),('wrap-iov',{'IOVP':0xfffffffc}),
        ('unaligned-iov',{'IOVOFF':1}),('readonly-iov',{'READONLY_IOV':1}),
        ('null-empty-iov',{'IOVP':0,'IOVCNT':0}),('null-empty-base',{'BASE':0,'LENGTH':0}),
        ('null-base',{'BASE':0}),('high-base',{'BASE':0x80000000}),('wrap-base',{'BASE':0xfffffffc}),
        ('readonly-base',{'READONLY_BASE':1}),('negative-length',{'LENGTH':-1}),('wide-length',{'LENGTH':0x80000000}),
        ('total-overflow',{'OVERFLOW':1,'IOVCNT':2}),('partial-fault',{'TWO':1,'BAD_SECOND':1}),
        ('bad-fd',{'FD':-1}),('file-fd',{'FD':1}),('bad-fd-null-message',{'FD':-1,'POINTER':0}),
        ('closed',{'CLOSED':1}),('unconnected',{'UNCONNECTED':1}),
        ('eof',{'MODE':1}),('nonblock-empty',{'MODE':2}),
        ('peek',{'FLAGS':2}),('peek-short',{'FLAGS':2,'LENGTH':3}),('peek-fault',{'FLAGS':2,'TWO':1,'BAD_SECOND':1}),
        ('peek-eof',{'FLAGS':2,'MODE':1}),
        ('null-name-length',{'NAMELEN':16}),('null-name-negative',{'NAMELEN':-1}),
        ('name-zero',{'NAME':1,'NAMELEN':0}),('name-short',{'NAME':1,'NAMELEN':1}),
        ('name-exact',{'NAME':1,'NAMELEN':16}),('name-negative',{'NAME':1,'NAMELEN':-1}),
        ('name-invalid',{'NAMEPTR':0x80000000,'NAMELEN':16}),
        ('null-rights-length',{'RIGHTSLEN':16}),('null-rights-negative',{'RIGHTSLEN':-1}),
        ('rights-invalid',{'RIGHTSPTR':1,'RIGHTSLEN':4}),('rights-negative',{'RIGHTSPTR':1,'RIGHTSLEN':-1}),
        ('bad-stack',{'BAD_STACK':0}),('delay',{'DELAY':1}),
        ('unsupported-flags',{'FLAGS':0x40000000,'POLICY':1})]:case(name,**s)
    for name,s in [
        ('readonly-message-name',{'READONLY_MSG':1,'NAME':1,'NAMELEN':16}),
        ('readonly-message-rights',{'READONLY_MSG':1,'RIGHTSPTR':1,'RIGHTSLEN':4}),
        ('readonly-message-both',{'READONLY_MSG':1,'NAME':1,'NAMELEN':16,'RIGHTSPTR':1,'RIGHTSLEN':4}),
        ('name-and-rights',{'NAME':1,'NAMELEN':16,'RIGHTSPTR':1,'RIGHTSLEN':4}),
        ('eof-name-rights',{'MODE':1,'NAME':1,'NAMELEN':16,'RIGHTSPTR':1,'RIGHTSLEN':4}),
        ('nonblock-name-rights',{'MODE':2,'NAME':1,'NAMELEN':16,'RIGHTSPTR':1,'RIGHTSLEN':4}),
        ('zero-name-rights',{'LENGTH':0,'NAME':1,'NAMELEN':16,'RIGHTSPTR':1,'RIGHTSLEN':4}),
        ('partial-fault-name-rights',{'TWO':1,'BAD_SECOND':1,'NAME':1,'NAMELEN':16,'RIGHTSPTR':1,'RIGHTSLEN':4}),
        ('bad-fd-null-iov',{'FD':-1,'IOVP':0}),('bad-fd-empty',{'FD':-1,'IOVCNT':0}),
        ('bad-fd-wide-length',{'FD':-1,'LENGTH':0x80000000}),('file-fd-null-message',{'FD':1,'POINTER':0}),
        ('unconnected-null-message',{'UNCONNECTED':1,'POINTER':0}),('unconnected-empty',{'UNCONNECTED':1,'IOVCNT':0})]:case(name,**s)
    def build(name,path,abi='o32',values=None,linker='lab/irix-recvmsg/probe.ld'):
        obj,elf=output/(name+'.o'),output/name
        flags=[x for k,v in (values or {}).items() for x in ['--defsym',f'{k}={v}']]
        tcp.run('as','-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-G','0',*flags,'-o',obj,ROOT/path)
        tcp.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-z','max-page-size=8192','-T',ROOT/linker,'-o',elf,obj)
        data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101)
        elf.write_bytes(data);elf.chmod(0o755);result['files'][name]={'sha256':tcp.digest(elf),'bytes':len(data)}
        return {line.split()[2]:int(line.split()[0],16) for line in tcp.run('nm','--defined-only',elf).splitlines() if len(line.split())==3}
    for abi in ['o32','n32']:
        for indirect in [False,True]:
            for suffix,s in definitions:
                name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix;number=len(result['cases'])+1
                values=dict(CASE=number,KIND=12,INDIRECT=int(indirect),TICKS=0,LENGTH=8,OFFSET=0,IOVOFF=0,IOVCNT=1,
                            FLAGS=0,MODE=0,NAMELEN=0,RIGHTSLEN=0)
                if abi=='n32':values['N32']=1
                values.update(s)
                if 'TWO' in s:values['IOVCNT']=2
                if 'UNCONNECTED' not in s:values['RECEIVE_CONNECTED']=1
                symbols=build(name,'lab/irix-recvmsg/probe.S',abi,values)
                result['cases'].append({'name':name,'number':number,'abi':abi,'symbols':values,
                    'addresses':{n:symbols[n] for n in ['payload_guard','name_guard','iov_space','iov_template','message_template','readonly_data']},
                    'reference':'POLICY' not in s,'record_bytes':192,
                    'user':suffix in ['recvmsg-length-8','recvmsg-two','recvmsg-readonly-message','recvmsg-partial-fault',
                                     'recvmsg-nonblock-empty','recvmsg-peek','recvmsg-name-exact']})
    count=sum('RECEIVE_CONNECTED' in c['symbols'] and c['reference'] for c in result['cases'])
    build('reference-receive','lab/irix-recvmsg/reference-receive.S',values={'COUNT':count},linker='lab/irix-o32/probe.ld')
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'{len(result["cases"])} socket/startup/receive fixtures built; {count} reference receive connections')

if __name__=='__main__':main()
