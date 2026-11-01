#!/usr/bin/env python3
"""Verify imported payload provenance, bounded observation and PNG fidelity."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def pixels(path):
    return subprocess.check_output(['magick', str(path), '-depth', '8', 'rgba:-'])


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--png', required=True, type=Path)
    a = p.parse_args()
    r = json.loads((a.run/'result.json').read_text())
    assert r['status'] == 'observed' and r['clean_shutdown'] and r['guest_payload_verified']
    assert r['pin'] == json.loads((ROOT/'lab/irix-signal/baseline.json').read_text())
    assert sha(ROOT/r['seed']/'result.json') == r['seed_result_sha256']
    for path, digest in r['sources'].items():
        assert sha(ROOT/path) == digest, path
    m = json.loads((a.run/'media/payload.json').read_text())
    public = json.loads((ROOT/'lab/irix-installed-desktop/manifest.json').read_text())
    assert sha(a.run/'media/payload.json') == r['payload_manifest_sha256'] == public['payload_manifest_sha256']
    archive = a.run/'media/payload.tgz'
    if r.get('staged_seed'):
        seed = json.loads((ROOT/r['seed']/'result.json').read_text())
        assert seed['clean_shutdown'] and seed['guest_payload_verified']
        assert seed['pin'] == r['pin'] and seed['payload_manifest_sha256'] == r['payload_manifest_sha256']
        assert seed['staged'] == r['staged']
        assert r['seed_disk_sha256'] == r['clone_disk_sha256'] == sha(ROOT/r['seed']/'disk.raw')
        archive = ROOT/'.work/irix-installed-desktop/payload.tgz'
    assert sha(archive) == m['payload_sha256'] == public['payload_sha256']
    font_manifest = ROOT/'lab/irix-x11-fonts/manifest.json'
    assert sha(font_manifest) == r['font_manifest_sha256']
    fonts = json.loads(font_manifest.read_text())
    expected_fonts = {Path(path).name:info['sha256'] for path, info in fonts['files'].items() if '/fonts/' in path}
    assert r['font_files'] == expected_fonts and len(expected_fonts) == 22
    for name, digest in expected_fonts.items():
        assert sha(a.run/'media'/name) == digest
    assert m['pages'] == public['pages'] and m['entries'] == public['entries']
    for path, info in m['paths'].items():
        if info['type'] == 'file':
            assert r['staged'][path] == info['sha256']
    assert len(r['controls']) == 2 and {c['phase'] for c in r['controls']} == {'before', 'after'}
    for c in r['controls']:
        assert c['actual'] == dict(errno_bytes=0, errno=0, exit=37, signal=0, killed=0,
                                  stdout='XIRI_ABI_PROBE\n', stderr='')
    assert r['native_x11_before'] and r['native_x11_after']
    assert r['executable_permissions_applied'] and r['persistent_helpers_installed']
    assert r['permission_manifest_sha256'] == sha(ROOT/'lab/irix-installed-desktop/permissions.json')
    assert r['manual_guard_control']['absent'] == r['manual_guard_control']['valid'] == r['manual_guard_control']['killed'] == 1
    assert r['guard']['absent'] == r['guard']['valid'] == 1
    assert sha(a.run/'desktop.xwd') == r['frame_sha256']
    assert (a.run/'desktop.tree').read_text() == r['tree']
    for c in r['components']:
        if c['pid']:
            assert sha(a.run/(c['name']+'.kdump')) == c['trace_sha256']
    a.png.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['magick', str(a.run/'desktop.xwd'), str(a.png)], check=True)
    raw = pixels(a.run/'desktop.xwd')
    assert len(raw) == 1024*768*4 and pixels(a.png) == raw
    report = dict(schema=1, status='import-and-observation-verified',
        qualifier_sha256=sha(Path(__file__)), directory=str(a.run),
        result_sha256=sha(a.run/'result.json'), serial_sha256=sha(a.run/'serial.log'),
        seed=r['seed'], seed_result_sha256=r['seed_result_sha256'],
        seed_disk_sha256=r.get('seed_disk_sha256'), clone_disk_sha256=r.get('clone_disk_sha256'),
        pin=r['pin'], sources=r['sources'], manifest_sha256=sha(ROOT/'lab/irix-installed-desktop/manifest.json'),
        pages=m['pages'], catalog_entries=len(m['entries']), guest_payload_verified=True,
        controls=r['controls'], native_x11_before=True, native_x11_after=True,
        permission_manifest_sha256=r['permission_manifest_sha256'],
        persistent_helpers_installed=True, manual_guard_control=r['manual_guard_control'],
        guard=r['guard'], clean_shutdown=True, components=r['components'], tree=r['tree'],
        user_layout=r['user_layout'], screenshot=dict(path=str(a.png), sha256=sha(a.png),
            source=str(a.run/'desktop.xwd'), pixels_match_xwd=True),
        limitations=['Import and observation only; no automatic claim that a window rendered or accepts input.',
            'Catalog launch, per-application interaction, later-login persistence and complete desktop behavior remain unqualified.',
            'Static dependency closure does not include every application data tree or delayed dependency.',
            'Original installation, package history, upgrade and removal remain separate work.'])
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print('Verified imported payload, native controls, descendant cleanup and PNG fidelity')


if __name__ == '__main__':
    main()
