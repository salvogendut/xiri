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
            dest.chmod(0o555)
            digest = hashlib.sha256(value).hexdigest()
            rows.append(f'{path}|file|0555|{digest}|replace-owned-file')
        (tree / 'files.tsv').write_text(''.join(row + '\n' for row in rows))
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
        for path in ('kernel/netbsd', 'root/etc/xiri/session.conf', 'root/usr/sbin/rpcbind',
                     'root/etc/rc.conf', 'root/etc/rc.conf.d/xiri_famd', 'root/etc/xiri/fam.conf',
                     'root/etc/rc.d/xdm', 'root/usr/local/share/xiri/examples/rc.conf.d/rpcbind'):
            with self.subTest(path=path), tempfile.TemporaryDirectory(dir=self.root) as d:
                work = Path(d)
                old = self.package(work / 'a', {path: b'old'})
                new = self.package(work / 'b', {path: b'new'})
                with self.assertRaisesRegex(ValueError, 'Unsupported upgrade destination'):
                    upgrade_delta(old, new, work)

    def test_fam_service_and_example_are_replacements_only(self):
        paths = ('root/etc/rc.d/xiri_famd', 'root/usr/local/share/xiri/examples/rc.conf.d/xiri_famd')
        old = self.package('old', dict.fromkeys(paths, b'previous'))
        new = self.package('new', dict.fromkeys(paths, b'candidate'))
        with tarfile.open(upgrade_delta(old, new, self.root)) as delta:
            for path in paths:
                self.assertEqual(delta.extractfile('old/' + path).read(), b'previous')
                self.assertEqual(delta.extractfile('new/' + path).read(), b'candidate')
        for path in paths:
            with self.subTest(path=path), tempfile.TemporaryDirectory(dir=self.root) as d:
                w = Path(d)
                missing = self.package(w / 'missing', {})
                present = self.package(w / 'present', {path: b'service'})
                for source, target in ((missing, present), (present, missing)):
                    with tempfile.TemporaryDirectory(dir=w) as work:
                        with self.assertRaisesRegex(ValueError, 'Unsupported service addition or retirement'):
                            upgrade_delta(source, target, Path(work))

    def test_add_and_retire_use_absent_sides_and_include_only_available_bytes(self):
        retired = 'root/usr/local/libexec/xiri/old-map'
        added = 'root/usr/local/bin/xiri-account-map'
        old = self.package('a', {retired: b'original'})
        new = self.package('b', {added: b'updated'})
        with tarfile.open(upgrade_delta(old, new, self.root)) as delta:
            rows = [line.split('|') for line in delta.extractfile('changes').read().decode().splitlines()]
            self.assertEqual(rows, [
                [added[4:], '-', '-', '0555', hashlib.sha256(b'updated').hexdigest()],
                [retired[4:], '0555', hashlib.sha256(b'original').hexdigest(), '-', '-'],
            ])
            self.assertEqual(delta.extractfile('old/' + retired).read(), b'original')
            self.assertEqual(delta.extractfile('new/' + added).read(), b'updated')
            self.assertNotIn('new/' + retired, delta.getnames())
            self.assertNotIn('old/' + added, delta.getnames())

    def test_inventory_changes_still_reject_other_destinations(self):
        for added in (True, False):
            with self.subTest(added=added), tempfile.TemporaryDirectory(dir=self.root) as d:
                w = Path(d)
                a, b = self.package(w / 'a', {}), self.package(w / 'b', {'root/etc/rc.d/xiri': b'service'})
                with self.assertRaisesRegex(ValueError, 'Unsupported upgrade destination'):
                    upgrade_delta(a if added else b, b if added else a, w)

    def test_refuse_adding_a_link_declared_as_a_regular_file(self):
        old = self.package('a', {})
        new = self.package('b', {self.changed: b'helper'})
        member = new / 'tree' / self.changed
        member.rename(member.with_name('other'))
        member.symlink_to('other')
        tar = new / 'native.tar.gz'
        tar.unlink()
        archive_tree(new / 'tree', tar)
        with self.assertRaisesRegex(ValueError, 'type or mode differs'):
            upgrade_delta(old, new, self.root)

    def test_refuse_retirement_if_new_archive_still_contains_the_helper(self):
        old = self.package('a', {self.changed: b'old'})
        new = self.package('b', {})
        hidden = new / 'tree' / self.changed
        hidden.parent.mkdir(parents=True)
        hidden.write_bytes(b'still installed by this archive')
        tar = new / 'native.tar.gz'
        tar.unlink()
        archive_tree(new / 'tree', tar)
        with self.assertRaisesRegex(ValueError, 'Unlisted upgrade member'):
            upgrade_delta(old, new, self.root)
