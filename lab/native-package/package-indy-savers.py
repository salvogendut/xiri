#!/usr/bin/env python3
"""Make an add-on CD from a release-matched xlock saver import."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--imported', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    record = json.loads((args.imported / 'manifest.json').read_text())
    release = record['release']
    if release not in ('6.5.22f', '6.5.30f'):
        parser.error('expected an Indy saver import')
    profile = ROOT / 'profiles' / f'irix-{release}-xlock-savers-v1.json'
    archive = args.imported / 'payload.tar.gz'
    if record['profile_sha256'] != sha256(profile) or record['payload_sha256'] != sha256(archive):
        parser.error('the profile or import archive has changed')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        stage = Path(tmp)
        disc = stage / 'cd'
        disc.mkdir()
        (disc / 'release').write_text(release + '\n')
        rows = []
        with tarfile.open(archive) as payload:
            for path, spec in json.loads(profile.read_text())['paths'].items():
                member = payload.getmember('emul/irix' + path)
                if not member.isfile() or member.mode not in (0o444, 0o555):
                    raise ValueError('unexpected saver file: ' + path)
                target = disc / 'files' / path.lstrip('/')
                target.parent.mkdir(parents=True, exist_ok=True)
                with payload.extractfile(member) as source, target.open('xb') as out:
                    shutil.copyfileobj(source, out)
                if sha256(target) != spec['sha256']:
                    raise ValueError('saver content differs: ' + path)
                rows.append(f'{spec["sha256"]} {member.mode:o} {path.lstrip("/")}')
        (disc / 'inventory').write_text('\n'.join(rows) + '\n')
        shutil.copyfile(Path(__file__).with_name('install-indy-savers.sh'), disc / 'install.sh')
        image = stage / 'savers.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'XIRI_SAVERS', '-o', image, disc], check=True)
        args.output.hardlink_to(image)


if __name__ == '__main__':
    main()
