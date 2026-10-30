#!/usr/bin/env python3
"""Qualify the bounded o32 loader and record the first vendor startup boundary."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('probe', ROOT / 'scripts/probe-netbsd.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def observation(output):
    match = re.search(r'^OBS path=\S+ errno_bytes=(\d+) errno=(\d+) exit=(-?\d+) signal=(\d+) killed=(\d+)$', output, re.M)
    if not match:
        raise RuntimeError('missing direct-exec observation')
    result = dict(zip(['errno_bytes', 'errno', 'exit', 'signal', 'killed'], map(int, match.groups())))
    for stream in ['stdout', 'stderr']:
        match = re.search(r'^' + stream.upper() + r' bytes=(\d+) hex=([0-9a-f]*)$', output, re.M)
        if not match:
            raise RuntimeError('missing captured ' + stream)
        data = bytes.fromhex(match[2])
        if len(data) != int(match[1]):
            raise RuntimeError('truncated ' + stream)
        result[stream] = data.decode('utf-8', errors='backslashreplace')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    args = parser.parse_args()
    args.debugger, args.boot_timeout = False, 300
    fixtures = ROOT / '.work/irix-o32-runtime'
    synthetic = json.loads((fixtures / 'manifest.json').read_text())
    pin = json.loads((ROOT / 'lab/irix-o32/runtime.json').read_text())
    vendor = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    kernel_dir = ROOT / '.work/netbsd-irix-build/runtime-tftp'
    kernel = kernel_dir / 'netbsd-XIRI_INDY'
    inputs = [(name, fixtures / name, info['sha256']) for name, info in synthetic['files'].items()]
    inputs += [('native-o32', ROOT / '.work/irix-o32-segments/native-o32', pin['native_control_sha256'])]
    inputs += [(c['fixture_name'], ROOT / '.work/irix-reference/vendor' / c['path'].lstrip('/'), c['sha256'])
               for c in vendor['candidates']]
    inputs += [(f'vendor-runtime-{i}', ROOT / '.work/irix-reference/vendor' / r['path'].lstrip('/'), r['sha256'])
               for i, r in enumerate(pin['runtimes'])]
    for name, path, sha in [*inputs, ('kernel', kernel, pin['kernel']['sha256'])]:
        if not path.is_file() or probe.sha256(path) != sha:
            parser.error(f'{name}: missing or different pinned input: {path}')
    output_root = ROOT / '.work/irix-runtime-runs'
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=output_root))
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(kernel_dir)), config, flags=re.M)
    lab = probe.Lab(args, directory, config_text=config)
    result = {'status': 'error', 'mode': args.mode, 'clean_shutdown': False, 'pin': pin,
              'synthetic_manifest': synthetic, 'observations': [],
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    started = time.monotonic()
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    success = {'errno_bytes': 0, 'errno': 0, 'exit': 37, 'signal': 0, 'killed': 0,
               'stdout': 'XIRI_ABI_PROBE\n', 'stderr': ''}
    rejected = {**success, 'errno_bytes': 4, 'errno': 8, 'exit': 126, 'stdout': ''}
    cases = [{'name': 'native-before', 'program': 'native-o32', 'interpreter': 'interpreter', 'expect': success}]
    cases += [{**c, 'expect': success if c['expect'] == 'output' else rejected} for c in synthetic['cases']]
    cases += [{'name': 'missing-interpreter', 'program': 'dynamic', 'interpreter': None,
               'expect': {**rejected, 'errno': 2}}]
    cases += [{'name': c['fixture_name'], 'program': c['fixture_name'], 'interpreter': 'vendor-runtime-0',
               'expect': pin['asa_expected'] if c['fixture_name'] == 'vendor-asa' else rejected}
              for c in vendor['candidates']]
    cases += [{'name': 'native-after', 'program': 'native-o32', 'interpreter': 'interpreter', 'expect': success}]
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
        for name, source, sha in inputs:
            probe.run(['cp', source, media / name])
            sums.append(f'SHA256 ({name}) = {sha}')
        (media / 'SHA256').write_text('\n'.join(sums) + '\n')
        (media / 'input.txt').write_text(' XIRI_VENDOR_O32\n')
        (media / 'payload.bin').write_bytes(bytes(range(256)) * 512)
        payload_sha = probe.sha256(media / 'payload.bin')
        for source, name in [(ROOT / 'lab/irix-o32/runtime-runner.c', 'runner.c'),
                             (ROOT / 'lab/indy-netbsd/probe.sh', 'probe.sh'), (kernel, 'netbsd')]:
            probe.run(['cp', source, media / name])
        result['runner_sha256'] = probe.sha256(media / 'runner.c')
        lines = ['#!/bin/sh', 'set -eu', 'cd /root/irix-runtime', 'ulimit -c 0']
        for case in cases:
            for name in [case['name'], case['program'], case['interpreter']]:
                if name is not None and not re.fullmatch(r'[A-Za-z0-9-]+', name):
                    raise RuntimeError('unsafe case name')
            lines += [f'echo STARTCASE {case["name"]}']
            if case['interpreter'] is None:
                lines += ['rm /emul/irix/usr/lib/libc.so.1']
            else:
                lines += [f'cp {case["interpreter"]} /emul/irix/usr/lib/libc.new',
                          'chmod 755 /emul/irix/usr/lib/libc.new',
                          'mv /emul/irix/usr/lib/libc.new /emul/irix/usr/lib/libc.so.1']
            command = './runner ./' + case['program']
            if case['name'] == 'vendor-asa':
                command = 'ktrace -i -t u -f runtime.ktrace ' + command
            lines += [command, f'echo ENDCASE {case["name"]}']
        lines += ['echo STARTTRACE', 'kdump -f runtime.ktrace -t u', 'echo ENDTRACE',
                  'sha256 -c SHA256', 'echo RUNTIME_DONE']
        (media / 'run.sh').write_text('\n'.join(lines) + '\n')
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-V', 'XIRI_RUNTIME', '-o', directory / 'probe.iso', media])
        lab.start()
        if lab.command('mkdir -p /cdrom /root/irix-runtime /emul/irix/usr/lib /emul/irix/lib && '
                       'mount -t cd9660 -o ro /dev/cd0a /cdrom && cp /cdrom/* /root/irix-runtime/ && '
                       'cp /cdrom/netbsd /netbsd && cd /root/irix-runtime && sha256 -c SHA256 && '
                       'chmod 755 dynamic native-o32 vendor-* bad-* && '
                       'cp vendor-runtime-1 /emul/irix/lib/rld && chmod 755 /emul/irix/lib/rld && '
                       'cc -O2 -Wall -Wextra -Werror runner.c -o runner', 180):
            raise RuntimeError('runtime import or native runner build failed')
        if lab.command(shlex.join(['sh', '/cdrom/probe.sh', pin['kernel']['ident'], result['kernel_sha256'], payload_sha]), 60):
            raise RuntimeError('native kernel/file/swap smoke failed')
        before = len(lab.serial_text())
        rc = lab.command('sh /root/irix-runtime/run.sh', 180)
        output = lab.serial_text()[before:]
        (directory / 'runtime-serial.txt').write_text(output)
        result['guest_exit_status'] = rc
        failures = []
        for case in cases:
            match = re.search(r'^STARTCASE ' + case['name'] + r'\n(.*?)^ENDCASE ' + case['name'] + r'$', output, re.M | re.S)
            if not match:
                raise RuntimeError('missing case ' + case['name'])
            actual = observation(match[1])
            passed = actual == case['expect']
            result['observations'].append({'name': case['name'], 'passed': passed, 'actual': actual, 'expected': case['expect']})
            if not passed:
                failures.append(case['name'])
                print(f'{case["name"]}: {actual}', flush=True)
        result['trace'] = [bytes.fromhex(s).decode() for s in
                           re.findall(r'irix_o32: \d+, ([0-9a-f]+)', output)]
        print('Vendor trace: ' + json.dumps(result['trace']), flush=True)
        parsed_trace = [dict((k, int(v, 0)) for k, v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)', line))
                        for line in result['trace']]
        expected_trace = pin['asa_trace_expected']
        result['trace_passed'] = len(parsed_trace) == len(expected_trace) and all(
            all(actual.get(k) == v for k, v in expected.items())
            for actual, expected in zip(parsed_trace, expected_trace))
        if rc or '\nRUNTIME_DONE\n' not in output or failures or not result['trace_passed']:
            raise RuntimeError('runtime qualification failed: ' + ', '.join(failures))
        if lab.command('test "$(cksum /root/xiri-probe)" = "3540535338 33 /root/xiri-probe"', 30):
            raise RuntimeError('native post-run file control failed')
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
