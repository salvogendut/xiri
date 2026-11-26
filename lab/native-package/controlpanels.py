"""Double-click the four SGI control panels on a clean 1280x1024 Indy desktop."""
import re
import shlex

from mozilla_lifecycle import position, raise_catalog


def blanking_timeout(guest):
    query = guest.read_text('xset q')
    return int(re.search(r'^\s*timeout:\s*(\d+)', query, re.M)[1])


def check(guest, out):
    tree = 'xwininfo -root -tree'
    report = {}
    # Icon positions are relative to the Catalog. Buttons are relative to
    # the visible SGI client, whose position 4Dwm chooses at startup.
    panels = (
        ('display', (690, 72), '"errorDialog_popup" "XSetmon"', (393, 86)),
        ('audiopanel', (216, 72), '"warningDialog_popup" "Apanel"', (285, 81)),
        ('sounds', (756, 148), '"errorDialog_popup" "DtSounds"', (325, 82)),
        ('screensaver', (638, 148), '"ScreenSaver"[)] +300x420', (96, 378)),
    )
    for name, icon, pattern, dismiss in panels:
        x, y = raise_catalog(guest)
        guest.monitor(f'ptr click {x+315} {y+461} left')
        guest.wait_for(tree + ' | grep -q "Icon Catalog: ControlPanels"', 60)
        guest.monitor(f'ptr click {x+icon[0]} {y+icon[1]} left 2')
        match = tree + ' | grep -E ' + shlex.quote(pattern)
        guest.wait_for(match + ' >/dev/null', 90)
        x, y = position(guest, pattern)
        row = {'window': guest.read_text(match).strip()}
        if name == 'screensaver':
            before = blanking_timeout(guest)
            toggle = f'ptr click {x+15} {y+116} left'
            guest.monitor(toggle)
            changed = blanking_timeout(guest)
            guest.monitor(toggle)
            restored = blanking_timeout(guest)
            if bool(before) == bool(changed) or restored != before:
                raise RuntimeError(f'Screen Saver timeout: {before} -> {changed} -> {restored}')
            row['timeout_seconds'] = [before, changed, restored]
        guest.capture(out / f'controlpanel-{name}.png')
        guest.monitor(f'ptr click {x+dismiss[0]} {y+dismiss[1]} left')
        guest.wait_for('! ' + match + ' >/dev/null', 60)
        row['closed'] = True
        report[name] = row
    return report
