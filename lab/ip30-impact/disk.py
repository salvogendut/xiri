#!/usr/bin/env python3
"""Install or cold-boot an Octane desktop disk on a private overlay."""
import argparse
import json
from pathlib import Path
import shutil
import signal
import subprocess
from types import SimpleNamespace

from wsconsole import load_probe, sha256

from xdm_login import qualify


def prepare_media(out, kernel, module, loader):
    files = {'netbsd': kernel, 'compat_irix_o32.kmod': module, 'ip30boot': loader,
             'prepare.sh': Path(__file__).with_name('prepare-disk.sh')}
    hashes = out / 'SHA256'
    hashes.write_text(''.join(f'SHA256 ({name}) = {sha256(path)}\n' for name, path in files.items()))
    subprocess.run(['genisoimage', '-quiet', '-R', '-o', out/'install.iso', '-graft-points',
                    f'SHA256={hashes}', *(f'{k}={v.resolve()}' for k, v in files.items())], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('install', 'qualify'))
    for key in ('emulator', 'firmware', 'disk', 'output', 'kernel', 'module', 'loader'):
        parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--board', choices=('solidimpact', 'highimpact'), required=True)
    parser.add_argument('--measure-redraw', action='store_true',
                        help='time visible 4Dwm window raises on a qualification boot')
    args = parser.parse_args()
    if args.measure_redraw and args.mode != 'qualify':
        parser.error('--measure-redraw requires qualify')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    paths = [args.disk, args.kernel, args.module, args.loader]
    for name in ('flash.bin', 'nvram.bin'):
        src = args.firmware / name
        paths.append(src)
        shutil.copyfile(src, out / name)
    probe = load_probe()
    probe.TOOLBOX = []
    probe.IRIS = args.emulator.resolve() / 'iris'
    probe.CI = args.emulator.resolve() / 'iris-ci'
    inputs = {str(p.resolve()): sha256(p) for p in [*paths, probe.IRIS, probe.CI]}
    subprocess.run(['cp', '--reflink=auto', '--', args.disk, out/'disk.chd'], check=True)
    config = f'''nvram = "nvram.bin"
banks = [512, 0, 0, 0]
headless = true
no_audio = true
ci = true
[machine]
profile = "octane_ip30"
cpu = "r10000"
cpus = 1
[octane]
flash = "flash.bin"
[graphics]
board = "{args.board}"
[scsi.1]
path = "disk.chd"
overlay = true
'''
    if args.mode == 'install':
        prepare_media(out, args.kernel, args.module, args.loader)
        config += ('[scsi.2]\ncdrom = true\npath = "install.iso"\n[network]\nmode = "nat"\n'
                   f'tftp_dir = {json.dumps(str(args.kernel.resolve().parent))}\n')
    lab = probe.Lab(SimpleNamespace(mode='ci', debugger=False), out, config_text=config,
                    working_directory=out, scsi1_from_config=True)
    result = dict(mode=args.mode, board=args.board, inputs=inputs, passed=False)

    def prompt(command):
        lab.send(command)
        lab.wait(r'\n>> ', 20)

    def interrupt(signum, frame):
        raise KeyboardInterrupt
    previous = signal.signal(signal.SIGTERM, interrupt)
    try:
        lab.start(boot=False)
        if args.mode == 'install':
            lab.wait(r'Option\?', 150)
            lab.send('5')
            lab.wait(r'\n>> ', 20)
            for var, value in [('SystemPartition', 'scsi(0)disk(1)rdisk(0)partition(8)'),
                               ('OSLoadPartition', 'scsi(0)disk(1)rdisk(0)partition(0)'),
                               ('OSLoader', 'boot'), ('OSLoadFilename', '/netbsd.ip30'),
                               ('OSLoadOptions', 'auto'), ('AutoLoad', 'Yes')]:
                prompt(f'setenv {var} {value}')
            lab.send('boot -f bootp():' + args.kernel.name + ' --s')
            lab.wait('Enter pathname of shell', 240)
            lab.send('')
            lab.wait(r'\n# ', 30)
            lab.send('mount -r -t cd9660 /dev/cd0a /cdrom && sh /cdrom/prepare.sh && umount /cdrom; echo OCTANE_RC=$?')
            if lab.wait(r'\nOCTANE_RC=(\d+)\n', 240)[1] != '0':
                raise RuntimeError('disk installation failed: ' + lab.serial_text()[-2000:])
            lab.send('shutdown -h now')
        else:
            lab.wait('Bootstrap, Revision', 150)
            lab.wait(r'file /netbsd\.ip30', 150)
            lab.wait(r'NetBSD [^\n]+\(XIRI_IP30_DESKTOP\)', 150)
            result['xdm'] = qualify(lab, out, measure_redraw=args.measure_redraw)
        lab.wait('unmounting done', 150)
        lab.wait(r'Option\?', 90)
        result['clean_halt'] = True
    except BaseException as exc:
        result['error'] = f'{type(exc).__name__}: {exc}'
        raise
    finally:
        try:
            lab.close()
        finally:
            signal.signal(signal.SIGTERM, previous)
            result['stopped'] = lab.process is None or lab.process.poll() is not None
            result['originals_unchanged'] = all(sha256(p) == h for p, h in inputs.items())
            result['passed'] = all(result.get(k) for k in ('clean_halt', 'stopped', 'originals_unchanged'))
            (out/'result.json').write_text(json.dumps(result, indent=2) + '\n')
    if not result['passed']:
        raise RuntimeError('Octane check failed')


if __name__ == '__main__':
    main()
