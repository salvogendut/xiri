#!/usr/bin/env python3
"""Read-only inventory of selected original fonts and C locale resources."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / '.work/irix-reference'
WORK = ROOT / '.work/irix-x11-fonts'
spec = importlib.util.spec_from_file_location('desktop', ROOT / 'scripts/inventory-irix-desktop.py')
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)


def main():
    pin = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    raw = REFERENCE / 'media/irix65.raw'
    if raw.stat().st_size != pin['logical_disk_bytes']:
        raise RuntimeError('reference image size mismatch')
    WORK.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LIBGUESTFS_BACKEND='direct',
               LIBGUESTFS_CACHEDIR=str(REFERENCE / 'guestfs-cache'),
               LIBGUESTFS_TMPDIR=str(REFERENCE / 'tmp'))
    listener = WORK / 'guestfish-listener.log'
    with listener.open('w') as stream:
        subprocess.run(['guestfish', '--ro', '-a', str(raw), '--listen'], env=env,
                       stdout=stream, stderr=stream, check=True, timeout=30)
    pid = re.search(r'GUESTFISH_PID=(\d+)', listener.read_text())[1]

    def call(*args):
        return subprocess.run(['guestfish', '--remote=' + pid, *args], capture_output=True,
                              text=True, check=True, timeout=120).stdout.rstrip('\n')

    def exists(path):
        return call('is-file', path, 'followsymlinks:true') == 'true'

    files, fonts, indexes, locale_candidates = {}, [], [], []

    def fetch(path):
        if not path.startswith('/') or '..' in PurePosixPath(path).parts:
            raise ValueError('unsafe guest path')
        if path in files:
            return WORK / 'root' / path.lstrip('/')
        if len(files) >= 128:
            raise RuntimeError('selected resource bound exceeded')
        local = WORK / 'root' / path.lstrip('/')
        local.parent.mkdir(parents=True, exist_ok=True)
        call('download', path, str(local))
        files[path] = dict(path=path, canonical_path=call('realpath', path),
                           bytes=local.stat().st_size,
                           sha256=hashlib.sha256(local.read_bytes()).hexdigest())
        if local.read_bytes().startswith(b'\x7fELF'):
            files[path].update(desktop.elf(local))
        return local

    try:
        call('run')
        call('mount-options', 'ro,norecovery', '/dev/sda1', '/')
        for pattern in ['/usr/lib/X11/fonts/*/fonts.dir', '/usr/lib/X11/fonts/*/*/fonts.dir']:
            for path in call('glob-expand', pattern, 'directoryslash:false').splitlines():
                if not exists(path):
                    continue
                indexes.append(path)
                for line in fetch(path).read_text(errors='replace').splitlines()[1:]:
                    fields = line.split(None, 1)
                    if len(fields) != 2:
                        continue
                    filename, xlfd = fields
                    if '-screen-' not in xlfd.lower() and '-fixed-' not in xlfd.lower():
                        continue
                    if PurePosixPath(filename).name != filename:
                        raise ValueError('unexpected font filename')
                    font_path = str(PurePosixPath(path).parent / filename)
                    fetch(font_path)
                    fonts.append(dict(path=font_path, xlfd=xlfd))
        locale_candidates = call('glob-expand', '/usr/lib/X11/locale/*', 'directoryslash:false').splitlines()
        for pattern in ['/usr/lib/X11/locale/C/*', '/usr/lib/X11/locale/iso8859-1/*',
                        '/usr/lib/X11/locale/common/*', '/usr/lib/X11/locale/common/*/*',
                        '/usr/lib32/X11/locale/common/*',
                        '/usr/lib/X11/locale/C', '/usr/lib/X11/locale/locale.dir',
                        '/usr/lib/X11/locale/locale.alias']:
            for path in call('glob-expand', pattern, 'directoryslash:false').splitlines():
                if exists(path):
                    fetch(path)
    finally:
        call('exit')
    result = dict(schema=1, source='Supplied IRIX 6.5.22m image, mounted ro,norecovery',
                  files=files, fonts=fonts, font_indexes=indexes, locale_candidates=locale_candidates,
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (WORK / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(fonts=len(fonts), screen_fonts=sum('-screen-' in f['xlfd'] for f in fonts),
                         font_indexes=indexes, files=len(files),
                         locale_files=[p for p in files if '/locale/' in p]), indent=2))


if __name__ == '__main__':
    main()
