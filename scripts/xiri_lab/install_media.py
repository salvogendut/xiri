"""Assemble local installer media for the two recorded clean Indy imports."""

import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

from . import ROOT, sha256
from .native_package import archive_tree


def validate_native(native):
    native_manifest = json.loads((native / 'manifest.json').read_text())
    profile = ROOT / 'profiles/netbsd-sgimips-indy-11.99.11-v1.json'
    if (
        native_manifest['profile'] != profile.stem
        or sha256(profile) != native_manifest['profile_sha256']
        or native_manifest['artifacts'] != json.loads(profile.read_text())['artifacts']
        or sha256(native / 'native.tar.gz') != native_manifest['archive_sha256']
    ):
        raise ValueError('Native package differs from its Indy build profile or manifest')
    return native_manifest['archive_sha256']


def upgrade_delta(before, after, work):
    previous = validate_native(before)
    delta = work / 'delta'
    delta.mkdir()
    (delta / 'previous').write_text(previous + '\n')
    rows = []
    with tarfile.open(before / 'native.tar.gz') as old, tarfile.open(after / 'native.tar.gz') as new:
        for metadata in ('target.conf', 'prerequisites.tsv'):
            content = new.extractfile(metadata).read()
            if old.extractfile(metadata).read() != content:
                raise ValueError('Native upgrade changes ' + metadata)
            (delta / metadata).write_bytes(content)

        def inventory(archive):
            return dict(line.split('|', 1) for line in archive.extractfile('files.tsv').read().decode().splitlines())

        a, b = inventory(old), inventory(new)
        for name in sorted(a.keys() | b.keys()):
            if a.get(name) == b.get(name):
                continue
            if not re.fullmatch(r'root/usr/local/(?:s?bin/xiri-|libexec/xiri/)[a-zA-Z0-9_][a-zA-Z0-9_.-]*', name):
                raise ValueError('Unsupported upgrade destination: ' + name)
            row = [name.removeprefix('root')]
            for side, archive, entry in [('old', old, a.get(name)), ('new', new, b.get(name))]:
                if entry is None:
                    if name in archive.getnames():
                        raise ValueError('Unlisted upgrade member in package: ' + name)
                    row.extend(['-', '-'])
                    continue
                kind, mode, digest, policy = entry.split('|')
                if kind != 'file' or policy != 'replace-owned-file' or not re.fullmatch('0[0-7]{3}', mode):
                    raise ValueError('Expected a managed regular file: ' + name)
                member = archive.getmember(name)
                if not member.isreg() or member.mode != int(mode, 8):
                    raise ValueError('Package member type or mode differs from helper: ' + name)
                dest = delta / side / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(archive.extractfile(name).read())
                if sha256(dest) != digest:
                    raise ValueError('Package ledger differs from helper: ' + name)
                row.extend([mode, digest])
            rows.append('|'.join(row))
    if not rows:
        raise ValueError('Native packages contain identical helpers')
    (delta / 'changes').write_text('\n'.join(rows) + '\n')
    path = work / 'delta.tgz'
    archive_tree(delta, path)
    return path


def run(args):
    native = args.native_package.resolve()
    vendor = args.vendor_payload.resolve()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError(f'Output already exists: {output}')
    validate_native(native)
    imported = json.loads((vendor / 'manifest.json').read_text())
    release = imported['release']
    record = json.loads((ROOT / 'docs/results/2026-11-23-clean-bootstrap.json').read_text())
    pin = record['installer_inputs_verified_on_host']['imports'].get(release)
    if (
        not pin
        or sha256(vendor / 'manifest.json') != pin['manifest_sha256']
        or sha256(vendor / 'payload.tar.gz') != pin['archive_sha256']
    ):
        raise ValueError('Expected a recorded desktop import for 6.5.22f or 6.5.30f')
    with tempfile.TemporaryDirectory(dir=output.parent) as temporary:
        work = Path(temporary)
        inputs = {
            'native.tgz': native / 'native.tar.gz',
            'payload.tgz': vendor / 'payload.tar.gz',
            'install.sh': ROOT / 'packaging/native/install-desktop.sh',
            'uninstall.sh': ROOT / 'packaging/native/uninstall-desktop.sh',
        }
        if args.upgrade_from:
            inputs['delta.tgz'] = upgrade_delta(args.upgrade_from, native, work)
            inputs['upgrade.sh'] = ROOT / 'packaging/native/upgrade-desktop.sh'
        table = '/emul/irix/usr/lib/filetype/desktop.otr'
        files = imported['files']
        (work / 'VENDOR').write_text(
            ''.join(
                f"SHA256 ({p[1:]}) = {r['sha256']}\n"
                for p, r in files.items()
                if r['type'] == 'file' and p != table
            )
        )
        (work / 'links').write_text(
            ''.join(f"{p[1:]}|{r['target']}\n" for p, r in files.items() if r['type'] == 'symlink')
        )
        (work / 'release').write_text(release + '\n')
        (work / 'table.sha').write_text(files[table]['sha256'] + '\n')

        # Include one filesystem block per entry for fragments and directories.
        def blocks(rows):
            return sum(8 + (size + 1023) // 1024 for size in rows)

        with tarfile.open(inputs['native.tgz']) as archive:
            native_kib = blocks(item.size for item in archive)
        vendor_kib = blocks(row.get('bytes', 0) for row in files.values())
        (work / 'space').write_text(f'{native_kib} {vendor_kib}\n')
        for name in ('VENDOR', 'links', 'release', 'table.sha', 'space'):
            inputs[name] = work / name
        (work / 'SHA256').write_text(''.join(f'SHA256 ({k}) = {sha256(v)}\n' for k, v in inputs.items()))
        inputs['SHA256'] = work / 'SHA256'
        iso = work / 'install.iso'
        subprocess.run(
            [
                'genisoimage',
                '-quiet',
                '-R',
                '-V',
                'XIRI_INSTALL',
                '-o',
                iso,
                '-graft-points',
                *(f'{name}={path}' for name, path in inputs.items()),
            ],
            check=True,
        )
        os.link(iso, output)
    print(f'IRIX {release} installer: {output}')
    return 0
