#!/usr/bin/env python3
"""Cold-boot an explicit fork kernel and verify its o32 experiment contract."""

import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('netbsd_probe', ROOT / 'scripts/probe-netbsd.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--expect', choices=['baseline', 'compat'], required=True)
    parser.add_argument('--suite', choices=['minimal', 'basics', 'segments'], default='minimal')
    parser.add_argument('--kernel-directory', type=Path, required=True)
    parser.add_argument('--ident', required=True)
    args = parser.parse_args()
    args.debugger, args.boot_timeout = False, 300
    kernel_dir = args.kernel_directory.resolve()
    kernel = kernel_dir / 'netbsd-XIRI_INDY'
    if not kernel.is_file() or not re.fullmatch(r'[A-Z0-9_]+', args.ident):
        parser.error('kernel directory must contain netbsd-XIRI_INDY; ident must be uppercase alphanumeric/underscore')
    fixtures = ROOT / '.work' / ('irix-o32-experiment' if args.suite == 'minimal' else f'irix-o32-{args.suite}')
    manifest = json.loads((fixtures / 'manifest.json').read_text())
    version, count = {'minimal': (1, 23), 'basics': (2, 34), 'segments': (3, 70)}[args.suite]
    if manifest.get('experiment_version') != version or len(manifest['fixtures']) != count:
        parser.error(f'rebuild the complete version {version} experiment ({count} fixtures)')
    output_root = ROOT / '.work/irix-experiment-runs'
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=f'{args.suite}-{args.expect}-{args.mode}-', dir=output_root))
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(kernel_dir)), config, flags=re.M)
    lab = probe.Lab(args, directory, config_text=config)
    result = {'mode': args.mode, 'expect': args.expect, 'suite': args.suite, 'ident': args.ident,
              'status': 'error', 'clean_shutdown': False,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'fixture_manifest': manifest}
    started = time.monotonic()
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    try:
        checkpoint = ROOT / '.work/indy-netbsd-kernel'
        result['base_disk_sha256'] = probe.sha256(checkpoint / 'disk.raw')
        for name in ['disk.raw', 'nvram.bin']:
            probe.run(['cp', '--reflink=auto', '--sparse=always', checkpoint / name, directory / name], timeout=120)
        result['nvram_sha256'] = probe.sha256(directory / 'nvram.bin')
        result['kernel_sha256'] = probe.sha256(kernel)
        result['emulator_sha256'] = probe.sha256(probe.IRIS)
        result['harness_sha256'] = probe.sha256(Path(__file__).resolve())
        media = directory / 'media'
        media.mkdir()
        cases, sums = [], []
        for name, metadata in manifest['fixtures'].items():
            if probe.sha256(fixtures / name) != metadata['sha256']:
                raise RuntimeError(f'{name}: fixture/manifest mismatch')
            probe.run(['cp', fixtures / name, media / name])
            sums.append(f'SHA256 ({name}) = {metadata["sha256"]}')
            expected = metadata['expect']
            if args.expect == 'baseline' and name != 'native-o32':
                expected = 'reject'
            cases.append(f'./{name} {expected}')
        for _ in range(5):
            cases.extend([f'./irix-o32-marked {"output" if args.expect == "compat" else "reject"}',
                          './native-o32 output'])
        if args.suite == 'segments':
            for _ in range(3):
                expected = 'output' if args.expect == 'compat' else 'reject'
                cases.extend([f'./irix-segments {expected}', f'./irix-segments-bss {expected}',
                              './native-o32 output'])
        (media / 'cases.txt').write_text('\n'.join(cases) + '\n')
        (media / 'SHA256').write_text('\n'.join(sums) + '\n')
        result['case_count'] = len(cases)
        for source, name in [(ROOT / 'lab/irix-o32/experiment-runner.c', 'runner.c'),
                             (ROOT / 'lab/indy-netbsd/probe.sh', 'probe.sh'), (kernel, 'netbsd')]:
            probe.run(['cp', source, media / name])
        result['runner_sha256'] = probe.sha256(media / 'runner.c')
        (media / 'payload.bin').write_bytes(bytes(range(256)) * 512)
        payload_sha = probe.sha256(media / 'payload.bin')
        if args.suite != 'minimal':
            (media / 'map-input.bin').write_bytes(bytes([0x11]) * 4096 + bytes([0x22]) * 4096)
            result['map_input_sha256'] = probe.sha256(media / 'map-input.bin')
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-V', 'XIRI_O32',
                   '-o', directory / 'probe.iso', media])
        lab.start()
        if lab.command('mkdir -p /cdrom /root/irix-experiment && '
                       'mount -t cd9660 -o ro /dev/cd0a /cdrom && '
                       'cp /cdrom/netbsd /netbsd && cp /cdrom/* /root/irix-experiment/ && '
                       'cd /root/irix-experiment && sha256 -c SHA256 && '
                       'chmod 755 native-o32 irix-* bad-* && '
                       'cc -O2 -Wall -Wextra -Werror runner.c -o runner', 180):
            raise RuntimeError('fixture import, hashes or runner compilation failed')
        smoke = shlex.join(['sh', '/cdrom/probe.sh', args.ident, result['kernel_sha256'], payload_sha])
        if lab.command(smoke, 60):
            raise RuntimeError('native kernel/file/swap smoke probe failed')
        before = len(lab.serial_text())
        rc = lab.command('cd /root/irix-experiment; ulimit -c 0; '
                         './runner cases.txt >experiment.log 2>&1; abi_rc=$?; '
                         'cat experiment.log; test "$abi_rc" -eq 0', 180)
        output = lab.serial_text()[before:]
        (directory / 'experiment-serial.txt').write_text(output)
        result['guest_exit_status'] = rc
        result['observations'] = [line for line in output.splitlines() if line.startswith('CASE ')]
        if rc or f'\nEXPERIMENT_PASS cases={len(cases)}\n' not in output:
            raise RuntimeError('execution matrix failed; inspect experiment-serial.txt')
        if len(result['observations']) != len(cases):
            raise RuntimeError('incomplete case observations')
        if lab.command('test "$(sysctl -n kern.configname)" = ' + shlex.quote(args.ident) +
                       ' && test "$(cksum /root/xiri-probe)" = "3540535338 33 /root/xiri-probe"', 15):
            raise RuntimeError('post-experiment native check failed')
        if args.suite != 'minimal' and lab.command(
                'test "$(sha256 -q /root/irix-experiment/map-input.bin)" = ' + result['map_input_sha256'], 15):
            raise RuntimeError('private file mapping changed the backing file')
        if args.suite == 'segments' and lab.command('cd /root/irix-experiment && sha256 -c SHA256', 30):
            raise RuntimeError('segment writes changed fixture files')
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
        print(result['error'], flush=True)
    finally:
        try:
            lab.close()
        except Exception as error:
            result.update(status='error', cleanup_error=str(error))
        result['clean_shutdown'] = lab.clean_shutdown
        if not lab.clean_shutdown:
            result['status'] = 'error'
        result['seconds'] = round(time.monotonic() - started, 3)
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
