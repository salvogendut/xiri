#!/usr/bin/env python3
"""Record unmodified vendor ELF rejection on the pinned static-only Xiri kernel."""

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
    parser.add_argument('--vendor-directory', type=Path, default=ROOT / '.work/irix-reference/vendor')
    args = parser.parse_args()
    args.debugger, args.boot_timeout = False, 300
    manifest = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    kernel_dir = ROOT / '.work/netbsd-irix-build/segments-tftp'
    kernel = kernel_dir / 'netbsd-XIRI_INDY'
    native = ROOT / '.work/irix-o32-segments/native-o32'
    pin = manifest['netbsd_probe_kernel']
    if not kernel.is_file() or probe.sha256(kernel) != pin['sha256']:
        parser.error('build the pinned segment kernel described in lab/irix-reference/README.md')
    if not native.is_file() or probe.sha256(native) != manifest['native_control_sha256']:
        parser.error('build the native control with scripts/build-irix-experiment.py --segments')
    inputs = [('native-o32', native, manifest['native_control_sha256'])]
    for candidate in manifest['candidates']:
        name = candidate['fixture_name']
        if not re.fullmatch(r'vendor-[A-Za-z0-9]+', name):
            parser.error('invalid fixture name in manifest')
        path = args.vendor_directory / candidate['path'].lstrip('/')
        if not path.is_file() or probe.sha256(path) != candidate['sha256']:
            parser.error(f'{path}: missing or different vendor file; see lab/irix-reference/README.md')
        inputs.append((name, path, candidate['sha256']))
    output_root = ROOT / '.work/irix-vendor-runs'
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=f'{args.mode}-', dir=output_root))
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(kernel_dir)), config, flags=re.M)
    lab = probe.Lab(args, directory, config_text=config)
    result = {'mode': args.mode, 'status': 'error', 'clean_shutdown': False,
              'purpose': 'rejection baseline; does not expect vendor execution',
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'manifest': manifest}
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
        sums = []
        cases = ['./native-o32 output']
        for name, source, sha in inputs:
            probe.run(['cp', source, media / name])
            sums.append(f'SHA256 ({name}) = {sha}')
            if name != 'native-o32':
                cases.append(f'./{name} reject')
        cases.append('./native-o32 output')
        result['case_count'] = len(cases)
        (media / 'cases.txt').write_text('\n'.join(cases) + '\n')
        (media / 'SHA256').write_text('\n'.join(sums) + '\n')
        for source, name in [(ROOT / 'lab/irix-o32/experiment-runner.c', 'runner.c'),
                             (ROOT / 'lab/indy-netbsd/probe.sh', 'probe.sh'), (kernel, 'netbsd')]:
            probe.run(['cp', source, media / name])
        result['runner_sha256'] = probe.sha256(media / 'runner.c')
        (media / 'payload.bin').write_bytes(bytes(range(256)) * 512)
        payload_sha = probe.sha256(media / 'payload.bin')
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-V', 'XIRI_VENDOR',
                   '-o', directory / 'probe.iso', media])
        lab.start()
        if lab.command('mkdir -p /cdrom /root/irix-vendor && '
                       'mount -t cd9660 -o ro /dev/cd0a /cdrom && '
                       'cp /cdrom/netbsd /netbsd && cp /cdrom/* /root/irix-vendor/ && '
                       'cd /root/irix-vendor && sha256 -c SHA256 && '
                       'chmod 755 native-o32 vendor-* && '
                       'cc -O2 -Wall -Wextra -Werror runner.c -o runner', 180):
            raise RuntimeError('import, hash verification, or runner compilation failed')
        smoke = shlex.join(['sh', '/cdrom/probe.sh', pin['ident'], result['kernel_sha256'], payload_sha])
        if lab.command(smoke, 60):
            raise RuntimeError('native kernel/file/swap smoke probe failed')
        before = len(lab.serial_text())
        rc = lab.command('cd /root/irix-vendor; ulimit -c 0; '
                         './runner cases.txt >vendor.log 2>&1; abi_rc=$?; '
                         'cat vendor.log; test "$abi_rc" -eq 0', 180)
        output = lab.serial_text()[before:]
        (directory / 'vendor-serial.txt').write_text(output)
        result['guest_exit_status'] = rc
        result['observations'] = [line for line in output.splitlines() if line.startswith('CASE ')]
        if rc or f'\nEXPERIMENT_PASS cases={len(cases)}\n' not in output or len(result['observations']) != len(cases):
            raise RuntimeError('unexpected execution/rejection behavior; inspect vendor-serial.txt')
        if lab.command('cd /root/irix-vendor && sha256 -c SHA256 && '
                       'test "$(cksum /root/xiri-probe)" = "3540535338 33 /root/xiri-probe"', 30):
            raise RuntimeError('post-run native file or vendor hash check failed')
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
