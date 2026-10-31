#!/usr/bin/env python3
"""Inventory supplied winterm/xwsh bytes read-only; publish only metadata."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent
REFERENCE = ROOT / '.work/irix-reference'
WORK = ROOT / '.work/irix-winterm'
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

    def fetch(path):
        if not path.startswith('/') or '..' in PurePosixPath(path).parts:
            raise ValueError('unsafe guest path')
        local = WORK / 'root' / path.lstrip('/')
        local.parent.mkdir(parents=True, exist_ok=True)
        call('download', path, str(local))
        return local, dict(path=path, canonical_path=call('realpath', path),
                           bytes=local.stat().st_size,
                           sha256=hashlib.sha256(local.read_bytes()).hexdigest())

    files, launchers, dependencies, unresolved, resources, programs = {}, {}, [], [], {}, []
    try:
        call('run')
        call('mount-options', 'ro,norecovery', '/dev/sda1', '/')
        for path in ['/usr/bin/X11/winterm', '/usr/sbin/winterm', '/usr/bin/winterm',
                     '/usr/bin/X11/xwsh', '/usr/sbin/xwsh', '/usr/bin/xwsh', '/usr/bin/gettxt']:
            if not exists(path):
                continue
            local, info = fetch(path)
            if local.read_bytes().startswith(b'\x7fELF'):
                programs.append(path)
            else:
                launchers[path] = info
        queue = list(programs)
        while queue:
            path = queue.pop(0)
            if path in files:
                continue
            if len(files) >= 128:
                raise RuntimeError('dependency closure exceeded bound')
            local, info = fetch(path)
            info.update(desktop.elf(local))
            files[path] = info
            abi = info['abi']
            queue.extend(info['interpreter'])
            queue.append('/lib32/rld' if abi == 'n32' else '/lib/rld')
            for needed in info['needed']:
                if '/' in needed:
                    raise ValueError('unexpected DT_NEEDED path')
                dirs = [d for value in info['rpath'] for d in value.split(':') if d.startswith('/')]
                dirs += (['/usr/lib32', '/usr/lib32/internal', '/lib32', '/opt/lib32'] if abi == 'n32'
                         else ['/usr/lib', '/usr/lib/internal', '/lib', '/opt/lib'])
                candidates = list(dict.fromkeys(d + '/' + needed for d in dirs))
                selected = next((p for p in candidates if exists(p)), None)
                edge = dict(source=path, needed=needed, selected=selected, searched=candidates)
                dependencies.append(edge)
                if selected:
                    queue.append(selected)
                else:
                    unresolved.append(edge)
        patterns = ['/usr/lib/X11/app-defaults/*Winterm*', '/usr/lib/X11/app-defaults/*Xwsh*',
                    '/usr/lib/X11/app-defaults/*winterm*', '/usr/lib/X11/app-defaults/*xwsh*',
                    '/usr/lib/X11/app-defaults/*Winter*', '/usr/lib/X11/app-defaults/*Wsh*',
                    '/usr/share/catman/*/cat1/winterm*', '/usr/share/catman/*/cat1/xwsh*']
        for pattern in patterns:
            for path in call('glob-expand', pattern, 'directoryslash:false').splitlines():
                if exists(path):
                    _, resources[path] = fetch(path)
    finally:
        call('exit')
    result = dict(schema=1, description='Supplied winterm/xwsh launchers, static ELF closure and resource candidates',
                  source='IRIX 6.5.22m; read-only ro,norecovery; raw size checked against intake pin',
                  programs=programs, launchers=launchers, files=files, dependencies=dependencies,
                  unresolved=unresolved, resources=resources,
                  resolution_scope='Static absolute RPATH followed by ABI-specific default directories; native ldd and runtime loading not qualified',
                  script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (WORK / 'manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(programs=programs, launchers=launchers, files=len(files),
                         resources=list(resources), unresolved=unresolved), indent=2))


if __name__ == '__main__':
    main()
