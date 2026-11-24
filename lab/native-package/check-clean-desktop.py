#!/usr/bin/env python3
"""Install one release on a new clone of the clean bootstrap and exercise both xdm sessions."""

import argparse
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import Guest, load_probe, sha256


def install(guest, release):
    cmd = guest.command
    cmd(
        'mkdir -p /cdrom && mount -t cd9660 -o ro /dev/cd0a /cdrom && test "$(cat /cdrom/release)" = '
        + release
    )
    cmd('test ! -e /emul/irix && test ! -e /usr/local/bin/xiri-desktop && test ! -e /usr/people/xiritest')
    cmd(
        'mkdir -p /usr/people /home && groupadd -g 1234 xiritest && '
        'useradd -m -g xiritest -u 1234 -d /usr/people/xiritest -s /bin/ksh -p "$(pwhash -b 6 xiritest)" xiritest && '
        'groupadd -g 1236 netbsdtest && useradd -m -g netbsdtest -u 1236 -G wheel -d /home/netbsdtest '
        '-s /bin/sh -p "$(pwhash -b 6 netbsdtest)" netbsdtest'
    )
    cmd('getent hosts "$(hostname)" >/dev/null || printf "127.0.0.1 %s\\n" "$(hostname)" >> /etc/hosts')
    cmd(
        "sed '/^ttyE0[[:space:]]/s/[[:space:]]on[[:space:]]/ off /; "
        "/^ttyZ0[[:space:]]/s/[[:space:]]off[[:space:]]/ on /' /etc/ttys > /etc/ttys.xiri && mv /etc/ttys.xiri /etc/ttys"
    )
    # Force a real activation failure after both trees have been published.
    # Creating a conflicting regular file must preserve that file and allow recovery.
    cmd(
        'mkdir -p /etc/xiri && echo "# site setting" > /etc/xiri/session.conf && '
        'echo "! user preference" > /usr/people/xiritest/.Xresources && chown xiritest:xiritest /usr/people/xiritest/.Xresources && '
        'test ! -e /usr/lib/desktop && echo "conflict witness" > /usr/lib/desktop'
    )
    paths = '/etc/passwd /etc/master.passwd /etc/group /etc/ttys /etc/hosts /etc/modules.conf /etc/rc.conf /usr/people/xiritest/.Xresources'
    cmd('sha256 ' + paths + ' > /root/clean-preserve.sha')
    cmd(
        '(sh /cdrom/install.sh >/root/clean-interrupt.log 2>&1 & worker=$!; '
        'until test -s /var/db/xiri-install/inputs; do kill -0 "$worker" || { tail /root/clean-interrupt.log; exit 1; }; sleep 1; done; '
        'kill -TERM "$worker" || exit 1; if wait "$worker"; then exit 1; fi; test ! -e /var/db/xiri-install/installed)',
        1200,
    )
    failure = 'sh /cdrom/install.sh > /root/clean-first.log 2>&1'
    cmd(
        'if '
        + failure
        + '; then false; else tail -12 /root/clean-first.log; grep -q "conflicting /usr/lib/desktop" '
        '/root/clean-first.log && grep -qx "conflict witness" /usr/lib/desktop && test ! -e /var/db/xiri-install/installed; fi',
        1800,
    )
    cmd(
        'rm /usr/lib/desktop && cat /etc/xiri/session.conf.example >> /etc/xiri/session.conf && '
        'sha256 /etc/xiri/session.conf >> /root/clean-preserve.sha'
    )
    for stage in ('resume', 'repeat'):
        cmd(
            'sh /cdrom/install.sh > /root/clean-'
            + stage
            + '.log 2>&1; r=$?; tail -12 /root/clean-'
            + stage
            + '.log; test "$r" = 0',
            1800,
        )
        cmd(
            'sha256 -c /root/clean-preserve.sha && cmp /var/db/xiri-install/inputs /var/db/xiri-install/installed'
        )
        if stage == 'resume':
            cmd(
                'install -o xiritest -g xiritest -m 700 /usr/local/share/xiri/xdm.xsession /usr/people/xiritest/.xsession && '
                'sha256 /usr/people/xiritest/.xsession /etc/rc.conf.d/xdm >> /root/clean-preserve.sha'
            )
    cmd('test ! -e /home/netbsdtest/.xsession && id -Gn netbsdtest | tr " " "\\n" | grep -qx wheel')
    return dict(
        release=release,
        receipts=guest.read_text('cat /var/db/xiri-install/installed').strip(),
        preserved=guest.read_text('cat /root/clean-preserve.sha').splitlines(),
        terminated_mid_install=True,
        original_conflict_preserved=True,
        resumed=True,
        repeated=True,
    )


def greeter(guest):
    guest.command('export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/X11R7/bin DISPLAY=:0')
    guest.wait_for('test -s /tmp/.X0-lock', 180)
    # Native NetBSD Xservers invokes the X symlink; the Xiri configuration names Xorg.
    authority = """$(ps -axww -o args= | awk '$1 ~ /^\\/usr\\/X11R7\\/bin\\/X(org)?$/ && $2 == ":0" {for(i=1;i<NF;i++) if($i=="-auth") print $(i+1)}')"""
    guest.wait_for('test -s "' + authority + '"', 90)
    guest.command('export XAUTHORITY=' + authority + '; test -s "$XAUTHORITY"')
    guest.wait_for("xwininfo -root -tree | grep -q '\"xlogin\"'", 150)


def login(guest, user):
    for command in ('key type ' + user, 'key Return', 'key type ' + user, 'key Return'):
        guest.monitor(command)


def desktop(guest, out, colour=None, while_logged_in=None):
    greeter(guest)
    guest.command('grep -Fq \'Option "NoAccel" "false"\' /usr/local/share/xiri/xorg.conf')
    acceleration = guest.read_text("grep -Ei 'NEWPORT.*(NoAccel|accel)|using.*XAA' /var/log/Xorg.0.log").strip()
    guest.command(
        'sysctl -n kern.consdev | grep ttyE0 && tty | grep ttyZ0 && /etc/rc.d/xiri_famd status && '
        '/etc/rc.d/rpcbind status && test -f /var/run/xiri-pty-ready'
    )
    session_dir = 'sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors 2>/dev/null | tail -1'
    guest.command('prior_job=$(' + session_dir + ')')
    login(guest, 'xiritest')
    guest.wait_for('job=$(' + session_dir + ') && test -n "$job" && test "$job" != "$prior_job" && test -s "$job/identity"', 240)
    guest.command(
        'job=$(' + session_dir + '); '
        'XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
        'test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; export DISPLAY=127.0.0.1:0 XAUTHORITY'
    )
    guest.wait_for('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready', 180)
    guest.wait_for("xwininfo -root -tree | grep -q 'Icon Catalog:'", 180)
    tree = guest.read_text('xwininfo -root -tree')
    for window in ('Icon Catalog:', 'Toolchest', 'winterm', 'xclock'):
        if window not in tree:
            raise RuntimeError('missing desktop window: ' + window)
    dimensions = guest.read_text('xdpyinfo | grep dimensions:').strip()
    if '1280x1024 pixels' not in dimensions:
        raise RuntimeError(dimensions)
    if colour:
        guest.command("xrdb -query | awk '$1 == \"winterm*foreground:\" && $2 == \"" + colour + "\" {ok=1} END {exit !ok}'")
    identity = guest.read_text('cat "$job/identity"').strip()
    if 'user=xiritest ' not in identity or 'home=/usr/people/xiritest cwd=/usr/people/xiritest ' not in identity:
        raise RuntimeError('unexpected desktop identity: ' + identity)
    handoff = guest.read_text('cat "$job/handoff"').strip()
    guest.command('test -s /usr/local/share/xiri/toolchest.chestrc && '
                  'grep -Fq /usr/local/bin/xiri-logout /usr/local/share/xiri/toolchest.chestrc')
    guest.command("su -m xiritest -c '/emul/irix/bin/sh -c \"echo IRIX_SHELL_OK\"' | grep -qx IRIX_SHELL_OK")
    guest.monitor('disp compositor gl')
    guest.monitor('screen wait 500 10000')
    guest.monitor('screen shot ' + str(out / 'desktop.png'))
    if while_logged_in:
        while_logged_in(guest)
    guest.command('su -m xiritest -c "env XIRI_SESSION_DIR=\'$job\' /usr/local/bin/xiri-logout"')
    greeter(guest)
    login(guest, 'netbsdtest')
    ctwm = "pgrep -u netbsdtest -f '^/usr/X11R7/bin/ctwm( |$)'"
    guest.wait_for(ctwm + ' >/dev/null', 120)
    guest.wait_for("xwininfo -root -tree | grep -q '\"UXTerm\"'", 120)
    native_processes = guest.read_text('ps -U netbsdtest -o pid,comm').strip()
    guest.monitor('screen wait 500 10000')
    guest.monitor('screen shot ' + str(out / 'ctwm.png'))
    guest.command('kill -TERM "$(' + ctwm + ')"')
    greeter(guest)
    return dict(
        identity=identity,
        winterm_handoff=handoff,
        dimensions=dimensions,
        newport_log=acceleration,
        windows=['Toolchest', 'Icon Catalog', 'winterm', 'xclock'],
        original_shell=True,
        native_session='ctwm + xterm',
        native_processes=native_processes,
        both_logouts=True,
        desktop_png_sha256=sha256(out / 'desktop.png'),
        ctwm_png_sha256=sha256(out / 'ctwm.png'),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('install', 'desktop'))
    for name in ('base', 'media', 'emulator', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--release', choices=('6.5.22f', '6.5.30f'), required=True)
    parser.add_argument('--bundle', type=Path, help='test a copy of a packaged CHD and its graphical PROM')
    parser.add_argument('--kernel', type=Path, help='matching unstripped kernel for the graphical halt check')
    args = parser.parse_args()
    base, medium, emu, out = (p.resolve() for p in (args.base, args.media, args.emulator, args.output))
    os.environ.pop('IRIS_CHD_DIFF_DIR', None)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    out.mkdir(parents=True, exist_ok=True)
    run = out / args.phase
    run.mkdir()
    disk = out / 'disk.raw'
    install_phase = args.phase == 'install'
    if install_phase:
        if disk.exists() or not json.loads((base / 'result.json').read_text())['passed']:
            raise ValueError('expected a new target and a qualified bootstrap')
        subprocess.run(['cp', '--reflink=auto', '--sparse=always', base / 'disk.raw', disk], check=True)
    if not install_phase and (not args.bundle or not args.kernel):
        parser.error('desktop requires --bundle and --kernel')
    bundle = args.bundle.resolve() if args.bundle else None
    if not install_phase:
        package = json.loads((bundle / 'manifest.json').read_text())
        if (
            package['release'] != args.release
            or sha256(bundle / 'netbsd-xiri.chd') != package['chd_sha256']
            or sha256(bundle / 'nvram.bin') != package['nvram_sha256']
            or sha256(emu / 'iris') != package['iris_sha256']
            or sha256(args.kernel)
            != json.loads((base / 'result.json').read_text())['native_sha256']['netbsd']
        ):
            raise ValueError('desktop test inputs differ from the packaged installation')
        disk = run / 'check.chd'
        subprocess.run(['cp', '--reflink=auto', bundle / 'netbsd-xiri.chd', disk], check=True)
    shutil.copyfile((base if install_phase else bundle) / 'nvram.bin', run / 'nvram.bin')
    cpu = 'r4400' if args.release == '6.5.22f' else 'r5000'
    cache = 'cache = "shadow"\n' if cpu == 'r5000' else ''
    config = (
        'ci = true\nno_audio = true\nscsi_deferred_int = true\nbanks = [128,128,0,0]\n'
        f'[machine]\nprofile = "indy_ip24"\ncpu = "{cpu}"\n'
        + cache
        + '[graphics]\nboard = "newport"\n[scsi.1]\noverlay = false\npath = '
        + json.dumps(str(disk))
        + '\n'
    )
    if not install_phase:
        config = config.replace('overlay = false', 'overlay = true')
    if install_phase:
        config += '[scsi.4]\ncdrom = true\npath = ' + json.dumps(str(medium)) + '\n'
    probe = load_probe()
    if install_phase:
        probe.TOOLBOX = []
    probe.IRIS, probe.CI = emu / 'iris', emu / 'iris-ci'
    lab = probe.Lab(
        SimpleNamespace(mode='ci' if install_phase else 'ordinary', debugger=False),
        run,
        config_text=config,
        working_directory=out,
        scsi1_from_config=True,
    )
    guest = Guest(lab)
    result = dict(release=args.release, cpu=cpu, iso_sha256=sha256(medium), iris_sha256=sha256(emu / 'iris'))
    if not install_phase:
        result['chd_sha256'] = package['chd_sha256']
        from xiri_lab.kernel_log import KernelLog

        symbols = subprocess.check_output(['nm', '-n', args.kernel], text=True)
        address = next(int(line.split()[0], 16) for line in symbols.splitlines() if line.endswith(' msgbufp'))
        console = KernelLog(lab, address)
    try:
        lab.start(boot=False)
        lab.wait('login: ', 600)
        lab.send('root')
        lab.wait('xiri-indy# ', 40)
        lab.logged_in = True
        result['checks'] = install(guest, args.release) if install_phase else desktop(guest, run)
        if install_phase:
            lab.send('shutdown -h now')
            lab.wait('unmounting done', 120)
            lab.wait(r'Option\?', 45)
            lab.clean_shutdown = True
            lab.logged_in = False
            lab.send('5')
            lab.wait('>> ', 20)
            lab.send('setenv -f console g')
            lab.wait('>> ', 20)
            lab.ci('rtc-save')
            shutil.copyfile(run / 'nvram.bin', out / 'nvram.bin')
        else:
            console.halt()
    except BaseException as error:
        result['error'] = str(error)
        if not install_phase and lab.logged_in:
            try:
                diagnostics = guest.read_text(
                    'tail -50 /var/log/xdm.log /var/log/xdm-errors /var/log/Xorg.0.log '
                    '/usr/people/xiritest/.xsession-errors /usr/people/xiritest/.xiri/sessions/session.*/*.log '
                    '/usr/people/xiritest/.xiri/sessions/session.*/*.err; '
                    'cat /etc/ttys | grep -E "^(console|ttyE0|ttyZ0)"; ps axww'
                )
                (run / 'guest-diagnostics.txt').write_text(diagnostics)
                console.halt()
            except Exception as diagnostic_error:
                result['diagnostic_error'] = str(diagnostic_error)
        raise
    finally:
        lab.close()
        result.update(
            halted=lab.clean_shutdown, stopped=lab.process is None or lab.process.poll() is not None
        )
        (run / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
