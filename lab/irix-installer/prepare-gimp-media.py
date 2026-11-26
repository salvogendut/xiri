#!/usr/bin/env python3
"""Collect the original May 2004 GIMP runtime and plug-in dependencies from four CDs."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile


def build(cds, output):
    here = Path(__file__).resolve().parent
    spec = json.loads((here / 'gimp-cd.json').read_text())
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        work = Path(tmp)
        media = work / 'cd'
        dist = media / 'dist'
        dist.mkdir(parents=True)
        for path, digest in spec['files'].items():
            target = dist / Path(path).name
            shutil.copyfile(cds / path, target)
            with target.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != digest:
                    raise ValueError(f'Unexpected Freeware distribution file: {path}')
        (media / 'selections').write_text('\n'.join(spec['subsystems']) + '\n')
        for name in ('gimp.sh', 'desktop-artwork.sh', 'xmahjongg.sh', 'package-filetypes.mk', 'unzip-upgrade.sh'):
            shutil.copyfile(here / name, media / name)
        iso = work / 'gimp.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'XIRI_GIMP_125', '-o', iso, media], check=True)
        output.hardlink_to(iso)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cds', type=Path, help='directory containing cd-1/dist through cd-4/dist')
    parser.add_argument('output', type=Path, help='new private ISO')
    args = parser.parse_args()
    build(args.cds, args.output)
