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


def verify_rpc_warnings(result):
    assert '_RC=0' in result['rpcbind_warning_check']
    events = result.get('rpcbind_warning_events')
    if events is not None:
        assert 'XIRI_RPC_WATCH_START' in events and 'XIRI_RPC_WATCH_END' in events
        assert events.index('XIRI_RPC_WATCH_START') < events.index('XIRI_RPC_WATCH_END')
        assert 'rpcbind: cannot bind' not in events
    else:
        # Preserve the qualification rules for historical observations.
        counts = re.search(r'RPC_BIND_WARNINGS_BEFORE=(\d+) AFTER=(\d+)', result['rpcbind_warning_check'])
        assert counts and counts[1] == counts[2]


def verify_irix_module(pin, seed, build, result):
    """Require matching artifacts and a filesystem-loaded personality at boot."""
    module = seed['irix_module']
    observed = result['irix_module']
    assert module['name'] == 'compat_irix_o32'
    assert module['build_manifest'] == pin['module_build_manifest']
    assert module['build_manifest_sha256'] == pin['module_build_manifest_sha256']
    for artifact, key in [('netbsd', 'native_kernel_sha256'), ('netbsd.boot', 'boot_kernel_sha256')]:
        assert build['artifacts'][artifact]['sha256'] == pin[key]
    assert module['sha256'] == build['artifacts']['compat_irix_o32.kmod']['sha256']
    assert seed['installed_files'][module['path']] == module['sha256']
    for path in ['/etc/modules.conf', '/etc/rc.conf']:
        assert path in seed['installed_files']
    for key in ['name', 'path', 'sha256']:
        assert observed[key] == module[key]
    for evidence in [module, observed]:
        assert re.search(r'^compat_irix_o32\s+exec\s+filesys\s', evidence['modstat'], re.M)
        assert evidence['securelevel'] == 1


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--png', required=True, type=Path)
    p.add_argument('--promote', action='store_true')
    p.add_argument('--source-equivalence', type=Path,
                   help='Committed-source record for this module build; preserves older records in the same lab.')
    p.add_argument('--record-bundle', action='store_true',
                   help='save verification in this bundle without changing the default image')
    a = p.parse_args()
    r = json.loads((a.run/'result.json').read_text())
    if r.get('scope') == 'xdm-direct-chd':
        from xiri_lab.xdm_qualification import qualify
        return qualify(a, verify_irix_module)
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
    for relative, digest in m.get('emulator_files', {}).items():
        assert sha(bundle/relative) == digest, relative
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
    if m['pin'].get('module_build_manifest'):
        build_path = bundle/'irix-module-build.json'
        assert sha(build_path) == m['pin']['module_build_manifest_sha256']
        assert sha(ROOT/m['pin']['module_build_manifest']) == sha(build_path)
        assert m['irix_module'] == seed_result['irix_module']
        verify_irix_module(m['pin'], seed_result, json.loads(build_path.read_text()), r)
    if seed_result.get('desktop_behavior'):
        assert sha(bundle/'desktop-behavior-resources.json') == seed_result['desktop_behavior']['resource_ledger_sha256']
        assert 'granite' in r['desktop_behavior']['backdrop']
        assert 'pixmap id #' in r['desktop_behavior']['backdrop']
        assert '_RC=0' in r['desktop_behavior']['home_layout']
        assert '"/usr/freeware/bin/xmahjongg" Executing' in r['desktop_behavior']['execution_events']
    if seed_result.get('native_rpcbind_build'):
        rpc = json.loads((bundle/'native-rpcbind-source.json').read_text())
        for key in ['source_revision', 'sources', 'rpcbind_sha256']:
            assert rpc[key] == seed_result['native_rpcbind_build'][key]
        verify_rpc_warnings(r)
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
    if seed_result.get('vendor_shell'):
        assert '\nIRIX_SHELL_IMAGE_OK\n' in seed_result['vendor_shell']
        assert r['winterm_home'] == '/usr/people/xiritest'
        assert '_RC=0' in r['native_null_device']
        launch = r['catalog_launch']
        assert launch['input'] == 'XTEST double-click' and launch['page'] == 'Freeware'
        assert launch['target'] == 'xmahjongg'
        assert launch['initial_pid'] > 0 and launch['launched_pid'] > 0
        assert launch['initial_pid'] != launch['launched_pid']
        assert '"xmahjongg"' in launch['tree']
        assert '"Icon Catalog: Freeware (Page 9 of 18)"' in launch['tree']
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
        rpcbind_warning_check=r.get('rpcbind_warning_check'),
        rpcbind_warning_events=r.get('rpcbind_warning_events'),
        bitmap_ledger_sha256=seed_result.get('bitmap_ledger_sha256'),
        support_files_verified=expected_support,
        native_controls_passed=True, tree=r['tree'], game_focus=r['game_focus'],
        session_logs=r['session_logs'], remaining_uid1234='', clean_shutdown=True,
        base_chd_unchanged=True, nvram_sha256=sha(a.run/'nvram.bin'),
        screenshot=screenshot,
        limitations=['Window observation does not establish gameplay or catalog actions.',
            'Complete desktop services and later-login application state remain unqualified.',
            'The exact pinned CLI emulator was tested; other IRIS builds need manual validation.'])
    if seed_result.get('vendor_shell'):
        report.update(winterm_home=r['winterm_home'], catalog_launch=r['catalog_launch'],
            native_null_device=r['native_null_device'], vendor_shell=seed_result['vendor_shell'])
        report['limitations'][0] = ('Catalog double-click launches xmahjongg; gameplay and '
            'opened-icon shape feedback remain unqualified.')
        report['limitations'].append('Winterm still uses NetBSD sh; interactive IRIX sh is unqualified. '
            'GIMP signal registration and xosview statistics interfaces remain unsupported.')
    if seed_result.get('desktop_behavior'):
        report['desktop_behavior'] = r['desktop_behavior']
        report['desktop_behavior_qualification'] = seed_result['desktop_behavior']
        report['limitations'][0] = ('Catalog launch, execution notification, granite and home links '
            'pass from the CHD; the source-disk qualification covers closed/opened/closed pixels. '
            'Gameplay, transient launch animation and full Dumpster operations remain unqualified.')
    if m.get('experimental_note'):
        report['experimental_note'] = m['experimental_note']
        report['limitations'].insert(0, m['experimental_note'])
        if seed_result.get('xorg_configuration', {}).get('acceleration_requested'):
            report['limitations'].append('The inherited closed/opened/closed icon-pixel qualification used software rendering; that state cycle was not repeated with XAA in this CHD probe.')
    if m.get('emulator_files'):
        report['emulator_files'] = m['emulator_files']
    if seed_result.get('xorg_configuration'):
        report['xorg_configuration'] = seed_result['xorg_configuration']
        assert r['xaa_enabled'] == seed_result['xorg_configuration']['acceleration_requested']
        report['xaa_enabled'] = r['xaa_enabled']
    if seed_result.get('newport_driver'):
        driver = seed_result['newport_driver']
        assert r['support_files_verified']['/usr/X11R7/lib/modules/drivers/newport_drv.so'] == driver['sha256']
        assert 'RENDER_PASS pixels=8536 mismatches=0' in r['render_probe']
        report['newport_driver'] = driver
        report['render_probe'] = r['render_probe']
    if r.get('console_size'):
        report['console_size'] = r['console_size']
    if m['pin'].get('module_build_manifest'):
        report['irix_module'] = r['irix_module']
        report['module_build_manifest_sha256'] = m['pin']['module_build_manifest_sha256']
        report['limitations'].append('The loadable personality still requires the Xiri fork core hooks; this is not a stock-NetBSD module.')
    if r.get('winterm_arranged'):
        report['winterm_arranged'] = r['winterm_arranged']
        report['winterm_geometry_before_arrangement'] = r['winterm_geometry_before_arrangement']
        report['limitations'].append('Winterm was explicitly resized for diagnostic input checks; its unassisted startup sizing remains unqualified in this run.')
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    if a.promote or a.record_bundle:
        manual_nvram = bundle/'nvram-graphics.bin' if m.get('manual_nvram_sha256') else a.run/'nvram.bin'
        if m.get('manual_nvram_sha256'):
            assert sha(manual_nvram) == m['manual_nvram_sha256']
        state_nvram = bundle/'prismatic-state/nvram.bin'
        if state_nvram.exists():
            assert sha(state_nvram) == m.get('manual_nvram_sha256', m['nvram_sha256']), 'Prismatic state has changed; preserve it'
        if not original.exists():
            shutil.copyfile(bundle/'manifest.json', original)
            shutil.copyfile(bundle/'nvram.bin', bundle/'verification/build-nvram.bin')
        shutil.copyfile(a.run/'nvram.bin', bundle/'nvram.bin')
        if (bundle/'prismatic-state').is_dir():
            shutil.copyfile(manual_nvram, bundle/'prismatic-state/nvram.bin')
        # Preserve each input manifest so later observations remain verifiable.
        retained = bundle/'verification'/('manifest-'+sha(source)+'.json')
        if source.resolve() != retained.resolve():
            shutil.copyfile(source, retained)
        promoted = dict(m, build_nvram_sha256=m.get('build_nvram_sha256', m['nvram_sha256']),
            nvram_sha256=report['nvram_sha256'], direct_chd_boot='verified',
            qualification=str(a.output), qualification_sha256=sha(a.output),
            qualification_run=str(a.run))
        (bundle/'manifest.json').write_text(json.dumps(promoted, indent=2)+'\n')
    if a.promote:
        public = dict(schema=1, bundle=r['bundle'], image=r['bundle']+'/netbsd-xiri.chd',
            chd_sha256=r['chd_sha256'], chd_bytes=m['chd_bytes'], logical_bytes=m['logical_bytes'],
            raw_sha256=m['source_raw_sha256'], nvram_sha256=report['nvram_sha256'],
            config_sha256=m['config_sha256'], kernel_source=m['pin']['source_revision'],
            copy_ledger_sha256=m['copy_ledger_sha256'],
            permission_manifest_sha256=m['permission_manifest_sha256'],
            qualification=str(a.output), qualification_sha256=sha(a.output))
        if m.get('manual_nvram_sha256'):
            public['manual_nvram_sha256'] = m['manual_nvram_sha256']
            public['manual_console'] = m['manual_console']
        if m.get('emulator_files'):
            public['emulator_revision'] = m['pin']['emulator_revision']
            public['emulator_files'] = m['emulator_files']
        if m['pin'].get('committed_source_revision'):
            public['kernel_source_equivalent_commit'] = m['pin']['committed_source_revision']
        if m['pin'].get('module_build_manifest'):
            public['irix_module'] = r['irix_module']
            public['module_build_manifest_sha256'] = m['pin']['module_build_manifest_sha256']
        if seed_result.get('newport_driver'):
            public['newport_driver_sha256'] = seed_result['newport_driver']['sha256']
            public['xaa_enabled'] = r['xaa_enabled']
        if seed_result.get('desktop_behavior'):
            public['desktop_behavior_resource_ledger_sha256'] = seed_result['desktop_behavior']['resource_ledger_sha256']
            public['native_fam_source_manifest_sha256'] = seed_result['native_fam_build']['source_manifest_sha256']
        (ROOT/'lab/irix-installed-desktop/image.json').write_text(json.dumps(public, indent=2)+'\n')
    print('Verified direct CHD boot, native X/Newport, visible xmahjongg, cleanup and PNG fidelity')


if __name__ == '__main__':
    main()
