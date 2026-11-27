#!/usr/bin/env python3
"""Exercise audio-CD insertion and digital playback on a private Indy desktop."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile
import time

import numpy as np

spec = importlib.util.spec_from_file_location('cdrom', Path(__file__).with_name('check-cdrom.py'))
cdrom = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cdrom)
desktop = cdrom.desktop


def button(guest, ordinal, out):
    guest.wait_for("xwininfo -name 'Audio CD' >/dev/null 2>&1", 10)
    tree = guest.read_text("xwininfo -name 'Audio CD' -tree")
    (out / 'player-tree.txt').write_text(tree)
    # Xaw's command widgets form the bottom row of the dialog.
    widgets = []
    for width, height, x, y in re.findall(r'(\d+)x(\d+)[+-]\d+[+-]\d+\s+\+(\d+)\+(\d+)', tree):
        w, h, x, y = map(int, (width, height, x, y))
        if 12 <= h <= 40 and w >= 16:
            widgets.append((y, x, w, h))
    bottom = max(y for y, x, w, h in widgets)
    row = sorted((x + w // 2, y + h // 2) for y, x, w, h in widgets if y == bottom)
    if len(row) != 4:
        raise ValueError(f'Expected Track 1, Track 2, Stop, Close: {row}')
    x, y = row[ordinal]
    guest.monitor(f'ptr click {x} {y} left')


def measure(path, begin, end):
    chunks = []
    rates = set()
    with path.open('rb') as capture:
        capture.seek(begin)
        while capture.tell() < end:
            port, rate, frames = struct.unpack('<BII', capture.read(9))
            samples = capture.read(frames * 4)
            if port == 0:
                rates.add(rate)
                chunks.append(np.frombuffer(samples, dtype='<i2').reshape((-1, 2)))
    rate, = rates
    pcm = np.concatenate(chunks)
    channels = []
    for channel in pcm.T:
        peaks = []
        for start in range(0, len(channel) - rate + 1, rate):
            second = channel[start:start + rate]
            peaks.append(int(np.abs(np.fft.rfft((second - second.mean()) * np.hanning(rate))).argmax()))
        if len(peaks) < 11 or any(abs(hz - 880) > 1 for hz in peaks):
            raise ValueError(f'Expected track two in both channels: {peaks}')
        channels.append(peaks)
    return dict(sample_rate=rate, frames=len(pcm), channel_peaks_hz=channels)


def run(args):
    bundle = args.bundle.resolve()
    source = bundle / 'netbsd-xiri.chd'
    sums = dict(line.split(None, 1)[::-1] for line in (bundle / 'SHA256SUMS').read_text().splitlines())
    if desktop.sha256(source) != sums['netbsd-xiri.chd']:
        raise ValueError('Base disk checksum mismatch')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    probe = desktop.load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = (args.emulator.resolve() / n for n in ('iris', 'iris-ci'))
    runtime = desktop.ROOT / 'runtime'
    files = {'netbsd': args.kernel, 'netbsd.boot': args.boot_kernel, 'module': args.module,
             'daemon': args.daemon, 'player': runtime / 'libexec/cd-player.sh',
             'rules': runtime / 'etc/applications.ftr'}
    install_files = {'netbsd': '/netbsd', 'netbsd.boot': '/netbsd.boot',
                     'module': '"$(sysctl -n kern.module.path)"/compat_irix_o32/compat_irix_o32.kmod',
                     'daemon': '/usr/local/libexec/xiri/cdromd', 'player': '/usr/local/libexec/xiri/cd-player.sh',
                     'rules': '/usr/local/share/xiri/applications.ftr'}
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        work = Path(tmp)
        disk = work / 'system.chd'
        # IRIS stores the private overlay beside the CHD, across both boots.
        subprocess.run(['cp', '--reflink=auto', source, disk], check=True)
        iso = work / 'update.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-o', iso, '-graft-points',
                        *(f'{k}={v.resolve()}' for k, v in files.items())], check=True)
        os.environ.update(IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(work / 'profile'))
        dac = work / 'dac'
        cpu = args.cpu
        for phase in ('install', 'play'):
            lab = desktop.native.open_lab(probe, work / phase, cpu, disk, bundle / 'state/nvram.bin')
            lab.config_text = lab.config_text.replace('overlay = false', 'overlay = true')
            lab.config_text = lab.config_text.replace('no_audio = true', 'no_audio = false')
            lab.config_text += '[audio]\nhost = "null"\n[scsi.6]\ncdrom = true\n'
            if phase == 'install':
                lab.config_text += f'path = {json.dumps(str(iso))}\n'
            else:
                os.environ['IRIS_AUDIO_DUMP'] = str(dac)
            try:
                guest = desktop.cold_root(lab)
                if phase == 'install':
                    guest.wait_for('test -f /CDROM/netbsd.boot', 60)
                    for name, dst in install_files.items():
                        mode = 555 if name in ('daemon', 'player') else 444
                        guest.command(f'install -r -m {mode} /CDROM/{name} {dst}')
                    guest.command('/usr/local/sbin/xiri-update-filetypes && sync')
                else:
                    desktop.saver.login_catalog(guest, desktop.saver.desktop.greeter, desktop.saver.desktop.login)
                    cdrom.tray(guest, 'empty')
                    time.sleep(5)
                    guest.capture(out / 'empty.png')
                    lab.ci('cdrom-load', '6', str(args.disc.resolve()))
                    cdrom.tray(guest, 'music')
                    toc = guest.read_text("su -f xiritest -c 'cdplay -f /dev/rcd0c info'")
                    if not re.search(r'^\s*2\s+0:14\.00\s+0:12\.00\s+900\s+900\s+audio$', toc, re.M):
                        raise ValueError(toc)
                    (out / 'toc.txt').write_text(toc)
                    guest.command('! mount | grep -q " on /CDROM "')
                    time.sleep(5)
                    guest.capture(out / 'music.png')
                    x, y = cdrom.changed_icon(out / 'empty.png', out / 'music.png')
                    guest.monitor(f'ptr click {x} {y} left 2')
                    window = "xwininfo -name 'Audio CD' >/dev/null 2>&1"
                    guest.wait_for(window, 45)
                    guest.capture(out / 'player.png')
                    begin = dac.stat().st_size if dac.exists() else 0
                    button(guest, 1, out)
                    # The active child runs under the desktop user's credentials.
                    guest.wait_for("pgrep -u xiritest -x cdplay >/dev/null", 10)
                    guest.wait_for("! pgrep -u xiritest -x cdplay >/dev/null", 60)
                    time.sleep(1)
                    audio = measure(dac, begin, dac.stat().st_size)
                    guest.capture(out / 'selected.png')
                    button(guest, 0, out)
                    guest.wait_for("pgrep -u xiritest -x cdplay >/dev/null", 10)
                    button(guest, 2, out)
                    guest.wait_for("! pgrep -u xiritest -x cdplay >/dev/null", 10)
                    button(guest, 3, out)
                    guest.wait_for('! ' + window, 15)
                    guest.command("su -f xiritest -c '/usr/local/libexec/xiri/cdromd --eject'")
                    cdrom.tray(guest, 'empty')
                    lab.ci('cdrom-load', '6', str(iso))
                    cdrom.tray(guest, 'data')
                    guest.command('test -r /CDROM/netbsd.boot')
                desktop.poweroff(lab)
            finally:
                lab.close()
    result = dict(release=bundle.name, cpu=cpu, base=sums['netbsd-xiri.chd'],
                  emulator=desktop.sha256(probe.IRIS), fixture=desktop.sha256(args.disc),
                  payload={k: desktop.sha256(v) for k, v in files.items()}, audio=audio)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('bundle', 'emulator', 'kernel', 'boot-kernel', 'module', 'daemon', 'disc', 'output'):
        parser.add_argument('--' + option, type=Path, required=True)
    parser.add_argument('--cpu', choices=['r4400', 'r5000'], required=True)
    run(parser.parse_args())
