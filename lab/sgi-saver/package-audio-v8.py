#!/usr/bin/env python3
"""Build a private audio-v8 repair CD from the qualified SGI saver CD for one release."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True, choices=('6.5.22f', '6.5.30f'))
    parser.add_argument('--saver-cd', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    results = ROOT / 'docs/results'
    receipt = json.loads((results / '2026-11-27-indy-saver-repair.json').read_text())
    session = ROOT / 'runtime/libexec/desktop-clients.sh'
    if sha256(session) != receipt['session_script_sha256']:
        parser.error('expected the qualified audio-v8 session replay correction')
    profile = json.loads((ROOT / f'profiles/irix-{args.release}-xlock-savers-v1.json').read_text())
    native = json.loads((results / '2026-11-27-indy-audio-v8.json').read_text())['native_sha256']
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        cd = Path(tmp) / 'cd'
        cd.mkdir()
        members = ['install.sh', 'install-xorg.sh', 'libextmod.so.0', 'module.sha256', 'inventory', 'release']
        contents = hashlib.sha256()
        for name in sorted(members + ['files' + path for path in profile['paths']]):
            dest = cd / ('install-savers.sh' if name == 'install.sh' else name)
            dest.parent.mkdir(parents=True, exist_ok=True)
            with dest.open('xb') as stream:
                subprocess.run(['isoinfo', '-R', '-i', args.saver_cd, '-x', '/' + name], stdout=stream, check=True)
            if not dest.stat().st_size:
                raise ValueError('Missing ' + name)
            contents.update(f'{sha256(dest)}  {name}\n'.encode())
        if contents.hexdigest() != receipt['releases'][args.release]['savers_v2_contents_sha256']:
            parser.error('expected the qualified savers-v2 contents for ' + args.release)
        shutil.copyfile(Path(__file__).with_name('install-audio-v8.sh'), cd / 'install.sh')
        shutil.copyfile(session, cd / 'desktop-clients.sh')
        (cd / 'native.sha256').write_text(native + '\n')
        checksums = [f'SHA256 ({p.relative_to(cd)}) = {sha256(p)}' for p in sorted(cd.rglob('*')) if p.is_file()]
        (cd / 'SHA256').write_text('\n'.join(checksums) + '\n')
        image = Path(tmp) / 'saver.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'XIRI_SAVER_V8', '-o', image, cd], check=True)
        args.output.hardlink_to(image)


if __name__ == '__main__':
    main()
