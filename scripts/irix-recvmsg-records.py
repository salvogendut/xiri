"""Legacy recvmsg reference oracle and independently verified source-peer output."""
import json
from pathlib import Path
import struct

_REFERENCE = None


def expected_record(case):
    """Use original-IRIX records, with only two explicit subset differences."""
    global _REFERENCE
    if _REFERENCE is None:
        path=Path(__file__).resolve().parent.parent/'lab/irix-recvmsg/reference.json'
        _REFERENCE={o['name']:o for o in json.loads(path.read_text())['observations']}
    s=case['symbols'];name=case['name']
    prefix=case['abi']+'-'+('indirect-' if s['INDIRECT'] else 'direct-')
    if 'DELAY' in s:
        # Original IRIX terminates in the delay slot. NetBSD returns normally.
        name=prefix+'recvmsg-length-8'
    elif 'POLICY' in s:
        # Reject foreign ownership/extended flags before touching queued data.
        # The invalid-header observation supplies the unchanged guarded bytes.
        name=prefix+'recvmsg-null-message'
    raw=bytes.fromhex(_REFERENCE[name]['stdout_hex'])
    if len(raw)!=192:raise ValueError('missing original recvmsg record: '+name)
    record=dict(zip(['magic','case','v0','v1','a3','checks','preserved','reserved'],struct.unpack('>8I',raw[:32])))
    record.update(case=case['number'],memory_hex=raw[32:].hex())
    if 'POLICY' in s:record.update(v0=122,a3=1)  # IRIX EOPNOTSUPP
    return record


def receive_records(data):
    if not data.startswith(b'RDY\n') or (len(data)-4)%12:
        raise ValueError('invalid receive-peer framing')
    return [dict(zip(['case','mode','bytes'],struct.unpack_from('>III',data,i)))
            for i in range(4,len(data),12)]


def expected_receive(case):
    mode=case['symbols']['MODE']
    return {'case':case['number'],'mode':mode,'bytes':8 if mode==0 else 0}
