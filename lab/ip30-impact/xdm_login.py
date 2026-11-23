"""Qualify the packaged Octane using the keyboard, pointer and guest scanout."""
import re
import time

from PIL import Image

from xiri_lab import sha256


def focus_terminal(lab, wm):
    # Xorg uses a software pointer. On this profile these PS/2 deltas
    # reach winterm's exposed title bar even with File Manager in front.
    movement = '635 22' if wm == '4Dwm' else '200 100'
    for command in ('ps2 mouse -1700 -1700 0', 'ps2 mouse ' + movement + ' 0',
                    'ps2 mouse 0 0 1', 'ps2 mouse 0 0 0'):
        lab.monitor_command(command)
        time.sleep(.4)


def qualify(lab, out):
    screen = out / 'current.png'
    results = {'sessions': [], 'screenshots': {}}

    def frame():
        if 'saved ' not in lab.monitor_command(f'screen shot {screen}'):
            raise RuntimeError('unable to capture the Octane screen')
        with Image.open(screen) as image:
            if image.size != (1280, 1024):
                raise ValueError(f'unexpected screen size {image.size}')
            return image.convert('RGB')

    def visible(state):
        image = frame()
        # Sample flat areas of the shipped greeter, terminal and backdrop.
        # The guest-side checks below also identify the actual WM and account.
        if state == 'proof':
            # A native xterm opens here only after the user's shell has
            # written the requested evidence and checked the display size.
            region = image.crop((850, 500, 1270, 880))
            return any(count > 2000 and g > 180 and r < 35 and b < 35
                       for count, (r, g, b) in region.getcolors(region.width * region.height))
        pixels = image.getpixel
        if state == 'greeter':
            return pixels((400, 320)) == (254, 254, 254) and pixels((1000, 700)) == (0, 0, 0)
        if state == '4Dwm':
            return pixels((690, 145)) == (0, 0, 62) and pixels((1050, 100)) != (0, 0, 0)
        return pixels((210, 170)) == (0, 0, 0) and pixels((1000, 700)) == (0, 34, 68)

    def wait_screen(state, timeout=200):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if visible(state):
                return
            time.sleep(1)
        raise TimeoutError(f'{state} did not appear')

    def save(name):
        frame()
        path = out / (name + '.png')
        path.write_bytes(screen.read_bytes())
        results['screenshots'][name] = dict(size=[1280, 1024], sha256=sha256(path))

    def key(text):
        # The monitor queues a full text burst faster than wscons can drain it.
        for char in text:
            if char == ' ':
                lab.monitor_command('key Space')
            else:
                reply = lab.monitor_command('key type ' + char)
                if 'typed 1 of 1 chars' not in reply:
                    raise ValueError('keyboard input failed: ' + reply)
            time.sleep(.035)
        lab.monitor_command('key Return')
        time.sleep(.4)

    def login(user, wm):
        key(user)
        key(user)
        wait_screen(wm)
        # Let saved applications finish mapping before taking keyboard focus.
        time.sleep(30 if wm == '4Dwm' else 3)
        focus_terminal(lab, wm)

    lab.wait('Starting xdm.', 480)
    wait_screen('greeter')
    save('xdm-greeter')
    sessions = [('xiritest', '4Dwm', '/usr/people/xiritest', 1234, 'xdm-irix'),
                ('netbsdtest', 'ctwm', '/home/netbsdtest', 1236, 'xdm-native')]
    for user, wm, home, uid, shot in sessions:
        login(user, wm)
        for attempt in range(3):
            focus_terminal(lab, wm)
            # A late window can steal focus halfway through a quoted command.
            lab.monitor_command('key Ctrl+c')
            key(f'(id -un; id -u; echo "$HOME"; pwd; id -Gn; pgrep -u $(id -u) -lf {wm}; '
                '/usr/X11R7/bin/xdpyinfo | grep dimensions:) > "$HOME/.ip30-proof"')
            key('grep -q 1280x1024 "$HOME/.ip30-proof" && /usr/X11R7/bin/xterm '
                '-geometry 30x6+900+620 -bg green -e /bin/sleep 10')
            try:
                wait_screen('proof', 25)
                break
            except TimeoutError:
                if attempt == 2:
                    raise
        deadline = time.monotonic() + 60
        while visible('proof'):
            if time.monotonic() >= deadline:
                raise TimeoutError('verification terminal did not close')
            time.sleep(1)
        focus_terminal(lab, wm)
        key('clear; cat "$HOME/.ip30-proof"; /sbin/sysctl hw.model')
        time.sleep(3)
        save(shot)
        key('/usr/local/bin/xiri-logout' if wm == '4Dwm'
            else 'pkill -u $(id -u) -x /usr/X11R7/bin/ctwm')
        wait_screen('greeter')

    save('xdm-after-logout')
    login('netbsdtest', 'ctwm')
    key('su -')
    time.sleep(2)
    key('')
    # Only transmit results from the guest on serial. All input goes through
    # the same keyboard and desktop terminals used in an interactive session.
    for user, wm, home, uid, shot in sessions:
        start = lab.offset
        key(f'(echo; echo OCTANE_{user}_BEGIN; cat {home}/.ip30-proof; echo OCTANE_END) >/dev/ttyC0')
        lab.wait(r'\nOCTANE_END\n', 45)
        data = lab.serial_text()[start:lab.offset]
        proof = re.search(r'(?:^|\n)OCTANE_'+user+r'_BEGIN\n(.*?)\nOCTANE_END', data, re.S)
        rows = proof[1].splitlines() if proof else []
        if (rows[:4] != [user, str(uid), home, home] or len(rows) < 7
                or (user == 'netbsdtest' and 'wheel' not in rows[4].split())
                or not any(wm in row for row in rows[5:-1]) or '1280x1024' not in rows[-1]):
            raise ValueError(f'unexpected {wm} session proof: {rows}')
        results['sessions'].append(dict(user=user, uid=uid, home=home, wm=wm,
                                        proof=rows, logout_returned_to_greeter=True))
    key('(id -u; sysctl -n hw.model; sysctl -n kern.securelevel; modstat | grep "^compat_irix_o32 "; echo OCTANE_ADMIN_OK) >/dev/ttyC0')
    admin = lab.wait(r'(?:^|\n)0\nIP30\n1\n(compat_irix_o32[^\n]+)\nOCTANE_ADMIN_OK\n', 45)
    results['module'] = admin[1]
    key('shutdown -h now')
    return results
