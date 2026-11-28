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
        for name in ['session-guard', 'x11-check', 'shell-handoff', 'save-session', 'stop-sessions', 'drop-bridge', 'desktop-sound', 'cdromd', 'recorder-audio.so']:
            (self.build/name).write_bytes(b'fixture executable\n')
        self.stage = self.root/'stage'

    def install(self, *args):
        subprocess.run(['sh', str(ROOT/'runtime/install.sh'), *args], check=True,
                       env={**os.environ, 'DESTDIR': str(self.stage), 'BUILDDIR': str(self.build)},
                       capture_output=True)

    def test_power_menu_upgrade_preserves_site_entries(self):
        menu = self.stage/'usr/local/share/xiri/toolchest.chestrc'
        menu.parent.mkdir(parents=True)
        menu.write_bytes((ROOT/'lab/irix-installed-desktop/toolchest.chestrc').read_bytes())
        self.install()
        self.assertIn('"/usr/local/bin/xiri-poweroff"', menu.read_text())
        self.assertTrue(os.access(self.stage/'usr/local/bin/xiri-poweroff', os.X_OK))
        menu.chmod(0o644)
        menu.write_text('# Site menus\n')
        self.install()
        self.assertEqual(menu.read_text(), '# Site menus\n')
        self.assertEqual(menu.with_suffix('.chestrc.example').read_bytes(),
                         (ROOT/'runtime/etc/toolchest.chestrc').read_bytes())

    def test_install_does_not_enable_services_implicitly(self):
        self.install()
        menu = (self.stage/'usr/local/share/xiri/toolchest.chestrc').read_text()
        self.assertIn('include /usr/lib/X11/system.chestrc', menu)
        self.assertIn('/usr/local/bin/xiri-logout', menu)
        self.assertIn('/usr/local/bin/xiri-poweroff', menu)
        self.assertEqual(list((self.stage/'etc/rc.conf.d').iterdir()), [])
        self.assertEqual((self.stage/'usr/local/bin/xiri-session').stat().st_mode & 0o777, 0o555)
        self.assertEqual(os.readlink(self.stage/'usr/local/libexec/xiri/command-shell'), '/bin/sh')
        self.assertEqual((self.stage/'etc/xiri/session.conf').stat().st_mode & 0o777, 0o644)

    def test_enable_and_reinstall_preserve_admin_configuration(self):
        self.install('--enable-services')
        self.assertEqual((self.stage/'etc/rc.conf.d/xiri_famd').read_text(), 'xiri_famd=YES\n')
        rpc = self.stage/'etc/rc.conf.d/rpcbind'
        self.assertIn('rpcbind_flags="-h 127.0.0.1"', rpc.read_text())
        cdrom = self.stage/'etc/rc.conf.d/xiri_cdrom'
        self.assertEqual(cdrom.read_text(), 'xiri_cdrom=YES\n')
        self.assertTrue(os.access(self.stage/'etc/rc.d/xiri_cdrom', os.X_OK))
        self.assertTrue(os.access(self.stage/'usr/local/libexec/xiri/cdromd', os.X_OK))
        self.assertTrue(os.access(self.stage/'usr/local/libexec/xiri/recorder-microphone', os.X_OK))
        self.assertEqual((self.stage/'usr/local/libexec/xiri/recorder-audio.so').stat().st_mode & 0o777, 0o555)
        self.assertEqual((self.stage/'usr/local/share/xiri/microphone').read_text().strip(), 'XiriMicrophone')
        self.assertTrue(os.access(self.stage/'usr/local/libexec/xiri/cd-player.sh', os.X_OK))
        self.assertEqual((self.stage/'etc/rc.conf.d/xiri_sessions').read_text(), 'xiri_sessions=YES\n')
        files = [rpc, cdrom, self.stage/'etc/rc.conf.d/xiri_famd', self.stage/'etc/rc.conf.d/xiri_sessions', self.stage/'etc/xiri/fam.conf',
                 self.stage/'etc/xiri/session.conf', self.stage/'etc/xiri/Xresources']
        for path in files:
            path.write_text('# local policy\n')
        self.install('--enable-services')
        for path in files:
            self.assertEqual(path.read_text(), '# local policy\n')
        self.assertEqual((self.stage/'etc/xiri/fam.conf.example').read_bytes(),
                         (ROOT/'runtime/etc/fam.conf').read_bytes())
        self.assertEqual((self.stage/'etc/xiri/Xresources.example').read_bytes(),
                         (ROOT/'runtime/etc/Xresources').read_bytes())

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
        native_include = '#include "/etc/X11/xdm/Xresources"'
        logo_path = '/usr/local/share/xiri/xdm-logo.xpm'
        lines = resources.read_text().splitlines()
        self.assertLess(lines.index(native_include), lines.index('xlogin*logoFileName: ' + logo_path))
        self.assertEqual((self.stage / logo_path[1:]).read_bytes(), (ROOT/'runtime/etc/xiri-logo.xpm').read_bytes())
        for path in (xdm, servers, resources):
            path.write_text('# administrator configuration\n')
        self.install('--enable-xdm')
        for path in (xdm, servers, resources):
            self.assertEqual(path.read_text(), '# administrator configuration\n')
        self.assertEqual(resources.with_suffix('.example').read_bytes(), (ROOT/'runtime/etc/xdm-Xresources').read_bytes())
        # Choosing a session and a password belongs to the account, not install.
        for name in ('etc/master.passwd', 'etc/ttys', 'usr/people', 'etc/X11'):
            self.assertFalse((self.stage/name).exists())

    def test_application_prefixes_preserve_existing_native_paths(self):
        for prefix in ('freeware', 'adobe'):
            (self.stage/'emul/irix/usr'/prefix).mkdir(parents=True)
        self.install()
        for prefix in ('freeware', 'adobe'):
            path = self.stage/'usr'/prefix
            self.assertEqual(os.readlink(path), '/emul/irix/usr/'+prefix)
            path.unlink()
        adobe = self.stage/'usr/adobe'
        adobe.mkdir()
        (adobe/'local').write_text('administrator data\n')
        freeware = self.stage/'usr/freeware'
        freeware.symlink_to('/administrator/absent-target')
        self.install()
        self.assertEqual((adobe/'local').read_text(), 'administrator data\n')
        self.assertEqual(os.readlink(freeware), '/administrator/absent-target')


if __name__ == '__main__':
    unittest.main()
