"""The offline upgrade builder must refuse deltas outside its guest updater's scope."""
import hashlib
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from xiri_lab import ROOT, sha256
from xiri_lab.install_media import upgrade_delta
from xiri_lab.native_package import archive_tree


class UpgradeMediaTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.changed = 'root/usr/local/sbin/xiri-sync-users'

    def package(self, name, entries):
        package = self.root / name
        tree = package / 'tree'
        tree.mkdir(parents=True)
        rows = []
        for path, value in entries.items():
            dest = tree / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(value)
            digest = hashlib.sha256(value).hexdigest()
            rows.append(f'{path}|file|0555|{digest}|replace-owned-file')
        (tree / 'files.tsv').write_text('\n'.join(rows) + '\n')
        (tree / 'target.conf').write_text('machine=sgimips\n')
        (tree / 'prerequisites.tsv').touch()
        archive_tree(tree, package / 'native.tar.gz')
        profile = ROOT / 'profiles/netbsd-sgimips-indy-11.99.11-v1.json'
        (package / 'manifest.json').write_text(json.dumps({
            'profile': profile.stem, 'profile_sha256': sha256(profile),
            'artifacts': json.loads(profile.read_text())['artifacts'],
            'archive_sha256': sha256(package / 'native.tar.gz'),
        }))
        return package

    def test_both_directions_and_only_changed_helpers(self):
        a = {self.changed: b'previous', 'root/etc/xiri/session.conf': b'site default'}
        old = self.package('a', a)
        new = self.package('b', {**a, self.changed: b'candidate'})
        with tarfile.open(upgrade_delta(old, new, self.root)) as delta:
            self.assertEqual(delta.extractfile('old/' + self.changed).read(), b'previous')
            self.assertEqual(delta.extractfile('new/' + self.changed).read(), b'candidate')
            self.assertEqual(delta.extractfile('previous').read().decode().strip(), sha256(old / 'native.tar.gz'))
            self.assertEqual(len(delta.extractfile('changes').read().splitlines()), 1)
            self.assertFalse(any('session.conf' in item.name for item in delta))

    def test_reject_unhandled_migrations(self):
        for path in ('kernel/netbsd', 'root/etc/xiri/session.conf', 'root/usr/sbin/rpcbind'):
            with self.subTest(path=path), tempfile.TemporaryDirectory(dir=self.root) as d:
                work = Path(d)
                old = self.package(work / 'a', {path: b'old'})
                new = self.package(work / 'b', {path: b'new'})
                with self.assertRaisesRegex(ValueError, 'Unsupported upgrade destination'):
                    upgrade_delta(old, new, work)

    def test_reject_inventory_changes(self):
        old = self.package('a', {self.changed: b'original'})
        new = self.package('b', {self.changed: b'updated', 'root/usr/local/bin/xiri-extra': b'extra'})
        with self.assertRaisesRegex(ValueError, 'adds or removes'):
            upgrade_delta(old, new, self.root)
