#!/usr/bin/env python3
"""Install the native ISO on an empty Indy disk, detach it and qualify an xdm login."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import Guest, load_probe, sha256


def open_lab(probe, directory, cpu, disk, prom, cd=None):
    directory.mkdir()
    shutil.copyfile(prom, directory / 'nvram.bin')
    config = ('ci = true\nno_audio = true\nbanks = [128,128,0,0]\n'
              f'[machine]\nprofile = "indy_ip24"\ncpu = "{cpu}"\n'
              '[graphics]\nboard = "newport"\n[scsi.1]\noverlay = false\n'
              f'path = {json.dumps(str(disk))}\n')
    if cd:
        config += f'[scsi.4]\ncdrom = true\npath = {json.dumps(str(cd))}\n'
    return probe.Lab(SimpleNamespace(mode='ci', debugger=False), directory, config_text=config,
                     working_directory=directory, scsi1_from_config=True)


def enter(lab, text=''):
    # The PROM and passwd both read the emulated Zilog UART a few bytes at a time.
    for i in range(0, len(text), 4):
        lab.ci('serial-send', '--no-cr', '--', text[i:i + 4])
        time.sleep(.06)
    lab.send('')


def installer(lab, password):
    lab.start(boot=False)
    menu = lab.wait(r'press <Esc>|Option\?', 120)
    if 'Esc' in menu.group():
        lab.send('\x1b', newline=False)
        lab.wait(r'Option\?', 40)
    enter(lab, '5')
    lab.wait('>> ', 30)
    enter(lab, 'boot -f scsi(0)cdrom(4)rdisk(0)partition(8)ip2xboot')

    def choose(pattern, text='', timeout=120):
        lab.wait(pattern, timeout)
        time.sleep(.25)
        enter(lab, text)

    choose('Installation messages in English')
    choose('Install NetBSD to hard disk')
    choose('Shall we continue', 'b')
    choose(r'sd0 \(6\.0G')
    choose('Use default partition sizes', 'b')
    choose('Partition sizes ok')
    choose('Shall we continue', 'b')
    for _ in range(10):
        result = lab.wait('Hit enter to continue|Full installation', 180)
        time.sleep(.25)
        enter(lab)
        if 'Full installation' in result.group():
            break
    else:
        raise RuntimeError('Partitioning did not reach set selection')
    choose('CD-ROM / DVD')
    lab.wait('All selected distribution sets unpacked successfully', 1200)
    choose('The extraction of the selected sets')
    choose('New password:')
    next_menu = lab.wait('Not now, continue!|Configure the additional items', 60)
    if 'Not now' in next_menu.group():
        enter(lab, 'x')
    choose('Finished configuring', 'l')
    choose(r'Enable xdm \(X Display Manager\).*?YES', 'p')
    choose(r'Username to add.{0,50}', 'native')
    choose('add this user to group wheel', 'b')
    choose('User shell')
    choose('New password:', password)
    choose('Retype new password:', password)
    choose('Finished configuring', 'r')
    lab.wait(r'# ', 20)
    enter(lab, "sed -i '/^ttyZ0/s/off secure/on secure/' /targetroot/etc/ttys && "
               "sed -n '/^ttyZ0/p' /targetroot/etc/ttys")
    lab.wait(r'\nttyZ0[^\n]*on secure', 30)
    enter(lab, 'exit')
    choose('Finished configuring', 'x')
    choose('is now complete')
    choose('Exit Install System', 'x')
    lab.wait(r'# ', 30)
    enter(lab, 'halt')
    lab.wait('unmounting done', 90)
    choose(r'Option\?', '5')
    for cmd in ('setenv OSLoader boot', 'setenv OSLoadFilename netbsd.boot',
                'setenv OSLoadOptions auto', 'setenv -f console g'):
        choose('>> ', cmd)
    lab.wait('>> ', 30)
    lab.ci('rtc-save')


def native_login(lab, password, output):
    lab.start(boot=False)
    # The first native startup populates the fontconfig cache.
    lab.wait('login: ', 900)
    enter(lab, 'root')
    lab.wait(r'# ', 60)
    enter(lab, "PS1='xiri-indy# '; export PS1")
    lab.wait('xiri-indy# ', 20)
    lab.logged_in = True
    guest = Guest(lab)
    guest.command('test ! -e /emul/irix && test -s /netbsd.boot && id native >/dev/null')
    kernel = guest.read_text('uname -a; modstat | grep "^compat_irix_o32 "')
    if 'XIRI_IRIX_MODULE' not in kernel or 'compat_irix_o32' not in kernel:
        raise RuntimeError('Installed kernel or module differs from the native Indy build')
    guest.command('export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/X11R7/bin DISPLAY=:0')
    authority = """$(ps -axww -o args= | awk '$1 ~ /^\\/usr\\/X11R7\\/bin\\/X(org)?$/ && $2 == ":0" {for(i=1;i<NF;i++) if($i=="-auth") print $(i+1)}')"""
    guest.wait_for('test -s "' + authority + '"', 120)
    guest.command('export XAUTHORITY=' + authority)
    greeter = ("""win=$(xwininfo -root -tree | awk '/"xlogin"/ {print $1; exit}') """
               """&& test -n "$win" && xwininfo -id "$win" | grep -q 'Map State: IsViewable'""")
    guest.wait_for(greeter, 150)
    dimensions = guest.read_text("xdpyinfo | awk '/dimensions:/ {print $2}'").strip()
    if dimensions != '1280x1024':
        raise RuntimeError(f'Unexpected X screen size: {dimensions}')
    def type_login():
        for key in ('key type native', 'key Return', 'key type ' + password, 'key Return'):
            guest.monitor(key)
            time.sleep(.4)

    type_login()
    started = time.monotonic()
    retried = False
    while time.monotonic() - started < 150:
        state = guest.read_text("if pgrep -u native -f '^/usr/X11R7/bin/ctwm( |$)' >/dev/null; "
                                f"then echo session; elif {greeter}; then echo greeter; fi").strip()
        if state == 'session':
            break
        if state == 'greeter' and not retried and time.monotonic() - started > 20:
            type_login()
            retried = True
        time.sleep(1)
    else:
        raise RuntimeError('Native xdm login did not start ctwm')
    session = guest.read_text("id native; pgrep -lf -u native '^/usr/X11R7/bin/ctwm( |$)'")
    if '/usr/X11R7/bin/ctwm' not in session:
        raise RuntimeError(f'Unexpected native desktop: {session}')
    guest.wait_for("""win=$(xwininfo -root -tree | awk '/"UXTerm"|"XTerm"/ {print $1; exit}') """
                   """&& test -n "$win" && xwininfo -id "$win" | grep -q 'Map State: IsViewable'""", 90)
    lab.ci('screenshot', str(output / 'ctwm.png'))
    enter(lab, 'shutdown -p now')
    lab.wait('Done running shutdown hooks', 120)
    lab.logged_in = False
    # Kernel shutdown messages go to the framebuffer in graphical PROM mode.
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        if 'Machine: soft power-off' in (lab.directory / 'emulator.log').read_text(errors='replace'):
            break
        if lab.process.poll() is not None:
            if lab.process.returncode:
                raise RuntimeError(f'IRIS exited with {lab.process.returncode}')
            break
        time.sleep(.5)
    else:
        raise RuntimeError('IRIS did not observe guest power-off')
    return dict(kernel=kernel, session=session, dimensions=dimensions)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('iso', 'emulator', 'serial-prom', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--cpu', choices=('r4400', 'r5000'), default='r4400')
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    probe = load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = (args.emulator.resolve() / name for name in ('iris', 'iris-ci'))
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        work = Path(tmp)
        disk = work / 'blank.raw'
        with disk.open('xb') as stream:
            stream.truncate(6 * 1024**3)
        os.environ.update(IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(work / 'profile'))
        password = secrets.token_hex(6)
        setup = open_lab(probe, work / 'install', args.cpu, disk, args.serial_prom, args.iso.resolve())
        try:
            installer(setup, password)
        finally:
            setup.close()
            if setup.serial_log.exists():
                shutil.copyfile(setup.serial_log, out / 'install.log')
        boot = open_lab(probe, work / 'boot', args.cpu, disk, setup.directory / 'nvram.bin')
        try:
            result = native_login(boot, password, out)
        finally:
            boot.close()
            if boot.serial_log.exists():
                shutil.copyfile(boot.serial_log, out / 'boot.log')
        result.update(cpu=args.cpu, iso_sha256=sha256(args.iso), iris_sha256=sha256(probe.IRIS),
                      ctwm_png_sha256=sha256(out / 'ctwm.png'))
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(f'Passed blank-disk install and native xdm login: {out}', flush=True)


if __name__ == '__main__':
    main()
