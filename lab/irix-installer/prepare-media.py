#!/usr/bin/env python3
"""Prepare the private installer supplement for a matching clean Indy desktop."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import sha256
from xiri_lab.irix_import import Donor, check_source, collect, write_payload

TOOLS = ('/sbin/stat', '/usr/sbin/inst', '/usr/sbin/versions',
         '/usr/sbin/showfiles', '/usr/sbin/showprods', '/usr/sbin/iconcatalogedit',
         '/var/inst/machfile')


def stage_base_media(media, release, source, instigator):
    discs = json.loads(Path(__file__).with_name('base-media.json').read_text())
    for path, disc in discs.items():
        if release not in disc['releases']:
            continue
        image = source / path
        if sha256(image) != disc['sha256']:
            raise ValueError(f'Installation disc hash mismatch: {image}')
        directory = media / disc['directory']
        directory.mkdir(exist_ok=True)
        for product in disc['products']:
            for suffix in ('', '.idb', '.sw'):
                name = product + suffix
                subprocess.run([instigator, 'dump', image, 'dist/' + name, directory],
                               stdout=subprocess.DEVNULL, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--release', required=True, choices=('6.5.22f', '6.5.30f'))
    parser.add_argument('--donor', type=Path, required=True, help='standalone original-media CHD or raw disk')
    parser.add_argument('--desktop-manifest', type=Path, required=True)
    parser.add_argument('--dist', type=Path, required=True, help='May 2004 CD 4 dist directory')
    parser.add_argument('--base-media-root', type=Path,
                        help='include the tested Foundation 1 and matching overlay distributions')
    parser.add_argument('--instigator', default='instigator', help='Instigator media reader executable')
    parser.add_argument('--output', type=Path, required=True, help='new private ISO')
    args = parser.parse_args()
    profile = json.loads((ROOT / 'profiles' / f'irix-{args.release}-v1.json').read_text())
    desktop = json.loads(args.desktop_manifest.read_text())
    if (desktop['status'] != 'payload-verified' or desktop['profile'] != profile['id'] or
            desktop['donor'] != profile['donor'] or desktop['release'] != args.release):
        parser.error('desktop manifest must match the selected original-media donor')
    if args.output.exists():
        parser.error('output already exists')
    source, kind, _ = check_source(args.donor, profile)
    inputs = json.loads((Path(__file__).parent / 'inputs.json').read_text())
    with tempfile.TemporaryDirectory(prefix='inst-media-', dir=args.output.parent) as tmp:
        work = Path(tmp)
        media = work / 'cd'
        dist = media / 'dist'
        dist.mkdir(parents=True)
        shutil.copyfile(ROOT / 'lab/irix-installer-helpers/setup-native-paths.sh',
                        media / 'setup-native-paths.sh')
        if args.base_media_root:
            stage_base_media(media, args.release, args.base_media_root, args.instigator)
            for name in ('prepare-live-base.sh', 'xmahjongg.sh', 'desktop-artwork.sh', 'package-filetypes.mk'):
                shutil.copyfile(Path(__file__).with_name(name), media / name)
        for path, row in inputs.items():
            if row['source'] == 'media':
                name = Path(path).name
                shutil.copyfile(args.dist / name, dist / name)
                if sha256(dist / name) != row['sha256']:
                    raise ValueError('CD 4 hash mismatch for ' + name)
        raw = source
        if kind == 'chd':
            raw = work / 'donor.raw'
            chdman = ['chdman'] if shutil.which('chdman') else ['toolbox', 'run', '-c', 'xiri-iris', 'chdman']
            subprocess.run([*chdman, 'extracthd', '-i', source, '-o', raw], check=True)
            if sha256(raw) != profile['donor']['raw_sha256']:
                raise ValueError('expanded donor hash mismatch')
        objects = work / 'objects'
        objects.mkdir()
        with Donor(raw, work) as donor:
            rows = {'/emul/irix' + p: dict(source=p, type='file', component='installer') for p in TOOLS}
            files, _, _ = collect(donor, rows, objects, library_paths=profile.get('library_paths'))
        additions = {}
        for path, row in files.items():
            existing = desktop['files'].get(path)
            if existing is None:
                additions[path] = row
            elif existing['type'] != row['type'] or existing.get('sha256') != row.get('sha256'):
                raise ValueError('desktop payload differs at ' + path)
        write_payload(media / 'installer.tgz', additions)
        ledger = {p: {k: v for k, v in row.items() if k in ('source', 'sha256', 'mode')}
                  for p, row in files.items()}
        (media / 'vendor.json').write_text(json.dumps(
            dict(release=args.release, donor=profile['donor'], files=ledger,
                 additions=sorted(additions)), sort_keys=True, indent=2) + '\n')
        (media / 'list').write_text('list fw_xmahjongg*\nquit\n')
        image = work / 'inst.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-o', image, media], check=True)
        # Publish the completed ISO without replacing another build.
        args.output.hardlink_to(image)
        print(f'{args.release}: {len(additions)} installer paths added; {sha256(image)}  {args.output}')


if __name__ == '__main__':
    main()
