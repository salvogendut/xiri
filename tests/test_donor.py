"""Protect donor provenance and reproduce the IRIS overlay's merged view."""
import fcntl
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from xiri_lab.donor import CHUNK, dirty_sectors, export_raw


class DonorExportTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.base = self.root/'disk.raw'
        self.base.write_bytes(b'B'*(CHUNK+1024))
        self.overlay = Path(str(self.base)+'.overlay')
        self.overlay.write_bytes(b'X'*(CHUNK+1024))
        self.map = Path(str(self.overlay)+'.dirty')
        self.lock = Path(str(self.base)+'.prismatic-lock')
        self.lock.touch()
        self.output = self.root/'merged.raw'

    def record(self, count, sectors):
        self.map.write_bytes(struct.pack('<Q', count)+b''.join(
            struct.pack('<Q', sector) for sector in sectors))

    def test_appended_duplicate_and_chunk_boundary_sectors(self):
        # Header counts only the initial flush; the last LBAs are appends.
        self.record(2, [2048, 1, 2047, 2048])
        before = [p.read_bytes() for p in (self.base, self.overlay, self.map)]
        result = export_raw(self.base, self.output)
        expected = bytearray(before[0])
        for sector in [1, 2047, 2048]:
            expected[sector*512:(sector+1)*512] = b'X'*512
        self.assertEqual(self.output.read_bytes(), expected)
        self.assertEqual(result['unique_dirty_sectors'], 3)
        self.assertEqual(result['dirty_entries'], 4)
        self.assertEqual([p.read_bytes() for p in (self.base, self.overlay, self.map)], before)

    def test_zero_sector_overrides_nonzero_base(self):
        self.record(1, [2])
        with self.overlay.open('r+b') as stream:
            stream.seek(1024)
            stream.write(b'\0'*512)
        export_raw(self.base, self.output)
        self.assertEqual(self.output.read_bytes()[1024:1536], b'\0'*512)

    def test_existing_destination_preserved(self):
        self.record(0, [])
        self.output.write_bytes(b'keep')
        with self.assertRaises(FileExistsError):
            export_raw(self.base, self.output)
        self.assertEqual(self.output.read_bytes(), b'keep')

    def test_busy_source_refused(self):
        self.record(0, [])
        with self.lock.open('rb') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(RuntimeError, 'in use'):
                export_raw(self.base, self.output)
        self.assertFalse(self.output.exists())

    def test_missing_map_or_short_overlay_refused(self):
        with self.assertRaises(FileNotFoundError):
            export_raw(self.base, self.output)
        self.record(1, [1])
        self.overlay.write_bytes(b'X'*512)
        with self.assertRaisesRegex(ValueError, 'shorter'):
            export_raw(self.base, self.output)
        self.assertFalse(self.output.exists())

    def test_corrupt_map_refused(self):
        for data in [b'', b'bad', struct.pack('<Q', 1), struct.pack('<QQ', 1, 9),
                     struct.pack('<Q', 0)+b'partial']:
            with self.subTest(data=data), self.assertRaises(ValueError):
                dirty_sectors(data, 4096)

    def test_concurrent_source_change_removes_incomplete_export(self):
        import hashlib
        self.record(0, [])
        original = hashlib.file_digest
        calls = 0

        def changing_digest(*args, **kwargs):
            nonlocal calls
            result = original(*args, **kwargs)
            calls += 1
            if calls == 3:
                # Simulate a writer that ignores the frontend lease.
                with self.base.open('r+b') as stream:
                    stream.write(b'C')
            return result

        with patch('xiri_lab.donor.hashlib.file_digest', side_effect=changing_digest):
            with self.assertRaisesRegex(RuntimeError, 'changed during export'):
                export_raw(self.base, self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
