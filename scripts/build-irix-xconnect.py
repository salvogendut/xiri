#!/usr/bin/env python3
"""Build original hostname, descriptor, sendmsg and shutdown ABI probes."""
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
    source, output = ROOT/'.work/irix-peername/probes', ROOT/'.work/irix-xconnect/probes'
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
    for p in ['lab/irix-xconnect/probe.S','lab/irix-xconnect/reference-message.S']:
        result['sources'][p]=tcp.digest(ROOT/p)
    definitions=[]
    def case(name,kind,**s):definitions.append((name,kind,s))
    for n in [-1,0,1,3,4,5,6,16,256,0x7fffffff]:case('hostname-length-'+str(n),8,LENGTH=n)
    for name,s in [('null',{'POINTER':0}),('high',{'POINTER':0x80000000}),
                   ('wrap',{'POINTER':0xfffffffe}),('null-zero',{'POINTER':0,'LENGTH':0}),
                   ('readonly',{'READONLY':1}),('unaligned',{'OFFSET':1}),
                   ('bad-stack',{'BAD_STACK':0}),('delay',{'DELAY':1})]:case('hostname-'+name,8,**s)
    for name,s in [('getfd',{'CMD':1}),('setfd',{'CMD':2,'ARG':1}),
                   ('clearfd',{'CMD':2,'ARG':0,'PRESET_FD':1}),
                   ('setfd-other',{'CMD':2,'ARG':2}),('setfd-all',{'CMD':2,'ARG':-1}),
                   ('getfl',{'CMD':3}),('getfl-read',{'FILE':0}),('getfl-write',{'FILE':1}),
                   ('getfl-rw',{'FILE':2}),('getfl-append',{'FILE':0xa}),
                   ('nonblock',{'CMD':4,'ARG':128}),('blocking',{'CMD':4,'ARG':0,'PRESET_FL':128}),
                   ('append',{'CMD':4,'ARG':8}),('both',{'CMD':4,'ARG':650}),
                   ('bad-fd',{'FD':-1}),('closed',{'CLOSED':1}),('bad-command',{'CMD':99}),
                   ('bad-fd-command',{'FD':-1,'CMD':99}),('bad-stack',{'BAD_STACK':0}),
                   ('delay',{'DELAY':1}),('borrow-nonblock',{'CMD':4,'ARG':128,'FCHECK':1}),
                   ('borrow-blocking',{'CMD':4,'ARG':0,'FCHECK':1,'PRESET_FL':128}),
                   ('borrow-append',{'CMD':4,'ARG':8,'FCHECK':1}),
                   ('unsupported-flags',{'CMD':4,'ARG':0x40000000,'POLICY':1})]:
        case('fcntl-'+name,9,**s)
    for name,s in [('one',{}),('two',{'TWO':1}),('sixteen',{'IOVCNT':16}),
                   ('empty',{'IOVCNT':0}),('negative-count',{'IOVCNT':-1}),('too-many',{'IOVCNT':17}),
                   ('null-message',{'POINTER':0}),('high-message',{'POINTER':0x80000000}),
                   ('wrap-message',{'POINTER':0xfffffff0}),('readonly-message',{'READONLY':1}),
                   ('unaligned-message',{'OFFSET':1}),('null-iov',{'IOVP':0}),
                   ('high-iov',{'IOVP':0x80000000}),('wrap-iov',{'IOVP':0xfffffffc}),
                   ('unaligned-iov',{'IOVOFF':1}),('null-empty-iov',{'IOVP':0,'IOVCNT':0}),
                   ('null-empty-base',{'BASE':0,'LENGTH':0}),('null-base',{'BASE':0}),
                   ('high-base',{'BASE':0x80000000}),('negative-length',{'LENGTH':-1}),
                   ('wide-length',{'LENGTH':0x80000000}),('total-overflow',{'OVERFLOW':1}),
                   ('partial-fault',{'TWO':1,'BAD_SECOND':1}),('bad-fd',{'FD':-1}),
                   ('file-fd',{'FD':1}),('bad-fd-null-message',{'FD':-1,'POINTER':0}),
                   ('bad-stack',{'BAD_STACK':0}),('delay',{'DELAY':1}),
                   ('unsupported-flags',{'FLAGS':0x40000000,'POLICY':1}),
                   ('unsupported-name',{'NAME':1,'POLICY':1}),
                   ('unsupported-rights',{'RIGHTS':1,'POLICY':1})]:case('sendmsg-'+name,10,**s)
    for n in [0,1,2,-1,3]:case('shutdown-how-'+str(n),11,HOW=n,ACK=int(n==1))
    for n in [0,1,2]:case('shutdown-repeat-'+str(n),11,HOW=n,REPEAT=1,ACK=int(n==1))
    for n in [0,1,2,-1]:case('shutdown-unconnected-'+str(n),11,HOW=n,UNCONNECTED=1)
    for name,s in [('bad-fd',{'FD':-1}),('bad-fd-how',{'FD':-1,'HOW':-1}),
                   ('file-fd',{'FD':1}),('closed',{'CLOSED':1}),
                   ('bad-stack',{'BAD_STACK':0}),('delay',{'DELAY':1})]:case('shutdown-'+name,11,**s)
    def build(name,path,abi='o32',values=None):
        obj,elf=output/(name+'.o'),output/name
        flags=[x for k,v in (values or {}).items() for x in ['--defsym',f'{k}={v}']]
        tcp.run('as','-EB','-mabi='+('n32' if abi=='n32' else '32'),'-mips3','-G','0',*flags,'-o',obj,ROOT/path)
        tcp.run('ld','-EB','-m','elf32btsmipn32' if abi=='n32' else 'elf32btsmip','--build-id=none','-T',ROOT/'lab/irix-o32/probe.ld','-o',elf,obj)
        data=bytearray(elf.read_bytes());data[7]=0;struct.pack_into('>I',data,36,0x20000021 if abi=='n32' else 0x20000101)
        elf.write_bytes(data);elf.chmod(0o755);result['files'][name]={'sha256':tcp.digest(elf),'bytes':len(data)}
    for abi in ['o32','n32']:
        for indirect in [False,True]:
            for suffix,kind,s in definitions:
                name=abi+'-'+('indirect-' if indirect else 'direct-')+suffix;number=len(result['cases'])+1
                values=dict(CASE=number,KIND=kind,INDIRECT=int(indirect),TICKS=0,LENGTH=16 if kind==8 else 8,
                            CMD=3,ARG=0,OFFSET=0,IOVOFF=0,IOVCNT=1,FLAGS=0,HOW=2,ACK=0)
                if abi=='n32':values['N32']=1
                values.update(s)
                if kind in [10,11] and 'UNCONNECTED' not in s:values['MESSAGE_CONNECTED']=1
                build(name,'lab/irix-xconnect/probe.S',abi,values)
                result['cases'].append({'name':name,'number':number,'abi':abi,'symbols':values,
                    'reference':not ('FCHECK' in s or 'POLICY' in s),'record_bytes':96 if kind==8 else 32,
                    'user':suffix in ['hostname-length-16','hostname-null','fcntl-getfd','fcntl-setfd','fcntl-nonblock',
                                     'fcntl-borrow-nonblock','sendmsg-two','sendmsg-null-message','shutdown-how-1']})
    count=sum('MESSAGE_CONNECTED' in c['symbols'] and c['reference'] for c in result['cases'])
    build('reference-message','lab/irix-xconnect/reference-message.S',values={'COUNT':count})
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(f'{len(result["cases"])} socket/startup fixtures built; {count} reference message connections')

if __name__=='__main__':main()
