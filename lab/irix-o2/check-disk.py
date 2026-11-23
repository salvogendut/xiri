#!/usr/bin/env python3
"""Cold-boot a standalone O2 disk and check the graphical sessions on a private overlay."""
import argparse
import json
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageChops

from o2_console import halt_to_prom

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import Guest, load_probe, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'emulator', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--check-greeter', action='store_true',
                        help='compare the bitmap greeting, prompts and typed username with the O2 reference')
    parser.add_argument('--frame-kernel', type=Path,
                        help='NetBSD kernel installed in the framed graphics console bundle')
    parser.add_argument('--netbsd', type=Path, default=ROOT.parent / 'NetBSD-xiri')
    args = parser.parse_args()
    bundle, emulator, out = (p.resolve() for p in (args.bundle, args.emulator, args.output))
    out.mkdir(parents=True, exist_ok=False)
    probe = load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = emulator / 'iris', emulator / 'iris-ci'
    inputs = {p: sha256(p) for p in (bundle/'netbsd-xiri.chd', bundle/'nvram.bin',
                                      bundle/'iris.toml', probe.IRIS, probe.CI)}
    subprocess.run(['cp', '--reflink=auto', bundle/'netbsd-xiri.chd', out/'netbsd-xiri.chd'], check=True)
    shutil.copyfile(bundle/'nvram.bin', out/'nvram.bin')
    config = (bundle/'iris.toml').read_text().replace('ci = false', 'ci = true')
    lab = probe.Lab(SimpleNamespace(mode='ci', debugger=False), out,
                    config_text=config, working_directory=out,
                    scsi1_from_config=True)
    guest = Guest(lab)
    result = {'sessions': [], 'inputs': {p.name: digest for p, digest in inputs.items()}}

    if args.frame_kernel:
        sys.path.insert(0, str(ROOT / 'lab/ip30-impact'))
        import wsconsole
        font = wsconsole.glyphs(args.netbsd)
        reference = wsconsole.console_frame.load_reference(args.netbsd / 'xiri/graphics/sgiconsole.png')

    def console(name, expected, timeout=20, row=None):
        path = out / (name + '.png')
        wsconsole.capture(lab, probe.CI, path, font, expected, reference=reference,
                          marker_row=row, timeout=timeout)
        return dict(wsconsole.console_frame.check(reference, path), visible_text=expected)

    def screenshot(name):
        path = out / (name + '.png')
        reply = subprocess.run([probe.CI, '--json', '--socket', lab.socket_path, 'screenshot', path],
                               check=True, capture_output=True, text=True, timeout=15)
        if json.loads(reply.stdout).get('fresh') is not True:
            raise RuntimeError('could not obtain fresh GBE scanout')
        return path.name

    def check_glyphs(name, regions):
        reference = ROOT / 'docs/results/2026-11-23-o2-xdm-password.png'
        with Image.open(reference) as expected, Image.open(out / name) as actual:
            for label, box in regions.items():
                # Exclude the blinking caret and compare the ink in each letter.
                def ink(frame):
                    return frame.crop(box).convert('L').point(lambda value: 255 if value < 80 else 0)
                if ImageChops.difference(ink(expected), ink(actual)).getbbox():
                    raise ValueError(f'{label} glyphs differ in {name}')
                result.setdefault('greeter_glyphs', []).append(label)

    def press(key):
        for event in ('keydown', 'keyup'):
            if 'ok' not in guest.monitor(f'o2 {event} {key}'):
                raise ValueError('O2 keyboard did not accept ' + key)
            time.sleep(.18)

    def check_failed_login():
        for field in ('xiriunknown', 'invalid'):
            for ch in field:
                press('Key' + ch.upper())
            press('Enter')
            time.sleep(.5)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            path = out / screenshot('xdm-rejected')
            with Image.open(path) as frame:
                # The stock greeter draws its failure message in dark red.
                area = frame.crop((335, 425, 740, 540)).convert('RGB')
                colors = area.getcolors(area.width * area.height)
                if sum(n for n, (r, g, b) in colors if r > 70 and max(g, b) < 30) >= 50:
                    result['rejected_login'] = True
                    return
            time.sleep(.25)
        raise ValueError('xdm did not display its failed-login message')

    def login(user):
        # Give xdm time to map the widget and take its keyboard grab.
        time.sleep(3)
        for field in ('username', 'password'):
            for ch in user:
                press('Key' + ch.upper())
            inspect = args.check_greeter and user == 'xiritest' and field == 'username'
            if inspect:
                time.sleep(.5)
                check_glyphs(screenshot('xdm-username'), {'xiritest': (480, 384, 548, 403)})
            press('Enter')
            time.sleep(2)
            if inspect:
                check_glyphs(screenshot('xdm-password'), {'Password': (350, 405, 460, 434)})

    def greeter():
        guest.wait_for('test -s /tmp/.X0-lock', 90)
        guest.command("export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | "
                      "awk '$1 == \"/usr/X11R7/bin/Xorg\" {for(i=1;i<NF;i++) "
                      "if($i == \"-auth\") print $(i+1)}'); export XAUTHORITY; test -s \"$XAUTHORITY\"")
        guest.wait_for("xwininfo -root -tree | grep -q '\"xlogin\"'", 90)

    def interrupt(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupt)
    try:
        lab.start(boot=False)
        if args.frame_kernel:
            result['boot_frame'] = console('boot-console', ['root on sd0a', 'Starting root file system check:'],
                                           timeout=180)
            path = out / 'boot-console.png'
            lines = wsconsole.screen_lines(path, font)
            row = next(i for i, line in enumerate(lines) if 'root on sd0a' in line)
            left, top, right, _ = wsconsole.console_frame.PANEL
            with Image.open(path) as image:
                ink = image.convert('RGB').crop((left, top + 16*row, right, top + 16*(row+1)))
                if (199, 199, 199) not in {rgb for _, rgb in ink.getcolors(ink.width * ink.height)}:
                    raise ValueError('kernel text did not render in the framed console foreground')
            result['boot_frame']['kernel_foreground_rgb'] = [199, 199, 199]
        else:
            lab.wait(r'file netbsd\.boot', 150)
            lab.wait(r'boot device: sd0', 180)
            lab.wait(r'root on sd0a', 30)
        lab.wait(r'login: ', 360)
        lab.send('root')
        lab.wait(r'xiri-indy# ', 30)
        lab.logged_in = True
        guest.command('export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/X11R7/bin:/usr/local/bin; '
                      'test "$(sysctl -n hw.model)" = SGI-IP32 && modstat | grep "^compat_irix_o32 "')
        if args.frame_kernel:
            guest.command('test "$(sha256 -q /netbsd)" = ' + sha256(args.frame_kernel))
            result['serial_recovery'] = guest.read_text('tty').strip()
            if result['serial_recovery'] != '/dev/ttyC0':
                raise ValueError(result['serial_recovery'])
        result['vendor_shell'] = guest.read_text("/emul/irix/bin/sh -c 'echo O2_VENDOR_SHELL_OK'").strip()
        if result['vendor_shell'] != 'O2_VENDOR_SHELL_OK':
            raise ValueError('IRIX shell did not return the expected output')
        greeter()
        result['display'] = guest.read_text('xdpyinfo | grep dimensions:').strip()
        if '1280x1024' not in result['display']:
            raise ValueError(result['display'])
        result['greeter'] = screenshot('xdm')
        if args.check_greeter:
            check_glyphs(result['greeter'], {'Welcome': (350, 283, 730, 343),
                                             'Login': (404, 377, 467, 405)})
            check_failed_login()
        login('xiritest')
        guest.wait_for("pgrep -u xiritest -f '^/emul/irix/usr/bin/X11/4Dwm( |$)' >/dev/null", 150)
        guest.wait_for("grep -q 'Logs: ' /usr/people/xiritest/.xsession-errors", 60)
        guest.command('job=$(sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors | tail -1); '
                      'test -d "$job"; XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
                      'test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; '
                      'export XAUTHORITY DISPLAY=127.0.0.1:0; test -r "$XAUTHORITY"')
        guest.wait_for("xwininfo -root -tree | grep -q '\"Icon Catalog: '", 100)
        tree = guest.read_text('xwininfo -root -tree')
        (out/'4dwm-windows.txt').write_text(tree)
        result['sessions'].append({'user': 'xiritest', 'wm': '4Dwm', 'screen': screenshot('4dwm')})
        guest.command('su -m xiritest -c "env XIRI_SESSION_DIR=\'$job\' /usr/local/bin/xiri-logout"')
        greeter()
        result['irix_logout'] = True
        login('netbsdtest')
        guest.wait_for("pgrep -u netbsdtest -f '(^|/)ctwm( |$)' >/dev/null", 90)
        guest.command('export XAUTHORITY=/home/netbsdtest/.Xauthority DISPLAY=:0; '
                      'xdpyinfo | grep 1280x1024')
        result['sessions'].append({'user': 'netbsdtest', 'wm': 'ctwm', 'screen': screenshot('ctwm')})
        guest.command('pkill -u netbsdtest -x /usr/X11R7/bin/ctwm')
        greeter()
        result['native_logout'] = True
        if args.frame_kernel:
            guest.command('/etc/rc.d/xdm stop')
            guest.wait_for('! pgrep -x Xorg >/dev/null', 60)
            guest.command("echo 'O2 console restored' > /dev/ttyE0")
            result['restored_frame'] = console('console-after-xorg', ['O2 console restored'])
            guest.command(r"printf '\033[2J\033[2;1HXiri scroll marker\033[42;1H' > /dev/ttyE0")
            console('before-scroll', ['Xiri scroll marker'], row=1)
            guest.command(r"printf '\n' > /dev/ttyE0")
            console('after-scroll', ['Xiri scroll marker'], row=0)
            result['scroll'] = wsconsole.console_frame.check_scroll_captures(
                reference, out/'before-scroll.png', out/'after-scroll.png')
            if not result['scroll']['passed']:
                raise ValueError('console scroll did not preserve the border')
            halt_to_prom(lab)
            lab.close()
            # Cold-boot the overlay just exercised, including its saved filesystem state.
            reboot = out / 'reboot'
            reboot.mkdir()
            shutil.copyfile(out/'nvram.bin', reboot/'nvram.bin')
            lab = probe.Lab(SimpleNamespace(mode='ci', debugger=False), reboot,
                            config_text=config, working_directory=out, scsi1_from_config=True)
            lab.start(boot=False)
            phrase = '/dev/rsd0a: file system is clean; not checking'
            wsconsole.capture(lab, probe.CI, reboot/'root-clean.png', font, [phrase],
                              reference=reference, timeout=180)
            result['clean_root_on_reboot'] = True
            lab.wait(r'login: ', 360)
            lab.send('root')
            lab.wait(r'xiri-indy# ', 30)
            lab.logged_in = True
            halt_to_prom(lab)
    except BaseException as error:
        result['error'] = f'{type(error).__name__}: {error}'
        if lab.process and lab.process.poll() is None:
            try:
                screenshot('last-screen')
            except (ValueError, RuntimeError, subprocess.SubprocessError):
                pass
        raise
    finally:
        lab.close()
        result['stopped'] = lab.process is None or lab.process.poll() is not None
        result['clean_halt'] = lab.clean_shutdown
        result['originals_unchanged'] = all(sha256(p) == digest for p, digest in inputs.items())
        required = ['native_logout', 'irix_logout', 'stopped', 'clean_halt', 'originals_unchanged']
        if args.frame_kernel:
            required.append('clean_root_on_reboot')
        result['passed'] = 'error' not in result and all(result.get(k) for k in required)
        (out/'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if not result['passed']:
        raise RuntimeError('O2 qualification incomplete')


if __name__ == '__main__':
    main()
