#!/usr/bin/env python3
"""Run the file-growth fixtures and two SGI applications on a private Xiri Indy."""
import argparse
import importlib.util
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import tarfile
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('desktop', ROOT / 'lab/native-iso/check-desktop.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)
audio = desktop.load('record', 'lab/native-iso/check-haltwo-record.py')

CASES = (
    'shared-past-eof-store', 'shared-past-eof-read', 'shared-grow-empty-store',
    'shared-no-grow-past-eof-store', 'shared-no-grow-past-eof-read',
    'shared-grow-within-file', 'shared-grow-file-readonly',
    'shared-file-second-map', 'shared-file-fork', 'installer-close-fork',
    'private-past-eof-store', 'shared-readonly-store',
)


def fixtures(path, directory):
    manifest = json.loads((path / 'manifest.json').read_text())
    commands = ['#!/bin/sh', 'set -eu', 'cd "$1"', 'ulimit -c 0', 'mkdir records']
    files = {}
    for case in manifest['cases']:
        name = case['name']
        _, dispatch, kind = name.split('-', 2)
        if dispatch != 'direct' or kind not in CASES:
            continue
        size = case['symbols']['FILE_SIZE']
        files[name] = path / name
        if desktop.sha256(files[name]) != manifest['files'][name]['sha256']:
            raise ValueError(f'Fixture checksum mismatch: {name}')
        commands.extend(['rm -f input.txt', f'sh setup.sh {size}', f'./{name} > records/{name}.out',
                         f'cp data records/{name}.data'])
    script = directory / 'cases.sh'
    script.write_text('\n'.join(commands) + '\n')
    files.update({'cases.sh': script, 'setup.sh': path / 'setup.sh', 'mapping': path / 'mapping'})
    return files


def observations(blob, *, vendor=False):
    rows = {}
    with tarfile.open(fileobj=io.BytesIO(blob)) as tar:
        for member in tar.getmembers():
            name = Path(member.name).name
            if not name.endswith('.out'):
                continue
            w = struct.unpack('>64I', tar.extractfile(member).read())
            if w[0] != 0x584d5348:
                raise ValueError(f'{name}: invalid fixture record')
            data = tar.extractfile(member.name[:-4] + '.data').read()
            kind = name.split('-', 2)[2][:-4]
            page, original_size, target = w[5], w[25], w[27]
            if page not in (4096, 8192, 16384):
                raise ValueError(f'{name}: unexpected page size {page}')
            expected = bytearray([0x3c]) * original_size
            child = (0, 0)
            errno = 0
            if kind in ('shared-past-eof-store', 'shared-past-eof-read', 'shared-grow-empty-store'):
                child = (1, 37)
                expected.extend(bytes((target // page + 1) * page - original_size))
                if kind.endswith('store'):
                    expected[target] = 0x73
            elif kind.startswith('shared-no-grow-past-eof'):
                child = (2, 10)  # IRIX SIGBUS
            elif kind == 'shared-readonly-store':
                child = (2, 11)  # IRIX SIGSEGV
            elif kind == 'shared-grow-file-readonly':
                errno = 13
            elif kind == 'private-past-eof-store':
                if vendor:
                    child = (1, 37)
                else:
                    errno = 22
            elif kind in ('shared-file-fork', 'installer-close-fork'):
                child = (1, 37)
                if kind == 'shared-file-fork':
                    expected[0], expected[w[17] - 1] = 0x8b, 0xc9
            elif kind in ('shared-file-second-map', 'shared-grow-within-file'):
                expected[0] = 0x9b if kind == 'shared-file-second-map' else 0x5a
                expected[w[17] - 1] = 0xa6
            actual_errno = w[2] if w[4] else 0
            if (actual_errno, w[28:30], data) != (errno, child, expected):
                raise ValueError(f'{name}: errno={actual_errno}, child={w[28:30]}, size={len(data)}')
            if w[22] == 1 and not w[53] and w[26] != original_size:
                raise ValueError(f'{name}: size changed at mmap')
            rows[name[:-4]] = dict(page=w[5], mmap_errno=w[2] if w[4] else 0,
                                  initial_bytes=w[25], mapped_bytes=w[26] if not w[53] else None,
                                  child_code=w[28], child_status=w[29], final_bytes=len(data),
                                  byte_at_target=data[w[27]] if w[27] < len(data) else None,
                                  uid=w[56], backing_sha256=hashlib.sha256(data).hexdigest())
    if len(rows) != 2 * len(CASES):
        raise ValueError('Incomplete fixture records')
    return rows


def record_in_editor(guest, out, fifo, source, dac):
    x, y = desktop.saver.position(guest, 'SoundEditor: Untitled')
    def click(dx):
        guest.monitor(f'ptr click {x+dx} {y+50} left')
    with audio.feed(source, fifo):
        click(48)  # Record
        time.sleep(4)
        click(123)  # Stop
        time.sleep(1)
    guest.capture(out / 'soundeditor-recorded.png')
    if 'Sound Editor: Error' in guest.read_text('xwininfo -root -tree'):
        (out / 'editor-playback.json').write_text(json.dumps({
            'observation': 'Record opened a Sound Editor error dialog',
        }, indent=2) + '\n')
        return
    start = dac.stat().st_size if dac.exists() else 0
    click(198)  # Play
    time.sleep(5)
    click(123)
    time.sleep(1)
    try:
        result = audio.measure_speaker(dac, start, mono=True)
    except (FileNotFoundError, ValueError) as error:
        result = {'observation': str(error)}
    (out / 'editor-playback.json').write_text(json.dumps(result, indent=2) + '\n')


def run(args):
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    bundle = args.bundle.resolve()
    source = bundle / 'netbsd-xiri.chd'
    sums = dict(line.split(None, 1)[::-1] for line in (bundle / 'SHA256SUMS').read_text().splitlines())
    if desktop.sha256(source) != sums['netbsd-xiri.chd']:
        raise ValueError('Base disk checksum mismatch')
    probe = desktop.load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = (args.emulator.resolve() / n for n in ('iris', 'iris-ci'))
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        work = Path(tmp)
        os.environ.update(IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(work / 'profile'))
        fifo, source_pcm, dac = (work / n for n in ('mic.fifo', 'tone.pcm', 'speaker.pcm'))
        os.mkfifo(fifo)
        source_pcm.write_bytes(audio.fixture() * 12)
        disk = work / 'system.chd'
        subprocess.run(['cp', '--reflink=auto', source, disk], check=True)
        files = fixtures(args.fixtures, work)
        iso = work / 'update.iso'
        if args.native_control:
            files['native'] = args.native_control
        else:
            files['native.c'] = ROOT / 'lab/irix-mmap-shared/native-control.c'
        files.update({'netbsd': args.kernel, 'netbsd.boot': args.boot_kernel, 'module': args.module})
        subprocess.run(['genisoimage', '-quiet', '-R', '-o', iso, '-graft-points',
                        *(f'{n}={p.resolve()}' for n, p in files.items())], check=True)
        for phase in ('install', 'test'):
            lab = desktop.native.open_lab(probe, work / phase, args.cpu, disk, bundle / 'state/nvram.bin')
            lab.config_text = lab.config_text.replace('overlay = false', 'overlay = true')
            lab.config_text = lab.config_text.replace('no_audio = true', 'no_audio = false')
            if phase == 'test':
                os.environ['IRIS_AUDIO_DUMP'] = str(dac)
            lab.config_text += f'[audio]\nhost = "null"\ninput_file = {json.dumps(str(fifo))}\n[scsi.6]\ncdrom = true\npath = {json.dumps(str(iso))}\n'
            try:
                guest = desktop.cold_root(lab)
                print(bundle.name, phase, 'booted', flush=True)
                guest.wait_for('test -r /CDROM/netbsd.boot', 90)
                if phase == 'install':
                    for n, dest in [('netbsd', '/netbsd'), ('netbsd.boot', '/netbsd.boot'),
                                    ('module', '"$(sysctl -n kern.module.path)"/compat_irix_o32/compat_irix_o32.kmod')]:
                        guest.command(f'install -r -m 444 /CDROM/{n} {dest}')
                    guest.command('sync')
                else:
                    guest.command('mkdir /tmp/ag && cp /CDROM/*direct-* /CDROM/*.sh /CDROM/mapping /tmp/ag && '
                                  'chmod 555 /tmp/ag/*direct-* && chown -R xiritest /tmp/ag && '
                                  "su -f xiritest -c 'sh /tmp/ag/cases.sh /tmp/ag'", 360)
                    native_setup = ('install -m 555 /CDROM/native /tmp/ag/native' if args.native_control
                                    else 'cc -O2 /CDROM/native.c -o /tmp/ag/native')
                    native = guest.command(native_setup + " && su -f xiritest -c 'ulimit -c 0; /tmp/ag/native'", 180)
                    if 'zero=1 shared=1 private=1 close=1 file=1 eof=1' not in native:
                        raise ValueError('Incomplete native control')
                    rows = observations(guest.read('cd /tmp/ag && tar cf - records'))
                    (out / 'mappings.json').write_text(json.dumps(rows, indent=2) + '\n')
                    print(bundle.name, 'mapping cases captured', flush=True)
                    desktop.saver.login_catalog(guest, desktop.saver.desktop.greeter, desktop.saver.desktop.login)
                    guest.command("su -f xiritest -c '/usr/local/libexec/xiri/cdromd --eject'")
                    lab.ci('cdrom-load', '6', str(args.disc.resolve()))
                    guest.wait_for("cdplay -f /dev/rcd0c info | grep -q audio", 30)
                    x, y = desktop.saver.position(guest, '"winterm"')
                    # Both programs inherit the same logged-in user's X credentials
                    # even if the first one takes focus, forks or opens a dialog.
                    apps = [('cdman', 'cdman -dev /dev/scsi/sc0d6l0'), ('soundeditor', 'soundeditor')]
                    for name, cmd in apps:
                        script = ['ulimit -c 0',
                                  f'ktrace -i -t cnu -f /tmp/{name}.trace '
                                  f'/emul/irix/usr/sbin/{cmd} >/tmp/{name}.log 2>&1',
                                  f'echo $? >/tmp/{name}.rc']
                        guest.command("printf '%s\\n' " + shlex.join(script) + f" >/tmp/ag/launch-{name}")
                    supervisor = ['touch /tmp/ag/ready', 'for app in cdman soundeditor; do',
                                  'while test ! -f /tmp/ag/go-$app; do sleep 1; done',
                                  'sh /tmp/ag/launch-$app &', 'done', 'wait']
                    guest.command("printf '%s\\n' " + shlex.join(supervisor) + " >/tmp/ag/start")
                    guest.monitor(f'ptr click {x+40} {y+40} left')
                    time.sleep(.5)
                    guest.monitor('key type sh /tmp/ag/start')
                    time.sleep(.5)
                    guest.monitor('key Return')
                    guest.wait_for('test -f /tmp/ag/ready', 30)
                    for name, _ in apps:
                        guest.command(f'touch /tmp/ag/go-{name}')
                        guest.wait_for(f'test -e /tmp/{name}.log', 60)
                        title = 'Sound ?Editor' if name == 'soundeditor' else 'CD ?(Player|Manager)'
                        # One bounded wait inside the guest also captures a live process
                        # that never maps a window, or a launcher that exits immediately.
                        guest.command(f"i=0; while test $i -lt 25 && test ! -s /tmp/{name}.rc && "
                                      f"! xwininfo -root -tree | grep -Eiq '{title}'; "
                                      "do sleep 1; i=$((i+1)); done; sleep 2", 60)
                        tree = guest.read_text('xwininfo -root -tree')
                        (out / f'{name}-tree.txt').write_text(tree)
                        log = guest.read_text(f'cat /tmp/{name}.log; cat /tmp/{name}.rc; ps -axw | grep -E "[s]oundeditor|[c]dman"')
                        (out / f'{name}.txt').write_text(log)
                        guest.capture(out / f'{name}.png')
                        print(name, log[:500], flush=True)
                        if name == 'soundeditor' and 'SoundEditor: Untitled' in tree:
                            record_in_editor(guest, out, fifo, source_pcm, dac)
                        guest.command(f'ktrace -c -p "$(pgrep -u xiritest -x {name} | head -1)" 2>/dev/null || true')
                        trace = guest.read_text(f'kdump -Nn -f /tmp/{name}.trace | tail -180')
                        (out / f'{name}-trace.txt').write_text(trace)
                        guest.command(f'pkill -u xiritest -x {name} || true')
                desktop.poweroff(lab)
            finally:
                for filename in ('serial.log', 'emulator.log'):
                    src = lab.directory / filename
                    if src.exists():
                        (out / f'{phase}-{filename}').write_bytes(src.read_bytes()[-100000:])
                lab.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    pack = sub.add_parser('pack-reference', help='prepare the donor fixture tar')
    pack.add_argument('fixtures', type=Path)
    pack.add_argument('output', type=Path)
    verify = sub.add_parser('read-reference', help='validate an original IRIX records.tar')
    verify.add_argument('archive', type=Path)
    test = sub.add_parser('test', help='run the Xiri tests')
    for name in ('bundle', 'emulator', 'fixtures', 'kernel', 'boot-kernel', 'module', 'disc', 'output'):
        test.add_argument('--' + name, required=True, type=Path)
    test.add_argument('--native-control', type=Path, help='cross-built native-control.c for a guest without cc')
    test.add_argument('--cpu', required=True, choices=['r4400', 'r5000'])
    args = parser.parse_args()
    if args.action == 'test':
        run(args)
    elif args.action == 'read-reference':
        print(json.dumps(observations(args.archive.read_bytes(), vendor=True), indent=2))
    else:
        with tempfile.TemporaryDirectory() as tmp, tarfile.open(args.output, 'x', format=tarfile.USTAR_FORMAT) as tar:
            for name, path in fixtures(args.fixtures, Path(tmp)).items():
                tar.add(path, arcname=name)
