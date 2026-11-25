"""Check the release and content boundary for optional browser media."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from xiri_lab import mozilla_media, sha256


class MozillaMediaTests(unittest.TestCase):
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
