#!/usr/bin/env python3
"""Decode selected records from the pinned big-endian LP64 NetBSD v2 trace.

This is not a general kdump replacement. The guest's o32 kdump splits native
64-bit argument slots and cannot name the foreign syscall table. Preserve raw
payloads and use the kernel's explicit irix_o32/irix_ret records for that ABI.
Layout: sys/sys/ktrace.h in the kernel revision recorded by each run.
"""
import re
import struct


def records(raw):
    offset = 0
    while offset < len(raw):
        if len(raw) - offset < 56:
            raise ValueError('short LP64 trace header')
        length, version, kind, pid = struct.unpack_from('>iHHi', raw, offset)
        sec, nsec = struct.unpack_from('>qq', raw, offset + 32)
        lwp = struct.unpack_from('>i', raw, offset + 48)[0]
        if version != 2 or not 0 <= length <= 1048576 or not 0 <= nsec < 10**9 or offset + 56 + length > len(raw):
            raise ValueError('invalid LP64 version-2 trace record')
        data = raw[offset + 56:offset + 56 + length]
        event = dict(offset=offset, kind=kind, pid=pid, lwp=lwp,
                     ns=sec * 10**9 + nsec,
                     comm=raw[offset + 12:offset + 29].split(b'\0', 1)[0].decode(), data=data)
        offset += 56 + length
        if kind == 1:
            code, size = struct.unpack_from('>ii', data)
            if size < 0 or size % 8 or len(data) != size + 8:
                raise ValueError('invalid LP64 syscall argument size')
            event.update(code=code, args=list(struct.unpack_from('>' + 'Q' * (size // 8), data, 8)))
        elif kind == 2:
            if len(data) != 24:
                raise ValueError('invalid LP64 syscall return size')
            code, eosys, error, v0, v1 = struct.unpack('>hhiQQ', data)
            event.update(code=code, error=error, v0=v0, v1=v1)
        elif kind == 4:
            fd, direction = struct.unpack_from('>ii', data)
            if direction not in [0, 1]:
                raise ValueError('invalid I/O direction')
            event.update(fd=fd, direction=direction, io=data[8:])
        elif kind == 5:
            if len(data) not in [40, 168]:
                raise ValueError('unexpected LP64 signal size')
            event.update(signal=struct.unpack_from('>i', data)[0],
                         action=struct.unpack_from('>Q', data, 8)[0])
        elif kind in [3, 7, 10, 11]:
            event['text'] = data.rstrip(b'\0').decode()
        elif kind == 8:
            if len(data) < 20:
                raise ValueError('short user trace record')
            event['label'] = data[:20].split(b'\0', 1)[0].decode()
            if event['label'] in ['irix_o32', 'irix_ret']:
                event['values'] = {k: int(v, 0) for k, v in
                                   re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)', data[20:].decode())}
        yield event


def foreign_pairs(events):
    pending = {}
    for event in events:
        label = event.get('label')
        key = event['pid'], event['lwp']
        if label == 'irix_o32':
            pending[key] = event
        elif label == 'irix_ret' and key in pending:
            call = pending.pop(key)
            number = call['values']['syscall']
            if number == 1000:
                number = call['values']['a0']
            if number != event['values']['syscall']:
                raise ValueError('foreign entry/return mismatch')
            yield dict(pid=event['pid'], lwp=event['lwp'], call=call['values'], result=event['values'])
