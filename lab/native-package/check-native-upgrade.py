"""Guest checks for check-kernel-rollback.py --upgrade-media."""

import runpy
import shlex
from pathlib import Path

media = runpy.run_path(str(Path(__file__).with_name('check-desktop-removal.py')))
HELPER = '/usr/local/sbin/xiri-sync-users'
STATE = '/var/db/xiri-install'
PRESERVE = (
    '/etc/master.passwd /etc/passwd /etc/group /etc/modules.conf /etc/rc.conf.d/xdm '
    '/etc/xiri/session.conf /usr/people/xiritest/.Xresources /usr/people/xiritest/.xsession '
    '/home/netbsdtest/upgrade-note /emul/irix/site-note /emul/irix/bin/sh '
    '/usr/local/share/xiri/fonts/site-note /var/db/xiri-install/original/usr/sbin/rpcbind'
)


def check(g, phase, release, colour, out, xdm):
    media['mount'](g, release)
    g.command(f's={STATE}; helper={HELPER}')
    if phase == 'upgrade':
        g.command('cp -p "$helper" /root/helper.old && cp "$s/installed" /root/receipt.old')
        g.command("su - xiritest -c " + shlex.quote(f"echo 'winterm*foreground: {colour}' >> ~/.Xresources"))
        g.command("su - netbsdtest -c 'umask 077 && echo native > ~/upgrade-note' && "
                  "echo '# local preference' >> /etc/xiri/session.conf && echo app > /emul/irix/site-note && "
                  "echo font > /usr/local/share/xiri/fonts/site-note")
        g.command('sha256 ' + PRESERVE + ' > /root/upgrade.sha && stat -f "%i:%u:%g:%Lp %N" '
                  + PRESERVE + ' > /root/upgrade.stat')
        # A conflicting site edit must survive an attempted update.
        g.command('echo "# owner edit" >> "$helper" && if sh /cdrom/upgrade.sh >/root/conflict.log 2>&1; '
                  'then false; else grep -q "local change at" /root/conflict.log && grep -q "owner edit" "$helper" '
                  '&& test ! -e "$s/upgrading" && cp -p /root/helper.old "$helper"; fi', 1200)
        # Signal the real shell at the first sync after the helper's atomic rename.
        # The shell runs the production script unchanged from the verified CD.
        interrupted = ('sync() { command sync; if ! cmp -s "$helper" /root/helper.old; then kill -TERM "$$"; fi; }; '
                       '. /cdrom/upgrade.sh')
        g.command('export helper; if sh -c ' + shlex.quote(interrupted) + ' /cdrom/upgrade.sh >/root/interrupted.log 2>&1; '
                  'then false; else test -s "$s/upgrading" && ! cmp -s "$helper" /root/helper.old && '
                  'cmp -s "$s/installed" /root/receipt.old; fi', 1200)
        media['media_command'](g, 'upgrade')
        media['media_command'](g, 'upgrade')
        g.command('test ! -e "$s/upgrading" && cp "$s/installed" /root/receipt.new && '
                  '! cmp -s /root/receipt.old /root/receipt.new')
    else:
        new = phase == 'upgraded'
        receipt = '/root/receipt.' + ('new' if new else 'old')
        g.command('(for f in "$s"/installed "$s"/inputs /emul/irix/.xiri-install-inputs '
                  '/usr/local/share/xiri/fonts/.xiri-install-inputs; do cmp "$f" ' + receipt + ' || exit 1; done)')
        g.command('cd /emul/irix/etc && "$helper" && stat -f %i passwd group > /root/account-inodes && "$helper" && '
                  'stat -f %i passwd group > /root/account-again && '
                  + ('cmp' if new else '! cmp -s') + ' /root/account-inodes /root/account-again && cd /root')
        if new:
            g.command('(cd /emul/irix/etc && cp group /root/group.ref && echo obsolete >> group && "$helper" && '
                      'cmp group /root/group.ref && test "$(stat -f %i passwd)" = "$(head -1 /root/account-inodes)")')
        result = xdm['desktop'](g, out, colour=colour)
        if new:
            media['media_command'](g, 'upgrade', '--rollback')
            media['media_command'](g, 'upgrade', '--rollback')
        g.command('cmp "$helper" /root/helper.old && cmp "$s/installed" /root/receipt.old')
    g.command('sha256 -c /root/upgrade.sha && stat -f "%i:%u:%g:%Lp %N" ' + PRESERVE + ' | cmp - /root/upgrade.stat')
    if phase == 'upgrade':
        return dict(local_edit_refused=True, interrupted_after_helper_replaced=True, resumed=True,
                    original_receipt=g.read_text('cat /root/receipt.old').strip(),
                    upgraded_receipt=g.read_text('cat /root/receipt.new').strip())
    return dict(desktop=result, unchanged_account_inodes=new, applied_colour=colour, preserved=PRESERVE.split())
