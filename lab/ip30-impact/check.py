#!/usr/bin/env python3
"""Boot an IP30 graphics or input test with an explicit IRIS board."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def capture_at_shell(boot, out, ci):
    """Sample after autoconfiguration and before the serial harness halts the guest."""
    serial = out / 'serial.log'
    while boot.poll() is None:
        if serial.exists() and 'Enter pathname of shell' in serial.read_text(errors='replace'):
            run = subprocess.run([str(ci), '--json', '--socket', str(out / 'iris.sock'),
                                  'screenshot', str(out / 'rectangle.png')],
                                 check=True, timeout=10, text=True, capture_output=True)
            info = json.loads(run.stdout)
            if info.get('fresh') is not True:
                raise ValueError('guest display did not publish a fresh frame')
            return
        time.sleep(0.2)
    raise ValueError('guest exited before the serial shell prompt')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--netbsd', type=Path, default=ROOT.parent / 'NetBSD-xiri')
    for arg in ('emulator', 'kernel', 'firmware', 'disk', 'output'):
        parser.add_argument('--' + arg, type=Path, required=True)
    parser.add_argument('--board', choices=('solidimpact', 'highimpact', 'none'), required=True)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--wsdisplay', action='store_true', help='verify kernel and shell text on wsdisplay')
    mode.add_argument('--xorg', action='store_true', help='check IOC3 input and full-screen wsfb')
    mode.add_argument('--rectangle', action='store_true',
                      help='capture the PIO test kernel scanout before shutdown')
    args = parser.parse_args()
    capture = args.rectangle and args.board != 'none'
    if capture:
        from scanout import check as check_scanout
    nvram = args.firmware / 'nvram.bin'
    # The Octane PROM uses the graphics console when a board is installed
    # and console=g. This harness sends boot commands over IOC3 serial.
    if args.board != 'none' and nvram.read_bytes()[0x11:0x13] != b'd\0':
        parser.error("use an Octane NVRAM saved after 'setenv console d'")
    if args.xorg and args.board == 'none':
        parser.error('--xorg requires an IMPACT board')
    if args.wsdisplay or args.xorg:
        from wsconsole import run
        run(args)
        return
    emulator = args.emulator.resolve()
    binary = emulator / 'iris'
    out = args.output.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    # The fork's serial boot harness selects board=none in its TOML.
    # Use IRIS's normal command-line override while retaining that harness's
    # private firmware/disk copies, shell checks and shutdown supervision.
    with tempfile.TemporaryDirectory(dir=out.parent) as directory:
        launchers = Path(directory)
        launcher = launchers / 'iris'
        launcher.write_text('#!/bin/sh\nexec ' + shlex.quote(str(binary)) +
                            ' "$@" --graphics ' + args.board + '\n')
        launcher.chmod(0o755)
        (launchers / 'iris-ci').symlink_to(emulator / 'iris-ci')
        probe = args.netbsd / 'xiri/platforms/probe.py'
        command = [sys.executable, str(probe), '--xiri', str(ROOT),
                   '--machine', 'octane', '--single-user', '--expect',
                   'XIRI_IP30_M3D2_READY', '--image', str(args.kernel),
                   '--disk', str(args.disk), '--flash', str(args.firmware / 'flash.bin'),
                   '--nvram', str(nvram), '--emulator',
                   str(launchers), '--output', str(out)]
        capture_error = None
        with subprocess.Popen(command) as boot:
            if capture:
                try:
                    capture_at_shell(boot, out, emulator / 'iris-ci')
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    capture_error = str(exc)
            if boot.wait() != 0:
                sys.exit(f'{args.board}: native boot failed; see {out / "result.json"}')

    serial = (out / 'serial.log').read_text(errors='replace')
    pattern = r'ip30gfxprobe0: IMPACT HQ4 at widget (\d+), id (0x[0-9a-f]+)'
    widgets = re.findall(pattern, serial)
    expected = [] if args.board == 'none' else [('11', '0xc003555')]
    counts = re.findall(r'ip30gfxprobe0: (\d+) IMPACT board\(s\)', serial)
    result = json.loads((out / 'result.json').read_text())
    with binary.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    result.update(board=args.board, widgets=widgets, iris_sha256=digest)
    if widgets != expected or counts != [str(len(expected))]:
        result.update(status='inventory-failed',
                      error=f'unexpected inventory: widgets={widgets}, counts={counts}')
    if args.rectangle:
        submitted = serial.count('ip30gfxprobe0: HQ4 rectangle submitted')
        if '(XIRI_IP30_HQ4_FILL)' not in serial:
            result.update(status='draw-failed', error='expected the HQ4 fill kernel')
        elif submitted != int(capture) or 'HQ4 rectangle submission failed' in serial:
            result.update(status='draw-failed', error=f'rectangles submitted: {submitted}')
        elif capture:
            try:
                if capture_error:
                    raise ValueError(capture_error)
                metrics = check_scanout(out / 'rectangle.png')
                metrics['fresh'] = True
                result['scanout'] = metrics
                if metrics['inside_errors'] or metrics['outside_errors']:
                    raise ValueError(f'pixel mismatches: {metrics}')
            except (ValueError, OSError) as exc:
                result.update(status='scanout-failed', error=str(exc))
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if result['status'] != 'passed':
        sys.exit(f"{args.board}: {result['error']}")
    print(f'{args.board}: {len(widgets)} HQ4, native shell and clean halt')


if __name__ == '__main__':
    main()
