#!/usr/bin/env python3
"""Package a qualified private CHD/overlay as a standalone manual preview."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess

from xiri_lab import ROOT, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--base-bundle', required=True, type=Path)
    parser.add_argument('--emulator-dir', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--port-base', required=True, type=int)
    args = parser.parse_args()
    source, base, emulator, out = [p.resolve() for p in
        (args.run, args.base_bundle, args.emulator_dir, args.output)]
    result = json.loads((source/'result.json').read_text())
    origin = json.loads((base/'manifest.json').read_text())
    assert result['status'] == 'passed' and result['clean_shutdown'] and result['base_unchanged']
    assert sha256(base/'manifest.json') == result['base_manifest_sha256']
    assert 1024 <= args.port_base <= 65527
    tool = shutil.which('chdman')
    if not tool:
        parser.error('chdman is required')
    disk, delta = source/'disk.chd', source/'disk.chd.diff.chd'
    inputs = {str(p):sha256(p) for p in [disk, delta, source/'result.json']}
    assert inputs[str(disk)] == result['base_chd_sha256']
    nvram = base/origin['qualification_nvram']
    assert sha256(nvram) == origin['qualification_nvram_sha256']
    pin = result['effective_emulator']
    for name, key in [('iris','iris_sha256'), ('iris-ci','ci_sha256')]:
        assert sha256(emulator/name) == pin[key]
    out.mkdir(parents=True, exist_ok=False)
    verification = out/'verification'
    verification.mkdir()
    commands = []

    def run(command, label):
        commands.append(command)
        print(out.name+': '+label, flush=True)
        with (verification/(label+'.log')).open('wb') as log:
            subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)

    image = out/'netbsd-xiri.chd'
    run([tool,'copy','-i',str(delta),'-ip',str(disk),'-o',str(image),'-c','zlib','-np','2'], 'merge')
    run([tool,'verify','-i',str(image)], 'verify')
    run([tool,'info','-i',str(image)], 'info')
    assert all(sha256(Path(p)) == h for p,h in inputs.items())
    (out/'emulator').mkdir()
    for name in ['iris','iris-ci']:
        shutil.copy2(emulator/name,out/'emulator'/name)
    shutil.copyfile(nvram,out/'nvram-graphics.bin')
    shutil.copyfile(nvram,verification/'initial-nvram.bin')
    shutil.copyfile(source/'result.json',verification/'source-qualification.json')
    shutil.copyfile(source/'probe-used.py',verification/'source-probe.py')
    config = (source/'iris.toml').read_text()
    config = re.sub(r'\n\[scsi\.4\]\n[^\[]*', '\n', config)
    config = re.sub(r'^tftp_dir\s*=.*\n', '', config, flags=re.M)
    for key, value in [('monitor_port', args.port_base+8),
                       ('serial_port_a', args.port_base), ('serial_port_b', args.port_base+1)]:
        config, count = re.subn(r'^'+key+r'\s*=.*$', key+' = '+str(value),config,flags=re.M)
        assert count == 1
    assert 'path = "netbsd-xiri.chd"' in config and '[scsi.4]' not in config
    assert 'ci = false' in config and 'headless = false' in config
    (out/'iris.toml').write_text(config)
    launcher = out/'run-iris.sh'
    launcher.write_text('#!/bin/sh\nset -eu\n'
        'bundle_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\n'
        'cd "$bundle_dir"\n'
        '# Keep manual writes in this preview folder.\n'
        'unset IRIS_CHD_DIFF_DIR\n'
        'exec ./emulator/iris --config iris.toml "$@"\n')
    launcher.chmod(0o755)
    subprocess.run(['sh','-n',str(launcher)],check=True)
    (out/'README.txt').write_text(
        'Xiri original-media desktop manual preview\n\n'
        'Run ./run-iris.sh. The included emulator and iris.toml select the tested CPU/cache.\n'
        'The graphical PROM should boot NetBSD and display xdm automatically.\n'
        'IRIX desktop: xiritest / xiritest. Native ctwm: netbsdtest / netbsdtest.\n'
        'Xorg uses the full 1280x1024 Newport display.\n'
        'Log out through Toolchest or the desktop menu to return to xdm.\n\n'
        'For shutdown, log in as netbsdtest, run su - in its terminal (empty root\n'
        'password), then shutdown -h now. Wait for halt/PROM before closing IRIS.\n'
        'Alternatively, native root login (empty password) is on serial B at\n'
        f'127.0.0.1:{args.port_base+1}.\n\n'
        'This CHD contains the merged qualified disk state. Your changes go to\n'
        'netbsd-xiri.chd.diff.chd beside it; keep that file to retain your work.\n'
        'The source qualification disks are preserved separately.\n\n'
        'These are original-media imports, with prepared user homes and saved\n'
        'catalog/session state. They do not contain the older manual image\'s\n'
        'extra freeware set (including GIMP and xmahjongg). Catalog entries\n'
        'alone do not establish application availability or compatibility.\n'
        'The 6.5.30 R5000 preview requires shadow cache mode; full-cache import\n'
        'integrity remains unresolved. Use the included IRIS launcher.\n\n'
        'PROM recovery if needed:\n'
        '  setenv systempartition scsi(0)disk(1)rdisk(0)partition(8)\n'
        '  setenv osloadpartition scsi(0)disk(1)rdisk(0)partition(0)\n'
        '  setenv osloader boot\n  setenv osloadfilename netbsd.boot\n'
        '  setenv osloadoptions auto\n  boot\n')
    manifest = dict(schema=1,status='packaged-from-qualified-state',profile=result['profile'],
        source_result_sha256=sha256(source/'result.json'),source_inputs=inputs,
        chd_sha256=sha256(image),chd_bytes=image.stat().st_size,
        emulated_cpu=result['emulated_cpu'],emulated_cache=result['emulated_cache'],
        effective_emulator=pin,effective_module=result['effective_module'],
        nvram_sha256=sha256(nvram),config_sha256=sha256(out/'iris.toml'),
        launcher_sha256=sha256(launcher),packager_sha256=sha256(Path(__file__)),
        chdman_sha256=sha256(Path(tool)),commands=commands,
        validation='CHD merge and integrity verification; desktop acceptance is the copied source result, not a new boot of this bundle.')
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(out/'run-iris.sh',flush=True)


if __name__ == '__main__':
    main()
