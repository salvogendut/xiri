"""IRIX lookup tables must preserve native identities without copying secrets."""
from pathlib import Path
import subprocess
import unittest

MAP = Path(__file__).resolve().parents[1]/'runtime/libexec/account-map.awk'


class AccountMapTests(unittest.TestCase):
    def project(self, table, text):
        return subprocess.run(['awk', '-v', 'database='+table, '-f', str(MAP)],
                              input=text, text=True, capture_output=True)

    def test_passwd_preserves_homes_and_ids_and_irix_root_convention(self):
        result = self.project('passwd', 'root:secret:0:0:Root:/root:/bin/ksh\n'
                              'alice:another-secret:1237:100:Alice:/usr/people/alice:/bin/ksh\n'
                              'bob:*:1238:100:Bob:/home/bob:/bin/sh\n')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, 'root:*:0:0:Root:/:/bin/sh\n'
                         'alice:*:1237:100:Alice:/usr/people/alice:/bin/sh\n'
                         'bob:*:1238:100:Bob:/home/bob:/bin/sh\n')

    def test_group_memberships_survive_without_passwords(self):
        result = self.project('group', 'shared:secret:1235:alice,bob\nwheel:*:0:root\n')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, 'shared:*:1235:alice,bob\nwheel:*:0:root\n')

    def test_incomplete_or_empty_lookup_is_rejected(self):
        for table, text in [('passwd', ''), ('group', ''), ('passwd', 'alice:*:1237\n'),
                            ('group', 'shared:*:not-a-gid:alice\n')]:
            with self.subTest(table=table, text=text):
                self.assertNotEqual(self.project(table, text).returncode, 0)
