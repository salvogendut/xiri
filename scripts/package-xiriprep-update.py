#!/usr/bin/env python3
"""Build a native-only Indy system update CD from two trusted XiriBSD installer ISOs."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

from xiri_lab.native_sources import ROOT

RUNTIME = '/usr/local/share/xiri/desktop-runtime.tgz'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def member(iso, name):
    return subprocess.check_output(['isoinfo', '-R', '-i', iso, '-x', '/' + name])


def file_in(archive, name):
    entry = archive.getmember('./' + name.lstrip('/'))
    if not entry.isfile() or entry.uid or entry.gid:
        raise ValueError(f'Expected a native root-owned file at {name}')
    return entry.mode, archive.extractfile(entry).read()


def installer(iso):
    inv = json.loads(member(iso, 'native-media.json'))
    version = inv['kernel_release']
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}', version):
        raise ValueError(f'Unexpected Indy release {version}')
    module = f'/stand/sgimips/{version}/modules/compat_irix_o32/compat_irix_o32.kmod'
    files = {}
    for prefix, paths in [('kern-GENERIC32_IP2x', ['/netbsd', '/netbsd.boot', RUNTIME]), ('modules', [module])]:
        name, = (n for n in inv['sha256'] if n.startswith('sgimips/binary/sets/' + prefix + '.'))
        data = member(iso, name)
        if sha(data) != inv['sha256'][name]:
            raise ValueError(f'Installer checksum mismatch at {name}')
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            files.update((path, file_in(archive, path)) for path in paths)
    return files


def installed_runtime(data, work):
    source = work / 'source'
    dest = work / 'dest'
    source.mkdir(parents=True)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        if any(not (m.isfile() or m.isdir()) for m in archive):
            raise ValueError('Unexpected file type in the native runtime')
        archive.extractall(source, filter='data')
    script = source / 'install.sh'
    if script.read_bytes() != (ROOT / 'runtime/install.sh').read_bytes():
        raise ValueError('Runtime installation layout differs. Review its file mapping before updating.')
    subprocess.run(['sh', script], env=dict(os.environ, DESTDIR=str(dest), BUILDDIR='build'), check=True)
    # install-shared installs famd separately. Live configuration and the
    # stock kernel always belong to the administrator.
    files = {'/usr/local/sbin/famd': (0o555, (source / 'build/famd').read_bytes())}
    for path in dest.rglob('*'):
        name = '/' + path.relative_to(dest).as_posix()
        if (name.startswith('/etc/xiri/') and not name.endswith('.example')) or name.startswith('/etc/rc.conf.d/'):
            continue
        if path.is_file() and not path.is_symlink():
            files[name] = (path.stat().st_mode & 0o7777, path.read_bytes())
    return files


def package(old, new, output):
    output = output.absolute()
    if output.exists() or output.is_symlink():
        raise ValueError(f'Output already exists: {output}')
    if old[RUNTIME] == new[RUNTIME]:
        raise ValueError('This combined update needs distinct desktop-runtime generations')
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        work = Path(tmp)
        cd = work / 'cd'
        objects = cd / 'objects'
        objects.mkdir(parents=True)
        for label, bundle in [('old', old), ('new', new)]:
            data = bundle[RUNTIME][1]
            (cd / (label + '-runtime')).write_text(sha(data) + '\n')
        before = old | installed_runtime(old[RUNTIME][1], work / 'old')
        after = new | installed_runtime(new[RUNTIME][1], work / 'new')
        if before.keys() != after.keys():
            raise ValueError('This updater requires the same kernel/module paths and runtime file layout')
        entries = []
        for name in sorted(before):
            old_mode, a = before[name]
            mode, b = after[name]
            if old_mode != mode:
                raise ValueError(f'Review mode migration for {name}')
            if name not in old and a == b:
                continue
            for data in [a, b]:
                (objects / sha(data)).write_bytes(data)
            entries.append(f'{name}|{mode:o}|{sha(a)}|{sha(b)}\n')
        (cd / 'files').write_text(''.join(entries))
        (cd / 'update-system.sh').write_bytes((ROOT / 'packaging/xiriprep/update-system.sh').read_bytes())
        checks = {p.relative_to(cd).as_posix(): sha(p.read_bytes()) for p in sorted(cd.rglob('*')) if p.is_file()}
        sums = ''.join(f'SHA256 ({name}) = {digest}\n' for name, digest in checks.items()).encode()
        (cd / 'SHA256').write_bytes(sums)
        candidate = work / 'update.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'XIRI_UPDATE', '-o', candidate, cd], check=True)
        checks['SHA256'] = sha(sums)
        for name, digest in checks.items():
            if sha(member(candidate, name)) != digest:
                raise ValueError(f'Update CD readback failed at {name}')
        os.link(candidate, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('previous', 'current', 'output'):
        parser.add_argument(key, type=Path)
    args = parser.parse_args()
    package(installer(args.previous), installer(args.current), args.output)
