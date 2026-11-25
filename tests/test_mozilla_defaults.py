"""Preserve local profile templates when installing the offline start page."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SETUP = Path(__file__).resolve().parents[1]/'packaging/mozilla/install-mozilla-defaults.sh'


class MozillaDefaultsTests(unittest.TestCase):
    def test_first_run_templates_and_existing_preferences(self):
        for release in ('6.5.22f', '6.5.30f'):
            with self.subTest(release=release), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                base = root/'emul/irix/var/netscape/mozilla'
                profile = base/'defaults/profile'
                (profile/'US').mkdir(parents=True)
                (profile/'US/bookmarks.html').touch()
                (base/'mozilla-bin').touch(mode=0o755)
                if release == '6.5.22f':
                    (base/'defaults/pref').mkdir()
                    (base/'defaults/pref/all.js').write_text('pref("general.useragent.misc", "rv:1.0.2");')
                else:
                    (base/'greprefs').mkdir()
                    (base/'greprefs/all.js').touch()
                template = profile/'US/prefs.js'
                template.write_text('// local template\n')
                def install():
                    return subprocess.run(['sh', str(SETUP)], env=dict(os.environ, DESTDIR=tmp),
                                          capture_output=True, umask=0o077)
                self.assertNotEqual(install().returncode, 0)
                self.assertEqual(template.read_text(), '// local template\n')
                self.assertFalse((base/'xiri-welcome.html').exists())
                template.unlink()
                for _ in range(2):
                    result = install()
                    self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(template.read_text().startswith('// Mozilla User Preferences\n\n'))
                self.assertIn('rv:1.0.2' if release=='6.5.22f' else 'ignore', template.read_text())
                self.assertEqual(template.stat().st_mode & 0o777, 0o644)
                self.assertEqual((profile/'prefs.js').read_bytes(), template.read_bytes())
                self.assertNotEqual((profile/'prefs.js').stat().st_ino, template.stat().st_ino)
