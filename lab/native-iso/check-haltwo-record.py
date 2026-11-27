#!/usr/bin/env python3
"""Record a known stereo input with a candidate kernel on a private Indy."""
import argparse
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import wave

spec = importlib.util.spec_from_file_location('desktop', Path(__file__).with_name('check-desktop.py'))
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)

RATE = 48000
FREQUENCIES = (440, 880)


def fixture():
    return b''.join(struct.pack('<hh', *(round(12000 * math.sin(2 * math.pi * hz * i / RATE))
                                         for hz in FREQUENCIES)) for i in range(RATE))


def measure(wav):
    with wave.open(io.BytesIO(wav)) as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (RATE, 2, 2):
            raise ValueError(f'Unexpected WAV format: {w.getparams()}')
        frames = list(struct.iter_unpack('<hh', w.readframes(w.getnframes())))
    if len(frames) < RATE // 2:
        raise ValueError(f'Short recording: {len(frames)} frames')
    # A middle 100 ms window contains an integer number of cycles of each tone.
    window = frames[len(frames)//2:len(frames)//2 + RATE//10]
    levels = []
    for ch in range(2):
        def amplitude(hz):
            angle = 2 * math.pi * hz / RATE
            re = sum(frame[ch] * math.cos(i * angle) for i, frame in enumerate(window))
            im = sum(frame[ch] * math.sin(i * angle) for i, frame in enumerate(window))
            return round(2 * math.hypot(re, im) / len(window))
        signal, other = amplitude(FREQUENCIES[ch]), amplitude(FREQUENCIES[1-ch])
        if signal < 1000 or signal < 8 * other:
            raise ValueError(f'Channel {ch}: wanted tone {signal}, other tone {other}')
        levels.append(dict(frequency_hz=FREQUENCIES[ch], amplitude=signal, other_tone=other))
    return dict(frames=len(frames), rate_hz=RATE, channels=levels)


def run(args):
    bundle = args.bundle.resolve()
    record = json.loads((bundle / 'qualification.json').read_text())
    base = bundle / 'netbsd-xiri.chd'
    if desktop.sha256(base) != record['chd_sha256']:
        raise ValueError('Unexpected base disk')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    probe = desktop.load_probe()
    probe.TOOLBOX = []
    with TemporaryDirectory(dir=out) as temp:
        work = Path(temp)
        os.environ.update(IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(work / 'profile'))
        disk = work / 'disk.chd'
        subprocess.run(['cp', '--reflink=auto', base, disk], check=True)
        tone = work / 'tone.pcm'
        os.mkfifo(tone)
        fixture_path = work / 'source.pcm'
        audio = fixture()
        fixture_path.write_bytes(audio * 12)
        play = work / 'play.wav'
        with wave.open(str(play), 'wb') as w:
            w.setparams((2, 2, RATE, 0, 'NONE', 'not compressed'))
            w.writeframes(audio * 3)
        cd = work / 'kernel.iso'
        source = args.build.resolve()
        files = {'netbsd': source/'kernel/netbsd', 'netbsd.boot': source/'kernel/netbsd.elf32',
                 'compat_irix_o32.kmod': source/'module/compat_irix_o32.kmod'}
        subprocess.run(['genisoimage', '-quiet', '-R', '-o', cd, '-graft-points',
                        *(f'{name}={f}' for name, f in files.items()), 'play.wav='+str(play)], check=True)
        result = dict(release=record['release'], cpu=record['cpu'], base_sha256=record['chd_sha256'],
                      kernel_sha256=desktop.sha256(files['netbsd.boot']))
        for phase, binaries in [('install', args.bootstrap), ('record', args.emulator)]:
            probe.IRIS, probe.CI = (binaries.resolve()/name for name in ('iris', 'iris-ci'))
            lab = desktop.native.open_lab(probe, work/phase, record['cpu'], disk, bundle/'nvram.bin', cd)
            lab.config_text = lab.config_text.replace('overlay = false', 'overlay = true')
            lab.config_text = lab.config_text.replace('no_audio = true', 'no_audio = false')
            lab.config_text += '[audio]\nhost = "null"\n'
            if phase == 'record':
                lab.config_text += 'input_file = ' + json.dumps(str(tone)) + '\n'
            try:
                print(record['release'], phase, flush=True)
                guest = desktop.cold_root(lab)
                if phase == 'install':
                    guest.command('mkdir -p /cdrom && mount -rt cd9660 /dev/cd0a /cdrom && '
                                  'install -r -m 444 /cdrom/netbsd.boot /netbsd.boot && '
                                  'install -r -m 444 /cdrom/netbsd /netbsd && '
                                  'install -r -m 444 /cdrom/compat_irix_o32.kmod '
                                  '$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod && '
                                  'umount /cdrom && sync')
                else:
                    guest.command('test "$(sha256 -q /netbsd.boot)" = '+result['kernel_sha256'])
                    result['emulator_sha256'] = desktop.sha256(probe.IRIS)
                    result['devices'] = guest.read_text('audiocfg list').strip()
                    guest.command('mkdir -p /cdrom && mount -rt cd9660 /dev/cd0a /cdrom')
                    # The helper can wait for the guest to open the FIFO while the
                    # test driver continues sending commands. Always reap it.
                    writer = subprocess.Popen([sys.executable, '-c',
                        'import shutil, sys; '
                        'shutil.copyfileobj(open(sys.argv[1], "rb"), open(sys.argv[2], "wb", buffering=0))',
                        fixture_path, tone], stderr=subprocess.DEVNULL)
                    try:
                        guest.command("su -f xiritest -c 'audioplay /cdrom/play.wav & player=$!; "
                                      "audiorecord -e slinear_le -P 16 -s 48000 -c 2 -t 1 /tmp/record.wav "
                                      "&& wait $player'", 60)
                    finally:
                        writer.terminate()
                        writer.wait()
                    result['input'] = 'raw stereo PCM via FIFO'
                    result['playback_during_capture'] = True
                    result.update(measure(guest.read('cat /tmp/record.wav')))
                desktop.poweroff(lab)
            except Exception:
                print(lab.serial_text()[-2200:], flush=True)
                log = lab.directory/'emulator.log'
                if log.exists():
                    print(log.read_text(errors='replace')[-1600:], flush=True)
                raise
            finally:
                lab.close()
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('bundle', 'bootstrap', 'emulator', 'build', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    run(parser.parse_args())
