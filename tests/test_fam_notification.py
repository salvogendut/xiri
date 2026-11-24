"""The service test must see both events read by IRIX fm on the same descriptor."""

from pathlib import Path
import runpy
import struct
import unittest

probe = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'lab/native-package/check-fam-service.py'))


class FamNotificationTests(unittest.TestCase):
    def packet(self, code):
        text = f'{code}12 {probe["MARKER"]}\n\0'.encode()
        return struct.pack('>I', len(text)) + text

    def record(self, payload, fd=7, direction=0, name=b'fm', pid=100):
        body = struct.pack('>II', fd, direction) + payload
        header = struct.pack('>IHHI', len(body), 2, 4, pid) + name
        return header.ljust(56, b'\0') + body

    def test_split_reads(self):
        first, second = self.packet('F'), self.packet('A')
        trace = self.record(first[:2]) + self.record(first[2:] + second)
        self.assertEqual(probe['client_events'](trace, 100, 12)['received'], ['Created', 'Deleted'])

    def test_unrelated_io_does_not_count(self):
        for changes in ({'fd': 8}, {'direction': 1}, {'name': b'famd'}, {'pid': 101}):
            with self.subTest(changes=changes):
                trace = self.record(self.packet('F')) + self.record(self.packet('A'), **changes)
                with self.assertRaises(ValueError):
                    probe['client_events'](trace, 100, 12)
