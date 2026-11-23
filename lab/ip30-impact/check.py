#!/usr/bin/env python3
"""Boot the IP30 inventory kernel with an explicit IRIS graphics board."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--netbsd', type=Path, default=ROOT.parent / 'NetBSD-xiri')
    for arg in ('emulator', 'kernel', 'firmware', 'disk', 'output'):
        parser.add_argument('--' + arg, type=Path, required=True)
    parser.add_argument('--board', choices=('solidimpact', 'highimpact', 'none'), required=True)
    args = parser.parse_args()
    nvram = args.firmware / 'nvram.bin'
    # The Octane PROM uses the graphics console when a board is installed
    # and console=g. This harness sends boot commands over IOC3 serial.
    if args.board != 'none' and nvram.read_bytes()[0x11:0x13] != b'd\0':
        parser.error("use an Octane NVRAM saved after 'setenv console d'")
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
        subprocess.run([sys.executable, str(probe), '--xiri', str(ROOT),
                        '--machine', 'octane', '--single-user', '--expect',
                        'XIRI_IP30_M3D2_READY', '--image', str(args.kernel),
                        '--disk', str(args.disk), '--flash', str(args.firmware / 'flash.bin'),
                        '--nvram', str(nvram), '--emulator',
                        str(launchers), '--output', str(out)], check=True)

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
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if result['status'] != 'passed':
        sys.exit(f"{args.board}: {result['error']}")
    print(f'{args.board}: {len(widgets)} HQ4, native shell and clean halt')


if __name__ == '__main__':
    main()
