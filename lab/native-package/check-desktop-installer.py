#!/usr/bin/env python3
"""Exercise the authenticated desktop Software Manager entry on a private Indy."""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import Guest, load_probe, sha256
from freeware_lifecycle import close_browser, freeware_tab, game_window, history, logout, WINDOWS
from mozilla_lifecycle import login_catalog, open_browser, position, raise_catalog

spec = importlib.util.spec_from_file_location(
    'indy_desktop', Path(__file__).with_name('check-clean-desktop.py')
)
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)
parser = argparse.ArgumentParser(description=__doc__)
for arg in ('bundle', 'prerequisites', 'freeware', 'output', 'emulator'):
    parser.add_argument('--' + arg, type=Path, required=True)
parser.add_argument('--entry', type=Path, help='separate helper CD for the older prerequisites disc')
parser.add_argument('--kernel', type=Path, required=True)
parser.add_argument('--prepared', action='store_true', help='input disk already contains the desktop entry')
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True, exist_ok=False)
bundle = args.bundle.resolve()
disk = out / 'disk.chd'
subprocess.run(['cp', '--reflink=auto', bundle / 'netbsd-xiri.chd', disk], check=True)
shutil.copyfile(bundle / 'nvram.bin', out / 'nvram.bin')
config = (bundle / 'iris.toml').read_text().replace('netbsd-xiri.chd', 'disk.chd')
media = [(4, args.prerequisites), (5, args.freeware)]
if args.entry:
    media.append((6, args.entry))
for slot, iso in media:
    config += f'\n[scsi.{slot}]\ncdrom = true\npath = {json.dumps(str(iso.resolve()))}\n'
probe = load_probe()
probe.IRIS, probe.CI = (args.emulator.resolve() / n for n in ('iris', 'iris-ci'))
lab = probe.Lab(
    SimpleNamespace(mode='ordinary', debugger=False),
    out,
    config_text=config,
    working_directory=out,
    scsi1_from_config=True,
)
guest = Guest(lab)
from xiri_lab.kernel_log import KernelLog

pins = json.loads((ROOT / 'profiles/netbsd-sgimips-indy-11.99.11-utime-v1.json').read_text())
if sha256(args.kernel) != pins['artifacts']['kernel']['sha256']:
    raise ValueError('the test needs the matching v6 kernel symbols')
symbols = subprocess.check_output(['nm', '-n', args.kernel], text=True)
console = KernelLog(lab, int(next(l.split()[0] for l in symbols.splitlines() if l.endswith(' msgbufp')), 16))
result = {}
signal.signal(signal.SIGTERM, signal.default_int_handler)
os.environ.pop('IRIS_CHD_DIFF_DIR', None)


def enter(value):
    if value:
        guest.monitor('key type ' + value)
    guest.monitor('key Return')
    time.sleep(2)


def auth_window(action):
    x, y = raise_catalog(guest)
    guest.monitor(f'ptr click {x+445} {y+461} left')
    guest.wait_for(WINDOWS + ' | grep -q "Icon Catalog: DesktopTools"', 60)
    guest.capture(out / (action + '-desktop-tools.png'))
    guest.monitor(f'ptr click {x+246} {y+78} left 2')
    guest.wait_for(WINDOWS + ' | grep -q "Software Manager authorization"', 80)
    x, y = position(guest, 'Software Manager authorization')
    guest.monitor(f'ptr click {x+105} {y+55} left')


def administer(action):
    auth_window(action)
    enter('netbsdtest')
    # su reads the password on its controlling terminal. Wait for the
    # visible second prompt row, past the area occupied by a bare cursor.
    x, y = position(guest, 'Software Manager authorization')
    prompt = out / 'administrator-prompt.png'
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        guest.lab.monitor_command(f'screen shot {prompt}')
        with Image.open(prompt) as screen:
            line = screen.crop((x + 14, y + 15, x + 55, y + 29)).convert('L')
            if sum(line.histogram()[:80]) > 30:
                break
        time.sleep(0.5)
    else:
        raise TimeoutError('NetBSD su did not present its password prompt')
    enter('netbsdtest')
    guest.wait_for(WINDOWS + ' | grep -q "Software Manager media"', 100)
    enter('fw_xmahjongg')
    enter(action)
    main = 'Software Manager 4.1 -'
    guest.wait_for(WINDOWS + ' | grep -q "' + main + '"', 180)
    x, y = position(guest, main)
    guest.monitor(f'ptr click {x+310} {y+152} left')
    guest.wait_for(WINDOWS + ' | grep -q "Software Manager 4.1 - Custom Installations"', 90)
    guest.capture(out / (action + '-selection.png'))
    guest.monitor(f'ptr click {x+43} {y+513} left')
    dialog = 'askUser_popup.*550x244'
    dialog_id = f"$({WINDOWS} | awk '/{dialog}/ {{print $1; exit}}')"
    guest.wait_for(f'test -n "{dialog_id}" && xwininfo -id "{dialog_id}" | grep -q IsViewable', 360)
    x, y = position(guest, dialog)
    guest.monitor(f'ptr click {x+25} {y+155} left')
    guest.monitor(f'ptr click {x+508} {y+209} left')
    guest.wait_for('! xwininfo -root -tree | grep -q "Software Manager media"', 180)


try:
    lab.start(boot=False)
    lab.wait('login: ', 480)
    lab.send('root')
    lab.wait('xiri-indy# ', 40)
    lab.logged_in = True
    desktop.greeter(guest)
    guest.command('mkdir -p /cdrom && mount -rt cd9660 /dev/cd0a /cdrom')
    if not args.prepared:
        guest.command('sh /cdrom/prepare-live-base.sh /cdrom >/var/tmp/xiri-base.log 2>&1', 1800)
    source = '/cdrom'
    if args.entry:
        source = '/mnt/entry'
        guest.command(
            'mkdir -p /mnt/entry && (test -b /dev/cd2a || (cd /dev && sh MAKEDEV cd2)) && mount -rt cd9660 /dev/cd2a /mnt/entry'
        )
    guest.command(f'sh {source}/install-entry.sh && sh {source}/install-entry.sh')
    if args.entry:
        guest.command('umount /mnt/entry')
    guest.command('umount /cdrom')
    guest.command(
        "sha256 /emul/irix/usr/lib/filetype/desktop.otr /emul/irix/usr/sbin/swmgr /emul/irix/var/netscape/mozilla/mozilla-bin /usr/people/xiritest/.xsession >/root/installer-preserved.sha"
    )
    login_catalog(guest, desktop.greeter, desktop.login)
    catalog = '/emul/irix/usr/lib/desktop/iconcatalog/pages/C'
    links = rf'find {catalog} -type l ! -path "*/Freeware/*" -exec ls -ld {{}} \; | sort'
    baseline = guest.read_text(links)
    release = guest.read_text("awk '{print $1}' /var/db/xiri-install/installed").strip()
    administer('install')
    result['installed'] = history(guest)
    if 'fw_xmahjongg.sw.xmahjongg' not in result['installed']:
        raise ValueError('The SGI installation history lacks the game')
    guest.command(
        'test -x /emul/irix/usr/freeware/bin/xmahjongg && test -f /emul/irix/var/inst/xiri-filetypes/xmahjongg'
    )
    logout(guest)
    login_catalog(guest, desktop.greeter, desktop.login)
    x, y = freeware_tab(guest)
    guest.monitor(f'ptr click {x+215} {y+80} left 2')
    guest.wait_for(WINDOWS + ' | grep -q XMahjongg', 150)
    result['game'] = game_window(guest, out)
    logout(guest)
    login_catalog(guest, desktop.greeter, desktop.login)
    administer('remove')
    guest.command(
        'sha256 -c /root/installer-preserved.sha && test ! -e /emul/irix/usr/freeware/bin/xmahjongg && test ! -L /emul/irix/usr/lib/desktop/iconcatalog/pages/C/Freeware/xmahjongg && test -L /emul/irix/usr/lib/desktop/iconcatalog/pages/C/Freeware/FreewareRelnotes'
    )
    result['removed'] = history(guest)
    if (
        any(row.startswith('fw_xmahjongg') for row in result['removed'])
        or 'fw_common.sw.index' not in result['removed']
    ):
        raise ValueError('Unexpected SGI history after removal')
    if guest.read_text(links) != baseline or not baseline.strip():
        raise ValueError('An unrelated catalog link changed')
    result['preserved_catalog_links'] = len(baseline.splitlines())
    open_browser(guest, release, 'Welcome to Xiri')
    guest.capture(out / 'preserved-browser.png')
    close_browser(guest, 'Welcome to Xiri')
    result['restored'] = True
    logout(guest)
    desktop.greeter(guest)
except Exception as exc:
    result['error'] = str(exc)
    if lab.monitor:
        try:
            guest.capture(out / 'failure.png')
        except Exception:
            pass
    raise
finally:
    try:
        if lab.logged_in:
            try:
                console.halt()
            except Exception as exc:
                result['halt_error'] = str(exc)
        lab.close()
    finally:
        result.update(
            stopped=lab.process is None or lab.process.poll() is not None, halted=lab.clean_shutdown
        )
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
