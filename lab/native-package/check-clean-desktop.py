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
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import Guest, load_probe, sha256


def prepare_install(guest, release):
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


def install(guest, release):
    cmd = guest.command
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


def disk_full(guest, run, target):
    guest.command('mkdir /fixture && mount -t cd9660 -o ro /dev/cd1a /fixture')
    try:
        guest.command(f'sh /fixture/disk-full.sh {target} >/root/space-result.log 2>&1; status=$?; '
                      'tail -12 /root/space-result.log; test "$status" = 0', 3600)
    finally:
        (run / 'space.log').write_text(guest.read_text(
            'cat /root/space-result.log; for f in /root/space-check/*.log; do echo "$f"; tail -12 "$f"; done'))
    return dict(recovered=['payload'] if target == 'payload' else ['install', 'upgrade'],
                receipt=guest.read_text('cat /var/db/xiri-install/installed').strip())


def install_mozilla(guest, release):
    for _ in range(2):
        guest.command('sh /cdrom/install.sh --mozilla >/root/mozilla-install.log 2>&1; rc=$?; '
                      'tail -10 /root/mozilla-install.log; test "$rc" = 0', 1800)
        guest.command('cmp /var/db/xiri-install/inputs /var/db/xiri-install/installed && '
                      'grep -qx enabled /var/db/xiri-install/mozilla/phase && '
                      'test -x /emul/irix/var/netscape/mozilla/mozilla-bin')
    guest.command('install -o xiritest -g xiritest -m 700 /usr/local/share/xiri/xdm.xsession '
                  '/usr/people/xiritest/.xsession && test ! -e /home/netbsdtest/.xsession')
    return dict(release=release, receipts=guest.read_text('cat /var/db/xiri-install/installed').strip(),
                mozilla=guest.read_text('cat /var/db/xiri-install/mozilla/identity').strip(), repeated=True)


def greeter(guest):
    guest.command('export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/local/bin:/usr/X11R7/bin DISPLAY=:0')
    guest.wait_for('test -s /tmp/.X0-lock', 180)
    # Native NetBSD Xservers invokes the X symlink; the Xiri configuration names Xorg.
    authority = """$(ps -axww -o args= | awk '$1 ~ /^\\/usr\\/X11R7\\/bin\\/X(org)?$/ && $2 == ":0" {for(i=1;i<NF;i++) if($i=="-auth") print $(i+1)}')"""
    guest.wait_for('test -s "' + authority + '"', 90)
    guest.command('export XAUTHORITY=' + authority + '; test -s "$XAUTHORITY"')
    guest.wait_for("""id=$(xwininfo -root -tree | awk '/"xlogin"/ {print $1; exit}') && """
                   """test -n "$id" && xwininfo -id "$id" | grep -q 'Map State: IsViewable'""", 150)


def login(guest, user):
    for command in ('key type ' + user, 'key Return', 'key type ' + user, 'key Return'):
        guest.monitor(command)


def sgi_clock(guest, out):
    guest.command("su -m xiritest -c 'export HOME=/usr/people/xiritest; test \"$(id -un)\" = xiritest && "
                  "cd \"$HOME\" && exec /emul/irix/usr/sbin/clock' >/tmp/test-sgi-clock.log 2>&1")
    window = r"""xwininfo -root -tree | awk '/\("clock" "Clock"\)/ {print $1; exit}'"""
    guest.wait_for('test -n "$(' + window + ')"', 120)
    guest.command('clock_id=$(' + window + '); test -n "$clock_id" && xprop -id "$clock_id" WM_CLASS')
    guest.command('xwd -silent -id "$clock_id" -out /tmp/clock-first.xwd && sleep 3 && '
                  'xwd -silent -id "$clock_id" -out /tmp/clock-second.xwd && '
                  'test -s /tmp/clock-first.xwd && test "$(wc -c </tmp/clock-first.xwd)" -eq "$(wc -c </tmp/clock-second.xwd)" && '
                  '! cmp -s /tmp/clock-first.xwd /tmp/clock-second.xwd')
    evidence = guest.read_text('xprop -id "$clock_id" WM_CLASS; cksum /tmp/clock-first.xwd /tmp/clock-second.xwd').splitlines()
    guest.capture(out / 'sgi-clock.png')
    guest.command('xkill -id "$clock_id" && rm /tmp/clock-first.xwd /tmp/clock-second.xwd && xdpyinfo >/dev/null')
    return dict(window=evidence[0], samples=evidence[1:], png_sha256=sha256(out / 'sgi-clock.png'))


def display_upgrade(guest, original, legacy):
    from xiri_lab.clock_fonts import FONT_DIR, FONT_HASHES, INDEX, INDEX_SHA
    pins = json.loads((ROOT / 'profiles/netbsd-sgimips-indy-11.99.11-glx-v1.json').read_text())['artifacts']
    cmd = guest.command
    greeter(guest)
    cmd('mount -r -t cd9660 /dev/cd0a /cdrom && test -f /cdrom/display-update')
    if guest.read_text('cat /var/db/xiri-install/installed').strip() != original:
        raise ValueError('unexpected receipt before display upgrade')
    cmd('sha256 /etc/master.passwd /usr/people/xiritest/.Xresources /etc/rc.conf.d/xdm >/tmp/site.sha')
    cmd('sh /cdrom/upgrade.sh >/tmp/display.log 2>&1; rc=$?; cat /tmp/display.log; '
        'test "$rc" != 0 && grep -q "stop xdm" /tmp/display.log', 360)
    cmd('/etc/rc.d/xdm stop')
    guest.wait_for("! pgrep '(^|/)(Xorg|X|xdm)$'")
    if legacy:
        cmd('mv /var/db/xiri-install/created /var/db/xiri-install/test-saved-ledger')
    receipts = []
    for side, flag in [('sha256', ''), ('stock_sha256', ' --rollback')]:
        for _ in range(2):
            cmd('sh /cdrom/upgrade.sh' + flag + ' >/tmp/display.log 2>&1 || { tail /tmp/display.log; false; }', 420)
        for key in ('xorg', 'glx'):
            row = pins[key]
            cmd(f'test "$(sha256 -q {row["destination"]})" = {row[side]} && '
                f'test "$(stat -f %u:%g:%Mp%03Lp {row["destination"]})" = 0:0:{row["mode"]}')
            cmd(f'test "$(sha256 -q /var/db/xiri-install/original{row["destination"]})" = {row["stock_sha256"]}')
        for name, digest in {**FONT_HASHES, INDEX: INDEX_SHA}.items():
            path = '/emul/irix/' + FONT_DIR + name
            cmd(f'test "$(sha256 -q {path})" = {digest}' if not flag else f'test ! -e {path}')
        cmd('sha256 -c /tmp/site.sha && cmp /var/db/xiri-install/inputs /var/db/xiri-install/installed')
        receipts.append(guest.read_text('cat /var/db/xiri-install/installed').strip())
    if receipts[0] == original or receipts[1] != original:
        raise ValueError('unexpected graphics upgrade receipts')
    if legacy:
        cmd('mv /var/db/xiri-install/test-saved-ledger /var/db/xiri-install/created')
    return dict(upgraded=receipts[0], restored=receipts[1], repeat=True,
                legacy_ownership=legacy, site_files_preserved=True)


def desktop(guest, out, colour=None, while_logged_in=None, check_clock=False):
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
    clock = sgi_clock(guest, out) if check_clock else None
    guest.command('su -m xiritest -c "env XIRI_SESSION_DIR=\'$job\' /usr/local/bin/xiri-logout"')
    greeter(guest)
    ctwm = "pgrep -u netbsdtest -f '^/usr/X11R7/bin/ctwm( |$)'"
    login(guest, 'netbsdtest')
    # Poll from the host so a busy emulator cannot leave a guest shell loop
    # holding the serial console when its host deadline expires.
    start = time.monotonic()
    retried = False
    while time.monotonic() - start < 150:
        state = guest.read_text(f'if {ctwm} >/dev/null; then echo session; '
                                """elif id=$(xwininfo -root -tree | awk '/"xlogin"/ {print $1; exit}') && """
                                """test -n "$id" && xwininfo -id "$id" | grep -q IsViewable; then echo greeter; fi""").strip()
        if state == 'session':
            break
        if state == 'greeter' and not retried and time.monotonic() - start > 20:
            guest.monitor('key ctrl+u')
            login(guest, 'netbsdtest')
            retried = True
        time.sleep(1)
    else:
        raise RuntimeError('native xdm login did not start ctwm')
    guest.wait_for("xwininfo -root -tree | grep -q '\"UXTerm\"'", 120)
    native_processes = guest.read_text("""ps -ax -o uid,pid,comm | awk -v uid="$(id -u netbsdtest)" 'NR==1 || $1==uid'""").strip()
    guest.monitor('screen wait 500 10000')
    guest.monitor('screen shot ' + str(out / 'ctwm.png'))
    guest.command('kill -TERM "$(' + ctwm + ')"')
    greeter(guest)
    checks = dict(
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
    if check_clock:
        checks['sgi_clock'] = clock
    return checks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('install', 'disk-full', 'desktop', 'display-upgrade', 'mozilla', 'kernel-update', 'kernel-image', 'kernel-base', 'freeware', 'freeware-upgrade', 'freeware-artwork', 'freeware-gimp', 'freeware-gimp-removal'))
    for name in ('media', 'emulator', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--base', type=Path, help='qualified bootstrap, required except for the clean Freeware check')
    parser.add_argument('--release', choices=('6.5.22f', '6.5.30f'), required=True)
    parser.add_argument('--bundle', type=Path, help='test a copy of a packaged CHD and its graphical PROM')
    parser.add_argument('--kernel', type=Path, help='matching unstripped kernel for the graphical halt check')
    parser.add_argument('--sgi-clock', action='store_true', help='verify original SGI Clock redraws in the Xiri session')
    parser.add_argument('--mozilla', action='store_true', help='select Mozilla on a fresh installation')
    parser.add_argument('--wget-fixture', type=Path, help='private wget test ISO for the Indy kernel checks')
    parser.add_argument('--cd4', type=Path, help='complete May 2004 Freeware CD 4 ISO for the freeware phase')
    parser.add_argument('--gimp-media', type=Path, help='May 2004 GIMP and prerequisite packages for freeware-gimp')
    parser.add_argument('--old-unzip', type=Path, help='UnZip 5.40 helper ISO for upgrade or shared artwork checks')
    parser.add_argument('--software-manager', action='store_true', help='use the original graphical installer for the Freeware transaction')
    parser.add_argument('--legacy-ownership', action='store_true', help='exercise a v4 install without the created-file ledger')
    parser.add_argument('--full-target', choices=('services', 'payload'), help='filesystem to fill during disk-full qualification')
    parser.add_argument('--first-product', choices=('xmahjongg', 'unzip'), help='first product to install and remove in the coexistence check')
    args = parser.parse_args()
    if bool(args.first_product) != (args.phase == 'freeware-artwork'):
        parser.error('--first-product is required for freeware-artwork only')
    kernel_check = args.phase in ('kernel-update', 'kernel-image')
    if bool(args.wget_fixture) != kernel_check:
        parser.error('supply --wget-fixture only for the Indy kernel checks')
    freeware = args.phase.startswith('freeware')
    gimp_removal = args.phase == 'freeware-gimp-removal'
    if bool(args.gimp_media) != (args.phase == 'freeware-gimp' or gimp_removal):
        parser.error('--gimp-media is required for the GIMP checks only')
    if bool(args.old_unzip) != (args.phase in ('freeware-upgrade', 'freeware-artwork')):
        parser.error('supply --old-unzip for the upgrade and artwork checks')
    if not (freeware or kernel_check or args.phase == 'kernel-base') and not args.base:
        parser.error(f'{args.phase} requires --base')
    if bool(args.cd4) != (freeware and not args.gimp_media):
        parser.error('--cd4 is required only for the CD 4 Freeware checks')
    if args.software_manager and args.phase != 'freeware':
        parser.error('--software-manager requires the freeware phase')
    if args.mozilla and args.phase != 'install':
        parser.error('--mozilla requires the install phase')
    if args.sgi_clock and args.phase != 'desktop':
        parser.error('--sgi-clock requires the desktop phase')
    if args.legacy_ownership and args.phase != 'display-upgrade':
        parser.error('--legacy-ownership requires the display-upgrade phase')
    if args.full_target and args.phase != 'disk-full':
        parser.error('--full-target requires the disk-full phase')
    base = args.base.resolve() if args.base else None
    medium, emu, out = (p.resolve() for p in (args.media, args.emulator, args.output))
    os.environ.pop('IRIS_CHD_DIFF_DIR', None)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    out.mkdir(parents=True, exist_ok=True)
    run = out / args.phase
    run.mkdir()
    disk = out / 'disk.raw'
    install_phase = args.phase in ('install', 'disk-full')
    if install_phase:
        if disk.exists() or not json.loads((base / 'result.json').read_text())['passed']:
            raise ValueError('expected a new target and a qualified bootstrap')
        subprocess.run(['cp', '--reflink=auto', '--sparse=always', base / 'disk.raw', disk], check=True)
    if not install_phase and (not args.bundle or not args.kernel):
        parser.error(f'{args.phase} requires --bundle and --kernel')
    bundle = args.bundle.resolve() if args.bundle else None
    if not install_phase:
        package = json.loads((bundle / 'manifest.json').read_text())
        if (freeware or kernel_check) and not package.get('mozilla_receipt'):
            raise ValueError('expected a clean desktop with Mozilla installed')
        if args.phase == 'kernel-base' and package.get('mozilla_receipt'):
            raise ValueError('expected a v5 Indy without the optional Mozilla component')
        if package.get('mozilla_receipt'):
            pins = json.loads((ROOT / 'docs/results/2026-11-25-mozilla-sigpoll.json').read_text())
            kernel_digest = pins['releases'][args.release]['image']['kernel_sha256']
        elif args.phase == 'kernel-base':
            native = json.loads((ROOT/'profiles/netbsd-sgimips-indy-11.99.11-glx-v1.json').read_text())
            kernel_digest = native['artifacts']['kernel']['sha256']
        else:
            kernel_digest = json.loads((base / 'result.json').read_text())['native_sha256']['netbsd']
        if args.phase in ('mozilla', 'kernel-image') and (
            not package.get('mozilla_receipt') or sha256(medium) != package['iso_sha256']
        ):
            raise ValueError('expected the Mozilla image and its matching installer')
        if (
            package['release'] != args.release
            or sha256(bundle / 'netbsd-xiri.chd') != package['chd_sha256']
            or sha256(bundle / 'nvram.bin') != package['nvram_sha256']
            or sha256(emu / 'iris') != package['iris_sha256']
            or sha256(args.kernel) != kernel_digest
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
    if args.phase != 'desktop':
        config += '[scsi.4]\ncdrom = true\npath = ' + json.dumps(str(medium)) + '\n'
    if args.phase == 'disk-full':
        fixture = run / 'fixture.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-o', fixture, Path(__file__).with_name('disk-full.sh')], check=True)
        config += '[scsi.5]\ncdrom = true\npath = ' + json.dumps(str(fixture)) + '\n'
    if kernel_check:
        config += '[scsi.5]\ncdrom = true\npath = ' + json.dumps(str(args.wget_fixture.resolve())) + '\n'
    if args.cd4:
        config += '[scsi.5]\ncdrom = true\npath = ' + json.dumps(str(args.cd4.resolve())) + '\n'
    if args.gimp_media:
        from freeware_gimp import verify_media
        verify_media(args.gimp_media, removal=gimp_removal)
        config += '[scsi.5]\ncdrom = true\npath = ' + json.dumps(str(args.gimp_media.resolve())) + '\n'
    if args.software_manager:
        fixture = run / 'swmgr-tools.iso'
        source = ROOT / 'lab/irix-installer'
        subprocess.run(['genisoimage', '-quiet', '-R', '-o', fixture,
                        source / 'xmahjongg.sh', source / 'desktop-artwork.sh', source / 'package-filetypes.mk'], check=True)
        config += '[scsi.6]\ncdrom = true\npath = ' + json.dumps(str(fixture)) + '\n'
    if args.old_unzip:
        from freeware_upgrade import verify_media
        shared_artwork = verify_media(args.old_unzip, require_shared=args.phase == 'freeware-artwork')
        config += '[scsi.6]\ncdrom = true\npath = ' + json.dumps(str(args.old_unzip.resolve())) + '\n'
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
    if args.gimp_media or args.old_unzip:
        pins = json.loads((ROOT / 'docs/results/2026-11-25-swmgr.json').read_text())
        if result['iso_sha256'] != pins['releases'][args.release]['supplement_sha256']:
            raise ValueError('expected the release-specific SGI installer supplement')
    if args.gimp_media:
        result['gimp_media_sha256'] = sha256(args.gimp_media)
    if args.old_unzip:
        result['cd4_sha256'] = sha256(args.cd4)
        result['old_unzip_iso_sha256'] = sha256(args.old_unzip)
        if result['cd4_sha256'] != pins['full_cd4_sha256']:
            raise ValueError('expected the qualified CD 4')
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
        if install_phase:
            prepare_install(guest, args.release)
            if args.phase == 'disk-full':
                result['checks'] = disk_full(guest, run, args.full_target or 'services')
            elif args.mozilla:
                result['checks'] = install_mozilla(guest, args.release)
            else:
                result['checks'] = install(guest, args.release)
        elif args.phase == 'display-upgrade':
            result['checks'] = display_upgrade(guest, package['receipt'], args.legacy_ownership)
        elif args.phase == 'kernel-base':
            from indy_kernel_lifecycle import check_base
            result['checks'] = check_base(guest, package, greeter)
        elif kernel_check:
            from indy_kernel_lifecycle import check
            result['checks'] = check(guest, run, package, desktop, args.phase == 'kernel-image')
        elif args.phase == 'mozilla':
            from mozilla_lifecycle import check
            result['checks'] = check(guest, run, package, greeter, login,
                                     json.loads((base / 'result.json').read_text())['native_sha256'])
        elif args.gimp_media:
            from freeware_gimp import check
            result['checks'] = check(guest, run, greeter, login, removal=gimp_removal)
        elif args.phase == 'freeware-artwork':
            from freeware_artwork import check
            result['checks'] = check(guest, run, args.release, args.first_product, greeter, login)
        elif args.phase == 'freeware-upgrade':
            from freeware_upgrade import check
            result['checks'] = check(guest, run, greeter, login, shared_artwork)
        elif args.phase == 'freeware':
            from freeware_lifecycle import check
            result['cd4_sha256'] = sha256(args.cd4)
            result['checks'] = check(guest, run, package, greeter, login, graphical=args.software_manager)
        else:
            if 'receipt' in package:
                if result['iso_sha256'] != package['iso_sha256']:
                    raise ValueError('installer CD differs from the packaged installation')
                receipt = guest.read_text('cat /var/db/xiri-install/installed').strip()
                if receipt != package['receipt']:
                    raise ValueError('unexpected installed package on cold boot: ' + receipt)
                result['receipt'] = receipt
            result['checks'] = desktop(guest, run, check_clock=args.sgi_clock)
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
