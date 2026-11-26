"""Run a release-pinned add-on CD regression on a disposable Indy v6 disk."""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

from . import ROOT, Guest, load_probe, sha256
from .kernel_log import KernelLog


def load_desktop():
    path = ROOT / 'lab/native-package/check-clean-desktop.py'
    spec = importlib.util.spec_from_file_location('desktop', path)
    desktop = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(desktop)
    return desktop


def run_indy_addon(check, description):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--release', required=True, choices=('6.5.22f', '6.5.30f'))
    for name in ('bundle', 'media', 'kernel', 'emulator', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    pins = json.loads((ROOT / f'docs/results/2026-11-26-controlpanels-{args.release}.json').read_text())
    disk = args.bundle / 'netbsd-xiri.chd'
    probe = load_probe()
    probe.IRIS = (args.emulator / 'iris').resolve()
    probe.CI = (args.emulator / 'iris-ci').resolve()
    if (sha256(disk), sha256(args.kernel), sha256(probe.IRIS)) != tuple(
            pins[key] for key in ('chd_sha256', 'kernel_sha256', 'iris_sha256')):
        parser.error('expected the v6 Indy inputs for ' + args.release)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    subprocess.run(['cp', '--reflink=auto', disk, out / 'disk.chd'], check=True)
    shutil.copyfile(args.bundle / 'nvram.bin', out / 'nvram.bin')
    config = (args.bundle / 'iris.toml').read_text().replace('"netbsd-xiri.chd"', json.dumps(str(out / 'disk.chd')))
    config += '\n[scsi.4]\ncdrom = true\npath = ' + json.dumps(str(args.media.resolve())) + '\n'
    lab = probe.Lab(SimpleNamespace(mode='ordinary', debugger=False), out, config_text=config,
                    working_directory=out, scsi1_from_config=True)
    guest = Guest(lab, pace_seconds=.014)
    symbols = subprocess.check_output(['nm', '-n', args.kernel], text=True)
    address = next(int(line.split()[0], 16) for line in symbols.splitlines() if line.endswith(' msgbufp'))
    try:
        lab.start(boot=False)
        lab.wait('login: ', 600)
        lab.send('root')
        lab.wait('xiri-indy# ', 40)
        lab.logged_in = True
        result = check(guest)
        KernelLog(lab, address).halt()
        result.update(release=args.release, clean_halt=True, iso_sha256=sha256(args.media),
                      chd_sha256=pins['chd_sha256'], kernel_sha256=pins['kernel_sha256'],
                      iris_sha256=pins['iris_sha256'],
                      nvram_input_sha256=sha256(args.bundle / 'nvram.bin'))
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        lab.close()
