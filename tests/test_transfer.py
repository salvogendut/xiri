"""Large lab transfers must never publish corrupt or failed producer output."""
import hashlib
from pathlib import Path
import re
import socket
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from xiri_lab.transfer import archive


class Producer:
    def __init__(self, payload, expected=None, fail=False):
        self.payload = payload
        self.expected = expected if expected is not None else payload
        self.fail = fail

    def command(self, command, timeout):
        if command.startswith('rm -f '):
            return
        if self.fail:
            raise RuntimeError('producer failed')
        port = int(re.search(r'192\.168\.231\.1 (\d+)', command)[1])
        with socket.create_connection(('127.0.0.1', port), timeout=2) as stream:
            stream.sendall(self.payload)
            stream.shutdown(socket.SHUT_WR)

    def read_text(self, command, timeout):
        return hashlib.sha256(self.expected).hexdigest() + '\n'


class ArchiveTransferTests(unittest.TestCase):
    def test_verified_payload_is_published(self):
        payload = bytes(range(256)) * 4096
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence.tgz'
            digest = archive(Producer(payload), 'test-producer', path, timeout=5)
            self.assertEqual(path.read_bytes(), payload)
            self.assertEqual(digest, hashlib.sha256(payload).hexdigest())
            self.assertFalse(path.with_name(path.name + '.partial').exists())

    def test_truncated_or_corrupt_payload_is_not_published(self):
        for received in (b'partial', b'corrupt'):
            with self.subTest(received=received), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'evidence.tgz'
                with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                    archive(Producer(received, expected=b'complete original'),
                            'test-producer', path, timeout=5)
                self.assertFalse(path.exists())
                self.assertEqual(path.with_name(path.name + '.partial').read_bytes(), received)

    def test_producer_failure_is_preserved_without_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence.tgz'
            with self.assertRaisesRegex(RuntimeError, 'producer failed'):
                archive(Producer(b'', fail=True), 'test-producer', path, timeout=5)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
