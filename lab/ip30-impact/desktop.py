"""Run the module lifecycle and the installed Xiri desktop on an Octane."""
import json
from pathlib import Path
import subprocess

from PIL import Image
from xiri_lab import sha256

ROOT = Path(__file__).resolve().parents[2]


def prepare(out, module, asa):
    lab = ROOT / 'lab'
    manifest = json.loads((lab / 'irix-reference/manifest.json').read_text())
    expected = next(entry['sha256'] for entry in manifest['candidates']
                    if entry['path'] == '/usr/bin/asa')
    if sha256(asa) != expected:
        raise ValueError('asa does not match the IRIX reference manifest')
    files = {'compat_irix_o32.kmod': module, 'vendor-asa': asa,
             'check-module.sh': lab / 'ip28-kernel/check-module.sh',
             'check-desktop.sh': lab / 'ip28-kernel/check-desktop.sh',
             'runner.c': lab / 'irix-lp64/runner.c', 'lifecycle.c': lab / 'irix-module/lifecycle.c',
             'type-ready.c': lab / 'irix-4dwm/type-ready.c',
             'desktop.sh': Path(__file__).with_name('desktop.sh')}
    iso = out / 'desktop.iso'
    subprocess.run(['genisoimage', '-quiet', '-R', '-o', iso, '-graft-points',
                    *(f'{name}={path.resolve()}' for name, path in files.items())], check=True)
    return iso


def run(lab, ci, out):
    # wsdisplay suppresses text-console output while X owns the screen.
    # The guest signals frame readiness on the independent IOC3 serial port.
    lab.send('mount -r -t cd9660 /dev/cd0a /cdrom && sh /cdrom/desktop.sh; echo OCTANE_DESKTOP_RC=$?')
    status = lab.wait(r'\nOCTANE_FRAME_READY\n|\nOCTANE_DESKTOP_RC=\d+\n|panic:', 600)
    if status[0].strip() != 'OCTANE_FRAME_READY':
        raise ValueError('desktop did not reach frame capture: ' + lab.serial_text()[-1800:])
    path = out / 'desktop.png'
    reply = subprocess.run([ci, '--json', '--socket', lab.socket_path, 'screenshot', path],
                           check=True, text=True, capture_output=True, timeout=15)
    if json.loads(reply.stdout).get('fresh') is not True:
        raise ValueError('missing fresh desktop frame')
    with Image.open(path) as image:
        colors = image.convert('RGB').getcolors(32)
        if image.size != (1280, 1024) or (colors is not None and len(colors) < 32):
            raise ValueError('unexpected desktop size or colour count')
    lab.monitor_command('key type touch "$XIRI_SESSION_DIR/ip30-captured"')
    lab.monitor_command('key Return')
    status = lab.wait(r'\nOCTANE_DESKTOP_RC=(\d+)\n|panic:', 240)
    if status[1] != '0':
        raise ValueError('desktop interaction or logout failed: ' + lab.serial_text()[-1800:])
    lab.wait(r'# ', 10)
    return dict(module_lifecycle=True, wm='4Dwm', clients=['Toolchest', 'Icon Catalog', 'winterm'],
                uid=1234, home='/usr/people/xiritest', size=[1280, 1024],
                png_sha256=sha256(path), logout=True)
