#!/usr/bin/env python3
"""Make a local IRIS CD from the original SGI Freeware UnZip 5.40 tardist."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

TARDIST_SHA256 = '48fea0e915d9d4a41227f3034503e6553aae7dfe31617bd469ede355fc56eda3'


def build(archive, output):
    with archive.open('rb') as source, tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        if hashlib.file_digest(source, 'sha256').hexdigest() != TARDIST_SHA256:
            raise ValueError('Expected the original SGI fw_unzip-5.40.tardist')
        source.seek(0)
        cd = Path(tmp) / 'cd'
        dist = cd / 'dist'
        dist.mkdir(parents=True)
        with tarfile.open(fileobj=source) as products:
            for name in ('fw_unzip', 'fw_unzip.idb', 'fw_unzip.sw'):
                member = products.getmember(name)
                if not member.isfile():
                    raise ValueError(f'Expected a regular file for {name}')
                with products.extractfile(member) as entry, (dist / name).open('wb') as copy:
                    shutil.copyfileobj(entry, copy)
        (cd / 'sample.txt').write_bytes(b'Xiri Freeware upgrade\n')
        with zipfile.ZipFile(cd / 'sample.zip', 'w', zipfile.ZIP_DEFLATED) as sample:
            sample.write(cd / 'sample.txt', 'sample.txt')
        for name in ('unzip-upgrade.sh', 'desktop-artwork.sh', 'xmahjongg.sh', 'package-filetypes.mk'):
            shutil.copyfile(Path(__file__).with_name(name), cd / name)
        iso = Path(tmp) / 'unzip.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'XIRI_UNZIP_540', '-o', iso, cd], check=True)
        os.link(iso, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('output', type=Path, help='new ISO path')
    args = parser.parse_args()
    build(args.archive, args.output)
