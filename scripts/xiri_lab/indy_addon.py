"""Run a release-pinned add-on CD regression on a disposable Indy disk."""
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


def run_indy_addon(check, description, *, check_audio_v8=None):
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument('--release', required=True, choices=('6.5.22f', '6.5.30f'))
    for name in ('bundle', 'media', 'kernel', 'emulator', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    if check_audio_v8 is not None:
        parser.add_argument('--audio-v8', action='store_true', help='start from a clean audio-v8 Prismatic base CHD')
    args = parser.parse_args()
    if check_audio_v8 is not None and args.audio_v8:
        check = check_audio_v8
        record = json.loads((ROOT / 'docs/results/2026-11-27-indy-audio-v8.json').read_text())
        release = record['releases'][args.release]
        pins = dict(chd_sha256=release['chd_sha256'], iris_sha256=release['clean_install']['iris_sha256'],
                    kernel_sha256=record['stock_bootstrap']['native_sha256']['netbsd'])
        disk = args.bundle / 'disk.chd'
        nvram = args.bundle / 'state/nvram.bin'
        cpu = release['clean_install']['cpu']
        cache = 'cache = "shadow"\n' if cpu == 'r5000' else ''
        config = ('banks = [128,128,0,0]\nscsi_deferred_int = true\n[machine]\nprofile = "indy_ip24"\n'
                  f'cpu = "{cpu}"\n{cache}[graphics]\nboard = "newport"\n[scsi.1]\noverlay = true\npath = "disk.chd"\n')
    else:
        pins = json.loads((ROOT / f'docs/results/2026-11-26-controlpanels-{args.release}.json').read_text())
        disk = args.bundle / 'netbsd-xiri.chd'
        nvram = args.bundle / 'nvram.bin'
        config = (args.bundle / 'iris.toml').read_text().replace('"netbsd-xiri.chd"', '"disk.chd"')
    probe = load_probe()
    probe.IRIS = (args.emulator / 'iris').resolve()
    probe.CI = (args.emulator / 'iris-ci').resolve()
    if (sha256(disk), sha256(args.kernel), sha256(probe.IRIS)) != tuple(
            pins[key] for key in ('chd_sha256', 'kernel_sha256', 'iris_sha256')):
        parser.error('unexpected Indy disk, kernel or emulator for ' + args.release)
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    subprocess.run(['cp', '--reflink=auto', disk, out / 'disk.chd'], check=True)
    shutil.copyfile(nvram, out / 'nvram.bin')
    config = config.replace('"disk.chd"', json.dumps(str(out / 'disk.chd')))
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
                      nvram_input_sha256=sha256(nvram))
        (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    finally:
        lab.close()
