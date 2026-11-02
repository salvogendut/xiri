#!/usr/bin/env python3
"""Independent expectations for raw readlink and desktop sysconf records."""
import struct


def expected(case, uid, *, native=False, page_bytes=4096):
    s = case['symbols']
    out = bytearray(64) + bytearray(b'\xa5'*512)
    value, error, payload = 0, 0, b''
    if s['TRAP'] == 1040:
        selector = s['COUNT']
        if selector not in [3, 11, 28, 29]:
            value, error = 22, 1
        else:
            value = {3:100, 11:page_bytes, 28:0, 29:0 if native else 1}[selector]
    else:
        path = case['path'].rstrip('/')
        links = {'tree/link':b'file', 'tree/dangling':b'missing', 'tree/loop-a':b'loop-b'}
        if s['BADPATH']:
            value, error = 14, 1
        elif path == 'tree/missing':
            value, error = 2, 1
        elif path == 'tree/deny/file' and uid:
            value, error = 13, 1
        elif path not in links:
            value, error = 22, 1
        else:
            count = s['COUNT'] if s['COUNT'] < 0x80000000 else 0
            payload = links[path][:count]
            value = len(payload)
            if payload and s['POINTER'] in [1, 2, 3]:
                payload, value, error = b'', 14, 1
            elif s['POINTER'] == 4:
                if len(payload) > s['TAIL']:
                    payload, value, error = payload[:s['TAIL']], 14, 1
                out[576-s['TAIL']:576-s['TAIL']+len(payload)] = payload
                payload = b''
        if payload:
            offset = 72+s['ALIGN']
            out[offset:offset+len(payload)] = payload
    struct.pack_into('>10I', out, 0, 0x58495152, s['CASE'], value,
                     0xfeedface, error, 0, uid, uid, uid, uid)
    return bytes(out)


def validate_reference(cases, observations):
    reference = {o['name']:o for o in observations}
    for c in cases:
        for uid in [0, 1234]:
            name = c['name']+'-'+str(uid)
            observation = reference[name]
            assert observation['exit'] == 0 and not observation['stderr'], name
            assert bytes.fromhex(observation['stdout_hex']) == expected(c, uid), name
    return len(reference)
