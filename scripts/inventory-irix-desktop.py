#!/usr/bin/env python3
"""Inventory a bounded desktop dependency closure from the read-only IRIX image.

Vendor bytes go only to .work. The generated JSON contains ELF/path metadata;
review it before copying it into lab/irix-desktop/manifest.json.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT / '.work/irix-desktop'
REFERENCE = ROOT / '.work/irix-reference'


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def elf(path):
    data = path.read_bytes()
    if data[:6] != b'\x7fELF\x01\x02':
        raise ValueError('expected ELF32 big endian: ' + str(path))
    h = struct.unpack_from('>HHIIIIIHHHHHH', data, 16)
    kind, machine, version, entry, phoff, shoff, flags, ehsize, phsize, phnum, shsize, shnum, shstr = h
    if machine != 8 or version != 1 or ehsize != 52 or phsize != 32 or phnum > 64:
        raise ValueError('unsupported ELF header')
    def span(offset, size):
        if offset < 0 or size < 0 or offset + size > len(data):
            raise ValueError('ELF range outside file')
        return data[offset:offset + size]
    def string(table, offset):
        if not 0 <= offset < len(table) or b'\0' not in table[offset:]:
            raise ValueError('invalid ELF string')
        return table[offset:].split(b'\0', 1)[0].decode('ascii')
    headers = [struct.unpack('>8I', span(phoff + i * phsize, phsize)) for i in range(phnum)]
    loads = [p for p in headers if p[0] == 1]
    def address(addr, size):
        for p in loads:
            if p[2] <= addr and addr + size <= p[2] + p[4]:
                return span(p[1] + addr - p[2], size)
        raise ValueError('dynamic address outside file-backed loads')
    dynamic = []
    for p in headers:
        if p[0] == 2:
            for i in range(0, p[4], 8):
                item = struct.unpack('>II', span(p[1] + i, 8))
                if item[0] == 0:
                    break
                dynamic.append(item)
    tags = dict(dynamic)
    strings = address(tags[5], tags[10]) if 5 in tags and 10 in tags else b''
    return {
        'class': 32, 'endian': 'big', 'machine': machine,
        'abi': 'n32' if flags & 0x20 else 'o32', 'type': kind,
        'flags': hex(flags), 'entry': hex(entry),
        'interpreter': [span(p[1], p[4]).rstrip(b'\0').decode('ascii') for p in headers if p[0] == 3],
        'needed': [string(strings, v) for k, v in dynamic if k == 1],
        'rpath': [string(strings, v) for k, v in dynamic if k in [15, 29]],
        'soname': [string(strings, v) for k, v in dynamic if k == 14],
        'loads': [{'offset': p[1], 'address': p[2], 'file_bytes': p[4],
                   'memory_bytes': p[5], 'flags': p[6], 'alignment': p[7]} for p in loads],
        'load_boundaries_8k': all(p[1] % 8192 == p[2] % 8192 == 0 and p[7] >= 8192 for p in loads),
        'liblist': [string(strings, struct.unpack_from('>I', address(tags[0x70000009], tags[0x70000010] * 20), i * 20)[0]) for i in range(tags.get(0x70000010, 0))],
        'mips_rld_version': tags.get(0x70000001), 'mips_flags': hex(tags.get(0x70000005, 0)),
    }


def static_analysis(files, edges, programs):
    result = {}
    for program in programs:
        needed, queue = set(), [program]
        while queue:
            source = queue.pop()
            for edge in edges:
                target = edge['selected']
                if edge['from'] == source and target and target not in needed:
                    needed.add(target)
                    queue.append(target)
        paths = sorted(needed | {program, '/lib32/rld'})
        collisions = []
        for i, left in enumerate(paths):
            for right in paths[i + 1:]:
                overlaps = []
                for a in files[left]['loads']:
                    for b in files[right]['loads']:
                        start = max(a['address'], b['address'])
                        end = min(a['address']+a['memory_bytes'], b['address']+b['memory_bytes'])
                        if start < end:
                            overlaps.append({'start': start, 'end': end})
                if overlaps:
                    collisions.append({'left': left, 'right': right, 'overlaps': overlaps})
        result[program] = {'needed_closure': sorted(needed),
                           'not_8k_aligned': [p for p in paths if not files[p]['load_boundaries_8k']],
                           'linked_address_collisions': collisions,
                           'interpretation': 'Static ELF ranges, not observed runtime placement; rld may relocate libraries'}
    return result


def inventory(pid):
    WORK.mkdir(exist_ok=True)
    local_root = WORK / 'root'
    local_root.mkdir(exist_ok=True)
    def guest(*args):
        r = subprocess.run(['guestfish', '--remote=' + str(pid), *args],
                           capture_output=True, text=True, check=True, timeout=120)
        return r.stdout.rstrip('\n')
    def isfile(path):
        return guest('is-file', path, 'followsymlinks:true') == 'true'
    def download(path):
        if not path.startswith('/') or '..' in PurePosixPath(path).parts:
            raise ValueError('unsafe guest path')
        canonical = guest('realpath', path)
        local = local_root / path.lstrip('/')
        local.parent.mkdir(parents=True, exist_ok=True)
        guest('download', path, str(local))
        return local, canonical
    originals = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    programs = [c for c in originals['candidates'] if c['fixture_name'] in ['vendor-4Dwm', 'vendor-toolchest']]
    files, edges, unresolved = {}, [], []
    queue = [c['path'] for c in programs] + ['/lib32/rld', '/lib32/libc.so.1']
    while queue:
        path = queue.pop(0)
        if path in files:
            continue
        if len(files) >= 128:
            raise RuntimeError('dependency closure exceeded bound')
        local, canonical = download(path)
        info = {'path': path, 'canonical_path': canonical, 'bytes': local.stat().st_size,
                'sha256': sha256(local), **elf(local)}
        if info['abi'] != 'n32':
            raise ValueError('non-n32 dependency: ' + path)
        files[path] = info
        for candidate in programs:
            if path == candidate['path'] and info['sha256'] != candidate['sha256']:
                raise RuntimeError('vendor program differs from intake pin')
        queue.extend(info['interpreter'])
        for needed in info['needed']:
            if '/' in needed:
                raise ValueError('unexpected DT_NEEDED path')
            # This is a static search policy, not an emulation of rld's full
            # selection rules. Native ldd observations must verify the choice.
            directories = [d for value in info['rpath'] for d in value.split(':') if d.startswith('/')]
            directories += ['/usr/lib32', '/usr/lib32/internal', '/lib32', '/opt/lib32']
            candidates = list(dict.fromkeys(d + '/' + needed for d in directories))
            found = next((p for p in candidates if isfile(p)), None)
            edge = {'from': path, 'needed': needed, 'selected': found, 'searched': candidates}
            edges.append(edge)
            if found:
                queue.append(found)
            else:
                unresolved.append(edge)
    patterns = [
        '/usr/lib/X11/app-defaults/*4D*', '/usr/lib/X11/app-defaults/*Tool*',
        '/usr/lib/X11/locale/locale.alias', '/usr/lib/X11/locale/locale.dir',
        '/usr/lib/X11/XtErrorDB', '/usr/lib/X11/system.*', '/usr/lib/X11/xdm/*', '/var/X11/xdm/*',
        '/usr/lib/X11/Xsession*', '/usr/lib/desktop/*',
        '/etc/config/desktop*', '/etc/config/xdm*', '/etc/init.d/xdm',
        '/usr/bin/ldd', '/usr/sbin/par', '/usr/bin/par', '/usr/bin/X11/Xsgi',
        '/usr/bin/X11/X', '/usr/bin/X11/xdm', '/usr/bin/X11/wait4wm',
        '/usr/bin/X11/tellwm', '/usr/bin/X11/reaper', '/usr/lib/X11/nodesktop.chestrc',
        '/usr/sbin/fm', '/usr/sbin/bgicons', '/usr/sbin/iconcatalog',
        '/usr/sbin/genDeviceIcons', '/usr/sbin/FLtoPopDB', '/usr/sbin/userenv',
        '/usr/sbin/soundscheme', '/usr/sysadm/bin/sabgicons',
        '/usr/share/catman/*/cat1/par*', '/usr/share/catman/*/cat1/4Dwm*',
        '/usr/share/catman/*/cat1/toolchest*', '/usr/share/catman/*/cat1/rld*',
    ]
    resources = {}
    for pattern in patterns:
        for path in guest('glob-expand', pattern, 'directoryslash:false').splitlines():
            if not isfile(path) or path in files or path in resources:
                continue
            # Retain metadata, not copyrighted text, in the public inventory.
            local, canonical = download(path)
            resources[path] = {'path': path, 'canonical_path': canonical,
                               'bytes': local.stat().st_size, 'sha256': sha256(local)}
    result = {'schema': 1, 'description': 'Static n32 desktop dependency closure and selected resource/service candidates; vendor bytes remain private',
              'reference_release': originals['reference_release'],
              'raw_disk_bytes': (REFERENCE / 'media/irix65.raw').stat().st_size,
              'raw_validation': 'Read-only ro,norecovery mount; size checked against intake pin, raw hash not recomputed',
              'script_sha256': sha256(Path(__file__).resolve()),
              'programs': [c['path'] for c in programs], 'files': files, 'dependencies': edges,
              'unresolved': unresolved, 'resource_patterns': patterns, 'resource_candidates': resources,
              'resolution_scope': 'DT_NEEDED closure using absolute embedded RPATH then /usr/lib32:/usr/lib32/internal:/lib32:/opt/lib32 as documented by the supplied rld manual; verify against native ldd, not a general rld resolver',
              'resources_scope': 'Selected filesystem candidates; presence does not prove a runtime requirement'}
    result['static_analysis'] = static_analysis(files, edges, result['programs'])
    (WORK / 'inventory.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'{len(files)} ELF paths, {len(edges)} dependency edges, {len(unresolved)} unresolved, {len(resources)} resource/service candidates', flush=True)
    return result


def main():
    pin = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    raw = REFERENCE / 'media/irix65.raw'
    if raw.stat().st_size != pin['logical_disk_bytes']:
        raise RuntimeError('reference image size mismatch')
    env = dict(os.environ, LIBGUESTFS_BACKEND='direct',
               LIBGUESTFS_CACHEDIR=str(REFERENCE / 'guestfs-cache'),
               LIBGUESTFS_TMPDIR=str(REFERENCE / 'tmp'))
    WORK.mkdir(exist_ok=True)
    listener = WORK / 'guestfish-listener.log'
    # The daemon inherits stdout; a PIPE would keep communicate() waiting
    # after the launcher exits. A file lets us read the reported PID directly.
    with listener.open('w') as stream:
        subprocess.run(['guestfish', '--ro', '-a', str(raw), '--listen'],
                       env=env, stdout=stream, stderr=stream, check=True, timeout=30)
    pid = re.search(r'GUESTFISH_PID=(\d+)', listener.read_text())[1]
    def call(*args):
        subprocess.run(['guestfish', '--remote=' + pid, *args], check=True, timeout=120)
    try:
        call('run')
        call('mount-options', 'ro,norecovery', '/dev/sda1', '/')
        inventory(pid)
    finally:
        call('exit')


if __name__ == '__main__':
    main()
