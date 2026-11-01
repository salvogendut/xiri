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
    a = p.parse_args()
    seed, out = a.seed_run.resolve(), a.output_directory.resolve()
    r = json.loads((seed/'result.json').read_text())
    assert r['status'] == 'observed' and r['clean_shutdown']
    assert r['guest_payload_verified'] and r['executable_permissions_applied']
    assert r['persistent_helpers_installed'] and r['native_x11_after']
    pin = json.loads((ROOT/'lab/irix-signal/baseline.json').read_text())
    assert r['pin'] == pin
    assert (seed/'disk.raw').stat().st_size == 8589934592
    out.mkdir(parents=True, exist_ok=False)
    (out/'tftp').mkdir()
    (out/'verification').mkdir()
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
    kernel = ROOT/'.work/netbsd-irix-signal-build/tftp/netbsd-XIRI_INDY'
    assert sha(kernel) == pin['boot_kernel_sha256']
    shutil.copyfile(kernel, out/'tftp/netbsd-XIRI_INDY')
    for source in ['lab/irix-installed-desktop/copy-ledger.json',
                   'lab/irix-installed-desktop/permissions.json']:
        shutil.copyfile(ROOT/source, out/Path(source).name)
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
    report = dict(schema=1, status='chd-roundtrip-verified', script_sha256=sha(Path(__file__)),
        source_run=str(seed.relative_to(ROOT)), source_result_sha256=sha(seed/'result.json'),
        source_raw_sha256=raw_hash, decoded_raw_sha256=raw_hash, logical_bytes=8589934592,
        sector_bytes=512, geometry=[16384,16,64], compression='zlib', pin=pin,
        chd_sha256=sha(image), chd_bytes=image.stat().st_size, nvram_sha256=sha(out/'nvram.bin'),
        config_sha256=sha(out/'iris.toml'), copy_ledger_sha256=sha(out/'copy-ledger.json'),
        permission_manifest_sha256=sha(out/'permissions.json'),
        tool_version=subprocess.run(TOOL, text=True, capture_output=True).stdout.splitlines()[0],
        commands=commands, direct_chd_boot='pending separate cold-boot probe')
    (out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Created', image, 'and verified exact raw-disk round trip', flush=True)


if __name__ == '__main__':
    main()
