"""Compare complete lock records, accounting for the directory-read setup."""
import struct


def compare(case, actual, reference):
    expected = bytearray(reference)
    differences = []
    if case['symbols'].get('KIND') == 2:
        # This read is fixture setup, not the fcntl operation under test.
        # NetBSD permits raw directory reads; IRIX 6.5.22 returns EISDIR.
        # Assert the specific observed behavior rather than masking bytes.
        assert struct.unpack_from('>3I', expected, 48) == (21, 0xfeedface, 1)
        struct.pack_into('>3I', expected, 48, 64, 0xfeedface, 0)
        differences.append('setup directory read: NetBSD 64 bytes; IRIX EISDIR')
    return dict(passed=actual==expected, expected_hex=expected.hex(),
                documented_setup_differences=differences)
