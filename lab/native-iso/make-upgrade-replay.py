#!/usr/bin/env python3
"""Recreate the older qualification generation using genuine archived Indy v7 files."""
import argparse
import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab.native_package import archive_tree
from xiri_lab.native_iso import digest

spec = importlib.util.spec_from_file_location('system_update', ROOT / 'scripts/package-xiriprep-update.py')
update = importlib.util.module_from_spec(spec)
spec.loader.exec_module(update)


def replay(iso, v7, output):
    if digest(v7, 'sha256') != 'c44f9f48f9c09841633053ebcf5c9c638c85c11da72cd8044e5850fda3d7481a':
        raise ValueError('Use the qualified 6.5.22f v7 CD for its native Indy binaries')
    current = update.installer(iso)
    earlier = current.copy()
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        source = work / 'runtime'
        with tarfile.open(fileobj=io.BytesIO(current[update.RUNTIME][1])) as archive:
            archive.extractall(source, filter='data')
        with tarfile.open(fileobj=io.BytesIO(update.member(v7, 'native.tgz'))) as archive:
            for path in current:
                if path == update.RUNTIME:
                    continue
                old = ('kernel' if path in ('/netbsd', '/netbsd.boot') else 'root') + path
                earlier[path] = current[path][0], archive.extractfile(old).read()
            # Both releases use the same native program builds. Leave the
            # donor-specific data, native configuration and users' homes alone.
            for target in (source / 'build').iterdir():
                paths = {'famd': 'usr/local/sbin/famd', 'shell-handoff': 'usr/libexec/xiri-shell'}
                old = paths.get(target.name, 'usr/local/libexec/xiri/' + target.name)
                if 'root/' + old in archive.getnames():
                    target.write_bytes(archive.extractfile('root/' + old).read())
            (source / 'libexec/desktop-clients.sh').write_bytes(
                archive.extractfile('root/usr/local/libexec/xiri/desktop-clients.sh').read())
        archive_tree(source, work / 'runtime.tgz')
        earlier[update.RUNTIME] = current[update.RUNTIME][0], (work / 'runtime.tgz').read_bytes()
        update.package(earlier, current, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('installer', 'v7', 'output'):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    replay(args.installer, args.v7, args.output)
