#!/usr/bin/env python3
"""Read Xiri user/namei records from a NetBSD LP64 version-2 ktrace file.

The guest's o32 kdump cannot decode some native LP64 structured user records.
This reader extracts only fixed-width Xiri text and pathname records, checking
that every record fits. It does not interpret arbitrary native structures.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct


def decode(data):
    at=0; pending={}; calls=[]; paths=[]
    while at<len(data):
        assert len(data)-at>=56, ('short header',at)
        size,version,kind,pid=struct.unpack_from('>IHHI',data,at)
        assert version==2 and size<=2068 and at+56+size<=len(data),(at,version,size)
        lwp=struct.unpack_from('>I',data,at+48)[0]
        body=data[at+56:at+56+size];at+=56+size;key=(pid,lwp)
        if kind==3:
            path=body.rstrip(b'\0').decode(errors='backslashreplace');paths.append(path)
            if key in pending: pending[key].setdefault('paths',[]).append(path)
        elif kind==8:
            label=body[:20].rstrip(b'\0').decode(errors='backslashreplace')
            if label not in ['irix_o32','irix_ret']: continue
            fields={k:int(v,0) for k,v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)',body[20:].decode())}
            if label=='irix_o32':
                pending[key]=dict(pid=pid,lwp=lwp,call=fields);calls.append(pending[key])
            elif key in pending:
                row=pending.pop(key)
                call=row['call']
                # syscall(2) records the raw trap at entry and its dispatched
                # number at return; a0 contains that indirect call number.
                expected=call['a0'] if call['syscall']==1000 else call['syscall']
                assert expected==fields['syscall'], (call,fields)
                row['result']=fields
    return dict(sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),paths=list(dict.fromkeys(paths)),calls=calls)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace',type=Path);parser.add_argument('--output',type=Path)
    args=parser.parse_args();result=decode(args.trace.read_bytes());text=json.dumps(result,indent=2)+'\n'
    if args.output:args.output.write_text(text)
    else:print(text,end='')


if __name__=='__main__':main()
