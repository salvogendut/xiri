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

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import Guest, load_probe, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'emulator', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
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

    def screenshot(name):
        path = out / (name + '.png')
        reply = subprocess.run([probe.CI, '--json', '--socket', lab.socket_path, 'screenshot', path],
                               check=True, capture_output=True, text=True, timeout=15)
        if json.loads(reply.stdout).get('fresh') is not True:
            raise RuntimeError('could not obtain fresh GBE scanout')
        return path.name

    def login(user):
        # Give xdm time to map the widget and take its keyboard grab.
        time.sleep(3)
        for field in (user, user):
            for key in [*('Key' + ch.upper() for ch in field), 'Enter']:
                for event in ('keydown', 'keyup'):
                    if 'ok' not in guest.monitor(f'o2 {event} {key}'):
                        raise ValueError('O2 keyboard did not accept ' + key)
                    time.sleep(.18)
            time.sleep(2)

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
        lab.wait(r'file netbsd\.boot', 150)
        lab.wait(r'boot device: sd0', 180)
        lab.wait(r'root on sd0a', 30)
        lab.wait(r'login: ', 360)
        lab.send('root')
        lab.wait(r'xiri-indy# ', 30)
        lab.logged_in = True
        guest.command('export PATH=/bin:/sbin:/usr/bin:/usr/sbin:/usr/X11R7/bin:/usr/local/bin; '
                      'test "$(sysctl -n hw.model)" = SGI-IP32 && modstat | grep "^compat_irix_o32 "')
        result['vendor_shell'] = guest.read_text("/emul/irix/bin/sh -c 'echo O2_VENDOR_SHELL_OK'").strip()
        if result['vendor_shell'] != 'O2_VENDOR_SHELL_OK':
            raise ValueError('IRIX shell did not return the expected output')
        greeter()
        result['display'] = guest.read_text('xdpyinfo | grep dimensions:').strip()
        if '1280x1024' not in result['display']:
            raise ValueError(result['display'])
        result['greeter'] = screenshot('xdm')
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
        result['passed'] = all(result.get(k) for k in
                               ('native_logout', 'irix_logout', 'stopped', 'clean_halt', 'originals_unchanged'))
        (out/'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if not result['passed']:
        raise RuntimeError('O2 qualification incomplete')


if __name__ == '__main__':
    main()
