"""Decode actual SGI drag records, including ambiguous STRING alternatives."""
import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('cc'), 'A host C compiler is required')
class DropFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.TemporaryDirectory(prefix='xiri-drop-test-')
        cls.decoder = pathlib.Path(cls.work.name) / 'decode'
        subprocess.run(['cc', '-O2', '-Wall', '-Wextra', '-Werror',
                        '-I'+str(ROOT/'runtime/libexec'), str(ROOT/'lab/drag-drop/decode.c'),
                        '-o', str(cls.decoder)], check=True)

    @classmethod
    def tearDownClass(cls):
        cls.work.cleanup()

    def decode(self, data, hostname='xiri-indy'):
        return subprocess.run([str(self.decoder), hostname], input=data, capture_output=True)

    def test_recorded_multi_file_selection(self):
        fixture = json.loads((ROOT/'lab/drag-drop/sgi-icons.json').read_text())
        result = self.decode(bytes.fromhex(fixture['hex']))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, fixture['uri_list'].encode())

    def test_uri_escaping_preserves_filename_bytes(self):
        record = b'Category:File Name:"/tmp/a\n\t%#?\\\xc3\xa9" Host:xiri-indy\0'
        result = self.decode(record)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'file:///tmp/a%0A%09%25%23%3F%5C%C3%A9\r\n')

    def test_remote_relative_and_non_file_inputs_are_rejected(self):
        for data in [b'Category:File Name:"/tmp/a" Host:remote\0',
                     b'Category:File Name:"../a" Host:xiri-indy\0',
                     b'Category:URL Name:"/tmp/a" Host:xiri-indy\0']:
            with self.subTest(data=data):
                result = self.decode(data)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b'')

    def test_malformed_records_fail_as_a_whole(self):
        good = b'Category:File Name:"/tmp/a" Host:xiri-indy\0'
        for data in [b'', b'\0', good[:-1], good+b'Name:"/tmp/b"\0',
                     good+good.replace(b'Name:', b'Name:"/tmp/injected" Name:'),
                     good.replace(b'"/tmp/a"', b'"/tmp/a'),
                     good.replace(b'"/tmp/a"', b'"/tmp/a"junk'),
                     good.replace(b'Host:xiri-indy', b'Host:xiri-indy Host:remote')]:
            with self.subTest(data=data):
                result = self.decode(data)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b'')

    def test_size_and_item_limits(self):
        record = b'Category:File Name:"/a" Host:xiri-indy\0'
        self.assertEqual(self.decode(record*256).returncode, 0)
        self.assertEqual(self.decode(record*257).returncode, 1)
        self.assertEqual(self.decode(b'x'*65537).returncode, 1)


if __name__ == '__main__':
    unittest.main()
