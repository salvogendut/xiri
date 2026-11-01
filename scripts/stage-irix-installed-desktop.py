#!/usr/bin/env python3
"""Build an emulation-root payload from the read-only installed-image inventory.

Vendor bytes stay in .work. No user account, device, package database or saved
personal session is copied. Original catalog symlink text is retained.
"""
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT/'.work/irix-installed-desktop'


def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()


def main():
    inventory = json.loads((WORK/'inventory.json').read_text())
    assert inventory['status'] == 'inventory-only' and not inventory['unresolved']
    paths = {}
    for path, info in inventory['files'].items():
        assert path.startswith('/') and '..' not in PurePosixPath(path).parts
        path = '/' + str(PurePosixPath(path)).lstrip('/')
        if path in paths:
            assert info['type'] == paths[path]['type']
            assert info.get('sha256') == paths[path].get('sha256')
            assert info.get('target') == paths[path].get('target')
        paths[path] = info
    records = {}
    with tarfile.open(WORK/'payload.tgz', 'w:gz') as archive:
        for path, info in sorted(paths.items(), key=lambda item: (len(PurePosixPath(item[0]).parts), item[0])):
            # Prevent a tar member from being written through an imported link.
            for parent in PurePosixPath(path).parents:
                assert paths.get(str(parent), {}).get('type', 'directory') == 'directory', path
            member = tarfile.TarInfo('emul/irix' + path)
            member.uid = member.gid = member.mtime = 0
            member.uname = member.gname = 'root'
            record = dict(type=info['type'])
            if info['type'] == 'file':
                source = WORK/'root'/path.lstrip('/')
                assert not source.is_symlink() and sha(source) == info['sha256'], path
                member.size = source.stat().st_size
                member.mode = 0o755 if int(info['mode'], 8) & 0o111 else 0o644
                record.update(sha256=info['sha256'], bytes=member.size, mode=oct(member.mode))
                with source.open('rb') as data:
                    archive.addfile(member, data)
            elif info['type'] == 'directory':
                member.type = tarfile.DIRTYPE
                member.mode = 0o755
                archive.addfile(member)
            elif info['type'] == 'symlink':
                member.type = tarfile.SYMTYPE
                member.mode = 0o777
                member.linkname = info['target']
                record['target'] = info['target']
                archive.addfile(member)
            else:
                raise ValueError('unsupported inventory member ' + path)
            records['/emul/irix' + path] = record
    manifest = dict(schema=1, status='staged-unqualified',
        inventory_sha256=sha(WORK/'inventory.json'), payload_sha256=sha(WORK/'payload.tgz'),
        staging_script_sha256=sha(Path(__file__)), paths=records,
        pages=inventory['pages'], entries=inventory['entries'],
        limitations=inventory['limitations'],
        mode_policy='Readable files; original executable bit retained; no set-id bits.')
    (WORK/'payload.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print('Staged', len(records), 'paths;', sum(i.get('bytes', 0) for i in records.values()), 'file bytes')


if __name__ == '__main__':
    main()
