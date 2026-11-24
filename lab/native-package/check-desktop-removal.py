"""Guest-side stages used by the Indy kernel round-trip runner with --install-media."""

import shlex
import re

STATE = '/var/db/xiri-install'
DRIVER = '/usr/X11R7/lib/modules/drivers/newport_drv.so'
PREFS = '/usr/people/xiritest/.Xresources'
NOTE = '/usr/people/xiritest/removal-note'
NATIVE_NOTE = '/home/netbsdtest/recovery-note'
PRESERVE = ' '.join(
    (
        PREFS,
        NOTE,
        '/usr/people/xiritest/.xsession',
        '/etc/xiri/session.conf',
        '/etc/passwd',
        '/etc/master.passwd',
        '/etc/group',
        '/etc/modules.conf',
        '/etc/ttys',
        '/etc/rc.conf',
        '/etc/X11/xorg.conf',
    )
)


def mount(g, release):
    g.command(
        'mkdir -p /cdrom && mount -t cd9660 -o ro /dev/cd0a /cdrom && '
        'test "$(cat /cdrom/release)" = ' + release
    )


def preserved(g):
    g.command(
        'sha256 -c /root/removal.sha && stat -f "%u:%g:%Lp %N" ' + PRESERVE + ' | cmp - /root/removal.modes'
    )


def media_command(g, action, flags=''):
    # Surface the guest log when a check fails, and preserve the exit status.
    g.command(
        f'sh /cdrom/{action}.sh {flags} >/root/{action}-cycle.log 2>&1; '
        f'r=$?; tail -8 /root/{action}-cycle.log; test "$r" = 0',
        2400,
    )


def remove(g, release, colour):
    mount(g, release)
    g.command('/etc/rc.d/xdm stop && /etc/rc.d/xiri_famd stop')
    g.command(
        'test ! -e /etc/X11/xorg.conf && '
        'sed \'s/"NoAccel" "false"/"NoAccel" "true"/\' /usr/local/share/xiri/xorg.conf > /etc/X11/xorg.conf && '
        'echo xdm=YES >> /etc/rc.conf'
    )
    g.command(
        'su - xiritest -c '
        + shlex.quote(
            f'umask 077 && echo "{release}" > {NOTE} && echo "winterm*foreground: {colour}" >> {PREFS}'
        )
    )
    g.command(
        'echo "# local preference" >> /etc/xiri/session.conf && '
        'echo "site payload" > /emul/irix/site-note && '
        'echo "site font" > /usr/local/share/xiri/fonts/site-note && '
        'sha256 '
        + PRESERVE
        + ' > /root/removal.sha && stat -f "%u:%g:%Lp %N" '
        + PRESERVE
        + ' > /root/removal.modes'
    )
    g.command("printf 'site font\\nsite payload\\n' > /root/site-notes")
    g.command(
        'cd / && sha256 -q usr/sbin/rpcbind > /root/installed-rpc.sha && '
        'sha256 -q var/db/xiri-install/original/usr/sbin/rpcbind > /root/original-rpc.sha && '
        'cp -p /usr/sbin/rpcbind /usr/sbin/rpcbind.site && echo "# site adjustment" >> /usr/sbin/rpcbind.site && mv -f /usr/sbin/rpcbind.site /usr/sbin/rpcbind && sha256 -q /usr/sbin/rpcbind > /root/edited-rpc.sha'
    )
    g.command(
        'if sh /cdrom/uninstall.sh >/root/legacy-check 2>&1; then false; else '
        'grep -q "older receipt" /root/legacy-check && test -f ' + STATE + '/installed; fi',
        900,
    )
    media_command(g, 'uninstall', '--legacy-clean-indy')
    media_command(g, 'uninstall')
    g.command(
        'test ! -e ' + STATE + '/installed && test ! -e /usr/local/bin/xiri-session && '
        'test ! -L /usr/lib/desktop && test ! -e /emul/irix && test ! -e /usr/local/share/xiri/fonts && '
        'test "$(readlink ' + DRIVER + ')" = newport_drv.so.0 && '
        'test "$(sha256 -q /usr/sbin/rpcbind)" = "$(cat /root/original-rpc.sha)"'
    )
    g.command(
        'h=$(echo /var/db/xiri-install/history.*); test "$(sha256 -q "$h/edits/usr/sbin/rpcbind")" = '
        '"$(cat /root/edited-rpc.sha)" && while read t; do cat "$t/site-note"; done < "$h/trees" '
        '| sort | cmp - /root/site-notes',
        90,
    )
    preserved(g)
    return {
        'restored_driver': 'newport_drv.so.0',
        'rpcbind_backup_and_edit_verified': True,
        'vendor_and_font_additions_retained': True,
        'repeat_removal': True,
    }


def native(g, out, xdm, screenshot):
    preserved(g)
    xdm['greeter'](g)
    xdm['login'](g, 'netbsdtest')
    ctwm = "pgrep -u netbsdtest -f '^/usr/X11R7/bin/ctwm( |$)'"
    g.wait_for(ctwm + ' >/dev/null && xwininfo -root -tree | grep -q \'"UXTerm"\'', 160)
    info = g.read_text(
        """w=$(xwininfo -root -tree | awk '/"UXTerm"/ {print $1; exit}'); xwininfo -id "$w" """
    )
    x, y = (int(re.search('Absolute upper-left ' + axis + r':\s*(-?\d+)', info)[1]) for axis in 'XY')
    g.monitor(f'ptr click {x + 40} {y + 30} left')
    g.monitor('key type umask 077; pwd > recovery-note')
    g.monitor('key Return')
    g.wait_for('test -s ' + NATIVE_NOTE, 35)
    g.command(
        'test "$(cat ' + NATIVE_NOTE + ')" = /home/netbsdtest && '
        'test "$(stat -f %Su:%Lp ' + NATIVE_NOTE + ')" = netbsdtest:600'
    )
    digest = screenshot(g, out / 'ctwm.png')
    g.command('kill -TERM "$(' + ctwm + ')"')
    xdm['greeter'](g)
    return {
        'login': 'netbsdtest',
        'window_manager': 'ctwm',
        'mapped_terminal': 'UXTerm',
        'logout_to_xdm': True,
        'png_sha256': digest,
    }


def reinstall(g, release):
    mount(g, release)
    g.command('/etc/rc.d/xdm stop')
    # The alias already matches the package. The service file has site settings.
    g.command(
        'mkdir -p /usr/local/share/xiri /etc/rc.conf.d && '
        'ln -s /emul/irix/usr/lib/desktop /usr/lib/desktop && '
        'echo rpcbind=YES > /etc/rc.conf.d/rpcbind && sha256 /etc/rc.conf.d/rpcbind >/root/site-rc.sha'
    )
    media_command(g, 'install')
    g.command('test -d ' + STATE + '/created && test ! -d ' + STATE + '/created/usr/lib/desktop')
    g.command(
        '(sh /cdrom/uninstall.sh >/root/interrupt-remove.log 2>&1 & worker=$!; '
        'until test ! -d /emul/irix && test -s ' + STATE + '/removing; do '
        'kill -0 "$worker" || exit 1; sleep 1; done; kill -TERM "$worker" || exit 1; '
        'if wait "$worker"; then exit 1; fi; test -s ' + STATE + '/removing)',
        1200,
    )
    media_command(g, 'uninstall')
    g.command(
        'test "$(readlink /usr/lib/desktop)" = /emul/irix/usr/lib/desktop && '
        'sha256 -c /root/site-rc.sha && test ! -e /usr/local/bin/xiri-session && '
        'test "$(readlink ' + DRIVER + ')" = newport_drv.so.0'
    )
    media_command(g, 'install')
    g.command(
        'cmp ' + STATE + '/inputs ' + STATE + '/installed && '
        'test "$(sha256 -q /usr/sbin/rpcbind)" = "$(cat /root/installed-rpc.sha)" && '
        'test "$(cat ' + NATIVE_NOTE + ')" = /home/netbsdtest && sha256 -c /root/site-rc.sha'
    )
    preserved(g)
    return {
        'reinstalled': release,
        'tracked_removal': True,
        'interrupted_removal_resumed': True,
        'preexisting_alias_and_service_preserved': True,
    }
