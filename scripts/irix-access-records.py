#!/usr/bin/env python3
"""The bounded access contract and explicit native-policy differences."""
import struct

# These controlled fixture leaves have no executable mode bit. Root's native
# VOP_ACCESS still requires one; original IRIX's ordinary X_OK accepts them.
NO_EXECUTE_BIT={'tree/file','tree/owner-read','tree/group','tree/other',
                'tree/none','tree/noexec','tree/deny/file','tree/search/file'}

def expected(case, identity, oracle, identities):
    out=bytearray(oracle);policy=None
    mode=case['symbols']['MODE'] & 0xffffffff
    if mode & ~7:
        # IRIX has extensions (including 8 and 16); the first implementation
        # deliberately supplies only F_OK/R_OK/W_OK/X_OK combinations.
        struct.pack_into('>I',out,8,22);struct.pack_into('>I',out,16,1)
        policy='unsupported mode outside the standard 0..7 subset'
    elif mode & 1 and identities[identity][0]==0 and case['path'] in NO_EXECUTE_BIT:
        struct.pack_into('>I',out,8,13);struct.pack_into('>I',out,16,1)
        policy='native root execute check requires an executable mode bit'
    elif case['path']=='/tmp/xiri-access-namespace/shadow' and identity==1:
        struct.pack_into('>I',out,8,13);struct.pack_into('>I',out,16,1)
        policy='emulation shadow permission denial'
    return bytes(out),policy
