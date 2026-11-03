"""Installation policy checks; process ownership is qualified on NetBSD."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RuntimeInstallTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.build = self.root/'build'
        self.build.mkdir()
        for name in ['session-guard', 'x11-check', 'shell-handoff']:
            (self.build/name).write_bytes(b'fixture executable\n')
        self.stage = self.root/'stage'

    def install(self, *args):
        subprocess.run(['sh', str(ROOT/'runtime/install.sh'), *args], check=True,
                       env={**os.environ, 'DESTDIR': str(self.stage), 'BUILDDIR': str(self.build)},
                       capture_output=True)

    def test_install_does_not_enable_services_implicitly(self):
        self.install()
        self.assertEqual(list((self.stage/'etc/rc.conf.d').iterdir()), [])
        self.assertEqual((self.stage/'usr/local/bin/xiri-session').stat().st_mode & 0o777, 0o555)
        self.assertEqual(os.readlink(self.stage/'usr/local/libexec/xiri/command-shell'), '/bin/sh')
        self.assertEqual((self.stage/'etc/xiri/session.conf').stat().st_mode & 0o777, 0o644)

    def test_enable_and_reinstall_preserve_admin_configuration(self):
        self.install('--enable-services')
        self.assertEqual((self.stage/'etc/rc.conf.d/xiri_famd').read_text(), 'xiri_famd=YES\n')
        rpc = self.stage/'etc/rc.conf.d/rpcbind'
        self.assertIn('rpcbind_flags="-h 127.0.0.1"', rpc.read_text())
        files = [rpc, self.stage/'etc/rc.conf.d/xiri_famd', self.stage/'etc/xiri/fam.conf',
                 self.stage/'etc/xiri/session.conf']
        for path in files:
            path.write_text('# local policy\n')
        self.install('--enable-services')
        for path in files:
            self.assertEqual(path.read_text(), '# local policy\n')
        self.assertEqual((self.stage/'etc/xiri/fam.conf.example').read_bytes(),
                         (ROOT/'runtime/etc/fam.conf').read_bytes())

    def test_xdm_opt_in_preserves_display_and_login_policy(self):
        self.install('--enable-services')
        self.assertFalse((self.stage/'etc/rc.conf.d/xdm').exists())
        self.install('--enable-xdm')
        xdm = self.stage/'etc/rc.conf.d/xdm'
        servers = self.stage/'etc/xiri/xdm/Xservers'
        resources = self.stage/'etc/xiri/xdm/Xresources'
        self.assertIn('xdm=YES', xdm.read_text())
        self.assertIn('-server /etc/xiri/xdm/Xservers', xdm.read_text())
        self.assertIn('-resources /etc/xiri/xdm/Xresources', xdm.read_text())
        self.assertIn('-config /usr/local/share/xiri/xorg.conf', servers.read_text())
        for path in (xdm, servers, resources):
            path.write_text('# administrator configuration\n')
        self.install('--enable-xdm')
        for path in (xdm, servers, resources):
            self.assertEqual(path.read_text(), '# administrator configuration\n')
        # Choosing a session and a password belongs to the account, not install.
        for name in ('etc/master.passwd', 'etc/ttys', 'usr/people', 'etc/X11'):
            self.assertFalse((self.stage/name).exists())


if __name__ == '__main__':
    unittest.main()
