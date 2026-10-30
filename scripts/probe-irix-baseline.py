#!/usr/bin/env python3
"""Measure native execution and foreign-ELF rejection before adding IRIX support."""

import argparse
import importlib.util
import json
from pathlib import Path
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('netbsd_probe', ROOT / 'scripts/probe-netbsd.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    args = parser.parse_args()
    args.debugger = False
    args.boot_timeout = 300
    fixtures = ROOT / '.work/irix-o32'
    manifest = json.loads((fixtures / 'manifest.json').read_text())
    output_root = ROOT / '.work/irix-o32-runs'
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=f'{args.mode}-', dir=output_root))
    lab = probe.Lab(args, directory)
    result = {'mode': args.mode, 'status': 'error', 'clean_shutdown': False,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'fixture_manifest': manifest}
    started = time.monotonic()
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    try:
        checkpoint = ROOT / '.work/indy-netbsd-kernel'
        result['base_disk_sha256'] = probe.sha256(checkpoint / 'disk.raw')
        for name in ['disk.raw', 'nvram.bin']:
            probe.run(['cp', '--reflink=auto', '--sparse=always', checkpoint / name,
                       directory / name], timeout=120)
        result['nvram_sha256'] = probe.sha256(directory / 'nvram.bin')
        result['kernel_sha256'] = probe.sha256(ROOT / '.work/netbsd-11.0/tftp/netbsd-XIRI_INDY')
        result['emulator_sha256'] = probe.sha256(probe.IRIS)
        result['harness_sha256'] = probe.sha256(Path(__file__).resolve())
        media = directory / 'media'
        media.mkdir()
        checks = []
        for name, metadata in manifest['fixtures'].items():
            if probe.sha256(fixtures / name) != metadata['sha256']:
                raise RuntimeError(f'{name}: rebuild fixtures; manifest mismatch')
            probe.run(['cp', fixtures / name, media / name])
            checks.append(f'test "$(sha256 -q /root/irix-probe/{name})" = {metadata["sha256"]}')
        probe.run(['cp', ROOT / 'lab/irix-o32/runner.c', media / 'runner.c'])
        result['runner_sha256'] = probe.sha256(media / 'runner.c')
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-V', 'XIRI_ABI',
                   '-o', directory / 'probe.iso', media])
        lab.start()
        command = ('mkdir -p /cdrom /root/irix-probe && '
                   'mount -t cd9660 -o ro /dev/cd0a /cdrom && '
                   'cp /cdrom/native-o32 /cdrom/irix-o32-* /cdrom/runner.c /root/irix-probe/ && ' +
                   ' && '.join(checks) + ' && '
                   'cd /root/irix-probe && chmod 755 native-o32 irix-o32-* && '
                   'cc -O2 -Wall -Wextra runner.c -o runner')
        if lab.command(command, 180):
            raise RuntimeError('fixture copy, hash check, or native runner build failed')
        print('Run native control and two direct-execve rejection checks', flush=True)
        before = len(lab.serial_text())
        rc = lab.command('cd /root/irix-probe; ulimit -c 0; '
                         './runner ./native-o32 ./irix-o32-marked ./irix-o32-unbranded '
                         '>baseline.log 2>&1; abi_rc=$?; cat baseline.log; '
                         'test "$abi_rc" -eq 0', 90)
        output = lab.serial_text()[before:]
        (directory / 'baseline-serial.txt').write_text(output)
        result['guest_exit_status'] = rc
        if rc or 'BASELINE_PASS native=works irix=ENOEXEC' not in output:
            raise RuntimeError('unexpected execution/rejection behavior; inspect baseline-serial.txt')
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
        print(result['error'], flush=True)
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        if not lab.clean_shutdown:
            result['status'] = 'error'
        result['seconds'] = round(time.monotonic() - started, 3)
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
