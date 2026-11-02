#!/usr/bin/env python3
"""Check directory names, field layouts, bounds, EOF and cursor preservation.

Inodes and cookies are filesystem values. Native inode/order expectations come
from a separate native readdir observer. Reference padding is unspecified and
sometimes contains stale IRIX kernel bytes, so it is not treated as a contract.
"""
import struct

SENTINEL = 0xa5a5a5a5
NAMES = ['.', '..', 'sub', 'a', 'elevenchars', 'link']


def unpack(data, offset, count, wide):
    entries = []; end = offset + count
    while offset < end:
        ino, cookie, size = struct.unpack_from('>QQH' if wide else '>IIH', data, offset)
        nameoff = 18 if wide else 10
        assert size >= nameoff+1 and size % (8 if wide else 4) == 0
        assert offset+size <= end
        namebytes = data[offset+nameoff:offset+size]
        assert b'\0' in namebytes
        name = namebytes.split(b'\0')[0].decode('ascii')
        assert size == ((nameoff+len(name)+1+(7 if wide else 3)) & ~(7 if wide else 3))
        assert ino > 0 and cookie > 0
        entries.append(dict(name=name, ino=ino, cookie=cookie, size=size))
        offset += size
    assert offset == end
    return entries


def compare(case, uid, data, reference=None, native=None):
    s = case['symbols']; wide = case['abi']=='n32' or s['TRAP'] in [1205, 1208]
    ncall = s['TRAP'] in [1207, 1208]
    words = struct.unpack('>1024I', data)
    try:
        assert words[0:2] == (0x58494452, s['CASE'])
        assert words[6:10] == (uid,)*4
        assert words[10] == (0xffffffff if s['FD_KIND'] else 3)
        assert words[3] == words[13] == 0xfeedface
        assert words[5] == 0 and words[11] == words[15] == 0
        isfile = case['path'] == 'tree/file'
        empty = case['path'] == 'tree/empty'
        names = NAMES[:2] if empty else NAMES
        metadata = native.get('entries') if native else None
        if metadata is not None:
            assert sorted(e['name'] for e in metadata) == sorted(names)
            names = [e['name'] for e in metadata]
        sizes = [((18 if wide else 10)+len(n)+1+(7 if wide else 3)) & ~(7 if wide else 3) for n in names]
        error = 9 if s['FD_KIND'] else 20 if isfile else 22 if s['COUNT'] in [0, 0xffffffff] else \
            14 if s['POINTER'] in [1, 2, 4] or s['COUNT']==65536 else 13 if s['POINTER']==3 else 0
        consumed = 0; used = 0
        if not error:
            for size in sizes:
                if used+size > s['COUNT']: break
                used += size; consumed += 1
        if not error and ncall and s['EOF_KIND'] != 1: error = 14
        assert words[2] == (error or used) and words[4] == int(bool(error))
        second_error = 9 if s['FD_KIND'] else 20 if isfile else 0
        second = 0 if second_error else sum(sizes[consumed:])
        assert words[12] == (second_error or second) and words[14] == int(bool(second_error))
        assert words[20] == (int(consumed == len(names)) if ncall and not error else SENTINEL)
        assert words[24] == (1 if ncall and not second_error else SENTINEL)
        first_entries = unpack(data, 128+s['ALIGN'], used, wide)
        second_entries = unpack(data, 1408, second, wide)
        entries = first_entries + second_entries
        if not second_error:
            assert [e['name'] for e in entries] == names
            assert len(set(e['cookie'] for e in entries)) == len(names)
            if metadata is not None:
                assert [e['ino'] for e in entries] == [e['ino'] for e in metadata]
        # All bytes outside defined header/records and the observed tail fault
        # remain the original sentinel. Directory padding itself is unspecified.
        allowed = set(range(80, 84)) | set(range(96, 100))
        allowed |= set(range(128+s['ALIGN'],128+s['ALIGN']+used))
        allowed |= set(range(1408,1408+second))
        if native is None and s['POINTER']==4 and s['TAIL']==1:
            allowed.add(3327)
        assert all(b==0xa5 for i,b in enumerate(data[64:],64) if i not in allowed)
        return dict(passed=True, entries=entries, first_bytes=used, second_bytes=second)
    except (AssertionError, ValueError, struct.error) as error:
        return dict(passed=False, reason=str(error) or 'directory contract mismatch',
                    first=list(words[2:5]), second=list(words[12:15]), eof=[words[20],words[24]])


def validate_reference(cases, observations):
    lookup = {o['name']:o for o in observations}
    assert len(lookup) == 2*len(cases)
    for c in cases:
        for uid in [0, 1234]:
            o = lookup[c['name']+'-'+str(uid)]
            assert o['exit']==0 and not o['stderr'], o['name']
            result = compare(c, uid, bytes.fromhex(o['stdout_hex']))
            assert result['passed'], (o['name'], result)
