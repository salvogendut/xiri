"""Verify the effective boot generation and both xdm sessions on a private Indy."""
import json
import shlex
import time

from xiri_lab import ROOT
from xiri_lab.mozilla_media import MODULE
from mozilla_lifecycle import open_browser, position, reboot

MOUNT = 'mkdir -p /cdrom && mount -rt cd9660 /dev/cd0a /cdrom'
RECORD = '/var/db/xiri-install'
PINS = json.loads((ROOT/'docs/results/2026-11-26-irix-utime.json').read_text())


def check_boot(guest, out, release, fixed, desktop):
    out.mkdir()
    cmd = guest.command
    module = PINS['module_sha256' if fixed else 'previous_module_sha256']
    cmd(f'test "$(sha256 -q {MODULE})" = {module} && modstat | grep -q "^compat_irix_o32 "')
    cmd('d=$(mktemp -d /var/tmp/xiri-wget.XXXXXX) && chmod 755 "$d" && mkdir "$d/cd" "$d/web" "$d/bin" && '
        'mount -rt cd9660 /dev/cd1a "$d/cd" && (cd "$d/bin" && tar xpf "$d/cd/wget.tar") && umount "$d/cd"')
    cmd('echo "Xiri test" >"$d/web/witness.txt" && TZ=UTC touch -t 200902132331.30 "$d/web/witness.txt" && '
        'test "$(stat -f %m "$d/web/witness.txt")" = 1234567890 && '
        'echo "<html><head><title>Xiri Indy timestamp check</title></head><body>Indy HTTP document</body></html>" >"$d/web/index.html"')
    cmd('/usr/libexec/httpd -f -n -i 127.0.0.1 -I 18373 "$d/web" >"$d/http.log" 2>&1 </dev/null & server=$!')
    guest.wait_for('ftp -o /dev/null http://127.0.0.1:18373/witness.txt >/dev/null 2>&1', 40)
    cmd('homefile=$(su - xiritest -c "mktemp -d") && chmod 755 "$homefile" && '
        f'test "$(sha256 -q "$d/bin/wget")" = {PINS["wget"]["sha256"]}')
    # Give wget its normal output path; -O handles timestamps differently.
    cmd('su - xiritest -c "cd \'$homefile\' && LD_LIBRARYN32_PATH=\'$d/bin\' \'$d/bin/wget\' '
        '-t 1 -T 15 http://127.0.0.1:18373/witness.txt" >"$d/client.log" 2>&1 && '
        'cmp "$homefile/witness.txt" "$d/web/witness.txt" && test "$(stat -f %Su "$homefile/witness.txt")" = xiritest')
    stamp = int(guest.read_text('stat -f %m "$homefile/witness.txt"').strip())
    log = guest.read_text('cat "$d/client.log"')
    if (stamp == 1234567890) != fixed or ('Function not implemented' in log) == fixed:
        raise ValueError(f'Unexpected wget result, mtime={stamp}: {log}')
    witness = {}
    def browser(g):
        title = 'Xiri Indy timestamp check'
        open_browser(g, release, 'Welcome to Xiri')
        x, y = position(g, 'Welcome to Xiri')
        g.monitor(f'ptr click {x+210} {y+170} left')
        g.monitor('key ctrl+l')
        g.monitor('key type http://127.0.0.1:18373/index.html')
        g.monitor('key Return')
        rendered = 'xwininfo -root -tree | grep -Fq "'+title+'"'
        if release == '6.5.22f' and not fixed:
            # Mozilla 1.0.1 sometimes restores a blank cached document after
            # rollback. Reload the entered URL once, as in mozilla_lifecycle.
            start = time.monotonic()
            while time.monotonic() - start < 25:
                if g.read_text('if '+rendered+'; then echo loaded; fi').strip() == 'loaded':
                    break
                time.sleep(1)
            else:
                g.monitor('key ctrl+shift+r')
                witness['reloaded'] = True
        g.wait_for(rendered, 120)
        witness['title'] = g.read_text('xwininfo -root -tree | grep -Fm1 "'+title+'"').strip()
        g.capture(out/'mozilla.png')
        g.monitor('key ctrl+q')
        g.wait_for('! pgrep -x mozilla-bin >/dev/null', 90)
    result = desktop(guest, out, while_logged_in=browser)
    cmd('kill "$server"; wait "$server" || :; rm -rf "$d" "$homefile"')
    return dict(module_sha256=module, mtime=stamp, bytes_match=True, owner='xiritest',
                wget_log=log.strip(), browser_title=witness['title'], desktop=result,
                browser_reloaded=witness.get('reloaded', False))


def check(guest, out, package, desktop, fresh):
    cmd = guest.command
    r = package['release']
    preserve = '/root/kernel-keep.sha'
    cmd(f'sha256 /etc/master.passwd /etc/group /etc/modules.conf /etc/rc.conf /etc/rc.conf.d/xiri_hosts '
        f'/usr/people/xiritest/.xsession >{preserve}')
    if fresh:
        cmd(f'grep -Fqx {shlex.quote(package["mozilla_receipt"])} {RECORD}/mozilla/identity && '
            f'grep -Fqx {shlex.quote(package["receipt"])} {RECORD}/installed && '
            f'! grep -Fq {MODULE} {RECORD}/mozilla/plan')
        result = check_boot(guest, out/'first-boot', r, True, desktop)
        cmd(f'sha256 /netbsd /netbsd.boot {MODULE} >/root/v6-boot.sha')
        cmd(MOUNT)
        for option in ('--remove-mozilla', '--mozilla'):
            cmd(f'sh /cdrom/install.sh {option} >/root/browser-component.log 2>&1; rc=$?; '
                'tail -5 /root/browser-component.log; test "$rc" = 0', 1800)
            cmd('sha256 -c /root/v6-boot.sha')
            if option == '--remove-mozilla':
                cmd(f'test ! -e {RECORD}/mozilla && test ! -e /emul/irix/var/netscape/mozilla/mozilla-bin')
        cmd(f'grep -Fqx {shlex.quote(package["mozilla_receipt"])} {RECORD}/mozilla/identity && sha256 -c {preserve}')
        result['browser_removed_and_reinstalled_with_same_boot_files'] = True
        return result
    result = {}
    cmd(f'cp -p {RECORD}/mozilla/plan /root/v5-plan && cp -p {RECORD}/mozilla/identity /root/v5-browser && '
        f'cp -p {RECORD}/installed /root/v5-desktop')
    for action, flag in [('updated',''), ('rolled-back',' --rollback')]:
        cmd(MOUNT)
        for attempt in ('first','repeat'):
            cmd('sh /cdrom/upgrade.sh'+flag+' >/root/kernel-update.log 2>&1; rc=$?; tail -5 /root/kernel-update.log; test "$rc" = 0', 1200)
            if attempt == 'repeat':
                cmd('grep -q "already installed" /root/kernel-update.log')
        if flag:
            cmd(f'cmp /root/v5-plan {RECORD}/mozilla/plan && cmp /root/v5-browser {RECORD}/mozilla/identity && '
                f'cmp /root/v5-desktop {RECORD}/installed')
        else:
            cmd(f'! grep -Fq {MODULE} {RECORD}/mozilla/plan && ! cmp -s /root/v5-desktop {RECORD}/installed')
        reboot(guest)
        cmd('sha256 -c '+preserve)
        result[action] = check_boot(guest, out/action, r, not flag, desktop)
    return result


def check_base(guest, package, greeter):
    """Round-trip a base-only installation whose v5 kernel also changes."""
    old = json.loads((ROOT/'profiles/netbsd-sgimips-indy-11.99.11-glx-v1.json').read_text())
    new = json.loads((ROOT/'profiles/netbsd-sgimips-indy-11.99.11-utime-v1.json').read_text())
    cmd = guest.command
    cmd(f'test ! -e {RECORD}/mozilla && grep -Fqx {shlex.quote(package["receipt"])} {RECORD}/installed')
    # The serial login is available while xdm is still starting on an R4400.
    greeter(guest)
    result = {}
    for stage, profile, flag in [('updated', new, ''), ('rolled-back', old, ' --rollback')]:
        cmd(MOUNT)
        cmd('sh /cdrom/upgrade.sh'+flag+' >/root/base-update.log 2>&1; rc=$?; '
            'tail -5 /root/base-update.log; test "$rc" = 0', 1200)
        reboot(guest)
        greeter(guest)
        for k in ('kernel', 'boot', 'module'):
            row = profile['artifacts'][k]
            cmd(f'test "$(sha256 -q {row["destination"]})" = {row["sha256"]}')
        cmd(f'modstat | grep -q "^compat_irix_o32 " && test ! -e {RECORD}/mozilla')
        result[stage] = dict(kernel=guest.read_text('sysctl -n kern.version').strip(),
                             module_sha256=profile['artifacts']['module']['sha256'], xdm=True,
                             receipt=guest.read_text(f'cat {RECORD}/installed').strip())
    if result['updated']['kernel'] == result['rolled-back']['kernel'] or result['rolled-back']['receipt'] != package['receipt']:
        raise ValueError('The base Indy did not restore the original kernel and receipt')
    return result
