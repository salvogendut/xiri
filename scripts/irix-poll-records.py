#!/usr/bin/env python3
"""Independent poll record expectations; document native pipe differences."""
import struct


def expected(case, uid, native=False):
    s = case['symbols']
    out = bytearray(64) + bytearray([0xa5] * 512)
    def word(index, value):
        struct.pack_into('>I', out, index*4, value)
    word(0, 0x5849504c); word(1, s['CASE'])
    word(3, 0xfeedface)
    for i in range(6, 10): word(i, uid)
    word(10, 3); word(11, 4)
    fd = [3, 4, 0xffffffff, 12345][s['FD_KIND']]
    word(18, fd); word(19, (s['EVENTS'] << 16) | 0xa5a5)
    word(20, 4); word(21, (4 << 16) | 0xa5a5)
    tail = s['TAIL'] if s['POINTER'] == 4 else 0
    if tail: out[576-tail:] = out[72:72+tail]
    error = 0; count = 0; event = 0
    if s['NFDS'] > 0x7fffffff:
        error = 22
    elif s['NFDS'] == 0:
        pass
    elif s['POINTER'] in [1, 2, 3] or (tail and tail < 8):
        error = 14
    else:
        if s['FD_KIND'] == 2: event = 0
        elif s['FD_KIND'] == 3 or s['STATE'] == 3: event = 32
        elif s['STATE'] == 2: event = 0x11 if native else 0x51
        elif s['FD_KIND'] == 1: event = s['EVENTS'] & 4
        elif s['STATE'] == 1: event = s['EVENTS'] & (0x41 if native else 0x45)
        count = int(event != 0) + int(s['NFDS'] == 2)
        struct.pack_into('>H', out, 574 if tail else 78, event)
        if s['NFDS'] == 2: struct.pack_into('>H', out, 86, 4)
    word(2, error or count); word(4, int(bool(error)))
    return bytes(out)


def validate_reference(cases, observations):
    lookup = {o['name']:o for o in observations}
    assert len(lookup) == 2 * len(cases)
    for c in cases:
        for uid in [0, 1234]:
            o = lookup[c['name']+'-'+str(uid)]
            assert o['exit'] == 0 and not o['stderr'], o['name']
            assert bytes.fromhex(o['stdout_hex']) == expected(c, uid), o['name']
