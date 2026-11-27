#!/usr/bin/env python3
"""Install the saver CD on a temporary copy of an Indy desktop and exercise Qix."""
from pathlib import Path
from functools import partial
import sys
import time

from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'lab/native-package')]
from xiri_lab.indy_addon import load_desktop, run_indy_addon
from mozilla_lifecycle import position, raise_catalog, login_catalog
from freeware_lifecycle import logout

desktop = load_desktop()


def click(guest, x, y):
    guest.monitor(f'ptr move {x} {y}')
    time.sleep(.7)
    guest.monitor('ptr down left')
    time.sleep(.35)
    guest.monitor('ptr up left')
    time.sleep(1)


def capture(guest, name):
    path = guest.lab.directory / (name + '.png')
    guest.monitor('screen shot ' + str(path))
    with Image.open(path) as frame:
        return frame.convert('RGB')


def animation(guest, name):
    frames = []
    for i in range(3):
        time.sleep(2)
        frame = capture(guest, name + str(i)).crop((80, 80, 1200, 940))
        if frame.convert('L').histogram()[0] < frame.width * frame.height * .85:
            raise RuntimeError(name + ' did not cover the display')
        frames.append(frame)
    changed = [sum(ImageChops.difference(a, b).convert('L').histogram()[1:]) for a, b in zip(frames, frames[1:])]
    if min(changed) < 1000:
        raise RuntimeError(f'{name} remained still: {changed}')
    guest.monitor('key space')
    for _ in range(12):
        time.sleep(.4)
        desk = capture(guest, name + '-wake')
        if desk.getpixel((850, 810)) == (134, 168, 200):
            return changed
    raise RuntimeError(name + ' did not return to Icon Catalog')


def check(guest, *, session_update=False):
    guest.command('mkdir -p /cdrom && mount -rt cd9660 /dev/cd0a /cdrom')
    guest.command('/etc/rc.d/xdm stop')
    guest.wait_for('! pgrep -x Xorg >/dev/null', 60)
    restore = [' --restore-session'] if session_update else []
    for action in ['', *restore, ' --restore-xorg', '', '']:
        guest.command('sh /cdrom/install.sh' + action)
    guest.command('/etc/rc.d/xdm start')
    return check_session(guest, check_next_login=session_update)


def open_panel(guest):
    x, y = raise_catalog(guest)
    guest.monitor(f'ptr click {x+315} {y+461} left')
    guest.wait_for('xwininfo -root -tree | grep -q "Icon Catalog: ControlPanels"', 60)
    # The catalog can update its title before it finishes laying out the icons.
    guest.monitor(f'ptr move {x+638} {y+148}')
    time.sleep(1)
    guest.monitor(f'ptr click {x+638} {y+148} left 2')
    panel = '"ScreenSaver"[)] +300x420'
    visible = "xwininfo -root -tree | grep -Eq '" + panel + "'"
    try:
        guest.wait_for(visible, 30)
    except RuntimeError:
        guest.monitor(f'ptr click {x+638} {y+176} left 2')
        guest.wait_for(visible, 60)
    return position(guest, panel)


def check_session(guest, check_next_login=False):
    login_catalog(guest, desktop.greeter, desktop.login)
    guest.command("xdpyinfo | grep -qx '    SCREEN-SAVER' && xdpyinfo | grep -qx '    MIT-SCREEN-SAVER'")
    x, y = open_panel(guest)
    click(guest, x+15, y+116)
    guest.wait_for("xset q | grep -Eq 'timeout: +600 '", 45)
    for _ in range(4):
        click(guest, x+70, y+306)
        time.sleep(2)
        row = capture(guest, 'settings').crop((x+66, y+301, x+102, y+313)).convert('L')
        if sum(row.histogram()[:40]) > 200:
            break
    else:
        raise RuntimeError('Qix was not selected')
    click(guest, x+210, y+199)
    demo = animation(guest, 'demo')
    # Use the server's actual inactivity timer, leaving the panel's preference intact.
    guest.command('xset s 8 600')
    time.sleep(16)
    idle = animation(guest, 'idle')
    guest.command('xset s 600 600')
    if check_next_login:
        click(guest, x+96, y+378)
        guest.wait_for("""! xwininfo -root -tree | grep -Eq '"ScreenSaver"[)] +300x420'""", 45)
        saved = guest.read_text('cat /usr/people/xiritest/.desktop-$(hostname)/panelsession')
        if '/usr/bin/X11/xlock -mode qix -besaver -nolock' not in saved:
            raise RuntimeError('The panel did not save the selected Qix command')
        logout(guest)
        login_catalog(guest, desktop.greeter, desktop.login)
        guest.command("xset q | grep -Eq 'timeout: +600 '")
        guest.command("grep -q '^/emul/irix/usr/bin/X11/xlock ' \"$job/panelsession\"")
        if guest.read_text('cat /usr/people/xiritest/.desktop-$(hostname)/panelsession') != saved:
            raise RuntimeError('Session replay changed the saved Screen Saver settings')
        guest.command('xset s 8 600')
        time.sleep(16)
        next_idle = animation(guest, 'next-login')
        guest.command('xset s 600 600')
        x, y = open_panel(guest)
    click(guest, x+15, y+116)
    guest.wait_for("xset q | grep -Eq 'timeout: +0 '", 40)
    click(guest, x+96, y+378)
    logout(guest)
    desktop.greeter(guest)
    guest.command("! ps -axww -o args | grep -Eq '(^|[ (])(/emul/irix)?[/]usr/bin/X11/xlock([ )]|$)'")
    result = dict(demo_changed_pixels=demo, idle_changed_pixels=idle, idle_timeout_seconds=8,
                key_wake='Space (Demo and idle)', original_timeout_seconds=600,
                disabled_timeout_seconds=0, logout_to_xdm=True)
    if check_next_login:
        result['next_login_idle_changed_pixels'] = next_idle
    return result


def main():
    run_indy_addon(check, __doc__, check_audio_v8=partial(check, session_update=True),
                   check_installed=partial(check_session, check_next_login=True))


if __name__ == '__main__':
    main()
