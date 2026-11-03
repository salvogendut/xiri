#!/usr/bin/env python3
"""Fetch or verify the pinned Newport source, then apply the Xiri texture fix."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import urllib.request

HERE = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('destination', type=Path)
parser.add_argument('--cache', type=Path, help='directory containing the original source files')
args = parser.parse_args()
pin = json.loads((HERE/'source.json').read_text())
args.destination.mkdir(parents=True, exist_ok=False)
for name, expected in pin['upstream_files_sha256'].items():
    if args.cache:
        data = (args.cache/name).read_bytes()
    else:
        url = f"https://raw.githubusercontent.com/NetBSD/xsrc/{pin['revision']}/{pin['path']}/{name}"
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise SystemExit('source hash mismatch: '+name)
    (args.destination/name).write_bytes(data)
subprocess.run(['git', 'apply', '--unsafe-paths',
                '--directory='+str(args.destination.resolve()),
                str(HERE/'texture-coordinates.patch')], check=True)
shutil.copyfile(HERE/'config.h', args.destination/'config.h')
print(args.destination)
