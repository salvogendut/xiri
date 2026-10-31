#!/usr/bin/env python3
"""Extract two original X resources read-only; keep vendor bytes under .work."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / '.work/irix-reference'
WORK = ROOT / '.work/irix-toolchest-input'
PATHS = ['/usr/lib/X11/XKeysymDB', '/usr/lib/X11/rgb.txt']


def main():
    raw = REFERENCE / 'media/irix65.raw'
    pin = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    if raw.stat().st_size != pin['logical_disk_bytes']:
        raise RuntimeError('reference image size mismatch')
    WORK.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LIBGUESTFS_BACKEND='direct',
               LIBGUESTFS_CACHEDIR=str(REFERENCE / 'guestfs-cache'),
               LIBGUESTFS_TMPDIR=str(REFERENCE / 'tmp'))
    listener = WORK / 'guestfish-listener.log'
    with listener.open('w') as stream:
        subprocess.run(['guestfish', '--ro', '-a', str(raw), '--listen'],
                       env=env, stdout=stream, stderr=stream, check=True, timeout=30)
    pid = re.search(r'GUESTFISH_PID=(\d+)', listener.read_text())[1]

    def call(*args):
        return subprocess.run(['guestfish', '--remote=' + pid, *args],
                              capture_output=True, text=True, check=True,
                              timeout=120).stdout.strip()

    records = {}
    try:
        call('run')
        call('mount-options', 'ro,norecovery', '/dev/sda1', '/')
        for path in PATHS:
            destination = WORK / 'root' / path.lstrip('/')
            destination.parent.mkdir(parents=True, exist_ok=True)
            call('download', path, str(destination))
            records[path] = dict(realpath=call('realpath', path),
                                 bytes=destination.stat().st_size,
                                 sha256=hashlib.sha256(destination.read_bytes()).hexdigest())
    finally:
        call('exit')
    result = dict(schema=1, source='User-supplied IRIX 6.5.22m image, mounted ro,norecovery',
                  files=records)
    (WORK / 'resources.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
