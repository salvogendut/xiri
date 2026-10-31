#!/usr/bin/env python3
"""Decode measured IRIX stat layouts and compare every guarded output byte.

Filesystem-dependent fields come from a native stat observer. The reference
supplies return/error behavior, copy extent, ABI widths and zero padding.
"""
import struct

SMALL = dict(dev=(0,4),ino=(16,4),mode=(20,4),nlink=(24,4),uid=(28,4),gid=(32,4),rdev=(36,4),size=(48,4),atime=(56,4),atime_nsec=(60,4),mtime=(64,4),mtime_nsec=(68,4),ctime=(72,4),ctime_nsec=(76,4),blksize=(80,4),blocks=(84,4),fstype=(88,16),projid=(104,4))
WIDE = dict(dev=(0,4),ino=(16,8),mode=(24,4),nlink=(28,4),uid=(32,4),gid=(36,4),rdev=(40,4),size=(56,8),atime=(68,4),atime_nsec=(72,4),mtime=(76,4),mtime_nsec=(80,4),ctime=(84,4),ctime_nsec=(88,4),blksize=(92,4),blocks=(96,8),fstype=(104,16),projid=(120,4))

def wide(case):
    return case['abi']=='n32' or case['symbols']['VERSION']==3

def size(case):
    return 152 if wide(case) else 136

def pack(fields, is_wide):
    out=bytearray(152 if is_wide else 136)
    for name,(offset,width) in (WIDE if is_wide else SMALL).items():
        value=fields[name]
        if name=='fstype':out[offset:offset+width]=value.encode().ljust(width,b'\0')
        else:out[offset:offset+width]=(value & ((1<<(width*8))-1)).to_bytes(width,'big')
    return bytes(out)

def unpack(payload, is_wide):
    result={}
    for name,(offset,width) in (WIDE if is_wide else SMALL).items():
        raw=payload[offset:offset+width]
        result[name]=raw.split(b'\0')[0].decode() if name=='fstype' else int.from_bytes(raw,'big',signed=name in ['size','blocks','atime','mtime','ctime','blksize','projid'])
    return result

def native_fields(native, is_wide):
    fields=dict(native)
    for name in ['dev','rdev']:
        fields[name]=((native[name+'_major']&0x3fff)<<18)|(native[name+'_minor']&0x3ffff)
    if native['mode']&0o170000 not in [0o020000,0o060000]:fields['rdev']=0
    if not is_wide:fields['size']=min(native['size'],0x7fffffff)
    fields.update(fstype='unknown',projid=0)
    return fields

def output(case, uid, errno, payload):
    """Build the complete record; prefix copy on EFAULT is reference behavior."""
    syms=case['symbols'];out=bytearray(64)+bytearray(b'\xa5'*512)
    struct.pack_into('>10I',out,0,0x58495354,syms['CASE'],errno,0xfeedface,int(errno!=0),1,uid,uid,uid,uid)
    if payload is not None:
        if 'TAIL' in syms:
            count=min(syms['TAIL'],len(payload));offset=576-syms['TAIL']
        else:count=len(payload);offset=72+syms['ALIGN']
        out[offset:offset+count]=payload[:count]
    return bytes(out)

def copies(case, errno):
    s=case['symbols']
    return errno==0 or (errno==14 and 'TAIL' in s and s['TAIL']>0)

def compare(case, uid, raw, reference, native):
    s=case['symbols'];error=struct.unpack_from('>I',reference,8)[0]
    # Check native lookup independently, including IRIX's trailing slash rule.
    if 'PATHPTR' in s:native_error=14
    elif native['errno']:native_error={62:90,63:78}.get(native['errno'],native['errno'])
    elif s['VERSION'] not in [2,3]:native_error=22
    elif 'BUFPTR' in s or 'READONLY' in s or ('TAIL' in s and s['TAIL']<size(case)):native_error=14
    else:native_error=0
    if native_error!=error:return {'passed':False,'reason':f'native lookup/validation error {native_error} differs from reference {error}'}
    payload=pack(native_fields(native,wide(case)),wide(case)) if copies(case,error) else None
    expected=output(case,uid,error,payload)
    mismatches=[i for i,(a,b) in enumerate(zip(raw,expected)) if a!=b]
    return {'passed':raw==expected,'expected_hex':expected.hex(),'differing_offsets':mismatches,'reference_errno':error}

def validate_reference(cases, observations):
    """Reconstruct whole records, including fault prefixes, from full records."""
    refs={o['name']:bytes.fromhex(o['stdout_hex']) for o in observations}
    for uid in [0,1234]:
        for c in cases:
            raw=refs[c['name']+'-'+str(uid)];error=struct.unpack_from('>I',raw,8)[0];payload=None
            if copies(c,error):
                if 'TAIL' in c['symbols']:
                    anchor=c['abi']+'-direct-'+('version-3' if c['symbols']['VERSION']==3 else 'file')+'-'+str(uid)
                    payload=refs[anchor][72:72+size(c)]
                else:
                    offset=72+c['symbols']['ALIGN'];payload=raw[offset:offset+size(c)]
                fields=unpack(payload,wide(c))
                if pack(fields,wide(c))!=payload:raise ValueError('nonzero padding: '+c['name'])
                if fields['fstype']!='xfs' or fields['projid']!=0:raise ValueError('filesystem fields: '+c['name'])
                path=c['path'].rstrip('/')
                if path in ['tree/file','tree/hard','tree/link','tree/./file','tree/dir/../file']:
                    for key,value in dict(size=15,mode=0o100640,nlink=2,uid=1234,gid=2345,atime=915246245,mtime=915246245).items():
                        if fields[key]!=value:raise ValueError(f'fixture metadata {c["name"]}: {key}')
                if path=='tree/large' and fields['size']!=(2147484672 if wide(c) else 2147483647):raise ValueError('large size: '+c['name'])
                if path in ['tree/char','tree/block']:
                    want=(1<<18|2) if path=='tree/char' else (3<<18|4)
                    if fields['rdev']!=want:raise ValueError('device encoding: '+c['name'])
            if output(c,uid,error,payload)!=raw:raise ValueError('guard, header or copy extent: '+c['name'])
    return len(refs)
