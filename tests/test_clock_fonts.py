"""Clock media must match its donor and preserve earlier payloads."""
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from xiri_lab.clock_fonts import augmented_payload, extract_fonts


class ClockMediaTests(unittest.TestCase):
    def test_wrong_overlay_rejected_before_extraction(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            disc = root / 'disc.iso'
            disc.write_bytes(b'wrong release')
            for release in ('6.5.22f', '6.5.30f'):
                imported = dict(release=release, profile=f'irix-{release}-v1')
                with self.assertRaisesRegex(ValueError, 'Overlay 1'):
                    extract_fonts(imported, disc, 'unused-extractor', root)

    def test_supplement_is_deterministic_and_preserves_prior_members(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            base, source = root / 'base.tgz', root / 'font'
            with tarfile.open(base, 'w:gz') as tar:
                info = tarfile.TarInfo('emul/irix/existing')
                info.mode, info.size = 0o555, 3
                tar.addfile(info, io.BytesIO(b'old'))
                link = tarfile.TarInfo('emul/irix/alias')
                link.type, link.linkname = tarfile.SYMTYPE, 'existing'
                tar.addfile(link)
            source.write_bytes(b'font')
            dest = 'emul/irix/usr/lib/X11/fonts/misc/iris10.pcf.Z'
            outputs = [root / 'a.tgz', root / 'b.tgz']
            for path in outputs:
                augmented_payload(base, {'/' + dest: source}, path)
            self.assertEqual(outputs[0].read_bytes(), outputs[1].read_bytes())
            with tarfile.open(outputs[0]) as tar:
                self.assertEqual(tar.extractfile('emul/irix/existing').read(), b'old')
                self.assertEqual(tar.getmember('emul/irix/alias').linkname, 'existing')
                self.assertEqual(tar.getmember(dest).mode, 0o444)
                self.assertEqual(tar.extractfile(dest).read(), b'font')
            for name in ('existing', 'alias/iris'):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    augmented_payload(base, {'/emul/irix/' + name: source}, root / name.split('/')[0])
