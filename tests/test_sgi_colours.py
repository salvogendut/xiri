"""Imported RGB data must retain exact values through Xcms conversion."""
from pathlib import Path
import subprocess
import unittest

SCRIPT = Path(__file__).resolve().parents[1]/'runtime/libexec/sgi-colours.awk'


class SgiColourTests(unittest.TestCase):
    def convert(self, source):
        return subprocess.run(['awk', '-f', str(SCRIPT)], input=source,
                              text=True, capture_output=True)

    def test_aliases_preserve_all_sixteen_bits_and_standard_names(self):
        result = self.convert('! comment\n125 158 192 SGILightBlue\n'
                              '125 158 192 sgi light blue\n'
                              '85 85 85 SGIDarkGray\n'
                              '255 255 255 SGIGray100\n'
                              '0 0 0 SGIGray0\n1 2 3 white\n')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(), [
            'XCMS_COLORDB_START 0.1',
            'sgilightblue\trgb:7d7d/9e9e/c0c0',
            'sgidarkgray\trgb:5555/5555/5555',
            'sgigray100\trgb:ffff/ffff/ffff',
            'sgigray0\trgb:0000/0000/0000',
            'XCMS_COLORDB_END'])

    def test_unusable_or_ambiguous_vendor_data_fails(self):
        for source in ('', '! no entries\n', '255 0 0 red\n',
                       '256 0 0 SGIRed\n',
                       '1 2 3 SGITest\n3 2 1 sgi test\n'):
            with self.subTest(source=source):
                self.assertNotEqual(self.convert(source).returncode, 0)


if __name__ == '__main__':
    unittest.main()
