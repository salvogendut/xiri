"""Expected output, including untouched guards, for the getpeername ABI probes."""
import struct


def expected_record(case):
    s = case['symbols']
    memory = bytearray([0xa5] * 64)
    name = 16 + s['NAME_OFFSET']
    length = name if 'OVERLAP' in s else 48 + s['LEN_OFFSET']
    capacity = s['LENGTH']
    memory[length:length+4] = struct.pack('>I', capacity & 0xffffffff)
    error = 0
    if s.get('FD') in [-1, 1, 3]:
        error = 95 if s['FD'] == 1 else 9
    elif 'LEN_POINTER' in s:
        error = 14
    elif 'REFUSED' in s:
        error = 22
    elif 'UNCONNECTED' in s:
        error = 134
    elif capacity < 0:
        error = 14
    elif capacity and ('POINTER' in s or 'READONLY_NAME' in s):
        error = 14
    else:
        count = min(capacity, 16)
        address = b'\x00\x02\x17\xe1\x7f\x00\x00\x01' + b'\0'*8
        memory[name:name+count] = address[:count]
        if 'READONLY_LEN' in s:
            error = 14
        else:
            memory[length:length+4] = struct.pack('>I', 16)
    return {'magic':0x58494431, 'case':case['number'], 'v0':error,
            'v1':0xfeedface, 'a3':int(bool(error)), 'checks':int('CONNECTED' in s),
            'preserved':0, 'reserved':0, 'memory_hex':memory.hex()}
