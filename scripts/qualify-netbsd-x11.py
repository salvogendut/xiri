#!/usr/bin/env python3
"""Cold-boot and qualify Newport X11 drawing, input, and a twm/xterm session."""

import argparse
import base64
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import time
import uuid

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('netbsd_probe', ROOT / 'scripts/probe-netbsd.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
GUEST = '/root/xiri-x11'
SETS = ['xbase', 'xcomp', 'xetc', 'xfont', 'xserver']


def guest(lab, result, name, command, timeout=60):
    print(name, flush=True)
    started = time.monotonic()
    before = len(lab.serial_text())
    check = {'name': name, 'guest_exit_status': None}
    result['checks'].append(check)
    try:
        check['guest_exit_status'] = lab.command(command, timeout)
    finally:
        check['seconds'] = round(time.monotonic() - started, 3)
    if check['guest_exit_status']:
        raise RuntimeError(f'{name}: guest exited {check["guest_exit_status"]}')
    return lab.serial_text()[before:]


def read_file(lab, path, destination):
    token = uuid.uuid4().hex
    before = len(lab.serial_text())
    # Keep the serial command on one line. Literal newlines expose BEGIN in
    # terminal echo/continuation prompts and can be mistaken for file output.
    if lab.command(f"printf '\\nBEGIN_{token}\\n' && base64 {path} && "
                   f"printf 'END_{token}\\n'", 120):
        raise RuntimeError(f'could not read {path}')
    output = lab.serial_text()[before:]
    match = re.search(rf'^BEGIN_{token}\n(.*?)^END_{token}$', output, re.M | re.S)
    if not match:
        raise RuntimeError(f'missing file capture: {path}')
    data = base64.b64decode(''.join(match[1].split()), validate=True)
    destination.write_bytes(data)
    return data.decode('latin1')


def monitor(lab, command):
    output = lab.monitor_command(command)
    with (lab.directory / 'monitor.log').open('a') as stream:
        stream.write(command + '\n' + output + '\n')
    if any(word in output.lower() for word in ['error:', 'unknown command', 'timed out']):
        raise RuntimeError(f'{command}: {output}')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--accelerated', action='store_true', help='reproduce the open XAA color failure')
    parser.add_argument('--boot-timeout', type=int, default=300)
    args = parser.parse_args()
    args.debugger = False
    if args.boot_timeout < 1:
        parser.error('boot timeout must be positive')
    output_root = ROOT / '.work/netbsd-x'
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=f'{args.mode}-', dir=output_root))
    lab = probe.Lab(args, directory)
    result = {'mode': args.mode, 'accelerated': args.accelerated, 'status': 'error',
              'checks': [], 'clean_shutdown': False,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    started = time.monotonic()
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    try:
        checkpoint = ROOT / '.work/indy-netbsd-kernel'
        result['base_disk_sha256'] = probe.sha256(checkpoint / 'disk.raw')
        result['kernel_sha256'] = probe.sha256(ROOT / '.work/netbsd-11.0/tftp/netbsd-XIRI_INDY')
        result['emulator_sha256'] = probe.sha256(probe.IRIS)
        result['harness_sha256'] = probe.sha256(Path(__file__).resolve())
        for name in ['disk.raw', 'nvram.bin']:
            probe.run(['cp', '--reflink=auto', '--sparse=always', checkpoint / name,
                       directory / name], timeout=120)
        result['nvram_sha256'] = probe.sha256(directory / 'nvram.bin')
        media = directory / 'media'
        media.mkdir()
        inputs = ROOT / '.work/netbsd-11.0'
        manifest = (ROOT / 'lab/netbsd-11.0/SHA512SUMS').read_text().splitlines()
        selected = [line for line in manifest if line.split()[1] in
                    [f'sgimips/binary/sets/{name}.tgz' for name in SETS]]
        if len(selected) != len(SETS):
            raise RuntimeError('X11 sets missing from pinned manifest')
        subprocess.run(['sha512sum', '-c', '-'], cwd=inputs,
                       input='\n'.join(selected) + '\n', text=True, check=True)
        for name in SETS:
            (media / f'{name}.tgz').symlink_to(inputs / f'sgimips/binary/sets/{name}.tgz')
        for name in ['probe.c', 'xorg.conf']:
            probe.run(['cp', ROOT / 'lab/indy-netbsd/x11' / name, media / name])
        if args.accelerated:
            config = media / 'xorg.conf'
            config.write_text(config.read_text().replace('Option "NoAccel" "true"', 'Option "NoAccel" "false"'))
        result['probe_sha256'] = probe.sha256(media / 'probe.c')
        result['xorg_config_sha256'] = probe.sha256(media / 'xorg.conf')
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-follow-links', '-V', 'XIRI_X11',
                   '-o', directory / 'probe.iso', media], timeout=60)
        lab.start()
        guest(lab, result, 'Install verified X11 sets',
              'mkdir -p /cdrom && mount -t cd9660 -o ro /dev/cd0a /cdrom && '
              '(set -e; for s in xbase xcomp xetc xfont xserver; do '
              'echo "Installing $s"; tar -xzpf /cdrom/$s.tgz -C /; done)', 1200)
        guest(lab, result, 'Prepare wsdisplay and build the Xlib probe',
              f'mkdir -p {GUEST} && cp /cdrom/probe.c /cdrom/xorg.conf {GUEST}/ && '
              'wsconscfg -f /dev/ttyEcfg 0 && '
              'cc -O2 -Wall -Wextra -I/usr/X11R7/include -L/usr/X11R7/lib '
              f'-Wl,-rpath,/usr/X11R7/lib {GUEST}/probe.c -lX11 -o {GUEST}/probe', 180)
        guest(lab, result, 'Start Newport Xorg and wait for a client connection',
              f'export PATH=/usr/X11R7/bin:$PATH DISPLAY=:0; '
              f'{{ Xorg :0 -config {GUEST}/xorg.conf -nolisten tcp -noreset '
              f'>{GUEST}/server.log 2>&1 & xpid=$!; }}; '
              'xwait=0; until xdpyinfo > /root/xdpyinfo.txt 2>/dev/null; do '
              'kill -0 "$xpid" || break; xwait=$((xwait + 1)); '
              'test "$xwait" -lt 60 || break; sleep 1; done; '
              'xdpyinfo > /root/xdpyinfo.txt && xset s off && xset -dpms', 120)
        guest(lab, result, 'Start drawing and input probe',
              f'{{ {GUEST}/probe >{GUEST}/probe.log 2>&1 & ppid=$!; }}; '
              f'xwait=0; until grep -q "PIXEL" {GUEST}/probe.log; do '
              'kill -0 "$ppid" || break; xwait=$((xwait + 1)); '
              'test "$xwait" -lt 30 || break; sleep 1; done; '
              f'grep -q READY {GUEST}/probe.log', 60)
        monitor(lab, 'screen info')
        monitor(lab, f'screen shot {directory}/drawing.png')
        pixel_checks = []
        # Xorg allocates 0xfe components on this release; compare the composed
        # frame as well as XGetImage, which reads the shadow buffer with NoAccel.
        for i, expected in enumerate(['fe0000', '00fe00', '0000fe', 'fefefe']):
            for x, y in [(100 + 120 * i, 160), (100 + 120 * i, 280),
                         (568 + 16 * (i % 2), 128 + 16 * (i // 2))]:
                output = monitor(lab, f'screen pix {x} {y}')
                match = re.search(r'= ([0-9a-fA-F]{6})', output)
                actual = match[1].lower() if match else None
                pixel_checks.append({'x': x, 'y': y, 'expected': expected, 'actual': actual})
        result['display_pixels'] = pixel_checks
        monitor(lab, 'key type Xiri_123')
        monitor(lab, 'key Return')
        for x, button in [(100, 'left'), (180, 'middle'), (260, 'right')]:
            monitor(lab, f'ptr click {x} 400 {button}')
        guest(lab, result, 'Keyboard text, releases, mouse movement and three buttons',
              f'sleep 1; grep -q TEXT_PASS {GUEST}/probe.log && '
              f'grep -q "KEY_UP Return" {GUEST}/probe.log && '
              f'grep -q "MOTION " {GUEST}/probe.log && '
              '(set -e; for b in 1 2 3; do '
              f'grep -q "BUTTON_DOWN $b " {GUEST}/probe.log; '
              f'grep -q "BUTTON_UP $b " {GUEST}/probe.log; done)')
        log = read_file(lab, f'{GUEST}/probe.log', directory / 'probe.log')
        result['drawing_passed'] = 'PIXELS_PASS' in log and 'PIXEL_FAIL' not in log
        guest(lab, result, 'Open a twm desktop and xterm',
              'kill "$ppid"; wait "$ppid" 2>/dev/null; '
              f'printf "RandomPlacement\\n" >{GUEST}/twmrc; '
              f'{{ twm -f {GUEST}/twmrc >{GUEST}/twm.log 2>&1 & wpid=$!; }}; '
              f'{{ xterm -geometry 80x24+100+100 -title Xiri-NetBSD '
              f'>{GUEST}/xterm.log 2>&1 & tpid=$!; }}; sleep 5; '
              'kill -0 "$wpid" && kill -0 "$tpid"', 90)
        monitor(lab, 'ptr click 200 200 left')
        monitor(lab, f'key type echo XIRI_XTERM_OK > {GUEST}/xterm-proof')
        monitor(lab, 'key Return')
        guest(lab, result, 'Command entered through the graphical terminal',
              f'sleep 1; test "$(cat {GUEST}/xterm-proof)" = XIRI_XTERM_OK')
        monitor(lab, f'screen shot {directory}/desktop.png')
        read_file(lab, '/root/xdpyinfo.txt', directory / 'xdpyinfo.txt')
        guest(lab, result, 'Stop X clients and server cleanly',
              'kill "$tpid" "$wpid"; wait "$tpid" 2>/dev/null; '
              'wait "$wpid" 2>/dev/null; kill "$xpid"; wait "$xpid"; sync', 90)
        read_file(lab, '/var/log/Xorg.0.log', directory / 'Xorg.0.log')
        if not result['drawing_passed'] or any(p['actual'] != p['expected'] for p in pixel_checks):
            raise RuntimeError('drawing/readback or composed display pixel mismatch')
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
        print(result['error'], flush=True)
        if lab.logged_in:
            for path, name in [(f'{GUEST}/probe.log', 'probe.log'),
                               ('/var/log/Xorg.0.log', 'Xorg.0.log'),
                               (f'{GUEST}/server.log', 'server.log')]:
                try:
                    read_file(lab, path, directory / name)
                except Exception as capture_error:
                    print(f'Capture {name}: {capture_error}', flush=True)
    finally:
        if lab.logged_in:
            try:
                lab.command('pkill -x probe; pkill -x xterm; pkill -x twm; '
                            'pkill -x Xorg; sleep 2; sync', 30)
            except Exception as error:
                print(f'X cleanup: {error}', flush=True)
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        if args.mode == 'ci' and (directory / 'emulator.pid').exists():
            pid = int((directory / 'emulator.pid').read_text())
            if pid <= 1:
                raise RuntimeError('invalid emulator PID for overlay retention')
            # CI puts its overlay in the container's /tmp. Preserve only this
            # stopped run's files beside its logs, including the dirty sidecar.
            for suffix in ['.overlay', '.overlay.dirty']:
                probe.run(probe.TOOLBOX + ['sh', '-c',
                          'if test -f "$1"; then mv -- "$1" "$2"; fi',
                          'xiri-overlay', f'/tmp/iris-ci-{pid}-scsi1{suffix}',
                          str(directory / f'live{suffix}')])
        result['seconds'] = round(time.monotonic() - started, 3)
        if not lab.clean_shutdown:
            result['status'] = 'error'
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
