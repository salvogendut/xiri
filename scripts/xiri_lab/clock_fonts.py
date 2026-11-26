"""Add the SGI Font Manager resources to an authenticated Indy desktop import."""
import gzip
import json
import os
from pathlib import Path
import subprocess
import tarfile

from . import ROOT, sha256

FONT_DIR = 'usr/lib/X11/fonts/'
FONT_HASHES = {
    'ps2xlfd_map': 'ad312e4fe00a89c1f642c131e510250e27b01f83d327afb1c92680ae175154a2',
    'misc/iris10.pcf.Z': '80511f387b1409779c52a1f7a6c10cc0addac88df6fa5735244aebe0bd6e0b11',
    'misc/iris12.pcf.Z': 'd8e4d171f962cef09114c2d661e45abd42c4a2c221cba26449db36879fec78e5',
    'misc/iris13.pcf.Z': '575cf3cfecdf3034aa2f8672cb81b24fd9dbd4f5b9cc13b74da51f7ad48acbb2',
}
INDEX = 'misc/fonts.dir'
INDEX_SHA = '5aff3ddd1a3b26812f72b7ddd295c2319afc05a7a5238386494afc2c325bd334'


def extract_fonts(imported, overlay, instigator, work):
    release = imported['release']
    profile = json.loads((ROOT / 'profiles' / f'irix-{release}-indy-glx-v1.json').read_text())
    media = json.loads((ROOT / 'lab/irix-installer/base-media.json').read_text())
    disc = media[profile['overlay']]
    if imported['profile'] != profile['base_profile'] or profile['release'] != release:
        raise ValueError('Expected the matching base import for IRIX ' + release)
    if release not in disc['releases'] or sha256(overlay) != disc['sha256']:
        raise ValueError('Expected the matching IRIX ' + release + ' Overlay 1 disc')
    args = [str(instigator), 'extract', '--name', 'clock']
    for name in FONT_HASHES:
        args.extend(['--path', FONT_DIR + name])
    subprocess.run([*args, overlay, work / 'extracted'], check=True)
    source = work / 'extracted/clock' / FONT_DIR
    subprocess.run(['mkfontdir', source / 'misc'], env=dict(os.environ, LC_ALL='C'), check=True)
    paths = {}
    for name, digest in {**FONT_HASHES, INDEX: INDEX_SHA}.items():
        path = source / name
        if not path.is_file() or path.is_symlink() or sha256(path) != digest:
            raise ValueError('Clock font content differs: ' + name)
        paths['/emul/irix/' + FONT_DIR + name] = path
    return paths


def augmented_payload(base, additions, output, modes=None):
    """Stream the verified base and add only previously vacant regular files."""
    with output.open('xb') as raw, gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as gz:
        with tarfile.open(base, 'r|gz') as old, tarfile.open(fileobj=gz, mode='w|', format=tarfile.USTAR_FORMAT) as new:
            dirs = set()
            names = set()
            for item in old:
                names.add(item.name)
                if item.isdir():
                    dirs.add(item.name)
                new.addfile(item, old.extractfile(item) if item.isreg() else None)
            for dest, source in sorted(additions.items()):
                relative = Path(dest.lstrip('/'))
                if str(relative) in names:
                    raise ValueError('Supplement overlaps vendor payload: ' + dest)
                for parent in reversed(relative.parents):
                    name = str(parent)
                    if name == '.' or name in dirs:
                        continue
                    if name in names:
                        raise ValueError('Invalid parent in supplement: ' + name)
                    info = tarfile.TarInfo(name)
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    new.addfile(info)
                    dirs.add(name)
                info = tarfile.TarInfo(str(relative))
                info.mode = (modes or {}).get(dest, 0o444)
                info.size = source.stat().st_size
                with source.open('rb') as stream:
                    new.addfile(info, stream)
