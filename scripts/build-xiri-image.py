#!/usr/bin/env python3
"""Package a halted, prepared NetBSD guest as a verified reusable CHD bundle."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
TOOL = ['toolbox', 'run', '-c', 'xiri-iris', 'chdman']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed-run', required=True, type=Path)
    p.add_argument('--output-directory', required=True, type=Path)
    p.add_argument('--baseline', type=Path, default=ROOT/'lab/irix-signal/baseline.json')
    p.add_argument('--kernel', type=Path, default=ROOT/'.work/netbsd-irix-signal-build/tftp/netbsd-XIRI_INDY')
    p.add_argument('--experimental-note', help='label a diagnostic image without claiming full qualification')
    p.add_argument('--iris-bin-dir', type=Path,
                   help='include the pinned standalone emulator and a local launch script')
    a = p.parse_args()
    seed, out = a.seed_run.resolve(), a.output_directory.resolve()
    r = json.loads((seed/'result.json').read_text())
    assert r['status'] == 'observed' and r['clean_shutdown']
    assert r['guest_payload_verified'] and r['executable_permissions_applied']
    assert r['persistent_helpers_installed'] and r['native_x11_after']
    pin = json.loads(a.baseline.read_text())
    assert r['pin'] == pin
    assert (seed/'disk.raw').stat().st_size == 8589934592
    out.mkdir(parents=True, exist_ok=False)
    (out/'tftp').mkdir()
    (out/'verification').mkdir()
    emulator_files = {}
    if a.iris_bin_dir:
        (out/'emulator').mkdir()
        for name, key in [('iris', 'emulator_sha256'), ('iris-ci', 'ci_client_sha256')]:
            source = a.iris_bin_dir/name
            assert sha(source) == pin[key], name
            destination = out/'emulator'/name
            shutil.copy2(source, destination)
            assert sha(destination) == pin[key], name
            emulator_files['emulator/'+name] = pin[key]
        launcher = out/'run-iris.sh'
        launcher.write_text('#!/bin/sh\nset -eu\n'
            'bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
            'cd "$bundle_dir"\nexec ./emulator/iris --config iris.toml "$@"\n')
        launcher.chmod(0o755)
        emulator_files['run-iris.sh'] = sha(launcher)
    raw_hash = sha(seed/'disk.raw')
    commands = []

    def run(args, name):
        commands.append(args)
        print(name, flush=True)
        with (out/'verification'/(name+'.log')).open('wb') as log:
            subprocess.run(args, stdout=log, stderr=subprocess.STDOUT, check=True)

    image = out/'netbsd-xiri.chd'
    run(TOOL+['createhd', '-i', str(seed/'disk.raw'), '-o', str(image),
              '-chs', '16384,16,64', '-ss', '512', '-hs', '16384', '-c', 'zlib', '-np', '2'], 'create')
    run(TOOL+['verify', '-i', str(image)], 'verify')
    decoded = out/'verification/roundtrip.raw'
    run(TOOL+['extracthd', '-i', str(image), '-o', str(decoded)], 'extract')
    assert decoded.stat().st_size == 8589934592 and sha(decoded) == raw_hash
    assert sha(seed/'disk.raw') == raw_hash
    shutil.copyfile(seed/'nvram.bin', out/'nvram.bin')
    shutil.copyfile(seed/'result.json', out/'seed-result.json')
    shutil.copyfile(ROOT/'lab/irix-installed-desktop/prismatic.cfg', out/'prismatic.cfg')
    readme = (ROOT/'lab/irix-installed-desktop/image-README.txt').read_text()
    if emulator_files:
        readme = ('Run ./run-iris.sh to use the included, tested IRIS backend.\n'
            'Prismatic must be rebuilt with the IRIS revision in manifest.json\n'
            'before using this accelerated image; the CHD cannot update its backend.\n\n'
            + readme)
    if r.get('desktop_behavior'):
        readme = readme.replace(
            'Opened-icon shape feedback and interactive IRIX shell use remain unqualified.',
            'xmahjongg changes to its running icon after launch and returns to its closed\n'
            'icon after exit. The desktop has the original granite backdrop plus\n'
            'filesystem, home and Dumpster icons; double-click opens their directory\n'
            'views. Dumpster empty/recovery and interactive IRIX shell use remain\n'
            'unqualified. Native xdm login is deferred until desktop behavior is complete.')
        readme = readme.replace('- Close the initially launched xmahjongg, then try its catalog entry.',
            '- Close the initially launched xmahjongg, then double-click its catalog entry.\n'
            '  Check the flat/running icon shapes before launch and after exit.\n'
            '- Open the filesystem, home and Dumpster desktop icons.\n'
            '  Do not assume every Dumpster action is implemented yet.')
    if not r.get('vendor_shell'):
        start = readme.index('Double-clicking xmahjongg')
        end = readme.index('Other original menu actions', start)
        readme = readme[:start] + ('This seed predates the original-shell update.\n'
            'Catalog launches and the winterm home directory fix are not qualified.\n') + readme[end:]
    if not r.get('desktop_services'):
        start = readme.index('Toolchest retains its original menus')
        end = readme.index('Other original menu actions', start)
        readme = readme[:start] + ('This older seed predates the desktop service repair.\n'
            'Its Toolchest customization follows its pinned seed configuration.\n'
            'Icon Catalog retains the Blank/communication limitation.\n') + readme[end:]
    if r.get('desktop_dimensions') != [1280, 1024]:
        start = readme.index('Xiri uses a 1280x1024 X screen.')
        end = readme.index('Other original menu actions', start)
        readme = readme[:start] + ('This legacy seed uses the earlier desktop configuration.\n'
            'Toolchest launches have not been qualified for it.\n') + readme[end:]
    if a.experimental_note:
        readme = 'EXPERIMENTAL IMAGE\n'+a.experimental_note+'\n\n'+readme
    (out/'README.txt').write_text(readme)
    (out/'prismatic-state').mkdir()
    manual_nvram = seed/'nvram.bin'
    if r.get('graphics_boot'):
        assert set(r['logout']) == {'toolchest', 'root-menu'}
        assert all(entry['returned_to_graphics_shell'] for entry in r['logout'].values())
        manual_nvram = seed/'nvram-graphics.bin'
        assert sha(manual_nvram) == r['graphics_nvram_sha256']
        shutil.copyfile(manual_nvram, out/'nvram-graphics.bin')
    shutil.copyfile(manual_nvram, out/'prismatic-state/nvram.bin')
    kernel = a.kernel.resolve()
    assert sha(kernel) == pin['boot_kernel_sha256']
    shutil.copyfile(kernel, out/'tftp/netbsd-XIRI_INDY')
    for source in ['lab/irix-installed-desktop/copy-ledger.json',
                   'lab/irix-installed-desktop/permissions.json']:
        shutil.copyfile(ROOT/source, out/Path(source).name)
    if r.get('desktop_services'):
        bitmap_ledger = ROOT/'lab/irix-desktop-bitmaps/copy-ledger.json'
        assert sha(bitmap_ledger) == r['bitmap_ledger_sha256']
        shutil.copyfile(bitmap_ledger, out/'bitmap-copy-ledger.json')
        shutil.copyfile(ROOT/'lab/native-fam/source.json', out/'native-fam-source.json')
    if r.get('desktop_behavior'):
        behavior_ledger = ROOT/'lab/irix-desktop-behavior/resources.json'
        assert sha(behavior_ledger) == r['desktop_behavior']['resource_ledger_sha256']
        shutil.copyfile(behavior_ledger, out/'desktop-behavior-resources.json')
    if r.get('native_rpcbind_build'):
        rpc_pin = ROOT/'lab/native-rpcbind/source.json'
        rpc = json.loads(rpc_pin.read_text())
        assert rpc['source_revision'] == r['native_rpcbind_build']['source_revision']
        assert rpc['sources'] == r['native_rpcbind_build']['sources']
        assert rpc['rpcbind_sha256'] == r['native_rpcbind_build']['rpcbind_sha256']
        shutil.copyfile(rpc_pin, out/'native-rpcbind-source.json')
    (out/'iris.toml').write_text('''# Run IRIS with this directory as its working directory.
nvram = "nvram.bin"
banks = [128, 128, 0, 0]
headless = false
no_audio = true
scsi_deferred_int = true
nat_subnet = "192.168.231.0/24"
monitor_port = 8898
serial_port_a = 8890
serial_port_b = 8891
ci = false
serial_log = "serial.log"

[machine]
profile = "indy_ip24"
cpu = "r4400"

[graphics]
board = "newport"

[scsi.1]
path = "netbsd-xiri.chd"
cdrom = false
overlay = true

[network]
mode = "nat"
mac = "08:00:69:12:34:57"
tftp_dir = "tftp"
''')
    if r.get('graphics_boot'):
        config = (out/'iris.toml').read_text().replace('nvram = "nvram.bin"', 'nvram = "nvram-graphics.bin"')
        (out/'iris.toml').write_text(config)
    report = dict(schema=1, status='chd-roundtrip-verified', script_sha256=sha(Path(__file__)),
        baseline=str(a.baseline.resolve().relative_to(ROOT)), baseline_sha256=sha(a.baseline),
        source_run=str(seed.relative_to(ROOT)), source_result_sha256=sha(seed/'result.json'),
        source_raw_sha256=raw_hash, decoded_raw_sha256=raw_hash, logical_bytes=8589934592,
        sector_bytes=512, geometry=[16384,16,64], compression='zlib', pin=pin,
        chd_sha256=sha(image), chd_bytes=image.stat().st_size, nvram_sha256=sha(out/'nvram.bin'),
        config_sha256=sha(out/'iris.toml'), copy_ledger_sha256=sha(out/'copy-ledger.json'),
        permission_manifest_sha256=sha(out/'permissions.json'),
        tool_version=subprocess.run(TOOL, text=True, capture_output=True).stdout.splitlines()[0],
        commands=commands, direct_chd_boot='pending separate cold-boot probe')
    if a.experimental_note:
        report['experimental_note'] = a.experimental_note
    if emulator_files:
        report['emulator_files'] = emulator_files
    if r.get('xorg_configuration'):
        report['xorg_configuration'] = r['xorg_configuration']
    if r.get('newport_driver'):
        report['newport_driver'] = r['newport_driver']
    if r.get('graphics_boot'):
        report['manual_nvram_sha256'] = sha(manual_nvram)
        report['manual_console'] = 'graphics; AutoLoad Yes; serial B diagnostic login'
    (out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Created', image, 'and verified exact raw-disk round trip', flush=True)


if __name__ == '__main__':
    main()
