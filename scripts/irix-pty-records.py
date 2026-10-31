#!/usr/bin/env python3
"""Explicit native policies for the bounded PTY allocator interfaces."""
import struct


def expected(case, reference):
    w = list(struct.unpack('>21I', reference))
    symbols = case['symbols']
    kind, mode = symbols['KIND'], symbols['MODE']
    policy = []
    if kind == 0:
        if mode & ~(3 | 4 | 8 | 128 | 256 | 512 | 1024 | 2048) or mode & 3 == 3:
            w[2], w[4], w[5], w[6] = 22, 1, 0, 0
            policy.append('Reject unsupported open bits/access mode before opening')
        elif mode & 4:
            w[5] = (w[5] & ~4) | 128
            policy.append('Canonical native NONBLOCK status for legacy NDELAY')
    elif kind == 1:
        if mode & ~(3 | 4 | 8 | 128 | 512):
            w[2], w[4], w[5], w[6] = 22, 1, 2, 0
            policy.append('Reject unsupported F_SETFL bits, preserving prior flags')
        elif mode & 4:
            w[5] = (w[5] & ~4) | 128
            policy.append('Canonical native NONBLOCK status for legacy NDELAY')
    elif kind == 3 and w[12] == 1234 and case['path'] == 'owned' and \
            'POINTER' not in symbols and symbols['OWNER'] in [0, 2345]:
        assert w[2] == 0 and w[4] == 0
        assert w[8:10] == [symbols['OWNER'], symbols['GROUP']]
        w[2], w[4], w[8], w[9] = 1, 1, 1234, 1234
        policy.append('Native chown denies unprivileged file giveaways and retains ownership')
    elif kind == 4:
        if case['path'] == '/dev/ptc':
            w[7] = 0o20666
            policy.append('Preserve native master mode rather than IRIX mode 020000')
        if any(symbols[k] != v for k, v in [('COMMAND', 0x5002), ('TIMEOUT', 0), ('LENGTH', 0), ('DATA', 0)]):
            w[2], w[4] = 89, 1
            w[17:21] = [symbols[k] for k in ['COMMAND', 'TIMEOUT', 'LENGTH', 'DATA']]
            policy.append('Only the measured four-word UNLKPT request is supported')
    return struct.pack('>21I', *w), policy
