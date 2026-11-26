#!/usr/bin/env python3
"""Build a reversible kernel update CD for one qualified 11.99.9 SGI platform."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
MODELS = {'ip28': 'SGI-IP28', 'ip30': 'IP30', 'o2': 'SGI-IP32'}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('platform', choices=MODELS)
parser.add_argument('--kernel', type=Path, required=True)
parser.add_argument('--module', type=Path, required=True)
parser.add_argument('--previous-kernel-sha256', required=True)
parser.add_argument('--boot', type=Path, help='O2 ELF32 boot image')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
if (args.platform == 'o2') != bool(args.boot):
    parser.error('only O2 requires --boot')
if len(args.previous_kernel_sha256) != 64 or any(
    c not in '0123456789abcdef' for c in args.previous_kernel_sha256
):
    parser.error('invalid previous kernel digest')
files = {
    'kernel': args.kernel,
    'module': args.module,
    'upgrade.sh': ROOT / 'packaging/native/upgrade-platform-kernel.sh',
}
if args.boot:
    files['boot'] = args.boot
with tempfile.TemporaryDirectory(dir=args.output.parent) as temp:
    stage = Path(temp)
    for name, value in [('previous-kernel', args.previous_kernel_sha256), ('model', MODELS[args.platform])]:
        files[name] = stage / name
        files[name].write_text(value + '\n')
    sums = stage / 'SHA256'
    sums.write_text(
        ''.join(
            f'SHA256 ({name}) = {hashlib.sha256(path.read_bytes()).hexdigest()}\n'
            for name, path in files.items()
        )
    )
    iso = stage / 'update.iso'
    subprocess.run(
        [
            'genisoimage',
            '-quiet',
            '-R',
            '-V',
            'XIRI_PLATFORM_V6',
            '-o',
            iso,
            '-graft-points',
            f'SHA256={sums}',
            *(f'{name}={path.resolve()}' for name, path in files.items()),
        ],
        check=True,
    )
    args.output.hardlink_to(iso)
