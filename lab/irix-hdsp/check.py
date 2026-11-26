#!/usr/bin/env python3
"""Install the native HDSP add-on on a private v6 Indy and exercise the SGI audio controls."""
from pathlib import Path
import re
import shlex
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'lab/native-package')]
from xiri_lab.indy_addon import load_desktop, run_indy_addon
from mozilla_lifecycle import login_catalog, position, raise_catalog, reboot
from freeware_lifecycle import logout


def open_panel(guest, icon, pattern):
    tree = 'xwininfo -root -tree'
    x, y = raise_catalog(guest)
    guest.monitor(f'ptr click {x+315} {y+461} left')
    guest.wait_for(tree + ' | grep -q "Icon Catalog: ControlPanels"', 60)
    guest.monitor(f'ptr click {x+icon[0]} {y+icon[1]} left 2')
    guest.wait_for(tree + ' | grep -Eq ' + shlex.quote(pattern), 90)
    return position(guest, pattern)


def click(guest, x, y):
    guest.monitor(f'ptr move {x} {y}')
    time.sleep(.5)
    guest.monitor('ptr down left')
    time.sleep(.35)
    guest.monitor('ptr up left')


def key_click(guest):
    query = guest.read_text('xset q')
    return int(re.search(r'key click percent:\s*(\d+)', query)[1])


AUDIO_PANEL = '"apanel" "Apanel"[)] +[0-9]+x[0-9]+'


def exercise_audio_controls(guest, report, x, y):
    out = guest.lab.directory
    read = lambda: guest.read_text('mixerctl -n outputs.master').strip()
    levels = [read()]
    for column, row in ((76, 112), (96, 143)):
        guest.monitor(f'ptr click {x+column} {y+row} middle')
        guest.wait_for('test "$(mixerctl -n outputs.master)" != ' + shlex.quote(levels[-1]), 30)
        levels.append(read())
    if levels[0] != '0,0' or not all(re.fullmatch(r'\d+,\d+', level) for level in levels):
        raise RuntimeError(f'Unexpected native mixer response: {levels}')
    if int(levels[1].split(',')[0]) <= int(levels[2].split(',')[0]):
        raise RuntimeError(f'Expected the second slider position to be quieter: {levels}')
    report['gui_mixer_levels'] = levels
    guest.capture(out / 'audiopanel.png')
    guest.monitor('key ctrl+q')
    guest.wait_for('! xwininfo -root -tree | grep -Eq ' + shlex.quote(AUDIO_PANEL), 60)


def check_audio_panel(guest, report):
    x, y = open_panel(guest, (216, 72), AUDIO_PANEL)
    exercise_audio_controls(guest, report, x, y)


def check(guest):
    desktop = load_desktop()
    cmd = guest.command
    out = guest.lab.directory
    mount = 'mount -rt cd9660 /dev/cd0a /cdrom'
    cmd('mkdir -p /cdrom && ' + mount)
    cmd('sh /cdrom/install.sh && sh /cdrom/install.sh --restore')
    cmd('test ! -L /emul/irix/dev/hdsp/hdsp0master && '
        'test ! -L /emul/irix/dev/hdsp/hdsp0events && test ! -e /etc/rc.d/xiri_hdsp')
    cmd('sh /cdrom/install.sh && sh /cdrom/install.sh')
    reboot(guest)
    cmd(mount)
    cmd('test -c /emul/irix/dev/hdsp/hdsp0events && test -c /emul/irix/dev/hdsp/hdsp0master')
    cmd('install -m 755 /cdrom/hdsp-query /tmp/hdsp-query')
    for probe in ('cvt-32', 'cvt-n32', 'trunc-32', 'trunc-n32'):
        cmd(f'install -m 555 /cdrom/{probe} /tmp/{probe} && su -m xiritest -c /tmp/{probe}')
    original = guest.read_text('mixerctl -n outputs.master').strip()
    if not re.fullmatch(r'\d+,\d+', original):
        raise ValueError('Unexpected HAL2 stereo mixer value: ' + original)
    call = 'su -m xiritest -c '
    cmd(call + '/tmp/hdsp-query >/tmp/hdsp.info && '
        'grep -Fxq "DEVICES 00000001 00000006 " /tmp/hdsp.info && '
        'grep -Fxq "OUTPUTS 00000001 00000006 " /tmp/hdsp.info && '
        'grep -Fxq "INTERFACES 00000001 00000016 " /tmp/hdsp.info')
    device = guest.read_text(call + '"audiocfg list"')
    rate = int(re.search(r'playback: [^\n]*?([0-9]+)Hz', device)[1])
    cmd('grep -Fqx "VALUE 00000006 1000000d 00000001 00010000 ' +
        f'{rate:08x} 00000000 ' + '" /tmp/hdsp.info')
    cmd('mixerctl -w outputs.master=0,0 && ' + call + '"/tmp/hdsp-query --event-test" >/tmp/hdsp.event')
    event = guest.read_text('cat /tmp/hdsp.event').splitlines()
    cmd('mixerctl outputs.master | grep -Fx outputs.master=64,128')
    cmd('mixerctl -w outputs.master=0,0')
    login_catalog(guest, desktop.greeter, desktop.login)
    sounds = '"DtSounds" "DtSounds"[)] +270x454'
    x, y = open_panel(guest, (756, 148), sounds)
    before = key_click(guest)
    click(guest, x+59, y+302)
    changed = key_click(guest)
    click(guest, x+59, y+302)
    restored = key_click(guest)
    if before == changed or before != restored:
        raise RuntimeError(f'Keyboard click: {before} -> {changed} -> {restored}')
    guest.capture(out / 'sounds.png')
    click(guest, x+66, y+411)
    guest.wait_for('! xwininfo -root -tree | grep -Eq ' + shlex.quote(sounds), 60)
    installed_module = guest.read_text('sha256 -q /cdrom/compat_irix_o32.kmod').strip()
    installed_kernel = guest.read_text('sha256 -q /netbsd').strip()
    installed_boot = guest.read_text('sha256 -q /netbsd.boot').strip()
    report = dict(module_sha256=installed_module, installed_kernel_sha256=installed_kernel,
                  installed_boot_sha256=installed_boot, conversion_probes=['cvt-32','cvt-n32','trunc-32','trunc-n32'],
                  native_sample_rate_hz=rate, mixer_before=original, stereo_probe='64,128', gain_event=event,
                  key_click_percent=[before, changed, restored])
    check_audio_panel(guest, report)
    cmd('mixerctl -w outputs.master=' + original)
    logout(guest)
    desktop.greeter(guest)
    report['logout_to_xdm'] = True
    cmd('sh /cdrom/install.sh --restore')
    reboot(guest)
    module = '$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod'
    cmd('for f in /netbsd /netbsd.boot ' + module + '; do cmp -s "$f" "$f.pre-hdsp" || exit 1; done')
    cmd('test ! -e /var/run/xiri-hdsp/events && test ! -L /emul/irix/dev/hdsp/hdsp0master')
    desktop.greeter(guest)
    report['restored_v6_after_reboot'] = True
    return report


if __name__ == '__main__':
    run_indy_addon(check, __doc__)
