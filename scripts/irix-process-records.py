"""Validate process relationships and canonicalize the bounded process ABI.

Only oracle siginfo padding is discarded. Native padding must be zero. PIDs
are checked as relationships before replacement with stable role identifiers.
"""
import struct

MAGIC = 0x58505243
SECOND = 0xfeedface
POISON = 0x5a5a5a5a
SIGNALS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15,
           30, 31, 20, 32, 28, 16, 23, 17, 18, 19, 21, 22, 26, 27, 24, 25]


def native_mask(foreign):
    result = [1 << 28, 1, 0, 0]  # inherited native SIGINFO and SIGRTMIN
    for number, native in enumerate(SIGNALS[1:], 1):
        if foreign & (1 << (number - 1)):
            result[(native - 1) // 32] |= 1 << ((native - 1) % 32)
    return result


def records(case, data, identity, actual=None):
    assert len(data) == 256 * case['records'], 'record count'
    rows = [list(struct.unpack('>64I', data[p:p+256])) for p in range(0, len(data), 256)]
    assert sorted(w[55] for w in rows) == ([0] if case['records'] == 1 else [0, 1, 2])
    rows.sort(key=lambda w: w[55])
    parent = rows[0][60]
    supervisor = rows[0][61]
    assert 0 < parent < 0x80000000 and 0 < supervisor < 0x80000000 and parent != supervisor
    child = rows[1][60] if len(rows) == 3 else None
    if child is not None:
        assert child > 0 and child not in [parent, supervisor]
        assert rows[0][2:5] == rows[2][2:5] == [child, 0, 0]
        assert rows[1][2:5] == [0, 1, 0]
        assert rows[0][32:34] == [parent, 0x12345678]
        assert rows[1][32:34] == [parent, 0x87654321]
        assert rows[1][34:40] == [0, SECOND, 0, 0, SECOND, 0]
        assert rows[1][40:44] == [0x20000, 0, 0, 0]
        assert rows[1][44:48] == [1, SECOND, 0, 65]
        assert rows[2][45:53] == [1, SECOND, 0, 1, SECOND, 0, 66, 0x12345678]
        assert rows[2][63] == child
    for w in rows:
        assert w[:2] == [MAGIC, case['symbols']['CASE']]
        assert w[56:60] == identity and w[62] == 0
        assert w[60:62] == ([child, parent] if w[55] == 1 else [parent, supervisor])
    if actual is not None:
        assert {k: actual[k] for k in ['exit', 'signal', 'timeout', 'valid', 'released', 'group_absent']} == dict(exit=0, signal=0, timeout=0, valid=1, released=1, group_absent=1)
        assert actual['stderr_hex'] == '' and actual['pid'] == parent
        snaps = actual['snapshots']
        assert len(snaps) == (2 if child else 1)
        assert sorted(s['role'] for s in snaps) == ([0, 1] if child else [0])
        for s in snaps:
            w = rows[s['role']]
            assert [s['pid'], s['ppid']] == w[60:62] and s['pgid'] == parent
            assert s['ids'] == identity and s['groups'] == 0
            mask = (0x20000 if s['role'] else 0x28000) if child else w[19]
            assert s['mask'] == native_mask(mask), ('native mask', s, native_mask(mask))
    return rows


def canonical(case, data, identity, oracle=False, actual=None):
    rows = records(case, data, identity, actual)
    symbols = case['symbols']
    child = rows[1][60] if len(rows) == 3 else None
    for w in rows:
        if child:
            if w[55] != 1:
                w[2] = 2
            if w[55] in [0, 1]:
                w[32] = 1
            else:
                w[63] = 2
                # The captured output includes four leading guard bytes.
                if w[7] == 0:
                    assert symbols['INFO_KIND'] in [0, 4]
                    out = bytearray(struct.pack('>34I', *w[8:42]))
                    start = 4 + (symbols['INFO_KIND'] == 4)
                    info = list(struct.unpack('>32I', out[start:start+128]))
                    assert info[3] in [0, child]
                    if info[3]:
                        assert info[:3] == [18, 1, 0] and info[5] == symbols['EXIT_CODE']
                        info[3] = 2
                    else:
                        assert symbols['WAIT_OPTIONS'] & 0x40
                        assert info[:8] == [0, 0, 0, 0, 0, 0xffffffff, 0, 0]
                    if oracle:
                        info[8:] = [0] * 24  # undefined original kernel padding
                    else:
                        assert info[8:] == [0] * 24, 'native siginfo padding'
                    assert info[4] == info[6] == info[7] == 0, 'accounting outside subset'
                    out[start:start+128] = struct.pack('>32I', *info)
                    w[8:42] = struct.unpack('>34I', out)
        w[60:62] = [2, 1] if w[55] == 1 else [1, 3]
    return rows


def expected(case, data, identity):
    rows = canonical(case, data, identity, oracle=True)
    policy = []
    if case['symbols']['KIND'] == 0:
        w = rows[0]
        if w[19] & 0x80000000 or any(w[20:23]):
            policy.append('traditional-signals-only')
        w[19] &= 0x7fffffff
        w[20:23] = [0, 0, 0]
    else:
        w = rows[2]
        s = case['symbols']
        if s['WAIT_TYPE'] == 7 or s['RUSAGE']:
            policy.append('positive-pid-no-rusage')
            w[5:8] = [89 if s['RUSAGE'] else 22, SECOND, 1]
            w[8:42] = [POISON] * 34
            w[42:45] = [0, s['EXIT_CODE'] << 8, 0]
        if w[7] == 0:
            policy.append('zero-owned-siginfo-padding')
    return rows, policy
