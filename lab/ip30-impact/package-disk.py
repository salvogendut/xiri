#!/usr/bin/env python3
"""Package a halted Octane installation for manual IRIS use."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from wsconsole import sha256


def write_configuration(dest, release, board):
    port = 20722 if release == '6.5.22' else 20730
    (dest/'iris.toml').write_text(f'''nvram = "nvram.bin"
banks = [512, 0, 0, 0]
headless = false
ci = false
no_audio = true
serial_log = "serial.log"
serial_log_overwrite = true
monitor_port = {port}
serial_port_a = {port + 1}
serial_port_b = {port + 2}
[machine]
profile = "octane_ip30"
cpu = "r10000"
cpus = 1
[octane]
flash = "flash.bin"
[graphics]
board = "{board}"
[scsi.1]
path = "netbsd-xiri.chd"
overlay = true
''')
    shutil.copy2(Path(__file__).with_name('run-disk.sh'), dest/'run-iris.sh')
    (dest/'README.txt').write_text(f'''Xiri for Octane R10000, IRIX {release}, {board}.

Run ./run-iris.sh to boot from SCSI disk 1. If IRIS is paused, press Ctrl-P.
At xdm, use xiritest / xiritest for 4Dwm or netbsdtest / netbsdtest for ctwm.
Serial administration is on localhost port {port + 1} (IOC3 port A).
Run shutdown -h now as root and wait for the PROM menu before closing IRIS.
IRIS keeps manual changes in a separate CHD overlay next to the image.
''')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installation', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--release', required=True, choices=('6.5.22', '6.5.30'))
    parser.add_argument('--chdman', default='chdman')
    args = parser.parse_args()
    src, dest = args.installation.resolve(), args.output.resolve()
    run = json.loads((src/'result.json').read_text())
    if run['mode'] != 'install' or not all(run[k] for k in
            ('passed', 'clean_halt', 'stopped', 'originals_unchanged')):
        raise ValueError('installation must have stopped after a successful clean halt')
    disk, overlay = src/'disk.chd', src/'disk.chd.diff.chd'
    original, = [Path(p) for p in run['inputs'] if p.endswith('.chd')]
    baseline = json.loads((original.parent/'qualification.json').read_text())
    parent_hash = run['inputs'][str(original)]
    if (baseline['release'] != args.release or baseline['chd_sha256'] != parent_hash
            or sha256(disk) != parent_hash):
        raise ValueError('release or parent disk does not match the installation')
    dest.mkdir(parents=True, exist_ok=False)
    image = dest/'netbsd-xiri.chd'
    subprocess.run([args.chdman, 'copy', '-i', overlay, '-ip', disk, '-o', image,
                    '-c', 'zlib', '-np', '2'], check=True)
    subprocess.run([args.chdman, 'verify', '-i', image], check=True)
    for name in ('nvram.bin', 'flash.bin'):
        shutil.copyfile(src/name, dest/name)
    write_configuration(dest, args.release, run["board"])
    print(f'{args.release} {sha256(image)}  {image}')


if __name__ == '__main__':
    main()
