"""Check the release and content boundary for optional browser media."""
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from xiri_lab import mozilla_media, sha256
from xiri_lab.indy_kernel_update import component_inventory
from xiri_lab.native_package import archive_tree


class MozillaMediaTests(unittest.TestCase):
    def test_kernel_transition_preserves_browser_group_policy_and_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            baseline = root/'source'
            browser = baseline/'root/browser'
            browser.mkdir(parents=True)
            browser.chmod(0o755)
            addon = browser/'plugin'
            addon.write_bytes(b'original')
            plan = baseline/'groups'
            plan.write_text('add|/browser\nold|/netbsd\n')
            kernel = baseline/'root/netbsd'
            kernel.write_bytes(b'old kernel')

            def inventory(name):
                destination = root/name
                archive_tree(baseline, destination)
                with tarfile.open(destination) as archive:
                    return component_inventory(archive)

            expected = inventory('old.tgz')
            kernel.unlink()
            plan.write_text('add|/browser\n')
            self.assertEqual(inventory('migrated.tgz'), expected)
            plan.write_text('config|/browser\n')
            self.assertNotEqual(inventory('policy.tgz'), expected)
            plan.write_text('add|/browser\n')
            addon.write_bytes(b'different')
            self.assertNotEqual(inventory('contents.tgz'), expected)
            addon.write_bytes(b'original')
            addon.chmod(0o755)
            self.assertNotEqual(inventory('mode.tgz'), expected)

    def test_only_the_matched_release_and_bytes_are_accepted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            profiles = root / 'profiles'
            profiles.mkdir()
            results = root / 'docs/results'
            results.mkdir(parents=True)
            archive = root / 'payload.tar.gz'
            archive.write_bytes(b'qualified browser')
            pins = {'browser_payload_sha256': sha256(archive)}
            releases = ('6.5.22f', '6.5.30f')
            (results / '2026-11-25-mozilla-sigpoll.json').write_text(json.dumps({
                'releases': {release: {'image': pins} for release in releases}
            }))
            for release in releases:
                (profiles / f'irix-{release}-mozilla-v1.json').write_text(release)
            with patch.object(mozilla_media, 'ROOT', root):
                for release in releases:
                    profile = profiles / f'irix-{release}-mozilla-v1.json'
                    archive.write_bytes(b'qualified browser')
                    manifest = dict(release=release, profile=profile.stem, profile_sha256=sha256(profile),
                                    donor={'sha256': release}, payload_sha256=pins['browser_payload_sha256'])
                    (root / 'manifest.json').write_text(json.dumps(manifest))
                    base = dict(release=release, donor=manifest['donor'])
                    self.assertEqual(mozilla_media.browser_archive(root, base), (archive, pins))
                    other = next(r for r in releases if r != release)
                    for mismatch in (dict(base, release=other), dict(base, donor={'sha256': 'other disk'})):
                        with self.subTest(base=mismatch), self.assertRaises(ValueError):
                            mozilla_media.browser_archive(root, mismatch)
                    archive.write_bytes(b'changed after import')
                    with self.assertRaises(ValueError):
                        mozilla_media.browser_archive(root, base)
