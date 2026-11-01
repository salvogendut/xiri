#!/usr/bin/env python3
"""Collect installed catalog entries, desktop assets and static app dependencies.

Read the supplied disk with ro,norecovery. Vendor bytes stay in ignored .work;
the manifest distinguishes resolved launch targets from runtime qualification.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import posixpath
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT/'.work/irix-installed-desktop'
REFERENCE = ROOT/'.work/irix-reference'
CATALOG = '/usr/lib/desktop/iconcatalog'
spec = importlib.util.spec_from_file_location('elf_inventory', ROOT/'scripts/inventory-irix-desktop.py')
inventory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inventory)
sha = inventory.sha256


def collect(pid):
    local = WORK/'root'
    local.mkdir(exist_ok=True)
    files, archives, entries, dependencies, unresolved = {}, {}, [], [], []

    def guest(*args):
        return subprocess.check_output(['guestfish', '--remote='+pid, *args], text=True, timeout=180).rstrip('\n')

    def isfile(path):
        return guest('is-file', path, 'followsymlinks:true') == 'true'

    def destination(path):
        assert path.startswith('/') and '..' not in PurePosixPath(path).parts
        result = local/path.lstrip('/')
        result.parent.mkdir(parents=True, exist_ok=True)
        return result

    def download(path):
        if path in files and files[path]['type'] == 'file': return local/path.lstrip('/')
        target = destination(path)
        guest('download', path, str(target))
        stat = guest('statns', path)
        mode = int(re.search(r'^st_mode: (\d+)$', stat, re.M)[1])
        files[path] = dict(type='file', canonical_path=guest('realpath', path), bytes=target.stat().st_size,
                           mode=oct(mode & 0o7777), sha256=sha(target))
        return target

    def tree(base):
        if guest('is-dir', base, 'followsymlinks:true') != 'true': return
        archive = WORK/(base.strip('/').replace('/','_')+'.tar')
        guest('tar-out', base, str(archive))
        archives[base] = dict(bytes=archive.stat().st_size, sha256=sha(archive))
        with tarfile.open(archive) as tar:
            for member in tar:
                relative = PurePosixPath(member.name)
                assert not relative.is_absolute() and '..' not in relative.parts
                path = posixpath.normpath(base+'/'+str(relative))
                info = dict(type='directory' if member.isdir() else 'symlink' if member.issym()
                            else 'hardlink' if member.islnk() else 'file' if member.isfile() else 'special',
                            mode=oct(member.mode), bytes=member.size)
                if member.issym() or member.islnk(): info['target'] = member.linkname
                if member.isfile():
                    data = tar.extractfile(member).read()
                    destination(path).write_bytes(data)
                    info['sha256'] = hashlib.sha256(data).hexdigest()
                # Never create original absolute symlinks in the host tree.
                files[path] = info
        print('Collected', base, flush=True)

    for base in [CATALOG, '/usr/lib/filetype', '/usr/lib/X11/app-defaults',
                 '/usr/lib/X11/schemes', '/usr/freeware/share/xmahjongg']:
        tree(base)
    for pattern in ['/usr/lib/X11/system.*', '/usr/lib/X11/xdm/Default*List',
                    '/usr/lib/images/*[Mm]ahjong*']:
        for path in guest('glob-expand', pattern, 'directoryslash:false').splitlines():
            if isfile(path): download(path)

    queue = []
    for path, info in list(files.items()):
        if not path.startswith(CATALOG+'/pages/C/'): continue
        parts = path[len(CATALOG+'/pages/C/'):].split('/')
        if len(parts) < 2 or info['type'] == 'directory': continue
        target = info.get('target', path)
        if not target.startswith('/'): target = posixpath.normpath(posixpath.dirname(path)+'/'+target)
        exists = isfile(path)
        entry = dict(page=parts[0], name='/'.join(parts[1:]), catalog_path=path,
                     target=target, resolved_file=exists)
        if exists:
            entry['canonical_path'] = guest('realpath', path)
            queue.append(target)
        else:
            entry['directory_target'] = guest('is-dir', path, 'followsymlinks:true') == 'true'
        entries.append(entry)
    queue += ['/usr/freeware/bin/xmahjongg', '/usr/sbin/iconcatalog', '/usr/lib/desktop/fmserv']
    analyzed = set()
    while queue:
        path = queue.pop(0)
        if path in analyzed: continue
        analyzed.add(path)
        if not isfile(path):
            unresolved.append(dict(path=path, reason='missing file'))
            continue
        target = download(path)
        data = target.read_bytes()
        if data[:4] == b'\x7fELF':
            try:
                elf = inventory.elf(target)
            except ValueError as error:
                files[path]['elf_error'] = str(error)
                unresolved.append(dict(path=path, reason='unsupported ELF metadata'))
                continue
            files[path]['elf'] = elf
            queue.extend(elf['interpreter'])
            for needed in elf['needed']:
                assert '/' not in needed
                dirs = [d for value in elf['rpath'] for d in value.split(':') if d.startswith('/')]
                dirs += (['/usr/lib32', '/usr/lib32/internal', '/lib32', '/usr/freeware/lib32']
                         if elf['abi'] == 'n32' else ['/usr/lib', '/usr/lib/internal', '/lib', '/usr/freeware/lib'])
                candidates = list(dict.fromkeys(d+'/'+needed for d in dirs))
                selected = next((p for p in candidates if isfile(p)), None)
                edge = dict(source=path, needed=needed, selected=selected, searched=candidates)
                dependencies.append(edge)
                if selected: queue.append(selected)
                else: unresolved.append(edge)
        elif data.startswith(b'#!'):
            interpreter = data.splitlines()[0][2:].strip().split()[0].decode()
            files[path]['script_interpreter'] = interpreter
            if interpreter.startswith('/'): queue.append(interpreter)
    homes = {}
    for pattern in ['/.desktop*', '/.Sgiresources', '/.4Dwmrc', '/.chestrc',
                    '/usr/people/*/.desktop*', '/usr/people/*/.Sgiresources',
                    '/usr/people/*/.4Dwmrc', '/usr/people/*/.chestrc']:
        for path in guest('glob-expand', pattern, 'directoryslash:false').splitlines():
            homes[path] = dict(directory=guest('is-dir', path, 'followsymlinks:true') == 'true')
    pages = {}
    for entry in entries: pages[entry['page']] = pages.get(entry['page'], 0)+1
    result = dict(schema=1, status='inventory-only', pages=pages, entries=entries,
                  files=files, archives=archives, dependencies=dependencies, unresolved=unresolved,
                  user_layout_candidates=homes, image_manifest_sha256=sha(ROOT/'lab/irix-reference/manifest.json'),
                  source_image_bytes=(REFERENCE/'media/irix65.raw').stat().st_size,
                  extraction='Read-only ro,norecovery; archive symlinks retained as metadata on the host.',
                  limitations=['Static dependencies do not establish working application launches.',
                      'Directory targets, script-invoked programs, dlopen modules and per-application data need further discovery.',
                      'User layouts are inventoried separately; native accounts and homes are not replaced.',
                      'Original installation history is not imported as a claim that every package is staged.'],
                  script_sha256=sha(Path(__file__)), elf_parser_sha256=sha(ROOT/'scripts/inventory-irix-desktop.py'))
    (WORK/'inventory.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Catalog:', len(entries), 'entries in', len(pages), 'pages;', len(files), 'paths;', len(unresolved), 'unresolved static dependencies', flush=True)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    raw = REFERENCE/'media/irix65.raw'
    assert raw.stat().st_size == json.loads((ROOT/'lab/irix-reference/manifest.json').read_text())['logical_disk_bytes']
    env = dict(os.environ, LIBGUESTFS_BACKEND='direct', LIBGUESTFS_CACHEDIR=str(REFERENCE/'guestfs-cache'),
               LIBGUESTFS_TMPDIR=str(REFERENCE/'tmp'))
    listener = WORK/'listener.log'
    with listener.open('w') as stream:
        subprocess.run(['guestfish', '--ro', '-a', str(raw), '--listen'], env=env,
                       stdout=stream, stderr=stream, check=True, timeout=30)
    pid = re.search(r'GUESTFISH_PID=(\d+)', listener.read_text())[1]
    try:
        subprocess.run(['guestfish', '--remote='+pid, 'run'], check=True, timeout=180)
        subprocess.run(['guestfish', '--remote='+pid, 'mount-options', 'ro,norecovery', '/dev/sda1', '/'], check=True, timeout=120)
        collect(pid)
    finally:
        subprocess.run(['guestfish', '--remote='+pid, 'exit'], check=True, timeout=120)


if __name__ == '__main__':
    main()
