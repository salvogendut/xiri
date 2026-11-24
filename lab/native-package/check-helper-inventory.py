"""Exercise a real add, caller update and retirement using the previous and candidate CDs."""

import runpy
import shlex
from pathlib import Path

prior = runpy.run_path(str(Path(__file__).with_name('check-native-upgrade.py')))
media = prior['media']
STATE = prior['STATE']
PRESERVE = prior['PRESERVE']
ADD = '/usr/local/bin/xiri-account-map'
RETIRE = '/usr/local/libexec/xiri/account-map.awk'


def refuse(g, command, reason, checks):
    g.command('if ' + command + ' >/root/conflict.log 2>&1; then false; else grep -Fq '
              + shlex.quote(reason) + ' /root/conflict.log && ' + checks + '; fi', 1200)


def interrupt(g, flags, condition):
    # Send TERM at a real sync after the new caller is live, before retirement.
    wrapper = 'sync() { command sync; if ' + condition + '; then kill -TERM "$$"; fi; }; . /cdrom/upgrade.sh'
    g.command('if sh -c ' + shlex.quote(wrapper) + ' /cdrom/upgrade.sh ' + flags
              + ' >/root/interrupted.log 2>&1; then false; else test -s "$s/upgrading" && '
              + condition + '; fi', 1200)


def initialize(g, release, colour, tracked):
    g.command('mkdir -p /prev && mount -t cd9660 -o ro /dev/cd1a /prev && test "$(cat /prev/release)" = ' + release)
    g.command('sh /prev/upgrade.sh >/root/base.log 2>&1', 1200)
    if tracked:
        g.command('/etc/rc.d/xdm stop && /etc/rc.d/xiri_famd stop && '
                  'sh /prev/uninstall.sh --legacy-clean-indy >>/root/base.log 2>&1', 2400)
        g.command('test ! -e "$retire" && echo "original site mapper" >/root/site-map && '
                  'install -m 440 /root/site-map "$retire" && sh /prev/install.sh >>/root/base.log 2>&1 && '
                  'test -d "$s/created" && cmp "$s/original$retire" /root/site-map', 2400)
    g.command('cp -p "$helper" /root/old-sync && cp -p "$retire" /root/old-map && cp "$s/installed" /root/receipt.old')
    g.command("su - xiritest -c " + shlex.quote(f"echo 'winterm*foreground: {colour}' >> ~/.Xresources"))
    g.command("su - netbsdtest -c 'umask 077 && echo native > ~/upgrade-note' && "
              "echo '# local layout preference' >> /etc/xiri/session.conf && echo app > /emul/irix/site-note && "
              "echo font > /usr/local/share/xiri/fonts/site-note")
    g.command('sha256 ' + PRESERVE + ' >/root/layout.sha && stat -f "%i:%u:%g:%Lp %N" ' + PRESERVE + ' >/root/layout.stat')


def check(g, phase, release, colour, out, xdm):
    tracked = release == '6.5.30f'
    flags = '' if tracked else '--legacy-clean-indy'
    command = 'sh /cdrom/upgrade.sh ' + flags
    g.command(f's={STATE}; add={ADD}; retire={RETIRE}; helper={prior["HELPER"]}; export s add retire helper')
    media['mount'](g, release)
    evidence = {}
    if phase == 'upgrade':
        initialize(g, release, colour, tracked)
        # Even byte-identical executable files are local collisions on a new name.
        g.command('mkdir /root/delta && (cd /root/delta && pax -rz -f /cdrom/delta.tgz) && '
                  'install -m 555 "/root/delta/new/root$add" "$add" && stat -f %i "$add" >/root/collision-inode')
        unchanged = 'test ! -e "$s/upgrading" && cmp "$s/installed" /root/receipt.old && cmp "$helper" /root/old-sync'
        refuse(g, command, 'occupied helper path', unchanged + ' && test "$(stat -f %i "$add")" = "$(cat /root/collision-inode)"')
        g.command('rm "$add" && ln -s /no-such-xiri-file "$add"')
        refuse(g, command, 'occupied helper path', unchanged + ' && test "$(readlink "$add")" = /no-such-xiri-file')
        g.command('rm "$add" && echo "# local" >>"$retire"')
        refuse(g, command, 'local change at', unchanged + ' && test ! -e "$add" && grep -qx "# local" "$retire"')
        g.command('cp -p /root/old-map "$retire"')
        if not tracked:
            refuse(g, 'sh /cdrom/upgrade.sh', 'unknown ownership', unchanged)
        interrupt(g, flags, 'test -x "$add" && ! cmp -s "$helper" /root/old-sync && cmp -s "$retire" /root/old-map')
        g.command('cmp "$s/installed" /root/receipt.old && "$helper"')
        media['media_command'](g, 'upgrade', flags)
        media['media_command'](g, 'upgrade', flags)
        g.command('cp "$s/installed" /root/receipt.new && ! cmp -s /root/receipt.old /root/receipt.new')
        evidence.update(collision_refused=['identical executable', 'dangling symlink'], edited_retirement_refused=True,
                        interrupted_before_retirement=True, resumed=True,
                        before=g.read_text('cat /root/receipt.old').strip(), after=g.read_text('cat /root/receipt.new').strip())
    else:
        new = phase == 'upgraded'
        receipt = '/root/receipt.' + ('new' if new else 'old')
        g.command('(for f in "$s"/installed "$s"/inputs /emul/irix/.xiri-install-inputs '
                  '/usr/local/share/xiri/fonts/.xiri-install-inputs; do cmp "$f" ' + receipt + ' || exit 1; done)')
        if new:
            g.command('test -x "$add" && "$helper" && getent passwd | "$add" passwd | cmp - /emul/irix/etc/passwd && '
                      'getent group | "$add" group | cmp - /emul/irix/etc/group')
            if tracked:
                g.command('cmp "$retire" /root/site-map && test "$(stat -f %u:%g:%Lp "$retire")" = 0:0:440 && test -d "$s/created$add"')
            else:
                g.command('test ! -e "$retire" && test ! -L "$retire"')
        else:
            g.command('test ! -e "$add" && test ! -L "$add" && cmp "$retire" /root/old-map && '
                      'cmp "$helper" /root/old-sync && "$helper" && test ! -e "$s/created$add"')
        evidence['desktop'] = xdm['desktop'](g, out, colour=colour)
        if new:
            reverse = '--rollback ' + flags
            interrupt(g, reverse, 'test -x "$add" && cmp -s "$helper" /root/old-sync && cmp -s "$retire" /root/old-map')
            g.command('cmp "$s/installed" /root/receipt.new && "$helper"')
            media['media_command'](g, 'upgrade', reverse)
            media['media_command'](g, 'upgrade', reverse)
            evidence['rollback_interrupted_and_resumed'] = True
    g.command('test ! -e "$s/upgrading" && sha256 -c /root/layout.sha && stat -f "%i:%u:%g:%Lp %N" '
              + PRESERVE + ' | cmp - /root/layout.stat')
    evidence['ownership'] = 'tracked with site original' if tracked else 'legacy clean Indy'
    return evidence
