"""Assemble local installer media for the two recorded clean Indy imports."""

import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile

from . import ROOT, sha256


def run(args):
    native = args.native_package.resolve()
    vendor = args.vendor_payload.resolve()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError(f'Output already exists: {output}')
    native_manifest = json.loads((native / 'manifest.json').read_text())
    profile = ROOT / 'profiles/netbsd-sgimips-indy-11.99.11-v1.json'
    if (
        native_manifest['profile'] != profile.stem
        or sha256(profile) != native_manifest['profile_sha256']
        or native_manifest['artifacts'] != json.loads(profile.read_text())['artifacts']
        or sha256(native / 'native.tar.gz') != native_manifest['archive_sha256']
    ):
        raise ValueError('Native package differs from its Indy build profile or manifest')
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
