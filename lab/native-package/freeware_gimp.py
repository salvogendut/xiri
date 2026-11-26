"""Edit an image with the CD 2 GIMP installation across two xdm sessions."""
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import time

from PIL import Image, ImageChops

from freeware_lifecycle import HOME, PAGE, TABLE, WINDOWS, freeware_tab, history, logout, software_manager, transaction
from mozilla_lifecycle import login_catalog, position
from xiri_lab import ROOT as PROJECT

IMAGE = HOME + '/gimp-cd2.ppm'
TITLE = 'gimp-cd2.ppm-'
SPEC = PROJECT / 'lab/irix-installer/gimp-cd.json'


def verify_media(iso, *, removal=False):
    if not removal:
        previous = PROJECT / 'docs/results/2026-11-26-freeware-gimp.json'
        with iso.open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() == json.loads(previous.read_text())['media_sha256']:
                return
    record = json.loads(SPEC.read_text())
    files = {'/dist/' + Path(path).name: digest for path, digest in record['files'].items()}
    for name in ('gimp.sh', 'desktop-artwork.sh', 'xmahjongg.sh', 'package-filetypes.mk', 'unzip-upgrade.sh'):
        files['/' + name] = hashlib.sha256(SPEC.with_name(name).read_bytes()).hexdigest()
    files['/selections'] = hashlib.sha256(('\n'.join(record['subsystems']) + '\n').encode()).hexdigest()
    for name, digest in files.items():
        data = subprocess.check_output(['isoinfo', '-R', '-i', iso, '-x', name])
        if hashlib.sha256(data).hexdigest() != digest:
            raise ValueError(f'Unexpected GIMP medium file {name}')


def wait_window(guest, title, timeout=180):
    guest.wait_for(WINDOWS + ' | grep -Fq ' + shlex.quote('"' + title), timeout)


def click(guest, title, dx, dy):
    x, y = position(guest, title)
    guest.monitor(f'ptr click {x + dx} {y + dy} left')


def dismiss_tip(guest):
    if '"GIMP Tip of the Day"' in guest.read_text(WINDOWS + ' | grep -F "GIMP Tip of the Day"'):
        click(guest, 'GIMP Tip of the Day', 460, 108)


def first_launch(guest):
    cmd = f'export HOME={HOME} USER=xiritest LOGNAME=xiritest; cd "$HOME" && exec /usr/freeware/bin/gimp {IMAGE}'
    guest.command('su -m xiritest -c ' + shlex.quote(cmd) + ' >/tmp/gimp-first.log 2>&1 </dev/null & :')
    wait_window(guest, 'GIMP User Installation')
    x, y = position(guest, 'GIMP User Installation')
    for _ in range(5):
        guest.monitor(f'ptr click {x+430} {y+491} left')
        time.sleep(2)
    wait_window(guest, TITLE, 300)
    dismiss_tip(guest)
    click(guest, TITLE, 55, -12)


def catalog_reopen(guest, out):
    x, y = freeware_tab(guest)
    guest.capture(out / 'freeware-page.png')
    guest.monitor(f'ptr click {x+100} {y+80} left 2')
    wait_window(guest, 'The GIMP', 180)
    dismiss_tip(guest)
    click(guest, 'The GIMP', 50, -12)
    guest.monitor('key ctrl+o')
    wait_window(guest, 'Load Image')
    guest.monitor('key type ' + IMAGE)
    guest.monitor('key Return')
    wait_window(guest, TITLE)
    click(guest, TITLE, 55, -12)


def fixture(guest):
    write = 'set -C; awk \'BEGIN {print "P3"; print "192 160"; print 255; for(i=0;i<192*160;i++) print "255 255 255"}\' >' + IMAGE
    guest.command('su - xiritest -c ' + shlex.quote(write))


def edit(guest, out):
    x, y = position(guest, TITLE)
    guest.monitor('key p')
    guest.monitor(f'ptr drag {x+52} {y+66} {x+151} {y+131} left')
    guest.monitor(f'ptr drag {x+151} {y+66} {x+52} {y+131} left')
    guest.monitor('key ctrl+s')
    # The PNM plug-in can ask whether to write ASCII or raw pixels.
    guest.wait_for('test "$(head -c 2 ' + IMAGE + ')" = P6 || ' + WINDOWS + ' | grep -i -q "Save as PNM"', 120)
    if '"Save as PNM"' in guest.read_text(WINDOWS + ' | grep -i PNM'):
        guest.monitor('key Return')
    guest.wait_for('test "$(head -c 2 ' + IMAGE + ')" = P6', 90)
    data = guest.read('cat ' + IMAGE)
    guest.capture(out / 'edited.png')
    return data


def quit_gimp(guest):
    click(guest, TITLE, 55, -12)
    guest.monitor('key ctrl+q')
    guest.wait_for('! (' + WINDOWS + ' | grep -Fq \'"The GIMP"\')', 90)


def check(guest, out, greeter, login, *, removal=False):
    guest.command('mkdir -p /cdrom /mnt/gimp && mount -rt cd9660 /dev/cd0a /cdrom && mount -rt cd9660 /dev/cd1a /mnt/gimp')
    guest.command('test ! -e /usr/freeware/bin/gimp && test ! -e /emul/irix/usr/freeware/bin/gimp && test ! -e /emul/irix/var/inst/hist')
    transaction(guest, 'sh /cdrom/prepare-live-base.sh /cdrom', 'freeware-base')
    if removal:
        from freeware_gimp_removal import baseline, remove_reinstall
        baseline(guest)
    login_catalog(guest, greeter, login)
    software_manager(guest, 'sh /mnt/gimp/gimp.sh /mnt/gimp', 'gimp', out)
    inventory = history(guest)
    expected = json.loads(SPEC.read_text())['subsystems']
    if sorted(s for s in inventory if s.count('.') == 2) != sorted(expected):
        raise ValueError('Unexpected Freeware subsystem inventory')
    guest.command(f'test -L {PAGE}/gimp && test {PAGE}/gimp -ef /usr/freeware/bin/gimp')
    binary = guest.read_text('sha256 -q /usr/freeware/bin/gimp-1.2').strip()
    version = guest.command("su -m xiritest -c '/usr/freeware/bin/gimp --version'")
    if 'GIMP version 1.2.5' not in version:
        raise ValueError('Installed GIMP did not report version 1.2.5')
    fixture(guest)
    first_launch(guest)
    saved = edit(guest, out)
    quit_gimp(guest)
    maintenance = remove_reinstall(guest, out, inventory, greeter, login) if removal else {}
    logout(guest)
    login_catalog(guest, greeter, login)
    catalog_reopen(guest, out)
    if guest.read('cat ' + IMAGE) != saved:
        raise ValueError('Saved GIMP image changed across xdm login')
    owner = guest.read_text('/usr/bin/stat -f %Su ' + IMAGE).strip()
    if owner != 'xiritest':
        raise ValueError('Unexpected owner of the saved image')
    window = guest.read_text(WINDOWS + ' | grep -m1 ' + TITLE).strip()
    x, y = position(guest, TITLE)
    guest.capture(out / 'reopened.png')
    pixels = verify_canvas(saved, out / 'reopened.png', x, y)
    table = guest.read_text('sha256 -q ' + TABLE).strip()
    quit_gimp(guest)
    if removal:
        from freeware_gimp_removal import STATE
        guest.command(f'sha256 -c {STATE}/user.sha')
    logout(guest)
    greeter(guest)
    return dict(reopened_window=window, saved_sha256=hashlib.sha256(saved).hexdigest(),
                owner=owner, binary_sha256=binary, table_sha256=table, subsystems=expected, **pixels, **maintenance)


def verify_canvas(saved, frame, x, y):
    # At 100% zoom the canvas starts after the rulers. GIMP overlays its
    # dotted layer boundary on the outermost row and column of each edge.
    with Image.open(io.BytesIO(saved)) as document, Image.open(frame) as screen:
        if document.size != (192, 160):
            raise ValueError('Unexpected saved image dimensions')
        dark = sum(document.convert('L').histogram()[:128])
        if not 1000 <= dark <= 12000:
            raise ValueError(f'Expected visible brush strokes, found {dark} dark pixels')
        left, top = x + 21, y + 21
        expected = document.convert('RGB').crop((1, 1, 191, 159))
        actual = screen.convert('RGB').crop((left+1, top+1, left+191, top+159))
        if ImageChops.difference(expected, actual).getbbox():
            raise ValueError('Reopened canvas pixels differ from the saved image')
        return dict(dark_pixels=dark, exact_interior_rgb_pixels=expected.width * expected.height)
