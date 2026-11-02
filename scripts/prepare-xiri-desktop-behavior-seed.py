#!/usr/bin/env python3
"""Carry a qualified desktop-behavior disk into graphical/image qualification."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--base', type=Path, default=ROOT/'.work/xiri-image/prepared-seed-20261102-shell')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    run, base, out = args.run.resolve(), args.base.resolve(), args.output.resolve()
    observed = json.loads((run/'result.json').read_text())
    previous = json.loads((base/'result.json').read_text())
    provenance = json.loads((base/'image-source.json').read_text())
    assert observed['status'] == 'passed' and observed['clean_shutdown']
    assert observed['base_raw_unchanged'] and observed['logout_cleanup']
    assert observed['seed'] == provenance and sha(base/'disk.raw') == provenance['raw_sha256']
    assert previous['status'] == 'observed' and previous['clean_shutdown']
    assert observed['pin'] == previous['pin']
    for source, digest in observed['sources'].items():
        assert sha(ROOT/source) == digest, source
    assert sha(ROOT/'scripts/probe-irix-desktop-behavior.py') == observed['harness_sha256']
    assert sha(ROOT/'lab/native-fam/source.json') == observed['native_fam']['source_manifest_sha256']
    ledger = ROOT/'lab/irix-desktop-behavior/resources.json'
    assert json.loads(ledger.read_text()) == observed['resources']
    out.mkdir(parents=True, exist_ok=False)
    for name in ['disk.raw', 'nvram.bin']:
        subprocess.run(['cp', '--reflink=auto', '--sparse=always', str(run/name), str(out/name)], check=True)
    result = dict(previous)
    installed = dict(previous['installed_files'])
    installed.update({
        '/usr/local/bin/xiri-desktop':observed['sources']['lab/irix-installed-desktop/xiri-desktop.sh'],
        '/usr/local/libexec/xiri/manual-session.sh':observed['sources']['lab/irix-installed-desktop/manual-session.sh'],
        '/usr/local/sbin/famd':observed['native_fam']['files']['src/famd']})
    installed.update({entry['destination']:entry['sha256'] for entry in observed['resources']['files']})
    result.update(native_fam_build=observed['native_fam'], installed_files=installed,
        native_before=observed['native_before'], native_after=observed['native_after'],
        graphics_boot=False, logout={},
        desktop_behavior=dict(run=str(run.relative_to(ROOT)), result_sha256=sha(run/'result.json'),
            resource_ledger_sha256=sha(ledger), catalog_state_cycle=observed['catalog_state_cycle']),
        behavior_preparation=dict(builder_sha256=sha(Path(__file__)),
            base_result_sha256=sha(base/'result.json'), base=provenance))
    result.pop('graphics_nvram_sha256', None)
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    (out/'image-source.json').write_text(json.dumps(dict(raw_sha256=sha(out/'disk.raw'),
        source_run=str(run.relative_to(ROOT)), source_result_sha256=sha(run/'result.json'),
        parent_image=provenance, status='awaiting graphical and CHD qualification'), indent=2)+'\n')
    print('Prepared candidate:', out)


if __name__ == '__main__':
    main()
