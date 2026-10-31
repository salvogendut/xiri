"""Measured startup-interface records and independent message-peer receipts."""
import struct


def expected_record(case):
    s=case['symbols'];kind=s['KIND'];error=value=checks=0
    result={'magic':0x58494431,'case':case['number'],'v0':0,'v1':0xfeedface,
            'a3':0,'checks':0,'preserved':0,'reserved':0}
    if kind==8:
        memory=bytearray([0xa5]*64);count=min(s['LENGTH'] & 0xffffffff,5)
        if 'POINTER' in s or 'READONLY' in s:error=14
        else:
            start=16+s['OFFSET'];memory[start:start+count]=b'IRIX\0'[:count]
            memory[start+count-1]=0
        result['memory_hex']=memory.hex()
    elif kind==9:
        current=(s.get('FILE',2)&3)|(s.get('FILE',0)&8)|s.get('PRESET_FL',0)|(0 if 'FILE' in s else 512)
        fdflags=s.get('PRESET_FD',0)&1
        if s.get('FD')==-1 or 'CLOSED' in s:error=9
        elif s['CMD'] not in [1,2,3,4] or 'POLICY' in s:error=22
        elif s['CMD']==1:value=fdflags
        elif s['CMD']==2:
            if s['ARG'] not in [0,1]:error=22
            else:fdflags=s['ARG']
        elif s['CMD']==3:value=current
        else:current=(current&515)|(s['ARG']&136)
        checks=0 if 'CLOSED' in s else fdflags if s['CMD'] in [1,2] else current
    elif kind==10:
        if s.get('FD') in [-1,1]:error=9 if s['FD']==-1 else 95
        elif 'POINTER' in s:error=14
        elif 'POLICY' in s:error=122
        elif s['IOVCNT'] not in range(1,17):error=97
        elif s['IOVCNT'] and 'IOVP' in s:error=14
        elif s['LENGTH'] & 0xffffffff > 0x7fffffff or 'OVERFLOW' in s:error=22
        elif s['LENGTH'] and 'BASE' in s or 'BAD_SECOND' in s:error=14
        else:value=0 if s['IOVCNT']==0 else 8 if 'READONLY' in s or 'TWO' in s else s['LENGTH']
    elif kind==11:
        if s.get('FD') in [-1,1] or 'CLOSED' in s:error=95 if s.get('FD')==1 else 9
        elif 'UNCONNECTED' in s or ('REPEAT' in s and s['HOW']==2):error=134
        elif s['HOW'] not in [0,1,2]:error=22
        else:checks=int('MESSAGE_CONNECTED' in s)
    else:raise ValueError('not a startup-interface fixture')
    result.update(v0=error or value,a3=int(bool(error)),checks=checks)
    return result


def message_records(data):
    if not data.startswith(b'RDY\n') or (len(data)-4)%24:
        raise ValueError('invalid message-peer framing')
    result=[]
    for offset in range(4,len(data),24):
        case,length=struct.unpack_from('>II',data,offset)
        payload=data[offset+8:offset+24]
        if length>16:raise ValueError('invalid message-peer length')
        result.append({'case':case,'bytes':length,'memory_hex':payload.hex()})
    return result


def expected_message(case,reference=False):
    s=case['symbols']
    if s['KIND']==11:count=8
    else:
        r=expected_record(case);count=r['v0'] if not r['a3'] else 0
    return {'case':case['number'],'bytes':count,'memory_hex':(b'XIRI_MSG'[:count]+bytes(16-count)).hex()}
