#!/usr/bin/env python3
"""Record, save, reopen and play a known microphone tone in the SGI editor."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import struct
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('desktop', ROOT / 'lab/native-iso/check-desktop.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)
audio = desktop.load('audio', 'lab/native-iso/check-haltwo-record.py')

TREE = 'xwininfo -root -tree'
APP = '/emul/irix/usr/sbin/soundeditor'
NAME = 'xiri-recording.aiff'
FILE = '/usr/people/xiritest/' + NAME


def aiff_pcm(data):
    """Read the stereo 16-bit big-endian PCM that Sound Editor saves by default."""
    form, length, kind = struct.unpack_from('>4sI4s', data)
    if form != b'FORM' or kind not in (b'AIFF', b'AIFC') or length + 8 != len(data):
        raise ValueError('Invalid AIFF form')
    chunks = {}
    pos = 12
    while pos + 8 <= len(data):
        tag, size = struct.unpack_from('>4sI', data, pos)
        pos += 8
        if pos + size > len(data):
            raise ValueError('Truncated AIFF chunk')
        chunks[tag] = data[pos:pos + size]
        pos += size + (size & 1)
    comm, sound = chunks[b'COMM'], chunks[b'SSND']
    channels, frames, width, exponent, mantissa = struct.unpack_from('>hIhHQ', comm)
    if (channels, width, exponent, mantissa) != (2, 16, 0x400e, 48000 << 48):
        raise ValueError('Expected two channels of 16-bit PCM at 48 kHz')
    if kind == b'AIFC' and comm[18:22] != b'NONE':
        raise ValueError('Expected uncompressed big-endian AIFF-C')
    offset, _ = struct.unpack_from('>II', sound)
    samples = sound[8 + offset:]
    if len(samples) < frames * 4:
        raise ValueError('Incomplete AIFF sample data')
    samples = samples[:frames * 4]
    pcm = bytearray(len(samples))
    pcm[0::2], pcm[1::2] = samples[1::2], samples[0::2]
    return pcm


def click(g, title, dx, dy):
    x, y = desktop.saver.position(g, title)
    g.monitor(f'ptr click {x + dx} {y + dy} left')


def launch(g, filename=''):
    title = 'SoundEditor: <' + NAME + '>' if filename else 'SoundEditor: Untitled'
    command = shlex.join([APP, filename] if filename else [APP])
    g.command("printf '%s\\n' " + shlex.quote(command) + ' >/tmp/xiri-editor')
    click(g, '"winterm"', 40, 40)
    g.monitor('key type sh /tmp/xiri-editor')
    g.monitor('key Return')
    g.wait_for(TREE + ' | grep -Fq ' + shlex.quote(title), 90)
    return title


def recording_child(trace):
    spawn = re.search(r'RET +\[129\] 0, (0x[0-9a-f]+|[0-9]+)', trace)
    if not spawn:
        raise ValueError('The recording worker did not start')
    pid = int(spawn.group(1), 0)
    child = '\n'.join(line for line in trace.splitlines() if line.split()[:1] == [str(pid)])
    if 'hdsp0r2' not in child or not re.search(r'RET +\[135\] 0(?:,|$)', child, re.M):
        raise ValueError('The worker did not open and release the recording port')
    return pid


def record(g, work, out, dac):
    g.command('test ! -e ' + FILE)
    title = launch(g)
    x, y = desktop.saver.position(g, title)
    # Attach to the daemonized GUI process; the launching winterm has returned.
    g.command("ep=$(ps -axww -o pid,args | awk '$2 ~ /soundeditor$/ {print $1;exit}'); "
              'test -n "$ep" && ktrace -i -t cn -f /tmp/editor.ktrace -p "$ep"')
    with audio.feed(work / 'input.pcm', work / 'input.fifo'):
        g.monitor(f'ptr click {x+48} {y+50} left')   # Record
        time.sleep(4)
        g.monitor(f'ptr click {x+123} {y+50} left')  # Stop
    g.wait_for("kdump -Nn -f /tmp/editor.ktrace | grep -Eq 'RET +\\[135\\] 0'", 30)
    g.command('ktrace -c -d -p "$ep"')
    trace = g.read_text("kdump -Nn -f /tmp/editor.ktrace | grep -E 'hdsp0r2|\\[(129|135)\\]'")
    (out / 'record-syscalls.txt').write_text(trace)
    worker_pid = recording_child(trace)
    g.monitor(f'ptr click {x+58} {y-12} left')
    g.monitor('key ctrl+s')
    g.wait_for(TREE + " | grep -Fq 'SoundEditor: File Save'", 30)
    click(g, 'SoundEditor: File Save', 150, 270)
    g.monitor('key End')
    g.monitor('key type ' + NAME)
    g.monitor('key Return')
    saved_title = 'SoundEditor: <' + NAME + '>'
    g.wait_for('test -s ' + FILE + ' && ' + TREE + ' | grep -Fq ' + shlex.quote(saved_title), 60)
    data = g.read('cat ' + FILE)
    saved = audio.measure_pcm(aiff_pcm(data), mono=True)
    saved.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    click(g, saved_title, 58, -12)
    g.monitor('key ctrl+q')
    g.wait_for('! ' + TREE + ' | grep -Fq ' + shlex.quote(saved_title), 30)
    reopened = launch(g, FILE)
    click(g, reopened, 58, -12)
    g.capture(out / 'reopened.png')
    start = dac.stat().st_size
    x, y = desktop.saver.position(g, reopened)
    g.monitor(f'ptr click {x+198} {y+50} left')  # Play
    time.sleep(2)
    g.monitor(f'ptr click {x+123} {y+50} left')
    time.sleep(.5)
    return {'worker_pid': worker_pid, 'aiff': saved, 'speaker': audio.measure_speaker(dac, start, mono=True)}


def run(args):
    bundle = args.bundle.resolve()
    base = bundle / 'netbsd-xiri.chd'
    checksums = dict(line.split(None, 1)[::-1] for line in (bundle / 'SHA256SUMS').read_text().splitlines())
    if desktop.sha256(base) != checksums[base.name]:
        raise ValueError('Unexpected base disk')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    probe = desktop.load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = (args.emulator.resolve() / n for n in ('iris', 'iris-ci'))
    files = {'module': args.module, 'netbsd': args.kernel, 'netbsd.boot': args.boot_kernel}
    if args.share_probe:
        files['fullshare'] = args.share_probe
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        work = Path(tmp)
        disk, iso, dac = (work / name for name in ('disk.chd', 'update.iso', 'speaker.pcm'))
        os.mkfifo(work / 'input.fifo')
        (work / 'input.pcm').write_bytes(audio.fixture() * 12)
        os.environ.update(IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(work / 'profile'), IRIS_AUDIO_DUMP=str(dac))
        subprocess.run(['cp', '--reflink=auto', base, disk], check=True)
        subprocess.run(['genisoimage', '-quiet', '-R', '-o', iso, '-graft-points',
                        *(name + '=' + str(path.resolve()) for name, path in files.items())], check=True)
        for phase in ('install', 'desktop'):
            lab = desktop.native.open_lab(probe, work / phase, args.cpu, disk, bundle / 'state/nvram.bin')
            lab.config_text = (lab.config_text.replace('overlay = false', 'overlay = true')
                               .replace('no_audio = true', 'no_audio = false')
                               + '[audio]\nhost = "null"\ninput_file = ' + json.dumps(str(work / 'input.fifo'))
                               + '\n[scsi.6]\ncdrom = true\npath = ' + json.dumps(str(iso)) + '\n')
            try:
                g = desktop.cold_root(lab)
                dest = '"$(sysctl -n kern.module.path)"/compat_irix_o32/compat_irix_o32.kmod'
                g.wait_for('test -r /CDROM/module', 90)
                if phase == 'install':
                    for name, target in [('module', dest), ('netbsd', '/netbsd'), ('netbsd.boot', '/netbsd.boot')]:
                        g.command(f'install -r -m 444 /CDROM/{name} {target}')
                    g.command('sync')
                else:
                    g.command('test "$(sha256 -q ' + dest + ')" = ' + desktop.sha256(args.module))
                    if args.share_probe:
                        g.command("mkdir -p /tmp/share/child && chown -R xiritest /tmp/share && "
                                  "install -m 555 /CDROM/fullshare /tmp/share/check && "
                                  "su -f xiritest -c 'cd /tmp/share && ./check' && "
                                  'test "$(stat -f %Lp /tmp/share/child/result)" = 600')
                    desktop.saver.login_catalog(g, desktop.saver.desktop.greeter, desktop.saver.desktop.login)
                    result = record(g, work, out, dac)
                    result.update(cpu=args.cpu, base_sha256=checksums[base.name],
                                  module_sha256=desktop.sha256(args.module), kernel_sha256=desktop.sha256(args.kernel),
                                  share_probe=bool(args.share_probe))
                    (out / 'recording.json').write_text(json.dumps(result, indent=2) + '\n')
                desktop.poweroff(lab)
            except Exception:
                for name in ('serial.log', 'emulator.log'):
                    log = lab.directory / name
                    if log.exists():
                        (out / (phase + '-' + name)).write_bytes(log.read_bytes()[-24000:])
                raise
            finally:
                lab.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('bundle', 'kernel', 'boot-kernel', 'module', 'emulator', 'output'):
        parser.add_argument('--' + flag, type=Path, required=True)
    parser.add_argument('--share-probe', type=Path)
    parser.add_argument('--cpu', choices=['r4400', 'r5000'], required=True)
    run(parser.parse_args())
