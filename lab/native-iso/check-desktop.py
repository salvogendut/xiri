#!/usr/bin/env python3
"""Install a blank Indy, import a reference donor on target and check two xdm desktops."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import Guest, load_probe, sha256


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


native = load('native_iso_check', 'lab/native-iso/check-install.py')
saver = load('native_saver_check', 'lab/sgi-saver/check.py')


def data_cd(release, donor, output):
    pin = json.loads((ROOT / 'lab/irix-donor' / (release + '.json')).read_text())
    if sha256(donor) != pin['chd_sha256']:
        raise ValueError(f'This regression uses the recorded standalone {release} donor')
    subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'OWNER_DONOR', '-o', output,
                    '-graft-points', 'IRIX donor.chd=' + str(donor)], check=True)


def cold_root(lab):
    lab.start(boot=False)
    lab.wait('login: ', 900)
    native.enter(lab, 'root')
    lab.wait(r'# ', 60)
    native.enter(lab, "PS1='xiri-indy# '; export PS1")
    lab.wait('xiri-indy# ', 30)
    lab.logged_in = True
    return Guest(lab)


def poweroff(lab):
    native.enter(lab, 'shutdown -p now')
    lab.wait('Done running shutdown hooks', 120)
    for _ in range(240):
        if 'Machine: soft power-off' in (lab.directory / 'emulator.log').read_text(errors='replace'):
            lab.logged_in = False
            return
        time.sleep(.5)
    raise RuntimeError('IRIS did not observe the guest powering off')


def prepare(guest, release):
    cmd = guest.command
    cmd('mkdir -p /cdrom && mount -r -t cd9660 /dev/cd0a /cdrom')
    cmd('test -x /usr/local/sbin/xiriprep && test ! -e /emul/irix && test ! -e /home/native/.xsession')
    cmd("/usr/local/libexec/xiri/setup-xiri-user.sh xiritest && usermod -p \"$(pwhash -b 5 xiritest)\" xiritest")
    prefs = '/usr/people/xiritest/.Xresources'
    cmd(f"su -f xiritest -c 'echo \"UXTerm*scrollBar: true\" > {prefs}; echo \"exec ctwm\" > ~/.xsession'")
    cmd(f'prefhash=$(sha256 -q {prefs}); prephome=/usr/people/xiritest')
    prep = """/usr/local/sbin/xiriprep --source '/cdrom/IRIX donor.chd' --user xiritest"""
    cmd(f'{prep} --check && test ! -e /var/db/xiri-install')
    # A release fingerprint can match even when a later resource has been damaged.
    cmd(f'plan=/usr/local/share/xiri/plans/{release}.plan && cp -p "$plan" /tmp/expected.plan && '
        f"sed '1s/[^|]*$/{'0' * 64}/'"
        ' /tmp/expected.plan > "$plan" && ! cmp -s "$plan" /tmp/expected.plan')
    cmd(f'! {prep} && test ! -e /emul/irix && test ! -e /usr/local/share/xiri/fonts && '
        'test ! -e /var/db/xiri-install/installed && grep -qx "exec ctwm" "$prephome/.xsession"')
    cmd('mv /tmp/expected.plan "$plan"')
    cmd(prep, 1800)
    cmd(prep, 240)
    cmd(f'test "$prefhash" = "$(sha256 -q {prefs})" && grep -qx "exec ctwm" "$prephome/.xsession.before-xiriprep" && '
        'test -x "$prephome/.xsession" && test ! -e /home/native/.xsession && '
        'cmp -s /var/db/xiri-install/installed /emul/irix/.xiri-install-inputs && '
        'cmp -s /var/db/xiri-install/installed /usr/local/share/xiri/fonts/.xiri-install-inputs && '
        'test -x /emul/irix/usr/bin/X11/xlock && umount /cdrom')
    return guest.read_text('cat /var/db/xiri-install/installed').strip()


def desktop(guest, output, password):
    q = saver.desktop
    q.greeter(guest)
    guest.command('test -f /var/run/xiri-pty-ready && /etc/rc.d/xiri_famd status && /etc/rc.d/rpcbind status')
    saver.login_catalog(guest, q.greeter, q.login)
    tree = guest.read_text('xwininfo -root -tree')
    windows = ['Icon Catalog:', 'Toolchest', 'winterm', 'xclock']
    if not all(w in tree for w in windows):
        raise ValueError(tree)
    dimensions = guest.read_text("xdpyinfo | awk '/dimensions:/ {print $2}'").strip()
    if dimensions != '1280x1024':
        raise ValueError(dimensions)
    handoff = guest.read_text('cat "$job/handoff"').strip()
    guest.lab.ci('screenshot', str(output / 'desktop.png'))
    saver.logout(guest)
    animation = saver.check_session(guest, check_next_login=True)
    for key in ('key type native', 'key Return', 'key type ' + password, 'key Return'):
        guest.monitor(key)
        time.sleep(.4)
    guest.wait_for("pgrep -u native -f '^/usr/X11R7/bin/ctwm( |$)' >/dev/null", 150)
    return dict(windows=windows, dimensions=dimensions, winterm=handoff, saver=animation, native_ctwm=True)


def run(args, work):
    probe = load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = (args.emulator.resolve() / name for name in ('iris', 'iris-ci'))
    cpu = 'r4400' if args.release == '6.5.22f' else 'r5000'
    os.environ.update(IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(work / 'profile'))
    cd = work / 'donor.iso'
    data_cd(args.release, args.donor.resolve(), cd)
    disk = work / 'blank.raw'
    with disk.open('xb') as stream:
        stream.truncate(6 * 1024**3)
    password = secrets.token_hex(6)
    install = native.open_lab(probe, work / 'install', cpu, disk, args.serial_prom, args.iso.resolve())
    try:
        native.installer(install, password)
    finally:
        install.close()
    prom = install.directory / 'nvram.bin'
    prep = native.open_lab(probe, work / 'prepare', cpu, disk, prom, cd)
    prep.config_text = prep.config_text.replace('[scsi.4]', '[scsi.6]')
    try:
        receipt = prepare(cold_root(prep), args.release)
        poweroff(prep)
    finally:
        prep.close()
    boot = native.open_lab(probe, work / 'desktop', cpu, disk, prom)
    try:
        result = desktop(cold_root(boot), args.output.resolve(), password)
        poweroff(boot)
    finally:
        boot.close()
    result.update(release=args.release, cpu=cpu, receipt=receipt, installer_sha256=sha256(args.iso),
                  donor_sha256=sha256(args.donor), iris_sha256=sha256(probe.IRIS))
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'donor', 'emulator', 'serial-prom', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--release', choices=['6.5.22f', '6.5.30f'], required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    with tempfile.TemporaryDirectory(dir=args.output) as tmp:
        run(args, Path(tmp).resolve())
