"""Assemble local installer media for the two recorded clean Indy imports."""

import json
import os
from pathlib import Path
import re
import subprocess
import tarfile
import tempfile

from . import ROOT, sha256
from .clock_fonts import augmented_payload, extract_fonts
from .native_package import archive_tree

INDY = 'netbsd-sgimips-indy-11.99.11-v1'
GLX = 'netbsd-sgimips-indy-11.99.11-glx-v1'


def validate_native(native):
    native_manifest = json.loads((native / 'manifest.json').read_text())
    if native_manifest['profile'] not in (INDY, GLX):
        raise ValueError('Expected an Indy native package')
    profile = ROOT / 'profiles' / (native_manifest['profile'] + '.json')
    if (
        sha256(profile) != native_manifest['profile_sha256']
        or native_manifest['artifacts'] != json.loads(profile.read_text())['artifacts']
        or sha256(native / 'native.tar.gz') != native_manifest['archive_sha256']
    ):
        raise ValueError('Native package differs from its Indy build profile or manifest')
    return native_manifest['archive_sha256']


def upgrade_delta(before, after, work, fonts=None, previous_vendor=None):
    previous = validate_native(before)
    delta = work / 'delta'
    delta.mkdir()
    (delta / 'previous').write_text(previous + '\n')
    rows = []
    with tarfile.open(before / 'native.tar.gz') as old, tarfile.open(after / 'native.tar.gz') as new:
        stock = {}
        if fonts:
            profile = json.loads((ROOT / 'profiles' / (GLX + '.json')).read_text())
            for key in ('xorg', 'glx'):
                artifact = profile['artifacts'][key]
                stock['root' + artifact['destination']] = artifact
            (delta / 'previous-vendor').write_text(previous_vendor + '\n')
        for metadata in ('target.conf', 'prerequisites.tsv'):
            content = new.extractfile(metadata).read()
            prior = old.extractfile(metadata).read()
            if stock and metadata == 'prerequisites.tsv':
                required = dict(line.split('|') for line in prior.decode().splitlines())
                if required.pop('/usr/X11R7/bin/Xorg', None) != stock['root/usr/X11R7/bin/Xorg']['stock_sha256']:
                    raise ValueError('Unexpected stock Xorg prerequisite')
                required['/usr/X11R7/lib/libglapi.so.1'] = 'e06d76ed8e6ffa6b14381dad9427ecd42b45d137a6a4fb2b707bb0cdc4fb1362'
                prior = ''.join(f'{path}|{digest}\n' for path, digest in sorted(required.items())).encode()
            if prior != content:
                raise ValueError('Native upgrade changes ' + metadata)
            (delta / metadata).write_bytes(content)

        def inventory(archive):
            return dict(line.split('|', 1) for line in archive.extractfile('files.tsv').read().decode().splitlines())

        a, b = inventory(old), inventory(new)
        for name, artifact in stock.items():
            if name in a or name not in b:
                raise ValueError('Expected a stock-to-GLX package transition')
            a[name] = '|'.join(('file', artifact['mode'], artifact['stock_sha256'], 'replace-owned-file'))
        service_files = {'root/etc/rc.d/xiri_famd', 'root/usr/local/share/xiri/examples/rc.conf.d/xiri_famd'}
        for name in sorted(a.keys() | b.keys()):
            if a.get(name) == b.get(name):
                continue
            if name in service_files:
                if name not in a or name not in b:
                    raise ValueError('Unsupported service addition or retirement: ' + name)
            elif name not in stock and not re.fullmatch(r'root/usr/local/(?:s?bin/xiri-|libexec/xiri/)[a-zA-Z0-9_][a-zA-Z0-9_.-]*', name):
                raise ValueError('Unsupported upgrade destination: ' + name)
            row = [name.removeprefix('root')]
            for side, archive, entry in [('old', old, a.get(name)), ('new', new, b.get(name))]:
                if entry is None:
                    if name in archive.getnames():
                        raise ValueError('Unlisted upgrade member in package: ' + name)
                    row.extend(['-', '-'])
                    continue
                kind, mode, digest, policy = entry.split('|')
                if name in stock and side == 'new' and digest != stock[name]['sha256']:
                    raise ValueError('Expected the qualified display artifact: ' + name)
                allowed_mode = mode == stock[name]['mode'] if name in stock else re.fullmatch('0[0-7]{3}', mode)
                if kind != 'file' or policy != 'replace-owned-file' or not allowed_mode:
                    raise ValueError('Expected a managed regular file: ' + name)
                backup = name in stock and side == 'old'
                reader = new if backup else archive
                member = reader.getmember('stock' + name[4:] if backup else name)
                if not member.isreg() or member.mode != (0o444 if backup else int(mode, 8)):
                    raise ValueError('Package member type or mode differs from ledger: ' + name)
                dest = delta / side / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(reader.extractfile(member).read())
                if sha256(dest) != digest:
                    raise ValueError('Package ledger differs from file: ' + name)
                row.extend([mode, digest])
            rows.append('|'.join(row))
    for dest, source in (fonts or {}).items():
        staged = delta / ('new/root' + dest)
        staged.parent.mkdir(parents=True, exist_ok=True)
        staged.write_bytes(source.read_bytes())
        rows.append('|'.join((dest, '-', '-', '0444', sha256(staged))))
    if not rows:
        raise ValueError('Native packages contain identical managed files')
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
        files = imported['files']
        graphics = json.loads((native / 'manifest.json').read_text())['profile'] == GLX
        if graphics != bool(args.clock_overlay):
            raise ValueError('The Indy GLX profile and its matching --clock-overlay must be used together')
        fonts = {}
        if graphics:
            fonts = extract_fonts(imported, args.clock_overlay, args.instigator, work)
            inputs['payload.tgz'] = work / 'payload.tgz'
            augmented_payload(vendor / 'payload.tar.gz', fonts, inputs['payload.tgz'])
            for dest, path in fonts.items():
                files[dest] = dict(type='file', sha256=sha256(path), bytes=path.stat().st_size)
            inputs['display-update'] = work / 'display-update'
            inputs['display-update'].write_text('Xorg GLX\n')
        if args.upgrade_from:
            inputs['delta.tgz'] = upgrade_delta(args.upgrade_from, native, work, fonts, pin['archive_sha256'])
            inputs['upgrade.sh'] = ROOT / 'packaging/native/upgrade-desktop.sh'
        table = '/emul/irix/usr/lib/filetype/desktop.otr'
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
