#!/usr/bin/env python3
"""Record a known stereo input with a candidate kernel on a private Indy."""
import argparse
from contextlib import contextmanager
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


def measure(wav, mono=False):
    with wave.open(io.BytesIO(wav)) as w:
        if (w.getframerate(), w.getnchannels(), w.getsampwidth()) != (RATE, 2, 2):
            raise ValueError(f'Unexpected WAV format: {w.getparams()}')
        return measure_pcm(w.readframes(w.getnframes()), mono)


def measure_pcm(pcm, mono=False):
    frames = list(struct.iter_unpack('<hh', pcm))
    if len(frames) < RATE // 2:
        raise ValueError(f'Short recording: {len(frames)} frames')
    if mono and any(left != right for left, right in frames):
        raise ValueError('Mono microphone channels differ')
    # A middle 100 ms window contains an integer number of cycles of each tone.
    window = frames[len(frames)//2:len(frames)//2 + RATE//10]
    levels = []
    for ch in range(2):
        def amplitude(hz):
            angle = 2 * math.pi * hz / RATE
            re = sum(frame[ch] * math.cos(i * angle) for i, frame in enumerate(window))
            im = sum(frame[ch] * math.sin(i * angle) for i, frame in enumerate(window))
            return round(2 * math.hypot(re, im) / len(window))
        source = 0 if mono else ch
        signal, other = amplitude(FREQUENCIES[source]), amplitude(FREQUENCIES[1-source])
        if signal < 1000 or signal < 8 * other:
            raise ValueError(f'Channel {ch}: wanted tone {signal}, other tone {other}')
        levels.append(dict(frequency_hz=FREQUENCIES[source], amplitude=signal, other_tone=other))
    return dict(frames=len(frames), rate_hz=RATE, channels=levels)


def measure_speaker(path, start, mono=False):
    # IRIS dumps one DAC burst per record, before host resampling.
    pcm = bytearray()
    with path.open('rb') as f:
        f.seek(start)
        while header := f.read(9):
            output, rate, count = struct.unpack('<BII', header)
            chunk = f.read(4 * count)
            if output != 0 or rate != RATE or len(chunk) != 4 * count:
                raise ValueError(f'Unexpected HAL2 output: {output}, {rate} Hz, {count} frames')
            pcm.extend(chunk)
    return measure_pcm(pcm, mono)


@contextmanager
def feed(source, fifo):
    # Opening a FIFO for writing may wait for the guest to arm its ADC.
    writer = subprocess.Popen([sys.executable, '-c',
        'import shutil, sys; '
        'shutil.copyfileobj(open(sys.argv[1], "rb"), open(sys.argv[2], "wb", buffering=0))',
        source, fifo], stderr=subprocess.DEVNULL)
    try:
        yield
    finally:
        writer.terminate()
        writer.wait()


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
        speaker = work / 'speaker.pcm'
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
        if args.probes:
            files['hdsp-query'] = args.probes.resolve()/'hdsp-query'
            for abi in ('n32', 'o32'):
                files['arena-'+abi] = args.probes.resolve()/('arena-'+abi)
        if args.donor:
            if desktop.sha256(args.donor) != record['donor_sha256']:
                raise ValueError('Wrong donor for this release')
            pkg = desktop.ROOT / 'packaging/xiriprep'
            files.update({'donor.chd': args.donor.resolve(), 'install-audio.sh': pkg/'install-audio.sh',
                          'release.audio': pkg/'plans'/(record['release']+'.audio'),
                          'xiri_devices': desktop.ROOT/'runtime/rc.d/xiri_devices'})
        subprocess.run(['genisoimage', '-quiet', '-R', '-o', cd, '-graft-points',
                        *(f'{name}={f}' for name, f in files.items()), 'play.wav='+str(play)], check=True)
        result = dict(release=record['release'], cpu=record['cpu'], base_sha256=record['chd_sha256'],
                      kernel_sha256=desktop.sha256(files['netbsd.boot']),
                      module_sha256=desktop.sha256(files['compat_irix_o32.kmod']))
        for phase, binaries in [('install', args.bootstrap), ('record', args.emulator)]:
            probe.IRIS, probe.CI = (binaries.resolve()/name for name in ('iris', 'iris-ci'))
            lab = desktop.native.open_lab(probe, work/phase, record['cpu'], disk, bundle/'nvram.bin', cd)
            lab.config_text = lab.config_text.replace('overlay = false', 'overlay = true')
            lab.config_text = lab.config_text.replace('no_audio = true', 'no_audio = false')
            lab.config_text += '[audio]\nhost = "null"\n'
            if phase == 'record':
                os.environ['IRIS_AUDIO_DUMP'] = str(speaker)
                lab.config_text += 'input_file = ' + json.dumps(str(tone)) + '\n'
            try:
                print(record['release'], phase, flush=True)
                guest = desktop.cold_root(lab)
                guest.command('mkdir -p /cdrom && mount -rt cd9660 /dev/cd0a /cdrom')
                if phase == 'install':
                    if args.donor:
                        guest.command('install -m 555 /cdrom/xiri_devices /etc/rc.d/xiri_devices && '
                                      'sh /cdrom/install-audio.sh /cdrom/donor.chd /cdrom/release.audio && '
                                      'sh /cdrom/install-audio.sh /cdrom/donor.chd /cdrom/release.audio')
                    guest.command('install -r -m 444 /cdrom/netbsd.boot /netbsd.boot && '
                                  'install -r -m 444 /cdrom/netbsd /netbsd && '
                                  'install -r -m 444 /cdrom/compat_irix_o32.kmod '
                                  '$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod && '
                                  'umount /cdrom && sync')
                else:
                    guest.command('test "$(sha256 -q /netbsd.boot)" = '+result['kernel_sha256'])
                    result['emulator_sha256'] = desktop.sha256(probe.IRIS)
                    result['devices'] = guest.read_text('audiocfg list').strip()
                    if args.probes:
                        for abi in ('n32', 'o32'):
                            guest.command(f"su -f xiritest -c '/cdrom/arena-{abi} /tmp/arena-{abi}'")
                        result['scratch_file_probes'] = ['n32', 'o32']
                    with feed(fixture_path, tone):
                        guest.command("su -f xiritest -c 'audioplay /cdrom/play.wav & player=$!; "
                                      "audiorecord -e slinear_le -P 16 -s 48000 -c 2 -t 1 /tmp/record.wav "
                                      "&& wait $player'", 60)
                    result['input'] = 'raw stereo PCM via FIFO'
                    result['playback_during_capture'] = True
                    result.update(measure(guest.read('cat /tmp/record.wav')))
                    if args.donor:
                        def sgi_record():
                            with feed(fixture_path, tone):
                                guest.command("su -f xiritest -c '/emul/irix/usr/sbin/sfrecord -channels 2 "
                                              "-width 16 -rate 48000 -time 1 -fileformat wave /tmp/sgi-mic.wav'", 60)
                            return guest.read('cat /tmp/sgi-mic.wav')

                        result['sfrecord'] = measure(sgi_record(), mono=True)
                        if args.probes:
                            guest.command("su -f xiritest -c '/cdrom/hdsp-query --mic-stereo'")
                            guest.command('rm /tmp/sgi-mic.wav')
                            result['sfrecord_stereo'] = measure(sgi_record())
                            guest.command("su -f xiritest -c '/cdrom/hdsp-query --mic-mono'")
                        start = speaker.stat().st_size
                        guest.command("su -f xiritest -c '/emul/irix/usr/sbin/sfplay /tmp/sgi-mic.wav'", 60)
                        result['sfplay_exit'] = 0
                        result['sfplay_output'] = measure_speaker(speaker, start, mono=not args.probes)
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
    parser.add_argument('--donor', type=Path, help='also import and test the two SGI audio clients')
    parser.add_argument('--probes', type=Path, help='directory from lab/irix-hdsp/build.sh for microphone controls and scratch-file checks')
    run(parser.parse_args())
