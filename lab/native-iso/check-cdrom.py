#!/usr/bin/env python3
"""Check the SGI CD-ROM desktop icon on a private copy of a prepared Indy."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
import time

from PIL import Image, ImageChops

spec = importlib.util.spec_from_file_location('desktop', Path(__file__).with_name('check-desktop.py'))
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


def tray(guest, state):
    guest.wait_for(f'grep -qx XiriCD-{state} /var/run/xiri-cdrom/CDROM', 45)


def icon(path):
    # The reference desktops place device icons on the right, above Icon Catalog.
    with Image.open(path) as image:
        return image.convert('RGB').crop((image.width - 140, 0, image.width, 405))


def changed_icon(empty, loaded):
    bounds = ImageChops.difference(icon(empty), icon(loaded)).getbbox()
    if bounds is None:
        raise ValueError('Inserting the disc did not change the desktop icon')
    x, y, right, bottom = bounds
    if not (16 <= right - x <= 80 and 10 <= bottom - y <= 80):
        raise ValueError(f'Unexpected desktop change in the device-icon column: {bounds}')
    with Image.open(empty) as image:
        return image.width - 140 + (x + right) // 2, (y + bottom) // 2


def run(args):
    bundle = args.bundle.resolve()
    disk = bundle / 'netbsd-xiri.chd'
    record = json.loads((bundle / 'qualification.json').read_text())
    if desktop.sha256(disk) != record['chd_sha256']:
        raise ValueError('Unexpected base disk')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    runtime = desktop.ROOT / 'runtime'
    probe = desktop.load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = (args.emulator.resolve() / n for n in ('iris', 'iris-ci'))
    with TemporaryDirectory(dir=out) as tmp:
        work = Path(tmp)
        os.environ.update(IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(work / 'profile'))
        # The checked CHD is read-only to IRIS. Its overlay is placed next to this private copy.
        copy = work / 'system.chd'
        subprocess.run(['cp', '--reflink=auto', disk, copy], check=True)
        fixture = work / 'README.txt'
        fixture.write_text('Xiri optical media check\n')
        disc = work / 'sample.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'XIRI_DISC', '-o', disc, fixture], check=True)
        install = work / 'install.iso'
        files = {'daemon': args.daemon.resolve(), 'service': runtime / 'rc.d/xiri_cdrom',
                 'clients': runtime / 'libexec/desktop-clients.sh', 'rules': runtime / 'etc/applications.ftr'}
        digests = {name: desktop.sha256(path) for name, path in files.items()}
        subprocess.run(['genisoimage', '-quiet', '-R', '-o', install, '-graft-points',
                        *(f'{k}={v}' for k, v in files.items())], check=True)
        lab = desktop.native.open_lab(probe, work / 'lab', record['cpu'], copy, bundle / 'nvram.bin')
        lab.config_text = lab.config_text.replace('overlay = false', 'overlay = true')
        lab.config_text += f'[scsi.6]\ncdrom = true\npath = {json.dumps(str(install))}\n'
        try:
            guest = desktop.cold_root(lab)
            cmd = guest.command
            # The base may already have automounted the helper CD.
            cmd('if test -x /etc/rc.d/xiri_cdrom; then /etc/rc.d/xiri_cdrom onestop || :; fi')
            cmd('mount -rt cd9660 /dev/cd0a /mnt && '
                'install -m 555 /mnt/daemon /usr/local/libexec/xiri/cdromd && '
                'install -m 555 /mnt/service /etc/rc.d/xiri_cdrom && '
                'install -m 555 /mnt/clients /usr/local/libexec/xiri/desktop-clients.sh && '
                'install -m 444 /mnt/rules /usr/local/share/xiri/applications.ftr')
            cmd('echo xiri_cdrom=YES >/etc/rc.conf.d/xiri_cdrom && /usr/local/sbin/xiri-update-filetypes && '
                '/etc/rc.d/xiri_cdrom start')
            # The system's existing manual mount must keep its owner.
            tray(guest, 'other')
            cmd('! /usr/local/libexec/xiri/cdromd --eject && test -r /mnt/daemon && umount /mnt && eject cd0')
            tray(guest, 'empty')
            desktop.saver.login_catalog(guest, desktop.saver.desktop.greeter, desktop.saver.desktop.login)
            time.sleep(5)
            guest.capture(out / 'empty.png')
            lab.ci('cdrom-load', '6', str(disc))
            tray(guest, 'data')
            cmd('mount | grep "^/dev/cd0a on /CDROM type cd9660 " | grep -q read-only && '
                f"""test "$(su -f xiritest -c 'sha256 -q /CDROM/README.txt')" = {desktop.sha256(fixture)}""")
            time.sleep(5)
            guest.capture(out / 'loaded.png')
            x, y = changed_icon(out / 'empty.png', out / 'loaded.png')
            cmd("cd /CDROM && ! su -f xiritest -c '/usr/local/libexec/xiri/cdromd --eject' && "
                "test -f README.txt && cd /")
            # In the reference desktop layout, SGI appends Eject CDROM as
            # the last row of the selected icon's Desktop popup.
            guest.monitor(f'ptr click {x} {y} left')
            guest.monitor('ptr down right')
            time.sleep(1)
            guest.capture(out / 'menu.png')
            guest.monitor(f'ptr move {x - 41} {y + 435}')
            guest.monitor('ptr up right')
            tray(guest, 'empty')
            cmd('! mount | grep -q " on /CDROM "')
            guest.monitor(f'ptr click {x - 140} {y + 15} left')
            time.sleep(5)
            guest.capture(out / 'ejected.png')
            if ImageChops.difference(icon(out / 'empty.png'), icon(out / 'ejected.png')).getbbox():
                raise ValueError('Eject did not restore the empty-drive icon')
            lab.ci('cdrom-load', '6', str(disc))
            tray(guest, 'data')
            time.sleep(5)
            guest.monitor(f'ptr click {x} {y} left 2')
            guest.wait_for("""xwininfo -root -tree | grep -F ':/CDROM": ("FileManager" "FileManager")'""", 45)
            guest.capture(out / 'opened.png')
            (out / 'windows.txt').write_text(guest.read_text('xwininfo -root -tree'))
            desktop.poweroff(lab)
        finally:
            lab.close()
    result = dict(release=record['release'], cpu=record['cpu'], base=record['chd_sha256'],
                  emulator=desktop.sha256(probe.IRIS), files=digests, icon_click=[x, y])
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('bundle', 'emulator', 'daemon', 'output'):
        parser.add_argument('--' + option, type=Path, required=True)
    run(parser.parse_args())
