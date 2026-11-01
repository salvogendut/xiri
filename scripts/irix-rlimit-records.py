"""Decode every resource-limit record independently of the guest implementation."""
import hashlib
import struct

MAGIC = 0x58524c4d
SENTINEL = 0xa5a5a5a5


def records(data):
    assert len(data) % 128 == 0
    return list(struct.iter_unpack('>32I', data))


def sequence(kind):
    if kind == 1:
        return [(0, wide, resource, pointer) for wide in [0,1]
                for resource, pointer in [(9,0),(0xffffffff,0),(0x80000000,0),
                    (0x7fffffff,0),(8,1),(8,2),(8,3),(8,4),(8,5),(9,1)]]
    return [(stage,wide,resource,0) for stage in ([0,1,2,3] if kind == 2 else [0])
            for wide in [0,1] for resource in range(9)]


def check(data, case, uid, page, limits):
    rows = records(data)
    kind = case['symbols']['KIND']
    assert len(rows) == case['records'] == len(sequence(kind))
    identities = {}
    for words, (stage, wide, resource, pointer) in zip(rows, sequence(kind)):
        assert words[:6] == (MAGIC,kind,stage,wide,resource,pointer)
        assert words[7] == 0xfeedface and words[9:13] == (uid,uid,uid,uid)
        assert words[13] > 1 and words[14] > 0 and words[15] == page
        assert words[24:] == (0,)*8
        pair = words[13:15]
        assert stage not in identities or identities[stage] == pair
        identities[stage] = pair
        error = 22 if resource >= 9 else 14 if pointer in [1,2,3,4] else 0
        assert words[6] == error and words[8] == int(error != 0), words
        expected = bytearray(b'\xa5'*32)
        if not error:
            # The original measurements establish the n32 layout independently
            # of which trap is selected. Native limits supply host values.
            is64 = wide or case['abi'] == 'n32'
            values = [min(value,0x7fffffffffffffff) if is64 else
                      0x7fffffff if value == 0x7fffffffffffffff else min(value,0xffffffff)
                      for value in limits[resource]]
            struct.pack_into('>QQ' if is64 else '>II',expected,9 if pointer == 5 else 8,*values)
        assert struct.pack('>8I',*words[16:24]) == expected, (case['name'],words,expected.hex())
    if kind == 2:
        assert identities[0] == identities[3]
        assert identities[1] == identities[2]
        assert identities[0][0] != identities[1][0]
        assert identities[1][1] == identities[0][0]
    return dict(records=len(rows),identities=identities,sha256=hashlib.sha256(data).hexdigest())


def wide_limits(data):
    rows = records(data)
    selected = {w[4]: ((w[18]<<32)|w[19],(w[20]<<32)|w[21])
                for w in rows if w[2] == 0 and w[3] == 1 and w[5] == 0}
    assert set(selected) == set(range(9))
    return selected
