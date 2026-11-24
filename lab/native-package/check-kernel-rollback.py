#!/usr/bin/env python3
"""Boot the saved stock kernel and then the Xiri desktop on one private Indy overlay."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import Guest, load_probe, sha256
from xiri_lab.kernel_log import KernelLog

HERE = Path(__file__).resolve().parent
xdm = runpy.run_path(str(HERE / 'check-clean-desktop.py'))
STOCK = runpy.run_path(str(HERE / 'check-clean-bootstrap.py'))['STOCK']
RECEIPT = '/var/db/xiri-install/installed'
XR = '/usr/people/xiritest/.Xresources'
USER_FILE = '/usr/people/xiritest/rollback-note'
NATIVE_FILE = '/home/netbsdtest/stock-note'
POLICY = (
    XR,
    USER_FILE,
    '/usr/people/xiritest/.xsession',
    '/etc/master.passwd',
    '/etc/group',
    '/etc/modules.conf',
    '/etc/rc.conf.d/xdm',
    '/etc/xiri/session.conf',
    RECEIPT,
)


def message_ring(kernel):
    symbols = subprocess.check_output(['nm', '-n', kernel], text=True)
    return next(int(line.split()[0], 16) for line in symbols.splitlines() if line.endswith(' msgbufp'))


def stock_reference(sets):
    name = 'kern-GENERIC32_IP2x.tgz'
    sums = (ROOT / 'lab/netbsd-11.0/SHA512SUMS').read_text().splitlines()
    expected = {path: digest for digest, path in (line.split() for line in sums)}
    with (sets / name).open('rb') as stream:
        if hashlib.file_digest(stream, 'sha512').hexdigest() != expected['sgimips/binary/sets/' + name]:
            raise ValueError('Stock kernel set checksum differs')
    with tarfile.open(sets / name) as archive, archive.extractfile('./netbsd') as stream:
        with tempfile.NamedTemporaryFile() as stock:
            shutil.copyfileobj(stream, stock)
            stock.flush()
            return sha256(stock.name), message_ring(stock.name)


def check_files(g):
    g.command(
        'sha256 -c /root/rollback.sha && stat -f "%u:%g:%Lp %N" '
        + ' '.join(POLICY)
        + ' | cmp - /root/rollback.modes'
    )


def seed(g, release, colour):
    g.command('test ! -e ' + USER_FILE + ' && test ! -e ' + NATIVE_FILE)
    command = f'cd && umask 077 && echo "Xiri {release}" > {USER_FILE} && echo "winterm*foreground: {colour}" >> {XR}'
    g.command('su - xiritest -c ' + shlex.quote(command))
    g.command(
        'sha256 ' + ' '.join(POLICY) + ' > /root/rollback.sha && '
        'stat -f "%u:%g:%Lp %N" ' + ' '.join(POLICY) + ' > /root/rollback.modes'
    )
    check_files(g)


def prom(lab, command):
    lab.send(command)
    lab.wait(r'\n>> ', 30)


def prepare_prom(probe, config, out, serial_prom):
    # Both operating systems get the same graphics console and serial getty.
    # Stop at the PROM before its countdown starts an operating system.
    run = out / 'prom'
    run.mkdir()
    shutil.copyfile(serial_prom, run / 'nvram.bin')
    probe.TOOLBOX = []
    lab = probe.Lab(
        SimpleNamespace(mode='ci', debugger=False),
        run,
        config_text=config,
        working_directory=out,
        scsi1_from_config=True,
    )
    try:
        lab.start(boot=False)
        lab.wait('press <Esc>', 120)
        lab.send('\x1b', newline=False)
        lab.wait(r'Option\?', 30)
        lab.send('5')
        lab.wait(r'\n>> ', 30)
        prom(lab, 'setenv -f console g')
        for kernel in ('netbsd.stock', 'netbsd.boot'):
            prom(lab, 'setenv OSLoadFilename ' + kernel)
            lab.send('printenv OSLoadFilename')
            lab.wait(r'OSLoadFilename=' + re.escape(kernel) + r'\s+>> ', 30)
            lab.ci('rtc-save')
            shutil.copyfile(run / 'nvram.bin', out / (kernel + '.prom'))
    finally:
        lab.close()


def screenshot(g, path):
    g.monitor('disp compositor gl')
    g.monitor('screen wait 500 10000')
    g.monitor('screen shot ' + str(path))
    return sha256(path)


def restored_desktop(g, out, colour):
    xdm['greeter'](g)
    xdm['login'](g, 'xiritest')
    g.wait_for("grep -q 'Logs: ' /usr/people/xiritest/.xsession-errors", 160)
    g.command(
        'job=$(sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors | tail -1); '
        'XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
        'test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; '
        'export DISPLAY=127.0.0.1:0 XAUTHORITY'
    )
    g.wait_for('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready', 180)
    for title in ('Toolchest', 'Icon Catalog:', 'winterm', 'xclock'):
        g.wait_for('xwininfo -root -tree | grep -Fq ' + shlex.quote(title), 90)
    g.command(
        "xrdb -query | awk '$1 == \"winterm*foreground:\" && $2 == \"" + colour + "\" {ok=1} END {exit !ok}'"
    )
    g.command("""su - xiritest -c '/emul/irix/bin/sh -c "echo RESTORED_SHELL"' | grep -qx RESTORED_SHELL""")
    geometry = g.read_text('xdpyinfo | grep dimensions:').strip()
    if '1280x1024 pixels' not in geometry:
        raise RuntimeError(geometry)
    image_digest = screenshot(g, out / 'restored.png')
    g.command('su -m xiritest -c "env XIRI_SESSION_DIR=\'$job\' /usr/local/bin/xiri-logout"')
    xdm['greeter'](g)
    return dict(
        dimensions=geometry,
        applied_resource=f'winterm*foreground: {colour}',
        clients=['4Dwm', 'Toolchest', 'Icon Catalog', 'winterm', 'xclock'],
        vendor_shell=True,
        logout_to_xdm=True,
        png_sha256=image_digest,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ('bundle', 'serial-prom', 'emulator', 'sets', 'kernel', 'output'):
        parser.add_argument('--' + arg, type=Path, required=True)
    media = parser.add_mutually_exclusive_group()
    media.add_argument('--upgrade-media', type=Path, help='qualify native helper upgrade and rollback')
    media.add_argument('--install-media', type=Path, help='qualify removing and reinstalling this release')
    parser.add_argument('--inventory-base-media', type=Path,
                        help='also mount the v2 CD and qualify the v2-to-v3 helper inventory migration')
    args = parser.parse_args()
    if args.inventory_base_media and not args.upgrade_media:
        parser.error('--inventory-base-media requires --upgrade-media')
    bundle, firmware, emulator, sets, kernel, out = [
        p.resolve()
        for p in (args.bundle, args.serial_prom, args.emulator, args.sets, args.kernel, args.output)
    ]
    record = json.loads((ROOT / 'docs/results/2026-11-23-clean-indy-desktops.json').read_text())
    release = json.loads((bundle / 'manifest.json').read_text())['release']
    pin = record['releases'][release]['image']
    original = bundle / 'netbsd-xiri.chd'
    if (
        sha256(original) != pin['chd_sha256']
        or sha256(emulator / 'iris') != pin['iris_sha256']
        or sha256(firmware) != STOCK['nvram.bin']
        or sha256(kernel) != record['bootstrap']['native_sha256']['netbsd']
    ):
        raise ValueError('Inputs differ from the qualified Indy components')
    stock, stock_msgbuf = stock_reference(sets)
    msgbuf = message_ring(kernel)
    config = (bundle / 'iris.toml').read_text()
    if 'overlay = true' not in config or 'path = "netbsd-xiri.chd"' not in config:
        raise ValueError('Expected the Indy overlay configuration')
    removal = upgrade = None
    phases = ('baseline', 'stock', 'restored')
    if args.install_media or args.upgrade_media:
        medium = (args.install_media or args.upgrade_media).resolve(strict=True)
        config += '\n[scsi.4]\ncdrom = true\npath = ' + json.dumps(str(medium)) + '\n'
    if args.upgrade_media:
        if args.inventory_base_media:
            previous_cd = args.inventory_base_media.resolve(strict=True)
            config += '\n[scsi.5]\ncdrom = true\npath = ' + json.dumps(str(previous_cd)) + '\n'
        check = 'check-helper-inventory.py' if args.inventory_base_media else 'check-native-upgrade.py'
        upgrade = runpy.run_path(str(HERE / check))
        phases = ('upgrade', 'upgraded', 'downgraded')
    elif args.install_media:
        removal = runpy.run_path(str(HERE / 'check-desktop-removal.py'))
        phases = ('remove', 'stock', 'reinstall', 'restored')
    os.environ.pop('IRIS_CHD_DIFF_DIR', None)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    out.mkdir(parents=True, exist_ok=False)
    subprocess.run(['cp', '--reflink=auto', original, out / 'netbsd-xiri.chd'], check=True)
    probe = load_probe()
    probe.IRIS, probe.CI = emulator / 'iris', emulator / 'iris-ci'
    toolbox = probe.TOOLBOX
    colour = {'6.5.22f': '#c9ecc9', '6.5.30f': '#c9d9ec'}[release]
    result = dict(release=release, chd_sha256=pin['chd_sha256'], stock_sha256=stock, boots=[])
    if removal or upgrade:
        result['media_sha256'] = sha256(medium)
    if args.inventory_base_media:
        result['base_media_sha256'] = sha256(previous_cd)
    try:
        prepare_prom(probe, config.replace('ci = false', 'ci = true'), out, firmware)
        probe.TOOLBOX = toolbox
        for phase in phases:
            print(f'{release}: {phase}', flush=True)
            stock_boot = phase == 'stock'
            filename = 'netbsd.stock' if stock_boot else 'netbsd.boot'
            run = out / phase
            run.mkdir()
            shutil.copyfile(out / (filename + '.prom'), run / 'nvram.bin')
            lab = probe.Lab(
                SimpleNamespace(mode='ordinary', debugger=False),
                run,
                config_text=config.replace('ci = false', 'ci = true'),
                working_directory=out,
                scsi1_from_config=True,
            )
            g = Guest(lab)
            evidence = dict(phase=phase)
            try:
                lab.start(boot=False)
                lab.wait('login: ', 600)
                lab.send('root')
                lab.wait('xiri-indy# ', 40)
                lab.logged_in = True
                evidence['kernel'] = g.read_text('uname -v').strip()
                expected = record['bootstrap']['stock_kernel' if phase == 'stock' else 'modular_kernel']
                if evidence['kernel'] != expected:
                    raise ValueError('Unexpected running kernel: ' + evidence['kernel'])
                g.command(
                    'test "$(sha256 -q /netbsd.stock)" = '
                    + stock
                    + ' && test "$(sha256 -q /netbsd)" = '
                    + record['bootstrap']['native_sha256']['netbsd']
                    + ' && test "$(sha256 -q /netbsd.boot)" = '
                    + record['bootstrap']['native_sha256']['netbsd.boot']
                )
                evidence['prom_filename'] = filename
                g.command('sysctl -n kern.consdev | grep -q ttyE0 && tty | grep -q ttyZ0')
                g.command('test "$(sysctl -n kern.securelevel)" = 1')
                if removal and phase in ('stock', 'reinstall'):
                    g.command('test ! -e ' + RECEIPT)
                else:
                    g.command('grep -q "^' + re.escape(release) + ' " ' + RECEIPT)
                if phase != 'stock':
                    g.command("modstat | grep -Eq '^compat_irix_o32[[:space:]]+exec[[:space:]]+filesys'")
                if upgrade:
                    evidence.update(upgrade['check'](g, phase, release, colour, run, xdm))
                elif removal and phase == 'remove':
                    evidence['uninstall'] = removal['remove'](g, release, colour)
                elif removal and phase == 'stock':
                    evidence['native'] = removal['native'](g, run, xdm, screenshot)
                elif removal and phase == 'reinstall':
                    evidence['install'] = removal['reinstall'](g, release)
                elif removal and phase == 'restored':
                    removal['preserved'](g)
                    evidence['desktop'] = restored_desktop(g, run, colour)
                    removal['preserved'](g)
                elif phase == 'baseline':
                    seed(g, release, colour)
                    evidence['preserved_paths'] = list(POLICY)
                elif phase == 'stock':
                    check_files(g)
                    g.command(
                        'su - netbsdtest -c '
                        + shlex.quote(f'umask 077 && echo "stock {release}" > {NATIVE_FILE}')
                    )
                    g.command('sha256 ' + NATIVE_FILE + ' > /root/stock-note.sha')
                    evidence['module_status'] = g.read_text('modstat 2>&1').strip()
                    if not evidence['module_status'].startswith('NAME '):
                        raise RuntimeError('Cannot read the stock kernel module list')
                    if re.search(r'^compat_irix_o32\s', evidence['module_status'], re.M):
                        raise RuntimeError('unexpected compatibility module on stock boot')
                    evidence['xdm_status'] = g.read_text('/etc/rc.d/xdm status 2>&1').strip()
                    if not evidence['xdm_status'].startswith('xdm is running'):
                        raise RuntimeError(evidence['xdm_status'])
                    evidence['messages'] = g.read_text(
                        "grep -Ei 'modload|compat_irix_o32|savecore' /var/run/rc.log | tail -10"
                    ).strip()
                    evidence['native_login'] = g.read_text('su - netbsdtest -c "id -un; pwd"').strip()
                    if evidence['native_login'].splitlines() != ['netbsdtest', '/home/netbsdtest']:
                        raise RuntimeError('Stock native user login failed')
                    evidence['greeter_png_sha256'] = screenshot(g, run / 'stock.png')
                else:
                    check_files(g)
                    g.command(
                        'sha256 -c /root/stock-note.sha && test "$(stat -f %Su '
                        + NATIVE_FILE
                        + ')" = netbsdtest'
                    )
                    evidence['desktop'] = restored_desktop(g, run, colour)
                    check_files(g)
                console = KernelLog(lab, stock_msgbuf if stock_boot else msgbuf, 4 if stock_boot else 8)
                console.halt()
            except Exception:
                if (removal or upgrade) and lab.logged_in:
                    try:
                        (run / 'diagnostic.txt').write_text(g.read_text(
                            'ps -axww -o args=; tail -70 /var/log/Xorg.0.log; tail -45 /var/log/xdm.log; '
                            'tail -30 /root/*-cycle.log /root/conflict.log /root/interrupted.log /root/base.log'
                        ))
                        screenshot(g, run / 'failure.png')
                        KernelLog(lab, stock_msgbuf if stock_boot else msgbuf, 4 if stock_boot else 8).halt()
                    except Exception as diagnostic_error:
                        evidence['diagnostic_error'] = str(diagnostic_error)
                raise
            finally:
                lab.close()
                evidence.update(
                    halted=lab.clean_shutdown, stopped=lab.process is None or lab.process.poll() is not None
                )
                result['boots'].append(evidence)
    except BaseException as error:
        result['error'] = str(error) or type(error).__name__
        raise
    finally:
        result['base_unchanged'] = sha256(original) == pin['chd_sha256']
        result['passed'] = (
            'error' not in result
            and result['base_unchanged']
            and len(result['boots']) == len(phases)
            and all(b['halted'] and b['stopped'] for b in result['boots'])
        )
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if not result['passed']:
        raise RuntimeError('Incomplete rollback qualification')


if __name__ == '__main__':
    main()
