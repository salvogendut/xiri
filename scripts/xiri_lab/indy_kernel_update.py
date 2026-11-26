"""Build a reversible boot-file transition for the two published v5 Indy CDs."""
import hashlib
import json
from pathlib import PurePosixPath
import subprocess
import tarfile

from . import ROOT, sha256
from .install_media import validate_native
from .mozilla_media import MODULE
from .native_package import archive_tree

BOOT_FILES = (MODULE, '/netbsd', '/netbsd.boot')
NATIVE_BOOT_MEMBERS = {'root'+MODULE, 'kernel/netbsd', 'kernel/netbsd.boot'}


def component_inventory(archive):
    """Compare the browser content and ownership independent of its old boot set."""
    files = {}
    excluded = {'root' + path for path in BOOT_FILES} | {'groups'}
    module_parents = {str(path) for path in PurePosixPath('root'+MODULE).parents}
    for member in archive.getmembers():
        if member.name in excluded or (member.isdir() and member.name != 'root' and member.name in module_parents):
            continue
        value = (hashlib.file_digest(archive.extractfile(member), 'sha256').hexdigest()
                 if member.isfile() else member.linkname)
        files[member.name] = (member.type, member.mode, value)
    groups = archive.extractfile('groups').read().decode().splitlines()
    return files, [g for g in groups if g.split('|')[1] not in BOOT_FILES]


def kernel_delta(previous, current, previous_iso, work, release, inputs):
    old = json.loads((ROOT/'docs/results/2026-11-25-mozilla-installer.json').read_text())['releases'][release]['manifest']
    native = validate_native(previous)
    if native != old['receipt'].split()[1] or sha256(inputs['payload.tgz']) != old['receipt'].split()[2]:
        raise ValueError('Expected the published v5 Indy native package and release-matched desktop')
    if sha256(previous_iso) != old['iso_sha256']:
        raise ValueError('Expected the matching v5 Mozilla installer ISO')
    delta = work/'kernel-delta'
    delta.mkdir()
    (delta/'previous').write_text(old['receipt']+'\n')
    (delta/'previous-mozilla').write_text(old['mozilla_receipt']+'\n')
    (delta/'new-native').write_text(sha256(current/'native.tar.gz')+'\n')
    old_component = work/'previous-mozilla.tgz'
    with old_component.open('wb') as f:
        subprocess.run(['isoinfo', '-R', '-i', previous_iso, '-x', '/mozilla.tgz'], stdout=f, check=True)
    if sha256(old_component) != old['mozilla_receipt'].split()[-1]:
        raise ValueError('Could not recover the published v5 Mozilla component')
    table = []
    with (tarfile.open(previous/'native.tar.gz') as a, tarfile.open(current/'native.tar.gz') as b,
          tarfile.open(old_component) as browser):
        def stable_files(t):
            return {row for row in t.extractfile('files.tsv').read().decode().splitlines()
                    if row.split('|')[0] not in NATIVE_BOOT_MEMBERS}
        if stable_files(a) != stable_files(b) or a.extractfile('prerequisites.tsv').read() != b.extractfile('prerequisites.tsv').read():
            raise ValueError('This kernel update cannot migrate unrelated native files')
        if 'mozilla.tgz' in inputs:
            with tarfile.open(inputs['mozilla.tgz']) as new_browser:
                if component_inventory(browser) != component_inventory(new_browser):
                    raise ValueError('Mozilla userspace or ownership changed in the kernel-only update')
        for path in BOOT_FILES:
            member = ('root' if path == MODULE else 'kernel')+path
            digests = []
            for t, name in ((a, member), (browser, 'root'+path), (b, member)):
                data = t.extractfile(name).read()
                digest = hashlib.sha256(data).hexdigest()
                (delta/digest).write_bytes(data)
                digests.append(digest)
            table.append('|'.join((path, *digests)))
    (delta/'files').write_text('\n'.join(table)+'\n')
    archive_tree(delta, work/'delta.tgz')
    return work/'delta.tgz'
