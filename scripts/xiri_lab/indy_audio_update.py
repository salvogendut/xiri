"""Build a reversible Indy audio update from consecutive qualified installers."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from . import ROOT, sha256


def extract_archives(iso, directory, receipt):
    directory.mkdir()
    release, native, vendor, browser = receipt.split()
    recorded = subprocess.check_output(['isoinfo', '-R', '-i', iso, '-x', '/release'], text=True)
    if recorded.strip() != release:
        raise ValueError('Wrong IRIX release on ' + str(iso))
    for name, expected in [('native.tgz', native), ('payload.tgz', vendor), ('mozilla.tgz', browser)]:
        path = directory / name
        with path.open('wb') as stream:
            subprocess.run(['isoinfo', '-R', '-i', iso, '-x', '/' + name], stdout=stream, check=True)
        if sha256(path) != expected:
            raise ValueError(f'{iso} has a different {name}')


def native_changes(before, after, blobs):
    changes = {}
    with tarfile.open(before) as old, tarfile.open(after) as new:
        def ledger(archive):
            return dict(row.split('|', 1) for row in archive.extractfile('files.tsv').read().decode().splitlines())

        previous, current = ledger(old), ledger(new)
        for name in sorted(previous.keys() | current.keys()):
            if previous.get(name) == current.get(name):
                continue
            dest = '/' + name.split('/', 1)[1]
            sides = []
            for archive, inventory in ((old, previous), (new, current)):
                if name not in inventory:
                    sides.append(('-', '-'))
                    continue
                kind, mode, value, policy = inventory[name].split('|')
                if kind == 'symlink':
                    sides.append(('link', value))
                elif kind == 'file':
                    content = archive.extractfile(name).read()
                    if hashlib.sha256(content).hexdigest() != value:
                        raise ValueError('Invalid native ledger: ' + name)
                    (blobs / value).write_bytes(content)
                    sides.append(('0444' if policy == 'separate-kernel-activation' else mode, value))
                else:
                    raise ValueError('Unsupported member: ' + name)
            changes[dest] = sides
    return changes


def vendor_changes(before, after, blobs):
    changes, previous = {}, {}
    for archive, first in ((before, True), (after, False)):
        with tarfile.open(archive, 'r|gz') as stream:
            for item in stream:
                if item.isdir():
                    continue
                content = stream.extractfile(item).read() if item.isfile() else None
                value = hashlib.sha256(content).hexdigest() if content is not None else item.linkname
                row = (item.type, item.mode, value)
                if first:
                    previous[item.name] = row
                elif item.name in previous:
                    if previous.pop(item.name) != row:
                        raise ValueError('Expected an additive audio payload: ' + item.name)
                elif item.isfile() and item.name.startswith('emul/irix/usr/'):
                    (blobs / value).write_bytes(content)
                    changes['/' + item.name] = [('-', '-'), (f'{item.mode:04o}', value)]
                else:
                    raise ValueError('Unexpected vendor addition: ' + item.name)
    if previous:
        raise ValueError('The audio payload removed vendor files')
    return changes


def run(args):
    results = ROOT / 'docs/results'
    v6 = json.loads((results / '2026-11-26-indy-v6.json').read_text())['releases'][args.release]['manifest']
    v7 = json.loads((results / '2026-11-26-indy-audio-installer.json').read_text())['releases'][args.release]
    v7_receipt = v7['clean_install']['receipts']
    browser = v6['mozilla_receipt'].split()[-1]
    source_gen = args.from_generation
    if source_gen == 'v6':
        target_gen = 'v7'
        previous, target = v6['receipt'], v7_receipt
    else:
        target_gen = 'v8'
        previous = v7_receipt
        digest = json.loads((results / '2026-11-27-indy-audio-v8.json').read_text())['native_sha256']
        target = ' '.join((args.release, digest, previous.split()[2]))
    output = args.output.absolute()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError('Output already exists: ' + str(output))
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        work = Path(tmp)
        cd = work / 'cd'
        blobs = cd / 'files'
        blobs.mkdir(parents=True)
        extract_archives(args.previous_media, work / 'old', previous + ' ' + browser)
        extract_archives(args.audio_media, work / 'new', target + ' ' + browser)
        changes = native_changes(work / 'old/native.tgz', work / 'new/native.tgz', blobs)
        if source_gen == 'v6':
            changes.update(vendor_changes(work / 'old/payload.tgz', work / 'new/payload.tgz', blobs))
            example = changes['/usr/local/share/xiri/examples/rc.conf.d/mixerctl'][1][1]
            config = b''.join(line for line in (blobs / example).read_bytes().splitlines(True) if not line.startswith(b'#'))
            digest = hashlib.sha256(config).hexdigest()
            (blobs / digest).write_bytes(config)
            changes['/etc/rc.conf.d/mixerctl'] = [('-', '-'), ('0644', digest)]
            first_boot = config + (ROOT / 'packaging/native/indy-audio-mixer-firstboot.sh').read_bytes()
            first_boot_hash = hashlib.sha256(first_boot).hexdigest()
            (blobs / first_boot_hash).write_bytes(first_boot)
            (cd / 'mixer-firstboot').write_text(first_boot_hash + '\n')
        # Publish the boot pair after preparing everything it depends on.
        names = sorted(changes, key=lambda p: (p in ('/netbsd', '/netbsd.boot'), p))
        rows = ['|'.join((path, *changes[path][0], *changes[path][1])) for path in names]
        (cd / 'changes').write_text('\n'.join(rows) + '\n')
        dirs = {parent for p in changes for parent in Path(p).parents if parent != Path('/')}
        parents = sorted(dirs, key=lambda d: (len(d.parts), str(d)))
        (cd / 'parents').write_text('\n'.join(map(str, parents)) + '\n')
        (cd / source_gen).write_text(previous + '\n')
        (cd / target_gen).write_text(target + '\n')
        (cd / 'browser').write_text(browser + '\n')
        shutil.copyfile(ROOT / 'packaging/native/upgrade-indy-audio.sh', cd / 'upgrade.sh')
        checksums = [f'SHA256 ({p.relative_to(cd)}) = {sha256(p)}' for p in sorted(cd.rglob('*')) if p.is_file()]
        (cd / 'SHA256').write_text('\n'.join(checksums) + '\n')
        image = work / 'upgrade.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'XIRI_INDY_AUDIO', '-o', image, cd], check=True)
        image.chmod(0o600)
        os.link(image, output)
    print('Indy audio update:', output)
    return 0
