"""Verified original application resources for a disposable image build."""
import hashlib
import json
from pathlib import PurePosixPath
import shlex
import shutil
import tarfile

from . import ROOT, sha256


PACKAGES = {
    'desks': ('scripts/stage-irix-desks.py', 'payload.tgz'),
    'documents': ('scripts/stage-irix-documents.py', 'payload.tgz'),
    'filemanager': ('scripts/stage-irix-filemanager.py', 'payload.tgz'),
    'session': ('scripts/stage-irix-session.py', 'payload.tgz'),
    'gnome': ('scripts/stage-irix-gnome.py', 'payload.tgz'),
    'terminal': ('scripts/stage-irix-terminal.py', 'terminal-resources.tgz'),
    'acrobat': ('scripts/stage-irix-acrobat.py', 'payload.tgz'),
}


def prepare(name, directory, media):
    stager, payload_name = PACKAGES[name]
    label = name.upper()
    ledger = directory/'manifest.json'
    manifest = json.loads(ledger.read_text())
    assert manifest['script_sha256'] == sha256(ROOT/stager)
    payload = directory/payload_name
    assert sha256(payload) == manifest['payload_sha256']
    paths = manifest['paths']
    destinations = {r['netbsd_destination'].lstrip('/'): r for r in paths.values()}
    assert len(destinations) == len(paths)
    for source, r in paths.items():
        p = PurePosixPath(source)
        assert p.is_absolute() and '..' not in p.parts
        assert r['netbsd_destination'] == '/emul/irix'+source
        assert '\n' not in source and '|' not in source
        assert int(r['mode'], 8) in (0o444, 0o555, 0o644, 0o755, 0o777)
        assert all(paths.get(str(parent), {}).get('type', 'directory') == 'directory'
                   for parent in p.parents)
    seen = set()
    with tarfile.open(payload) as archive:
        for member in archive:
            assert member.name in destinations and member.name not in seen
            seen.add(member.name)
            r = destinations[member.name]
            assert member.uid == member.gid == 0 and member.mode == int(r['mode'], 8)
            if r['type'] == 'file':
                assert member.isfile() and member.size == r['bytes']
                assert hashlib.file_digest(archive.extractfile(member), 'sha256').hexdigest() == r['sha256']
            elif r['type'] == 'directory':
                assert member.isdir()
            else:
                assert r['type'] == 'symlink' and member.issym() and member.linkname == r['target']
    assert seen == set(destinations)
    shutil.copyfile(payload, media/(name+'-resources.tgz'))
    shutil.copyfile(ledger, media/(name+'-resources.json'))
    records = sorted(paths.values(), key=lambda r:r['netbsd_destination'])
    files = {r['netbsd_destination']:r['sha256'] for r in records if r['type'] == 'file'}
    (media/(label+'-SHA256')).write_text(''.join(f'SHA256 ({p}) = {h}\n' for p,h in files.items()))
    (media/(label+'-PATHS')).write_bytes(b''.join(r['netbsd_destination'].encode()+b'\0' for r in records))
    types = {'file':0o100000, 'directory':0o40000, 'symlink':0o120000}
    (media/(label+'-STAT')).write_text(''.join(
        f"{r['netbsd_destination']}|{types[r['type']]|int(r['mode'],8):o}|0|0\n" for r in records))
    checks = ['#!/bin/sh', 'set -eu', f'sha256 -c /cdrom/{label}-SHA256',
              f"xargs -0 stat -f '%N|%p|%u|%g' </cdrom/{label}-PATHS >/root/{name}-resource-stat",
              f'cmp /cdrom/{label}-STAT /root/{name}-resource-stat']
    for r in records:
        if r['type'] == 'symlink':
            checks.append('test "$(readlink '+shlex.quote(r['netbsd_destination'])+')" = '+shlex.quote(r['target']))
    (media/(name+'-verify.sh')).write_text('\n'.join(checks)+'\n')
    return dict(manifest_sha256=sha256(ledger), payload_sha256=manifest['payload_sha256'],
                paths=len(records), files=files,
                application_qualification='Recorded separately from resource verification.')
