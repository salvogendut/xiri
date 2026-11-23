"""Exercise IOC3 input and compare full-screen wsfb with the Xlib reference."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
IP28 = ROOT/'lab/ip28-kernel'


def prepare(out):
    media = out/'xorg.iso'
    files = [('xorg.sh', Path(__file__).with_name('xorg.sh')),
             ('frame.sh', Path(__file__).with_name('frame.sh')),
             ('xorg.conf', IP28/'xorg.conf'), ('framebuffer.c', IP28/'framebuffer.c'),
             ('probe.c', ROOT/'lab/indy-netbsd/x11/probe.c')]
    subprocess.run(['genisoimage', '-quiet', '-R', '-o', media, '-graft-points',
                    *(f'{name}={path}' for name, path in files)], check=True)
    return media


def run(lab, ci, out):
    serial = lab.serial_text()
    for pattern in (r'pckbd0 at iockbc0', r'pms0 at iockbc0',
                    r'wskbd0 at pckbd0: console keyboard', r'wsmouse0 at pms0'):
        if not re.search(pattern, serial):
            raise ValueError(f'missing native attachment: {pattern}')

    lab.monitor_command('key type echo octane-keyboard')
    lab.monitor_command('key Return')
    lab.wait(r'\noctane-keyboard\n', 30)
    lab.wait(r'# ', 10)
    lab.send('mount -r -t cd9660 /dev/cd0a /cdrom && sh /cdrom/xorg.sh; echo OCTANE_X_RC=$?')
    phase = lab.wait(r'XIRI_START_XORG|\nOCTANE_X_RC=\d+|panic:', 240)[0]
    if phase != 'XIRI_START_XORG':
        raise ValueError(f'guest framebuffer preflight failed: {phase}')
    spec = importlib.util.spec_from_file_location('ip28_scanout', IP28/'scanout.py')
    scanout = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scanout)
    deadline = time.monotonic() + 150
    path = out/'xorg.png'
    metrics = {}
    while time.monotonic() < deadline:
        if re.search(r'\nOCTANE_X_RC=\d+|panic:', lab.serial_text()[lab.offset:]):
            raise ValueError('Xorg exited before the reference frame')
        cmd = [ci, '--json', '--socket', lab.socket_path, 'screenshot', path]
        reply = subprocess.run(cmd, check=True, text=True, capture_output=True, timeout=10)
        if json.loads(reply.stdout).get('fresh') is True:
            metrics = scanout.check(path)
            if metrics['passed']:
                break
        time.sleep(1)
    else:
        raise ValueError(f'no matching Xorg scanout: {metrics}')
    for command in ('key type Xiri_123', 'key Return', 'ps2 mouse 10 5 0',
                    'ps2 mouse 0 0 1', 'ps2 mouse 0 0 0', 'ps2 mouse 0 0 4',
                    'ps2 mouse 0 0 0', 'ps2 mouse 0 0 2', 'ps2 mouse 0 0 0'):
        lab.monitor_command(command)
    status = lab.wait(r'\nOCTANE_X_RC=(\d+)\n', 180)[1]
    if status != '0':
        raise ValueError(f'guest Xorg input or drawing check failed: {status}')
    lab.wait(r'# ', 15)
    return dict(scanout=metrics, console_keyboard=True, typed='Xiri_123',
                relative_motion=True, pressed_and_released=[1, 2, 3])
