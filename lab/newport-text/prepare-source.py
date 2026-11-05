#!/usr/bin/env python3
"""Prepare the pinned Newport texture and software-fallback corrections."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('destination', type=Path)
parser.add_argument('--cache', type=Path, help='verified original Newport source cache')
args = parser.parse_args()
pin = json.loads((HERE/'source.json').read_text())
for path, digest in pin['inputs_sha256'].items():
    if hashlib.sha256((ROOT/path).read_bytes()).hexdigest() != digest:
        raise SystemExit('source input hash mismatch: '+path)
command = [sys.executable, str(ROOT/'lab/newport-xaa/prepare-source.py'), str(args.destination)]
if args.cache:
    command += ['--cache', str(args.cache)]
subprocess.run(command, check=True)
subprocess.run(['git', 'apply', '--unsafe-paths',
                '--directory='+str(args.destination.resolve()),
                str(HERE/'shadow-fallback.patch')], check=True)
