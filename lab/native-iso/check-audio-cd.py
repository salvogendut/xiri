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


def measure(path, begin, end, trim_silence=False):
    chunks = []
    rates = set()
    with path.open('rb') as capture:
        capture.seek(begin)
        while capture.tell() < end:
            header = capture.read(9)
            if len(header) != 9:
                raise ValueError('Incomplete audio capture header')
            port, rate, frames = struct.unpack('<BII', header)
            samples = capture.read(frames * 4)
            if len(samples) != frames * 4 or capture.tell() > end:
                raise ValueError('Incomplete audio capture frame')
            if port == 0:
                rates.add(rate)
                chunks.append(np.frombuffer(samples, dtype='<i2').reshape((-1, 2)))
    if len(rates) != 1 or 0 in rates:
        raise ValueError(f'Expected one active DAC sample rate, got {rates}')
    rate, = rates
    pcm = np.concatenate(chunks)
    result = dict(sample_rate=rate, frames=len(pcm))
    if trim_silence:
        # The SGI player opens HAL2 before handing it the first CD sector.
        active = np.flatnonzero(np.any(pcm != 0, axis=1))
        if not active.size:
            raise ValueError('DAC capture contains only silence')
        start, stop = int(active[0]), int(active[-1]) + 1
        result.update(leading_silent_frames=start, trailing_silent_frames=len(pcm)-stop)
        pcm = pcm[start:stop]
    channels = []
    for channel in pcm.T:
        peaks = []
        for start in range(0, len(channel) - rate + 1, rate):
            second = channel[start:start + rate]
            peaks.append(int(np.abs(np.fft.rfft((second - second.mean()) * np.hanning(rate))).argmax()))
        if len(peaks) < 11 or any(abs(hz - 880) > 1 for hz in peaks):
            raise ValueError(f'Expected track two in both channels: {peaks}')
        channels.append(peaks)
    result['channel_peaks_hz'] = channels
    return result


def native_player(guest, dac, out):
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
    return audio


def sgi_player(guest, dac, out, work, realtime, icon_xy):
    """Measure the donor application independently of the desktop's NetBSD player."""
    tree = "xwininfo -root -tree"
    if realtime:
        x, y = desktop.saver.position(guest, '"winterm"')
        guest.monitor(f'ptr click {x+40} {y+40} left')
        guest.monitor('key type /emul/irix/usr/sbin/cdman')
        guest.monitor('key Return')
    else:
        x, y = icon_xy
        guest.monitor(f'ptr click {x} {y} left')
        guest.monitor('ptr down right')
        time.sleep(1)
        guest.capture(out / 'sgi-menu.png')
        guest.monitor(f'ptr move {x-41} {y+435}')
        guest.monitor('ptr up right')
    guest.wait_for(tree + " | grep -q ScsiPlayer", 60)
    processes = guest.read_text("ps -axww -o user,pid,ppid,args")
    pids = re.findall(r'^xiritest\s+(\d+)\s+\d+\s+(?:/emul/irix)?/usr/sbin/cdman(?:\s|$)', processes, re.M)
    if len(pids) != 1:
        raise ValueError(f'Expected one SGI player under the desktop account, found {pids}')
    if realtime:
        guest.command(f'/usr/sbin/schedctl -C SCHED_RR -P 0 -p {pids[0]}')
    info = guest.read_text("cat /emul/irix/CDROM/info.disc")
    for line in ('album.tracks: 2', 'track1.start: 00:02:00', 'track1.duration: 00:12:00',
                 'track2.start: 00:14:00', 'track2.duration: 00:11:74'):
        if line not in info.splitlines():
            raise ValueError(info)
    (out / 'info.disc').write_text(info)
    guest.capture(out / 'sgi-player.png')
    x, y = desktop.saver.position(guest, 'ScsiPlayer')
    log = work / 'cd-bus.log'
    guest.monitor('log scsi file ' + str(log))
    guest.monitor('log scsi on')
    begin = dac.stat().st_size
    try:
        guest.monitor(f'ptr click {x+60} {y+95} left')  # Track 2
        time.sleep(.5)
        guest.monitor(f'ptr click {x+290} {y+168} left')  # Play
        time.sleep(3)
    finally:
        guest.monitor('log scsi off')
    bus = log.read_text()
    read_cd = 'SCSI target cmd be cdb=[be, 04, 00, 00, 03, 84,'
    if read_cd not in bus:
        raise ValueError('SGI player did not read track two at sector 900')
    guest.capture(out / 'sgi-selected.png')
    time.sleep(3)
    windows = guest.read_text(tree + " | grep -i cdplayer")
    (out / 'sgi-windows.txt').write_text(windows)
    warning = 'warningDialog_popup' in windows
    if warning:
        wx, wy = desktop.saver.position(guest, 'warningDialog_popup')
        guest.monitor(f'ptr click {wx+362} {wy+86} left')
    time.sleep(16)
    end = dac.stat().st_size
    result = dict(selected_track=2, first_sector=900, realtime=realtime, warning_dialog=warning,
                  dac_bytes=end-begin)
    if realtime or end > begin:
        result['audio'] = measure(dac, begin, end, trim_silence=True)
    guest.monitor('key ctrl+q')
    time.sleep(2)
    result['closed_with_ctrl_q'] = 'ScsiPlayer' not in guest.read_text(tree)
    return result


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
             'rules': runtime / 'etc/applications.ftr', 'devices': runtime / 'rc.d/xiri_devices'}
    install_files = {'netbsd': '/netbsd', 'netbsd.boot': '/netbsd.boot',
                     'module': '"$(sysctl -n kern.module.path)"/compat_irix_o32/compat_irix_o32.kmod',
                     'daemon': '/usr/local/libexec/xiri/cdromd', 'player': '/usr/local/libexec/xiri/cd-player.sh',
                     'rules': '/usr/local/share/xiri/applications.ftr', 'devices': '/etc/rc.d/xiri_devices'}
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
                        mode = 555 if name in ('daemon', 'player', 'devices') else 444
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
                    audio = native_player(guest, dac, out)
                    vendor = None
                    if args.sgi or args.sgi_realtime:
                        vendor = sgi_player(guest, dac, out, work, args.sgi_realtime, (x, y))
                    if vendor:
                        # Release any remaining donor workers before testing the next disc.
                        guest.command("for p in $(ps -axww -o user,pid,args | "
                                      "awk '$1==\"xiritest\" && ($3==\"/emul/irix/usr/sbin/cdman\" || "
                                      "$3==\"/usr/sbin/cdman\") {print $2}'); "
                                      "do kill -KILL \"$p\" 2>/dev/null || :; done")
                    guest.command("su -f xiritest -c '/usr/local/libexec/xiri/cdromd --eject'")
                    cdrom.tray(guest, 'empty')
                    lab.ci('cdrom-load', '6', str(iso))
                    cdrom.tray(guest, 'data')
                    guest.command('test -r /CDROM/netbsd.boot && test ! -L /emul/irix/CDROM && '
                                  'test ! -e /var/run/xiri-cdrom/mtab')
                desktop.poweroff(lab)
            finally:
                lab.close()
    result = dict(release=bundle.name, cpu=cpu, sgi=vendor, base=sums['netbsd-xiri.chd'],
                  emulator=desktop.sha256(probe.IRIS), fixture=desktop.sha256(args.disc),
                  payload={k: desktop.sha256(v) for k, v in files.items()}, audio=audio)
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ('bundle', 'emulator', 'kernel', 'boot-kernel', 'module', 'daemon', 'disc', 'output'):
        parser.add_argument('--' + option, type=Path, required=True)
    parser.add_argument('--sgi', action='store_true',
                        help='also compare the donor player with the native selector')
    parser.add_argument('--sgi-realtime', action='store_true',
                        help='give only the open SGI player SCHED_RR priority 0 and require audio from it')
    parser.add_argument('--cpu', choices=['r4400', 'r5000'], required=True)
    run(parser.parse_args())
