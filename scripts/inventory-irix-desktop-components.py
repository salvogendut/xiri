#!/usr/bin/env python3
"""Extract the next desktop components and their static n32 library closure."""
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / '.work/irix-desktop-components'
REFERENCE = ROOT / '.work/irix-reference'
spec = importlib.util.spec_from_file_location('desktop_inventory', ROOT / 'scripts/inventory-irix-desktop.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
PROGRAMS = ['/usr/sbin/fm', '/usr/sbin/bgicons', '/usr/sbin/iconcatalog', '/usr/lib/desktop/fmserv']
PATTERNS = [
    '/usr/lib/X11/app-defaults/*[Ff][Mm]*',
    '/usr/lib/X11/app-defaults/*[Ff]ile*',
    '/usr/lib/X11/app-defaults/*[Ii]con*',
    '/usr/lib/X11/app-defaults/*[Bb]g*',
    '/usr/lib/X11/app-defaults/*[Dd]esk*',
    '/usr/lib/X11/xdm/DefaultIconList', '/usr/lib/X11/xdm/DefaultDeviceList',
]


def collect(pid):
    local_root = WORK / 'root'
    local_root.mkdir(exist_ok=True)

    def guest(*args):
        return subprocess.check_output(['guestfish', '--remote=' + pid, *args], text=True, timeout=120).rstrip('\n')

    def isfile(path):
        return guest('is-file', path, 'followsymlinks:true') == 'true'

    def download(path):
        if not path.startswith('/') or '..' in PurePosixPath(path).parts:
            raise ValueError('invalid image path: ' + path)
        local = local_root / path.lstrip('/')
        local.parent.mkdir(parents=True, exist_ok=True)
        canonical = guest('realpath', path)
        guest('download', path, str(local))
        return local, dict(path=path, canonical_path=canonical, bytes=local.stat().st_size,
                          sha256=inventory.sha256(local))

    previous = json.loads((ROOT / 'lab/irix-desktop/manifest.json').read_text())
    known = dict(previous['resource_candidates'], **previous['files'])
    files, edges, unresolved = {}, [], []
    queue = PROGRAMS + ['/lib32/rld', '/lib32/libc.so.1']
    while queue:
        path = queue.pop(0)
        if path in files:
            continue
        if len(files) >= 128:
            raise RuntimeError('library closure exceeded 128 paths')
        local, info = download(path)
        info.update(inventory.elf(local))
        if info['abi'] != 'n32':
            raise ValueError('non-n32 dependency: ' + path)
        if path in known and info['sha256'] != known[path]['sha256']:
            raise ValueError('existing image pin differs: ' + path)
        files[path] = info
        queue.extend(info['interpreter'])
        for needed in info['needed']:
            if '/' in needed:
                raise ValueError('unexpected dependency path')
            dirs = [d for rpath in info['rpath'] for d in rpath.split(':') if d.startswith('/')]
            dirs += ['/usr/lib32', '/usr/lib32/internal', '/lib32', '/opt/lib32']
            candidates = list(dict.fromkeys(d + '/' + needed for d in dirs))
            selected = next((p for p in candidates if isfile(p)), None)
            edge = dict(source=path, needed=needed, selected=selected, searched=candidates)
            edges.append(edge)
            if selected:
                queue.append(selected)
            else:
                unresolved.append(edge)
    resources = {}
    for pattern in PATTERNS:
        for path in guest('glob-expand', pattern, 'directoryslash:false').splitlines():
            if path not in resources and isfile(path):
                _, resources[path] = download(path)
    # Inventory roots without claiming every entry is required or staging an
    # entire desktop database before a client demonstrates which paths it uses.
    roots = {}
    for path in ['/usr/lib/filetype', '/usr/lib/desktop', '/usr/lib/desktop/iconcatalog',
                 '/usr/lib/X11/schemes', '/usr/share/icons', '/usr/lib/images']:
        if guest('is-dir', path, 'followsymlinks:true') == 'true':
            roots[path] = guest('ls', path).splitlines()
    result = dict(schema=1, description='Static next-component closure; runtime behavior is separately observed',
                  reference_release=previous['reference_release'], programs=PROGRAMS, files=files,
                  dependencies=edges, unresolved=unresolved, resources=resources, resource_patterns=PATTERNS,
                  resource_roots=roots, raw_disk_bytes=(REFERENCE / 'media/irix65.raw').stat().st_size,
                  raw_validation='Read-only ro,norecovery mount; size and existing selected file pins checked',
                  resolver='Absolute embedded RPATH, then /usr/lib32, /usr/lib32/internal, /lib32, /opt/lib32; static selection, not a native ldd observation',
                  script_sha256=inventory.sha256(Path(__file__).resolve()),
                  elf_parser_sha256=inventory.sha256(ROOT / 'scripts/inventory-irix-desktop.py'))
    (WORK / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(files)} ELF paths, {len(resources)} resources, {len(unresolved)} unresolved dependencies', flush=True)
    if unresolved:
        raise RuntimeError('unresolved static dependencies; inspect inventory.json')


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    pin = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    raw = REFERENCE / 'media/irix65.raw'
    if raw.stat().st_size != pin['logical_disk_bytes']:
        raise RuntimeError('reference image size mismatch')
    env = dict(os.environ, LIBGUESTFS_BACKEND='direct', LIBGUESTFS_CACHEDIR=str(REFERENCE / 'guestfs-cache'),
               LIBGUESTFS_TMPDIR=str(REFERENCE / 'tmp'))
    listener = WORK / 'guestfish-listener.log'
    with listener.open('w') as stream:
        subprocess.run(['guestfish', '--ro', '-a', str(raw), '--listen'], env=env,
                       stdout=stream, stderr=stream, check=True, timeout=30)
    pid = re.search(r'GUESTFISH_PID=(\d+)', listener.read_text())[1]
    try:
        subprocess.run(['guestfish', '--remote=' + pid, 'run'], check=True, timeout=120)
        subprocess.run(['guestfish', '--remote=' + pid, 'mount-options', 'ro,norecovery', '/dev/sda1', '/'], check=True, timeout=120)
        collect(pid)
    finally:
        subprocess.run(['guestfish', '--remote=' + pid, 'exit'], check=True, timeout=120)


if __name__ == '__main__':
    main()
