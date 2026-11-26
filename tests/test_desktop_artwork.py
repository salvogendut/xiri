import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest

HELPER = Path(__file__).resolve().parents[1] / 'lab/irix-installer/desktop-artwork.sh'
OPEN = '''
set -eu
root=$1
types=$root/usr/lib/filetype
table=$types/desktop.otr
fail() { echo "$*" >&2; exit 1; }
sha256() { sha256sum "$2" | cut -d' ' -f1; }
. "$2"
trap artwork_close EXIT
artwork_open
'''


class ArtworkMigration(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.workspace = Path(temporary.name)
        self.target('default')

    def target(self, name):
        self.root = self.workspace / name
        self.receipts = self.root / 'var/inst'
        self.table = self.root / 'usr/lib/filetype/desktop.otr'
        self.table.parent.mkdir(parents=True)
        self.table.write_bytes(b'original')

    def old_install(self, name, artwork):
        receipt = self.receipts / ('xiri-' + name)
        receipt.mkdir(parents=True)
        (receipt / 'baseline.otr').write_bytes(self.table.read_bytes())
        self.table.write_bytes(artwork)
        (receipt / 'published.sha256').write_text(hashlib.sha256(artwork).hexdigest() + '\n')

    def open(self, check=True):
        return subprocess.run(['sh', '-c', OPEN, 'test', self.root, HELPER],
                              capture_output=True, text=True, check=check)

    def test_migrate_two_independent_snapshots(self):
        for first, second in [('unzip', 'xmahjongg'), ('xmahjongg', 'unzip')]:
            with self.subTest(first=first):
                self.target(first)
                self.old_install(first, b'one')
                self.old_install(second, b'both')
                self.open()
                shared = self.receipts / 'xiri-filetypes'
                self.assertEqual((shared / 'baseline.otr').read_bytes(), b'original')
                self.assertEqual(self.table.read_bytes(), b'both')
                self.assertTrue(all((shared / name).is_file() for name in (first, second)))

    def test_preflight_with_no_enrolled_products_releases_the_snapshot(self):
        self.open()
        self.assertFalse((self.receipts / 'xiri-filetypes').exists())
        self.table.write_bytes(b'new site desktop')
        self.open()
        self.assertEqual(self.table.read_bytes(), b'new site desktop')

    def test_preserve_independent_edit_and_active_legacy_lock(self):
        self.old_install('unzip', b'zip')
        zip_state = self.receipts / 'xiri-unzip'
        lock = zip_state / 'lock'
        lock.mkdir()
        self.assertNotEqual(self.open(False).returncode, 0)
        self.assertTrue(lock.is_dir())
        self.assertFalse((self.receipts / 'xiri-xmahjongg/lock').exists())
        lock.rmdir()
        self.table.write_bytes(b'site edit')
        self.assertNotEqual(self.open(False).returncode, 0)
        self.assertEqual(self.table.read_bytes(), b'site edit')
        self.assertEqual((zip_state / 'baseline.otr').read_bytes(), b'original')
        self.assertFalse((self.receipts / 'xiri-filetypes').exists())
