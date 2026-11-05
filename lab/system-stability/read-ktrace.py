#!/usr/bin/env python3
"""Decode the pinned LP64 NetBSD kernel's big-endian version-2 native traces.

The matching kernel DWARF confirms a 56-byte header, with 64-bit seconds and
nanoseconds at offsets 32/40. Native o32 kdump does not decode that timestamp
layout correctly. This is intentionally not a general ktrace-format reader.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import struct


def records(raw):
    offset=0
    while offset<len(raw):
        if len(raw)-offset<56: raise ValueError('truncated LP64 header')
        length,version,kind,pid=struct.unpack_from('>iHHi',raw,offset)
        sec,nsec=struct.unpack_from('>qq',raw,offset+32)
        lid=struct.unpack_from('>i',raw,offset+48)[0]
        if version!=2 or not 0<=length<=1048576 or not 0<=nsec<1000000000:
            raise ValueError('invalid LP64 version-2 trace header')
        if offset+56+length>len(raw): raise ValueError('truncated record')
        payload=raw[offset+56:offset+56+length]
        item=dict(offset=offset,kind=kind,pid=pid,lid=lid,time_ns=sec*1000000000+nsec,
                  command=raw[offset+12:offset+29].split(b'\0',1)[0].decode())
        if kind==1:
            if length<8: raise ValueError('short syscall')
            code,argsize=struct.unpack_from('>ii',payload)
            if argsize<0 or argsize!=length-8: raise ValueError('invalid syscall arguments')
            item.update(code=code,args=payload[8:].hex())
        elif kind==2:
            if length!=24: raise ValueError('invalid LP64 syscall return')
            code,unused,error,rv0,rv1=struct.unpack('>hhiqq',payload)
            item.update(code=code,error=error,retval=rv0,retval1=rv1)
        elif kind==5:
            if length<4: raise ValueError('short signal')
            item['signal']=struct.unpack_from('>i',payload)[0]
        elif kind==6:
            if length!=8: raise ValueError('invalid context switch')
            out,user=struct.unpack('>ii',payload)
            if out not in (0,1) or user not in (0,1): raise ValueError('invalid switch flags')
            item.update(out=out,user=user)
        yield item
        offset+=56+length


def summarize(raw):
    parsed=list(records(raw))
    active={};switched={};calls=[];switches=[];unpaired=[]
    for i,entry in enumerate(parsed):
        key=entry['pid'],entry['lid']
        if entry['kind']==1:
            if key in active: unpaired.append(active[key][1])
            active[key]=(i,entry)
        elif entry['kind']==2:
            previous=active.pop(key,None)
            if previous is None or previous[1]['code']!=entry['code']:
                unpaired.append(entry);continue
            index,begin=previous
            elapsed=entry['time_ns']-begin['time_ns']
            calls.append(dict(pid=entry['pid'],lid=entry['lid'],command=entry['command'],
                code=entry['code'],error=entry['error'],elapsed_ns=elapsed,
                begin=begin,end=entry,index=index,end_index=i))
        elif entry['kind']==6:
            if entry['out']:
                if key in switched: unpaired.append(switched[key])
                switched[key]=entry
            else:
                begin=switched.pop(key,None)
                if begin:
                    switches.append(dict(pid=entry['pid'],lid=entry['lid'],
                        elapsed_ns=entry['time_ns']-begin['time_ns'],begin=begin,end=entry))
    longest=sorted(calls,key=lambda c:c['elapsed_ns'],reverse=True)[:12]
    for call in longest:
        call['events']=parsed[max(0,call['index']-2):min(len(parsed),call['end_index']+4)]
        # A long syscall may contain many switches. Preserve the raw trace;
        # keep this summary bounded without silently discarding their count.
        call['event_count']=len(call['events'])
        if len(call['events'])>32: call['events']=call['events'][:16]+call['events'][-16:]
    sleeps=[c['elapsed_ns'] for c in calls if c['code']==430]
    processes={}
    for pid in sorted({entry['pid'] for entry in parsed}):
        own=[c['elapsed_ns'] for c in calls if c['pid']==pid and c['code']==430]
        processes[pid]=dict(nanosleep_count=len(own),nanosleep_max_ns=max(own,default=None),
                           nanosleeps_over_second=sum(n>1000000000 for n in own))
    return dict(schema=1,format='NetBSD LP64 big-endian ktrace v2',
        sha256=hashlib.sha256(raw).hexdigest(),records=len(parsed),
        record_types=dict(collections.Counter(e['kind'] for e in parsed)),
        paired_syscalls=len(calls),unpaired_syscalls=unpaired,
        unfinished_syscalls=[item[1] for item in active.values()],
        unfinished_switches=list(switched.values()),
        nanosleep_count=len(sleeps),nanosleep_max_ns=max(sleeps,default=None),
        nanosleeps_over_second=sum(n>1000000000 for n in sleeps),
        processes=processes,
        longest_syscalls=longest,
        longest_switches=sorted(switches,key=lambda e:e['elapsed_ns'],reverse=True)[:12],
        signals=[e for e in parsed if e['kind']==5])


def self_test():
    def record(kind,payload,sec=1,nsec=123456789,version=2):
        head=bytearray(56)
        struct.pack_into('>iHHi',head,0,len(payload),version,kind,42)
        head[12:17]=b'test\0'
        struct.pack_into('>qqi',head,32,sec,nsec,1)
        return bytes(head)+payload
    begin=record(1,struct.pack('>iiQQ',430,16,0x7fff1230,0))
    end=record(2,struct.pack('>hhiqq',430,0,0,0,0),nsec=323456789)
    result=summarize(begin+end)
    assert result['nanosleep_count']==1 and result['nanosleep_max_ns']==200000000
    controls=[begin[:-1],end[:50],record(6,b'bad'),
              record(1,struct.pack('>ii',430,8)),record(6,b'12345678',nsec=1000000000),
              record(6,b'12345678',version=1)]
    for raw in controls:
        try:list(records(raw))
        except ValueError:pass
        else:raise AssertionError('invalid trace accepted')
    return len(controls)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trace',nargs='?',type=Path)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--self-test',action='store_true')
    args=parser.parse_args()
    if args.self_test:print('Rejected '+str(self_test())+' malformed trace controls')
    if args.trace:
        report=summarize(args.trace.read_bytes());report['trace']=str(args.trace)
        text=json.dumps(report,indent=2)+'\n'
        if args.output:args.output.write_text(text)
        else:print(text,end='')

if __name__=='__main__':main()
