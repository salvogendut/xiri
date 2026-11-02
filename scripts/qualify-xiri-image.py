#!/usr/bin/env python3
"""Qualify a cold-boot desktop observation and optionally promote its boot NVRAM."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
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
    p.add_argument('--promote', action='store_true')
    a = p.parse_args()
    r = json.loads((a.run/'result.json').read_text())
    bundle = ROOT/r['bundle']
    original = bundle/'verification/build-manifest.json'
    candidates = [bundle/'manifest.json', original,
                  *sorted((bundle/'verification').glob('manifest-*.json'))]
    source = next((path for path in candidates if path.exists() and
                   sha(path) == r['input_manifest_sha256']), None)
    assert source is not None, 'the probe input manifest must be retained'
    m = json.loads(source.read_text())
    assert sha(source) == r['input_manifest_sha256']
    assert m['status'] == 'chd-roundtrip-verified'
    assert m['source_raw_sha256'] == m['decoded_raw_sha256']
    assert m['logical_bytes'] == 8589934592
    assert sha(bundle/'netbsd-xiri.chd') == m['chd_sha256'] == r['chd_sha256']
    assert sha(bundle/'seed-result.json') == m['source_result_sha256']
    assert sha(bundle/'copy-ledger.json') == m['copy_ledger_sha256']
    assert sha(bundle/'permissions.json') == m['permission_manifest_sha256']
    assert sha(bundle/'iris.toml') == m['config_sha256']
    baseline = ROOT/m.get('baseline','lab/irix-signal/baseline.json')
    if 'baseline_sha256' in m:
        assert sha(baseline) == m['baseline_sha256']
    assert r['pin'] == m['pin'] == json.loads(baseline.read_text())
    assert r['status'] == 'observed' and r['clean_shutdown'] and r['base_chd_unchanged']
    assert r['direct_disk_boot'] and r['newport_x11']
    assert not r['remaining_uid1234']
    assert re.search(r'GUARD .*absent=1 valid=1', r['session_logs'])
    for key in ('native_control', 'native_after'):
        assert 'XIRI_ABI_PROBE' in r[key] and '_RC=0' in r[key]
    for path, digest in r['sources'].items():
        assert sha(ROOT/path) == digest, path
    seed_result = json.loads((bundle/'seed-result.json').read_text())
    staged = seed_result['staged']
    dimensions = seed_result.get('desktop_dimensions', [1024, 768])
    expected_support = {f['netbsd_destination']:f['sha256']
        for f in json.loads((bundle/'copy-ledger.json').read_text())['files']
        if f['type'] == 'file' and f['netbsd_destination'] not in staged}
    expected_support.update(seed_result.get('installed_files', {}))
    if seed_result.get('desktop_services'):
        assert sha(bundle/'bitmap-copy-ledger.json') == seed_result['bitmap_ledger_sha256']
        assert sha(bundle/'native-fam-source.json') == seed_result['native_fam_build']['source_manifest_sha256']
        expected_support.update({f['netbsd_destination']:f['sha256'] for f in
            json.loads((bundle/'bitmap-copy-ledger.json').read_text())['files'] if f['type']=='file'})
        assert r['desktop_services'] and r['services_absent_after']
        assert 'of 18)' in r['tree'] and 'Trusted Path' not in r['tree']
    assert r['support_files_verified'] == expected_support
    assert 'TYPE_WINDOW' in r['game_focus'] and 'viewable=1' in r['game_focus']
    assert '"xmahjongg"' in r['tree']
    a.png.parent.mkdir(parents=True, exist_ok=True)
    if r.get('framebuffer_png_sha256'):
        # Use actual composed Newport colors. The big-endian XWD-to-PNG path
        # currently reverses red/blue compared with this capture. Preserve the two
        # PROM overscan columns instead of modifying the framebuffer PNG.
        source_frame = a.run/'desktop.png'
        assert sha(source_frame) == r['framebuffer_png_sha256']
        assert 'Compositor: sw' in r['compositor']
        header = source_frame.read_bytes()[:24]
        assert header[:8] == b'\x89PNG\r\n\x1a\n'
        assert struct.unpack('>II',header[16:24]) == (dimensions[0]+2,dimensions[1])
        raw = pixels(source_frame)
        assert len(raw) == (dimensions[0]+2)*dimensions[1]*4
        assert len(set(raw[i:i+4] for i in range(0,len(raw),4))) > 32
        shutil.copyfile(source_frame, a.png)
        screenshot = dict(path=str(a.png),sha256=sha(a.png),source=str(source_frame),
            method='IRIS software framebuffer PNG',byte_identical=True,
            dimensions=[dimensions[0]+2,dimensions[1]])
    else:
        source_frame = a.run/'game.xwd'
        assert sha(source_frame) == r['game_frame_sha256']
        subprocess.run(['magick', str(source_frame), '-strip', str(a.png)], check=True)
        raw = pixels(source_frame)
        assert len(raw) == dimensions[0]*dimensions[1]*4 and pixels(a.png) == raw
        screenshot = dict(path=str(a.png), sha256=sha(a.png),source=str(source_frame),pixels_match_xwd=True)
    report = dict(schema=1, status='disk-boot-and-desktop-observation-verified',
        qualifier_sha256=sha(Path(__file__)), directory=str(a.run), bundle=r['bundle'],
        result_sha256=sha(a.run/'result.json'), serial_sha256=sha(a.run/'serial.log'),
        build_manifest_sha256=r['input_manifest_sha256'],
        chd_sha256=r['chd_sha256'], chd_bytes=m['chd_bytes'],
        logical_bytes=m['logical_bytes'], raw_sha256=m['source_raw_sha256'],
        pin=r['pin'], sources=r['sources'], copy_ledger_sha256=m['copy_ledger_sha256'],
        permission_manifest_sha256=m['permission_manifest_sha256'],
        direct_disk_boot=True, newport_x11=True, desktop_dimensions=dimensions,
        desktop_services=bool(r.get('desktop_services')),
        services_absent_after=r.get('services_absent_after'),
        bitmap_ledger_sha256=seed_result.get('bitmap_ledger_sha256'),
        support_files_verified=expected_support,
        native_controls_passed=True, tree=r['tree'], game_focus=r['game_focus'],
        session_logs=r['session_logs'], remaining_uid1234='', clean_shutdown=True,
        base_chd_unchanged=True, nvram_sha256=sha(a.run/'nvram.bin'),
        screenshot=screenshot,
        limitations=['Window observation does not establish gameplay or catalog actions.',
            'Complete desktop services and later-login application state remain unqualified.',
            'The exact pinned CLI emulator was tested; other IRIS builds need manual validation.'])
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    if a.promote:
        if not original.exists():
            shutil.copyfile(bundle/'manifest.json', original)
            shutil.copyfile(bundle/'nvram.bin', bundle/'verification/build-nvram.bin')
        shutil.copyfile(a.run/'nvram.bin', bundle/'nvram.bin')
        if (bundle/'prismatic-state').is_dir():
            shutil.copyfile(a.run/'nvram.bin', bundle/'prismatic-state/nvram.bin')
        # Preserve each input manifest so later observations remain verifiable.
        retained = bundle/'verification'/('manifest-'+sha(source)+'.json')
        if source.resolve() != retained.resolve():
            shutil.copyfile(source, retained)
        promoted = dict(m, build_nvram_sha256=m.get('build_nvram_sha256', m['nvram_sha256']),
            nvram_sha256=report['nvram_sha256'], direct_chd_boot='verified',
            qualification=str(a.output), qualification_sha256=sha(a.output),
            qualification_run=str(a.run))
        (bundle/'manifest.json').write_text(json.dumps(promoted, indent=2)+'\n')
        public = dict(schema=1, bundle=r['bundle'], image=r['bundle']+'/netbsd-xiri.chd',
            chd_sha256=r['chd_sha256'], chd_bytes=m['chd_bytes'], logical_bytes=m['logical_bytes'],
            raw_sha256=m['source_raw_sha256'], nvram_sha256=report['nvram_sha256'],
            config_sha256=m['config_sha256'], kernel_source=m['pin']['source_revision'],
            copy_ledger_sha256=m['copy_ledger_sha256'],
            permission_manifest_sha256=m['permission_manifest_sha256'],
            qualification=str(a.output), qualification_sha256=sha(a.output))
        (ROOT/'lab/irix-installed-desktop/image.json').write_text(json.dumps(public, indent=2)+'\n')
    print('Verified direct CHD boot, native X/Newport, visible xmahjongg, cleanup and PNG fidelity')


if __name__ == '__main__':
    main()
