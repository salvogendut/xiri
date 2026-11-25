"""Cold first launch, component rollback and in-place upgrade on a private Indy."""
import re

from xiri_lab.mozilla_media import LAUNCHER, MODULE, NETWORK


def reboot(guest):
    lab = guest.lab
    lab.offset = len(lab.serial_text())
    lab.send('shutdown -r now')
    lab.wait('login: ', 600)
    lab.send('root')
    lab.wait('xiri-indy# ', 40)


def position(guest, title):
    info = guest.read_text(f"""xwininfo -root -tree | awk '/{title}/ {{print $1; exit}}' | xargs -n 1 xwininfo -id""")
    return tuple(int(re.search('Absolute upper-left ' + axis + r':\s*(-?\d+)', info)[1]) for axis in 'XY')


def browser(guest, out, greeter, login, stage, release):
    greeter(guest)
    session = 'sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors 2>/dev/null | tail -1'
    guest.command('previous=$(' + session + ')')
    login(guest, 'xiritest')
    guest.wait_for('job=$(' + session + ') && test "$job" != "$previous" && test -s "$job/identity"', 240)
    guest.command('job=$(' + session + '); XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
                  'test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; '
                  'export DISPLAY=127.0.0.1:0 XAUTHORITY')
    guest.wait_for('test -s "$XAUTHORITY" && xwininfo -root -tree 2>/dev/null | grep -q "Icon Catalog:"', 240)
    windows = 'xwininfo -root -tree'
    x, y = position(guest, 'Icon Catalog:')
    guest.monitor(f'ptr click {x + 65} {y + 461} left')
    guest.wait_for(windows + ' | grep -q "Icon Catalog: Applications"', 45)
    # The 6.5.22f donor places About Netscape Messenger before Mozilla.
    icon = 278 if release == '6.5.22f' else 100
    guest.monitor(f'ptr click {x + icon} {y + 70} left 2')
    guest.wait_for(windows + ' | grep -q "Welcome to Xiri"', 240)
    x, y = position(guest, 'Welcome to Xiri')
    guest.monitor(f'ptr click {x + 240} {y + 200} left')
    guest.monitor('key ctrl+l')
    guest.monitor('key type http://info.cern.ch/hypertext/WWW/TheProject.html')
    guest.monitor('key Return')
    rendered = windows + ' | grep -qi "World Wide Web project"'
    if stage == 'after-upgrade' and release == '6.5.22f':
        # A restored 1.0.1 profile can finish with an empty document.
        # Give it one uncached reload when the expected title is still missing.
        try:
            guest.wait_for(rendered, 60)
        except RuntimeError as error:
            if not str(error).startswith('guest command failed (1):'):
                raise
            guest.monitor('key ctrl+shift+r')
    guest.wait_for(rendered, 120)
    title = guest.read_text(windows + ' | grep -im 1 "World Wide Web project"').strip()
    guest.capture(out / (stage + '.png'))
    guest.monitor('key ctrl+q')
    guest.wait_for('! pgrep -x mozilla-bin >/dev/null', 90)
    return title


def check(guest, out, package, greeter, login, baseline):
    cmd = guest.command
    mount = 'mount -rt cd9660 /dev/cd0a /cdrom'
    profile = '/usr/people/xiritest/.mozilla'
    record = '/var/db/xiri-install/mozilla'
    if guest.read_text('cat ' + record + '/identity').strip() != package['mozilla_receipt']:
        raise ValueError('unexpected installed Mozilla component')
    kernel = guest.read_text('sysctl -n kern.version').strip()
    cmd('modstat | grep -q "^compat_irix_o32 " && /etc/rc.d/xiri_hosts status && '
        'cat /emul/irix/ns/.local/hosts.byname/info.cern.ch | grep -qi info.cern.ch')
    first = browser(guest, out, greeter, login, 'first-boot', package['release'])
    cmd(f'find {profile} -type f -name prefs.js -exec sha256 {{}} \\; >/root/mozilla-profile.sha && '
        f'find {profile} -type f -name bookmarks.html -exec sha256 {{}} \\; >>/root/mozilla-profile.sha && '
        'grep -q /prefs.js /root/mozilla-profile.sha && grep -q /bookmarks.html /root/mozilla-profile.sha')
    digests = guest.read_text('cat /root/mozilla-profile.sha').splitlines()
    cmd('echo "# site preference" >> /etc/rc.conf.d/xiri_hosts && '
        'sha256 /etc/rc.conf.d/xiri_hosts /usr/people/xiritest/.xsession /var/db/xiri-install/installed >/root/mozilla-site.sha')
    cmd(mount)
    witness = '/emul/irix/var/netscape/mozilla/components/local-extension.note'
    cmd(f'test ! -e {witness} && echo local > {witness}')
    cmd('if sh /cdrom/install.sh --remove-mozilla >/root/browser-conflict.log 2>&1; then false; else '
        'grep -q "save local changes to .*/components" /root/browser-conflict.log && '
        f'grep -qx local {witness} && grep -qx enabled {record}/phase && rm {witness}; fi', 1200)
    cmd('sh /cdrom/install.sh --remove-mozilla >/root/browser-remove.log 2>&1; rc=$?; '
        'tail -8 /root/browser-remove.log; test "$rc" = 0', 1200)
    for path, key in [('/netbsd', 'netbsd'), ('/netbsd.boot', 'netbsd.boot'), (MODULE, 'compat_irix_o32.kmod')]:
        cmd(f'test "$(sha256 -q {path})" = {baseline[key]}')
    cmd(f'test ! -e {record} && test ! -L {LAUNCHER} && test -f {LAUNCHER} && '
        'test ! -e /emul/irix/var/netscape/mozilla/mozilla-bin && test ! -e /etc/rc.d/xiri_hosts && '
        '! mount | grep -q "^xiri-hosts " && sha256 -c /root/mozilla-profile.sha && sha256 -c /root/mozilla-site.sha')
    reboot(guest)
    restored = guest.read_text('sysctl -n kern.version').strip()
    if kernel == restored:
        raise ValueError('rollback booted the browser kernel again')
    greeter(guest)
    cmd('modstat | grep -q "^compat_irix_o32 " && sha256 -c /root/mozilla-profile.sha && sha256 -c /root/mozilla-site.sha')
    cmd(mount)
    cmd('sh /cdrom/install.sh --mozilla >/root/browser-upgrade.log 2>&1; rc=$?; '
        'tail -8 /root/browser-upgrade.log; test "$rc" = 0', 1200)
    cmd('sha256 -c /root/mozilla-profile.sha && sha256 -c /root/mozilla-site.sha')
    reboot(guest)
    if guest.read_text('sysctl -n kern.version').strip() != kernel:
        raise ValueError('upgraded guest booted the wrong kernel')
    cmd(f'test "$(sha256 -q {MODULE})" = {NETWORK["compat_irix_o32.kmod"][1]} && '
        '/etc/rc.d/xiri_hosts status && sha256 -c /root/mozilla-profile.sha && sha256 -c /root/mozilla-site.sha')
    last = browser(guest, out, greeter, login, 'after-upgrade', package['release'])
    return dict(first_boot=first, after_upgrade=last, profile_files=digests,
                browser_kernel=kernel, restored_kernel=restored, rollback_xdm=True,
                site_files_preserved=True, local_extension_preserved=True)
