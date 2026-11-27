#!/usr/bin/env python3
"""Install a blank Indy, import a pinned donor on target and check two xdm desktops."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import secrets
import shutil
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


def donor_medium(donor, work, makefs):
    if makefs:
        directory = work / 'donors'
        directory.mkdir()
        shutil.copyfile(donor, directory / 'IRIX donor.chd')
        output = work / 'donors.ffs'
        subprocess.run([makefs, '-t', 'ffs', '-B', 'be', '-o', 'version=2',
                        output, directory], check=True)
        return output
    output = work / 'donor.iso'
    subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'OWNER_DONOR', '-o', output,
                    '-graft-points', 'IRIX donor.chd=' + str(donor)], check=True)
    return output


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


def prepare(guest, release, filesystem):
    cmd = guest.command
    mount = 'ffs /dev/sd1c' if filesystem else 'cd9660 /dev/cd0a'
    cmd(f'mkdir -p /cdrom && mount -r -t {mount} /cdrom')
    cmd('test -x /usr/local/sbin/xiriprep && test ! -e /emul/irix && test ! -e /home/native/.xsession')
    cmd("/usr/local/libexec/xiri/setup-xiri-user.sh xiritest && usermod -p \"$(pwhash -b 5 xiritest)\" xiritest")
    prefs = '/usr/people/xiritest/.Xresources'
    cmd(f"su -f xiritest -c 'echo \"UXTerm*scrollBar: true\" > {prefs}; echo \"exec ctwm\" > ~/.xsession'")
    cmd(f'prefhash=$(sha256 -q {prefs}); prephome=/usr/people/xiritest')
    prep = """/usr/local/sbin/xiriprep --source '/cdrom/IRIX donor.chd' --user xiritest --allow-shutdown"""
    denied = """su -f xiritest -c 'test ! -x /sbin/shutdown'"""
    checked = cmd(f'{prep} --check && test ! -e /var/db/xiri-install && {denied}')
    profile = next((line.split(': ', 1)[1] for line in checked.splitlines()
                    if line.startswith('Desktop profile: ')), release + '.plan')
    if (f'Identified IRIX {release} from ' not in checked or
            profile.split('-', 1)[0].removesuffix('.plan') != release):
        raise ValueError(f'Unexpected desktop profile: {profile}')
    # A release fingerprint can match even when a later resource has been damaged.
    cmd(f'plan=/usr/local/share/xiri/plans/{profile} && cp -p "$plan" /tmp/expected.plan && '
        f"sed '1s/[^|]*$/{'0' * 64}/'"
        ' /tmp/expected.plan > "$plan" && ! cmp -s "$plan" /tmp/expected.plan')
    cmd(f'! {prep} && {denied} && test ! -e /emul/irix && test ! -e /usr/local/share/xiri/fonts && '
        'test ! -e /var/db/xiri-install/installed && grep -qx "exec ctwm" "$prephome/.xsession"')
    cmd('mv /tmp/expected.plan "$plan"')
    cmd(prep, 1800)
    cmd('groupsum=$(sha256 -q /etc/group)')
    cmd(prep, 240)
    cmd("""test "$groupsum" = "$(sha256 -q /etc/group)" && su -f xiritest -c 'test -x /sbin/shutdown' && """
        """su -f native -c 'test ! -x /sbin/shutdown'""")
    cmd(f'test "$prefhash" = "$(sha256 -q {prefs})" && grep -qx "exec ctwm" "$prephome/.xsession.before-xiriprep" && '
        'test -x "$prephome/.xsession" && test ! -e /home/native/.xsession && '
        'cmp -s /var/db/xiri-install/installed /emul/irix/.xiri-install-inputs && '
        'cmp -s /var/db/xiri-install/installed /usr/local/share/xiri/fonts/.xiri-install-inputs && '
        'test -x /emul/irix/usr/bin/X11/xlock && umount /cdrom')
    receipt = guest.read_text('cat /var/db/xiri-install/installed').strip()
    if receipt.split()[0] != release or receipt.split()[-1] != guest.read_text('sha256 -q "$plan"').strip():
        raise ValueError(f'Installed receipt does not match {profile}: {receipt}')
    return receipt


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


def check_game(guest, output):
    from freeware_lifecycle import freeware_tab, game_window, history, logout, transaction
    q = saver.desktop
    q.greeter(guest)
    cmd = guest.command
    cmd('mkdir -p /cdrom /mnt/freeware && mount -rt cd9660 /dev/cd0a /cdrom && '
        'mount -rt cd9660 /dev/cd1a /mnt/freeware')
    cmd('sha256 /usr/people/xiritest/.Xresources /usr/people/xiritest/.xsession '
        '/var/db/xiri-install/installed >/root/before-game.sha')
    transaction(guest, 'sh /cdrom/prepare-live-base.sh /cdrom', 'bootstrap')
    cmd('sha256 /emul/irix/usr/lib/filetype/desktop.otr >>/root/before-game.sha')
    transaction(guest, 'sh /cdrom/xmahjongg.sh install /mnt/freeware', 'install-game')
    installed = history(guest)
    if 'fw_xmahjongg.sw.xmahjongg' not in installed:
        raise RuntimeError('SGI inst did not record xmahjongg')
    saver.login_catalog(guest, q.greeter, q.login)
    x, y = freeware_tab(guest)
    guest.monitor(f'ptr click {x + 215} {y + 80} left 2')
    guest.wait_for('xwininfo -root -tree | grep -q XMahjongg', 120)
    window = game_window(guest, output)
    logout(guest)
    q.greeter(guest)
    transaction(guest, 'sh /cdrom/xmahjongg.sh remove /mnt/freeware', 'remove-game')
    remaining = history(guest)
    if 'fw_xmahjongg.sw.xmahjongg' in remaining:
        raise RuntimeError('SGI inst still lists the removed game')
    cmd('test ! -e /emul/irix/usr/freeware/bin/xmahjongg && '
        'test ! -L /emul/irix/usr/lib/desktop/iconcatalog/pages/C/Freeware/xmahjongg && '
        'sha256 -c /root/before-game.sha')
    return dict(window=window, installed=installed, after_removal=remaining)


def run(args, work):
    probe = load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = (args.emulator.resolve() / name for name in ('iris', 'iris-ci'))
    cpu = 'r5000' if args.release == '6.5.30f' else 'r4400'
    os.environ.update(IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(work / 'profile'))
    expected_hash = args.donor_sha256
    if not expected_hash:
        pin = json.loads((ROOT / 'lab/irix-donor' / (args.release + '.json')).read_text())
        expected_hash = pin['chd_sha256']
    if sha256(args.donor) != expected_hash:
        raise ValueError(f'Donor differs from the expected {args.release} disk')
    medium = donor_medium(args.donor.resolve(), work, args.makefs)
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
    prep = native.open_lab(probe, work / 'prepare', cpu, disk, prom)
    slot = '[scsi.2]\noverlay = true' if args.makefs else '[scsi.6]\ncdrom = true'
    prep.config_text += f'{slot}\npath = {json.dumps(str(medium))}\n'
    try:
        receipt = prepare(cold_root(prep), args.release, args.makefs)
        poweroff(prep)
    finally:
        prep.close()
    boot = native.open_lab(probe, work / 'desktop', cpu, disk, prom)
    try:
        result = desktop(cold_root(boot), args.output.resolve(), password)
        poweroff(boot)
    finally:
        boot.close()
    if args.software_cd:
        games = native.open_lab(probe, work / 'software', cpu, disk, prom, args.software_cd.resolve())
        games.config_text += f'[scsi.5]\ncdrom = true\npath = {json.dumps(str(args.freeware_cd.resolve()))}\n'
        try:
            result['freeware'] = check_game(cold_root(games), args.output.resolve())
            poweroff(games)
        finally:
            games.close()
    result.update(release=args.release, cpu=cpu, receipt=receipt, installer_sha256=sha256(args.iso),
                  donor_sha256=sha256(args.donor), iris_sha256=sha256(probe.IRIS))
    (args.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'donor', 'emulator', 'serial-prom', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--release', choices=['6.5.22f', '6.5.22m', '6.5.30f'], required=True)
    parser.add_argument('--makefs', type=Path, help='NetBSD nbmakefs for donors on a second FFS disk')
    parser.add_argument('--donor-sha256', help='expected CHD hash for an independently installed donor')
    parser.add_argument('--software-cd', type=Path, help='release-specific installer supplement')
    parser.add_argument('--freeware-cd', type=Path, help='May 2004 Freeware disc 4')
    args = parser.parse_args()
    if args.release == '6.5.22m' and not args.donor_sha256:
        parser.error('supply the SHA256 of the independently sourced maintenance donor')
    if bool(args.software_cd) != bool(args.freeware_cd):
        parser.error('supply the installer supplement and Freeware disc together')
    args.output.mkdir(parents=True, exist_ok=False)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    with tempfile.TemporaryDirectory(dir=args.output) as tmp:
        run(args, Path(tmp).resolve())
