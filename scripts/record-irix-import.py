#!/usr/bin/env python3
"""Record every imported path and its target, including native font copies."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed-run', required=True, type=Path)
    p.add_argument('--output', type=Path, default=ROOT/'lab/irix-installed-desktop/copy-ledger.json')
    a = p.parse_args()
    inv = json.loads((ROOT/'.work/irix-installed-desktop/inventory.json').read_text())
    payload = json.loads((ROOT/'.work/irix-installed-desktop/payload.json').read_text())
    seed = json.loads((a.seed_run/'result.json').read_text())
    modes = json.loads((ROOT/'lab/irix-installed-desktop/permissions.json').read_text())
    records = {}
    for target, info in payload['paths'].items():
        source = target.removeprefix('/emul/irix')
        record = dict(irix_source=source, netbsd_destination=target, **info,
                      provenance='installed-image payload')
        if target in modes['files']:
            record['mode'] = '0555'
            record['source_mode'] = modes['files'][target]['source_mode']
            record['mode_reason'] = 'Current native VEXEC check for ELF mappings'
        records[target] = record
    for target, digest in seed['staged'].items():
        if target in records:
            assert records[target]['sha256'] == digest
        else:
            assert target.startswith('/emul/irix/')
            records[target] = dict(irix_source=target.removeprefix('/emul/irix'),
                netbsd_destination=target, type='file', sha256=digest,
                provenance='earlier qualified desktop seed', mode='0555')
    manifests = ['lab/irix-x11-fonts/manifest.json', 'lab/irix-toolchest-input/resources.json']
    for manifest in manifests:
        for source, info in json.loads((ROOT/manifest).read_text())['files'].items():
            target = ('/usr/local/share/xiri/fonts/'+Path(source).name if '/fonts/' in source
                      else '/emul/irix'+source)
            record = dict(irix_source=source, netbsd_destination=target, type='file',
                sha256=info['sha256'], bytes=info['bytes'], mode='0444', provenance=manifest)
            if target in records:
                assert records[target]['sha256'] == record['sha256']
            else:
                records[target] = record
    pin = json.loads((ROOT/'lab/irix-signal/baseline.json').read_text())
    for item in pin['runtimes']:
        target = '/emul/irix'+item['path']
        if target in records:
            assert records[target]['sha256'] == item['sha256']
        else:
            records[target] = dict(irix_source=item['path'], netbsd_destination=target,
                type='file', sha256=item['sha256'], mode='0555',
                provenance='earlier qualified runtime pin')
    report = dict(schema=1, script_sha256=sha(Path(__file__)),
        inventory_sha256=sha(ROOT/'.work/irix-installed-desktop/inventory.json'),
        payload_manifest_sha256=sha(ROOT/'.work/irix-installed-desktop/payload.json'),
        permission_manifest_sha256=sha(ROOT/'lab/irix-installed-desktop/permissions.json'),
        source_seed=str(a.seed_run), source_seed_result_sha256=sha(a.seed_run/'result.json'),
        resource_manifests={m:sha(ROOT/m) for m in manifests},
        files=sorted(records.values(), key=lambda r:r['netbsd_destination']),
        native_generated=['/netbsd', '/netbsd.boot', '/usr/local/bin/xiri-desktop',
            '/usr/local/libexec/xiri/{manual-guard,session,manual-session.sh,setup-pty.sh}',
            '/usr/libexec/xiri-shell', '/usr/local/share/xiri/xorg.conf',
            '/usr/local/share/xiri/fonts/fonts.dir', '/usr/people/xiritest',
            '/var/tmp/xiri-desktop/session.*', '/emul/irix/dev/ptc and PTY aliases/mounts'],
        exclusions=['IRIX kernel, Xsgi, boot scripts, installed-package history and old personal home state are not imported.',
            'Static libraries and catalog registration do not include every application data tree or delayed dependency.'])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(len(records), 'source-to-destination records')


if __name__ == '__main__':
    main()
