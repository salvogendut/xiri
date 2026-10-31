#!/usr/bin/env python3
"""Verify fixed-width SIOCNREAD records and explicitly bounded policy differences."""
import json
from pathlib import Path
import struct

ROOT=Path(__file__).resolve().parent.parent


def expected(case,uid,contract):
    s=case['symbols']; suffix=case['name'].split('-',2)[2]
    rule=contract['cases'][suffix]
    error=rule['errno']
    header=[0x58494e52,s['CASE'],error,0xfeedface,int(error!=0),1,uid,uid,uid,uid,0,0,0,0,0,0]
    if s['KIND']==0 and s['STATE']>=2:header[10]=17
    result=bytearray(struct.pack('>16I',*header)+b'\xa5'*96)
    count=struct.pack('>I',rule['count']) if 'count' in rule else b''
    if rule.get('copied',0):
        if 'TAIL' in s:
            result[128-s['TAIL']:128-s['TAIL']+rule['copied']]=count[:rule['copied']]
        else:
            start=72+s['ALIGN'];result[start:start+rule['copied']]=count[:rule['copied']]
    if 'REPEAT' in s:result[84:88]=count
    if header[10]:result[128:145]=b'0123456789ABCDEFG'
    return bytes(result)


def validate_reference(cases,observations):
    contract=json.loads((ROOT/'lab/irix-siocnread/abi.json').read_text())
    refs={o['name']:o for o in observations}
    assert len(refs)==len(observations)==2*len(cases)
    for uid in [0,1234]:
        for case in cases:
            name=case['name']+'-'+str(uid);o=refs[name]
            assert o['exit']==0 and not o['stderr'],name
            assert bytes.fromhex(o['stdout_hex'])==expected(case,uid,contract),name
    return len(refs)


def compare(case,uid,raw,reference):
    # No field is masked. Any deliberate unsupported-command policy is encoded
    # separately from the measured oracle in abi.json and this comparator.
    contract=json.loads((ROOT/'lab/irix-siocnread/abi.json').read_text())
    want=bytearray(expected(case,uid,contract))
    if bytes(want)!=reference:raise ValueError('unreviewed reference: '+case['name'])
    if case['symbols']['COMMAND']!=0x4004730a:
        # Unsupported foreign selectors never reach native ioctl dispatch.
        struct.pack_into('>I',want,8,89);struct.pack_into('>I',want,16,1)
        want[64:128]=b'\xa5'*64
    return dict(passed=raw==want,expected_hex=want.hex(),differing_offsets=[i for i,(a,b) in enumerate(zip(raw,want)) if a!=b])
