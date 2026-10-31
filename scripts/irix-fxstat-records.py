#!/usr/bin/env python3
"""Check guarded fxstat records using measured stat layouts and native fstat."""
import importlib.util
from pathlib import Path
import struct
s=importlib.util.spec_from_file_location('stat_records',Path(__file__).with_name('irix-xstat-records.py'))
base=importlib.util.module_from_spec(s);s.loader.exec_module(base)
wide,size,pack,unpack,copies=base.wide,base.size,base.pack,base.unpack,base.copies

def output(case,uid,error,payload):
    data=bytearray(base.output(case,uid,error,payload));struct.pack_into('>I',data,0,0x58494653)
    return bytes(data)

def descriptor(case):
    symbols=case['symbols']
    if symbols.get('FD')==0:return ['STDIN',0]
    return ['tree/second' if 'REOPEN' in symbols else case['path'],symbols['OPEN_FLAGS']]

def expected_errno(case):
    syms=case['symbols']
    if 'CLOSED' in syms or ('FD' in syms and syms['FD']!=0):return 9
    if syms['VERSION'] not in [2,3]:return 22
    if 'BUFPTR' in syms or 'READONLY' in syms or ('TAIL' in syms and syms['TAIL']<size(case)):return 14
    return 0

def compare(case,uid,raw,reference,native):
    error=struct.unpack_from('>I',reference,8)[0]
    expected_error=expected_errno(case)
    if native['errno'] and expected_error!=9:
        return dict(passed=False,reason='native descriptor setup failed: '+str(native['errno']))
    if error!=expected_error:return dict(passed=False,reason=f'validation/descriptor error {expected_error} differs from reference {error}')
    payload=pack(base.native_fields(native,wide(case)),wide(case)) if copies(case,error) else None
    expected=output(case,uid,error,payload)
    return dict(passed=raw==expected,expected_hex=expected.hex(),differing_offsets=[i for i,(a,b) in enumerate(zip(raw,expected)) if a!=b],reference_errno=error)

def validate_reference(cases,observations):
    refs={o['name']:bytes.fromhex(o['stdout_hex']) for o in observations}
    for uid in [0,1234]:
        for case in cases:
            raw=refs[case['name']+'-'+str(uid)];error=struct.unpack_from('>I',raw,8)[0];payload=None
            if error!=expected_errno(case):raise ValueError('validation order: '+case['name'])
            if copies(case,error):
                if 'TAIL' in case['symbols']:
                    anchor=case['abi']+'-direct-'+('version-3' if case['symbols']['VERSION']==3 else 'file')+'-'+str(uid)
                    payload=refs[anchor][72:72+size(case)]
                else:
                    offset=72+case['symbols']['ALIGN'];payload=raw[offset:offset+size(case)]
                fields=unpack(payload,wide(case))
                if pack(fields,wide(case))!=payload:raise ValueError('padding: '+case['name'])
                path,flags=descriptor(case)
                if path=='tree/file':
                    for key,value in dict(size=15,mode=0o100644,nlink=1,uid=1234,gid=2345,atime=915246245,mtime=915246245).items():
                        if fields[key]!=value:raise ValueError(f'{case["name"]}: {key}')
                if path=='tree/second' and fields['size']!=7:raise ValueError('reused descriptor')
                if path=='STDIN' and (fields['mode']!=0o100000 or fields['size']!=16):raise ValueError('inherited unreadable descriptor')
                if path=='tree/large' and fields['size']!=(2147484672 if wide(case) else 2147483647):raise ValueError('large size')
            if output(case,uid,error,payload)!=raw:raise ValueError('guard/header/copy extent: '+case['name'])
    return len(refs)
