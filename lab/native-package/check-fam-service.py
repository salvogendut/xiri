"""Indy v3/v4 FAM upgrade and rollback, including a vendor File Manager socket read."""

from pathlib import Path
import re
import runpy
import shlex
import struct

prior = runpy.run_path(str(Path(__file__).with_name('check-helper-inventory.py')))
media = prior['media']
SCRIPT = '/etc/rc.d/xiri_famd'
EXAMPLE = '/usr/local/share/xiri/examples/rc.conf.d/xiri_famd'
SITE = '/var/log/xiri fam site.log'
DEFAULT = '/var/log/xiri-fam.log'
MARKER = 'xiri-fam-notification.txt'
PRESERVED = ('/etc/rc.conf.d/xiri_famd /etc/xiri/fam.conf /etc/rc.conf /etc/modules.conf '
             '/usr/people/xiritest/.Xresources /usr/people/xiritest/.xsession /etc/master.passwd')


def verify_log(g, path):
    g.command('log=' + shlex.quote(path) + '; pid=$(cat /var/run/xiri_famd.pid); '
              'kill -0 "$pid" && awk -v msg="famd[$pid]: log level is LOG_DEBUG" '
              '\'$0=="append-witness"{seen=1; started=0} seen && index($0,msg){started=1} '
              'END{exit !started}\' "$log"')


def client_events(data, pid, request):
    """Decode reads by this fm PID from the big-endian LP64 v2 trace."""
    pos = 0
    reads = {}
    while pos < len(data):
        if len(data) - pos < 56:
            raise ValueError('short ktrace header')
        size, version, kind, owner = struct.unpack_from('>IHHI', data, pos)
        comm = data[pos+12:pos+29].split(b'\0')[0]
        pos += 56
        if version != 2 or pos + size > len(data):
            raise ValueError('invalid ktrace record')
        if kind == 4 and owner == pid and comm == b'fm':
            fd, direction = struct.unpack_from('>II', data, pos)
            if direction == 0:
                reads.setdefault(fd, bytearray()).extend(data[pos+8:pos+size])
        pos += size
    packets = []
    for code in ('F', 'A'):
        payload = f'{code}{request} {MARKER}\n\0'.encode()
        packets.append(struct.pack('>I', len(payload)) + payload)
    for fd, stream in reads.items():
        first = stream.find(packets[0])
        if first >= 0 and stream.find(packets[1], first + len(packets[0])) >= 0:
            return dict(pid=pid, process='fm', descriptor=fd, request=request,
                        filename=MARKER, received=['Created', 'Deleted'])
    raise ValueError('IRIX fm did not read both framed FAM events on the same descriptor')


def notification(g, out):
    g.command('watch=$(su - xiritest -c \'mktemp -d "$HOME/FamCheck.XXXXXX"\') && test -d "$watch"')
    g.command('su -m xiritest -c "cd /usr/people/xiritest && HOME=/usr/people/xiritest '
              '/emul/irix/usr/sbin/fm $watch" >/tmp/fm-check.log 2>&1 </dev/null & fmlaunch=$!')
    g.wait_for(r'xwininfo -root -tree | grep -Fq "\"xiri-indy:$watch\""')
    g.wait_for(r'grep -F "\"$watch\" EndExist" "$log" | grep -q ImdFileMonitor_')
    subscription = g.read_text(r'grep -F "monitor dir \"$watch\"" "$log" | tail -1').strip()
    match = re.search(r'ImdFileMonitor_(\d+) said: request (\d+) monitor dir', subscription)
    if not match:
        raise ValueError('missing original File Manager subscription: ' + subscription)
    pid, request = map(int, match.groups())
    g.command(f'ps -p {pid} -o comm= | grep -qw fm && ktrace -v 2 -t i -f /root/fm.trace -p {pid}')
    for verb, event in [('touch', 'Created'), ('rm', 'Deleted')]:
        g.command(f'{verb} "$watch/{MARKER}"')
        g.wait_for(f'grep -Fq \'ImdFileMonitor_{pid}: request {request} "{MARKER}" {event}\' "$log"', 60)
    g.command(f'sleep 2 && ktrace -c -p {pid}')
    trace = g.read('cat /root/fm.trace')
    result = client_events(trace, pid, request)
    (out / 'fm.ktrace').write_bytes(trace)
    g.command(f'kill -TERM {pid} && rmdir "$watch"')
    return result


def migrate(g, rollback=False):
    side, other = ('old', 'new') if rollback else ('new', 'old')
    flags = '--rollback' if rollback else ''
    # Stop immediately after the real rename of the rc.d script. The other
    # file and the installed receipt must still be from the source package.
    intercept = ('mv() { command mv "$@" || return; '
                 'if test "$#" = 3 && test "$3" = "$script"; then kill -TERM "$$"; fi; }; . /cdrom/upgrade.sh')
    g.command('if sh -c ' + shlex.quote(intercept) + ' /cdrom/upgrade.sh ' + flags +
              ' >/root/interrupted.log 2>&1; then false; else test -s "$s/upgrading" && '
              f'cmp "$script" "/root/delta/{side}/root$script" && cmp "$example" "/root/delta/{other}/root$example" && '
              f'cmp "$s/installed" /root/receipt.{other}; fi', 1200)
    media['media_command'](g, 'upgrade', flags)
    media['media_command'](g, 'upgrade', flags)
    g.command('test ! -e "$s/upgrading" && '
              f'cmp "$script" "/root/delta/{side}/root$script" && cmp "$example" "/root/delta/{side}/root$example"')


def check(g, phase, release, colour, out, xdm):
    media['mount'](g, release)
    g.command(f'export s={prior["STATE"]} script={SCRIPT} example={EXAMPLE}')
    if phase == 'upgrade':
        g.command('mkdir /prev && mount -t cd9660 -o ro /dev/cd1a /prev && test "$(cat /prev/release)" = ' +
                  release + ' && sh /prev/upgrade.sh --legacy-clean-indy >/root/base.log 2>&1', 1200)
        setting = 'if test -f /etc/xiri/use-site-log; then xiri_famd_logfile="' + SITE + '"; fi'
        g.command('echo ' + shlex.quote(setting) + ' >>/etc/rc.conf.d/xiri_famd && '
                  "echo '# site FAM policy' >>/etc/xiri/fam.conf && "
                  'su - xiritest -c ' + shlex.quote(f"echo 'winterm*foreground: {colour}' >> ~/.Xresources"))
        g.command('sha256 ' + PRESERVED + ' >/root/site.sha && stat -f "%i:%u:%g:%Lp %N" ' + PRESERVED +
                  ' >/root/site.stat && cp "$s/installed" /root/receipt.old && '
                  'mkdir /root/delta && (cd /root/delta && pax -rz -f /cdrom/delta.tgz)')
        g.command('initial=$(cat /var/run/xiri_famd.pid); echo "# local startup" >>"$script"')
        prior['refuse'](g, 'sh /cdrom/upgrade.sh', 'local change at ' + SCRIPT,
                        'test ! -e "$s/upgrading" && grep -Fxq "# local startup" "$script" && '
                        'cmp "$example" "/root/delta/old/root$example" && cmp "$s/installed" /root/receipt.old')
        g.command('cat "/root/delta/old/root$script" >"$script"')
        migrate(g)
        g.command('cp "$s/installed" /root/receipt.new && test "$initial" = "$(cat /var/run/xiri_famd.pid)" && '
                  'kill -0 "$initial" && echo append-witness >>/var/log/xiri-fam.log && /etc/rc.d/xiri_famd restart')
        verify_log(g, DEFAULT)
        g.command('touch /etc/xiri/use-site-log && echo append-witness >' + shlex.quote(SITE))
        result = dict(edited_script_refused=True, interrupted_between_files=True, resumed=True,
                      service_pid_preserved=True, v4_default=DEFAULT)
    else:
        new = phase == 'upgraded'
        path = SITE if new else DEFAULT
        side = 'new' if new else 'old'
        g.command(f'(for file in "$s"/installed "$s"/inputs /emul/irix/.xiri-install-inputs '
                  f'/usr/local/share/xiri/fonts/.xiri-install-inputs; do cmp "$file" /root/receipt.{side} || exit 1; done)')
        verify_log(g, path)
        g.command('test -f /etc/xiri/use-site-log && head -1 ' + shlex.quote(SITE) + ' | grep -qx append-witness')
        result = dict(logfile=path)
        def observe(guest):
            result['notification'] = notification(guest, out)
        result['desktop'] = xdm['desktop'](g, out, colour=colour, while_logged_in=observe)
        if new:
            migrate(g, rollback=True)
            g.command('echo append-witness >>/var/log/xiri-fam.log')
            result['rollback_interrupted_and_resumed'] = True
    g.command('sha256 -c /root/site.sha && stat -f "%i:%u:%g:%Lp %N" ' + PRESERVED + ' | cmp - /root/site.stat')
    return result
