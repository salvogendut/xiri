#!/usr/bin/env python3
"""Compare a read-only IRIX raw donor with the tracked 6.5.22m copy ledgers.

This inventories source bytes and link text, not runtime compatibility. It does
not install anything or change the selected Xiri reference.
"""
import argparse
from collections import Counter
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import subprocess

from xiri_lab.donor import sha256

ROOT = Path(__file__).resolve().parent.parent
LEDGERS = [
    'lab/irix-installed-desktop/copy-ledger.json',
    'lab/irix-desktop-bitmaps/copy-ledger.json',
    'lab/irix-desktop-behavior/resources.json',
    'lab/irix-gimp/resources.json',
    'lab/irix-gnome/preferences-resources.json',
    'lab/irix-terminal/resources.json',
    'lab/irix-acrobat/resources.json',
    'lab/irix-session/resources.json',
    'lab/irix-filemanager/resources.json',
    'lab/documents/resource-ledger.json',
    'lab/irix-desks/resources.json',
    'lab/irix-toolchest-input/resources.json',
]
ESSENTIAL = [
    '/usr/bin/X11/4Dwm', '/usr/bin/X11/toolchest', '/usr/bin/X11/xclock',
    '/usr/sbin/winterm', '/usr/sbin/xwsh', '/usr/sbin/iconcatalog',
    '/usr/sbin/fm', '/usr/lib/desktop/fmserv', '/usr/sbin/ov', '/usr/sbin/fftr',
    '/usr/bin/X11/tellwm', '/usr/lib/desktop/telldesktop',
    '/sbin/sh', '/bin/csh', '/lib/rld', '/lib32/rld',
]
WINTERM_LEDGER = 'lab/irix-winterm/manifest.json'


def references():
    paths = {}
    for name in LEDGERS:
        data = json.loads((ROOT/name).read_text())
        rows = data.get('files', data.get('paths'))
        for key, row in (rows.items() if isinstance(rows, dict) else enumerate(rows)):
            path = row.get('irix_source', row.get('source', row.get('realpath', key)))
            if not isinstance(path, str) or not path.startswith('/'):
                raise ValueError('unrecognized source path in '+name)
            record = {k: row[k] for k in ('type', 'sha256', 'target') if k in row}
            record.setdefault('type', 'file')
            record['ledger'] = name
            paths.setdefault(path, []).append(record)
    core = json.loads((ROOT/'lab/irix-desktop/manifest.json').read_text())
    for path, row in core['files'].items():
        paths.setdefault(path, []).append(dict(type='file', sha256=row['sha256'],
                                               ledger='lab/irix-desktop/manifest.json'))
    winterm = json.loads((ROOT/WINTERM_LEDGER).read_text())
    for path, row in winterm['launchers'].items():
        paths.setdefault(path, []).append(dict(type='file', sha256=row['sha256'],
                                               ledger=WINTERM_LEDGER))
    return paths, sorted(set(core['files']) | set(ESSENTIAL))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw', required=True, type=Path)
    parser.add_argument('--output-directory', required=True, type=Path)
    parser.add_argument('--partition', default='/dev/sda1')
    parser.add_argument('--retain-essential-files', action='store_true',
                        help='keep downloaded core files for further byte comparison')
    args = parser.parse_args()
    out = args.output_directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for name in ('cache', 'tmp', 'elf'):
        (out/name).mkdir()
    env = dict(os.environ, LIBGUESTFS_BACKEND='direct',
               LIBGUESTFS_CACHEDIR=str(out/'cache'), LIBGUESTFS_TMPDIR=str(out/'tmp'))
    expected, core = references()
    for path in core:
        expected.setdefault(path, [])
    raw_hash = sha256(args.raw)
    result = {'schema': 1, 'scope': __doc__.strip(), 'status': 'incomplete',
              'raw_sha256': raw_hash, 'script_sha256': sha256(__file__),
              'reference_release': '6.5.22m', 'mount_options': 'ro,norecovery',
              'ledgers': {n: sha256(ROOT/n) for n in LEDGERS + ['lab/irix-desktop/manifest.json', WINTERM_LEDGER]},
              'paths': {}, 'essential_paths': core}
    pid = None
    try:
        with (out/'listener.log').open('w+') as log:
            subprocess.run(['guestfish', '--ro', '--format=raw', '-a', str(args.raw.resolve()),
                            '--listen'], env=env, stdout=log, stderr=log, check=True, timeout=45)
            log.seek(0)
            pid = re.search(r'GUESTFISH_PID=(\d+)', log.read())[1]
        (out/'guestfish.pid').write_text(pid+'\n')

        def guest(*arguments, missing_ok=False):
            r = subprocess.run(['guestfish', '--remote='+pid, *arguments], env=env,
                               text=True, capture_output=True, timeout=180)
            if r.returncode:
                if missing_ok and ('No such file or directory' in r.stderr or
                                   'Not a directory' in r.stderr):
                    return None
                detail = r.stderr or (out/'listener.log').read_text()[-1500:]
                raise RuntimeError(str(arguments)+': '+detail)
            return r.stdout.rstrip('\n')

        guest('run')
        result['filesystems'] = guest('list-filesystems')
        result['partitions'] = guest('part-list', '/dev/sda')
        guest('mount-options', 'ro,norecovery', args.partition, '/')
        result['filesystem'] = guest('statvfs', '/')
        result['release_file'] = (guest('cat', '/etc/issue')
                                  if guest('exists', '/etc/issue') == 'true' else None)
        absent = [prefix for prefix in ['/usr/freeware', '/usr/adobe', '/usr/aw', '/usr/AutoCAD']
                  if guest('exists', prefix) == 'false']
        spec = importlib.util.spec_from_file_location('irix_elf', ROOT/'scripts/inventory-irix-desktop.py')
        elf = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(elf)
        for i, (path, refs) in enumerate(sorted(expected.items())):
            record = {'reference': refs}
            result['paths'][path] = record
            parent = next((p for p in absent if path == p or path.startswith(p+'/')), None)
            found = not parent and (guest('exists', path) == 'true' or
                                    guest('is-symlink', path) == 'true')
            details = guest('lstatns', path) if found else None
            if details is None:
                record['status'] = 'missing'
                if parent:
                    record['absent_parent'] = parent
                continue
            fields = dict(re.findall(r'^(\w+): (-?\d+)$', details, re.M))
            mode = int(fields['st_mode'])
            kind = ('symlink' if stat.S_ISLNK(mode) else 'directory' if stat.S_ISDIR(mode)
                    else 'file' if stat.S_ISREG(mode) else 'special')
            record.update(type=kind, source_mode=oct(stat.S_IMODE(mode)), bytes=int(fields['st_size']))
            if kind == 'symlink':
                record['target'] = guest('readlink', path)
            readable = kind == 'file' or (kind == 'symlink' and
                        guest('is-file', path, 'followsymlinks:true') == 'true')
            if readable and (path in core or any(r['type'] == 'file' for r in refs)):
                record['sha256'] = guest('checksum', 'sha256', path)
                record['canonical_path'] = guest('realpath', path)
            if not refs:
                record['status'] = 'present_without_reference'
            elif all(r['type'] == 'file' and 'sha256' in r for r in refs):
                record['status'] = ('same_bytes' if all(r['sha256'] == record.get('sha256') for r in refs)
                                    else 'different_bytes' if readable else 'different_type')
            elif all(r['type'] == kind and (kind != 'symlink' or r.get('target') == record['target'])
                     for r in refs):
                record['status'] = 'same_type_and_link' if kind == 'symlink' else 'same_type'
            else:
                record['status'] = 'different_type_or_link'
            if path in core and readable:
                local = out/'elf'/path.lstrip('/').replace('/', '_')
                guest('download', path, str(local))
                try:
                    record['elf'] = elf.elf(local)
                except ValueError as error:
                    record['elf_note'] = str(error)
                if not args.retain_essential_files:
                    local.unlink()
            if i % 200 == 0:
                print('Compared', i+1, 'of', len(expected), flush=True)
        result['summary'] = dict(Counter(r['status'] for r in result['paths'].values()))
        result['essential_summary'] = dict(Counter(result['paths'][p]['status'] for p in core))
        result['raw_unchanged'] = sha256(args.raw) == raw_hash
        if not result['raw_unchanged']:
            raise RuntimeError('raw donor changed during read-only comparison')
        result['status'] = 'compared'
        print('Comparison:', result['summary'], 'essential:', result['essential_summary'], flush=True)
    except BaseException as error:
        result.update(status='failed', error=str(error))
        raise
    finally:
        if pid:
            subprocess.run(['guestfish', '--remote='+pid, 'exit'], env=env,
                           capture_output=True, timeout=60)
        (out/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
