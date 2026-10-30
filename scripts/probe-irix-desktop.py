#!/usr/bin/env python3
"""Capture desktop startup boundaries on the pinned LP64 kernel, with controls."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


probe = module('probe', 'probe-netbsd.py')
runtime = module('runtime', 'probe-irix-runtime.py')


def trace_signature(trace):
    calls = []
    for line in trace['calls']:
        fields = {k: int(v, 0) for k, v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)', line)}
        number = fields['syscall']
        item = {'syscall': number}
        if number in [1000, 1040, 1056, 1107]:
            item['a0'] = fields['a0']
        if number == 1107:
            item.update(a1=fields['a1'], a2=fields['a2'])
        calls.append(item)
    return {'calls': calls, 'paths': [p for p in trace['paths'] if p.startswith(('/emul/irix/', '/usr/lib32/', '/lib32/', '/dev/'))]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    args = parser.parse_args()
    args.debugger, args.boot_timeout = False, 300
    pin = json.loads((ROOT / 'lab/irix-lp64/baseline.json').read_text())
    inventory = json.loads((ROOT / 'lab/irix-desktop/manifest.json').read_text())
    expectations_path = ROOT / 'lab/irix-desktop/expectations.json'
    expectations = json.loads(expectations_path.read_text()) if expectations_path.exists() else None
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    seed = ROOT / '.work/indy-netbsd-kernel'
    kernel_dir = ROOT / '.work/netbsd-irix64-build/tftp'
    native_kernel = ROOT / '.work/netbsd-irix64-build/kernel-media/netbsd'
    inputs = [('native-o32', ROOT / '.work/irix-o32-segments/native-o32', pin['native_o32_sha256'])]
    vendor = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    for c in vendor['candidates']:
        inputs.append((c['fixture_name'], ROOT / '.work/irix-reference/vendor' / c['path'].lstrip('/'), c['sha256']))
    for r in pin['runtimes']:
        inputs.append((r['name'], ROOT / '.work/irix-reference/vendor' / r['path'].lstrip('/'), r['sha256']))
    library_inputs = {}
    for i, (path, info) in enumerate(inventory['files'].items()):
        if path.startswith('/usr/bin/'):
            continue
        name = f'library-{i:02d}'
        inputs.append((name, ROOT / '.work/irix-desktop/root' / path.lstrip('/'), info['sha256']))
        library_inputs[path] = name
    checked = [*inputs, ('emulator', probe.IRIS, pin['emulator_sha256']),
               ('ci client', probe.CI, pin['ci_client_sha256']),
               ('disk', seed / 'disk.raw', pin['base_disk_sha256']),
               ('nvram', seed / 'nvram.bin', pin['nvram_sha256']),
               ('boot kernel', kernel_dir / 'netbsd-XIRI_INDY', pin['boot_kernel_sha256']),
               ('native kernel', native_kernel, pin['native_kernel_sha256'])]
    for name, path, sha in checked:
        if probe.sha256(path) != sha:
            parser.error('input differs: ' + name)
    output = ROOT / '.work/irix-desktop-runs'
    output.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=output))
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(kernel_dir)), config, flags=re.M)
    lab = probe.Lab(args, directory, config_text=config)
    result = {'status': 'error', 'mode': args.mode, 'clean_shutdown': False,
              'pin': pin, 'inventory_sha256': probe.sha256(ROOT / 'lab/irix-desktop/manifest.json'),
              'harness_sha256': probe.sha256(Path(__file__).resolve()),
              'runner_sha256': probe.sha256(ROOT / 'lab/irix-lp64/runner.c'),
              'observations': [], 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    started = time.monotonic()
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    normal = {'errno_bytes': 0, 'errno': 0, 'exit': 0, 'signal': 0, 'killed': 0, 'stdout': '', 'stderr': ''}
    native = {**normal, 'exit': 37, 'stdout': 'XIRI_ABI_PROBE\n'}
    cases = [{'name': 'native-before', 'program': 'native-o32', 'expect': native}]
    for label, ids in [('root', [0,0,0,0]), ('user', [1234,1234,5678,5678])]:
        cases += [{'name': 'asa-'+label, 'program': 'vendor-asa', 'ids': ids,
                   'expect': {**normal, 'stdout': 'XIRI_VENDOR_O32\n'}},
                  {'name': 'echo-'+label, 'program': 'vendor-echo', 'ids': ids, 'argv': ['XIRI_VENDOR_N32'],
                   'expect': {**normal, 'stdout': 'XIRI_VENDOR_N32\n'}}]
    for stage in ['runtime', 'closure']:
        for label, ids in [('root', [0,0,0,0]), ('user', [1234,1234,5678,5678])]:
            for program in ['4Dwm', 'toolchest']:
                cases.append({'name': stage+'-'+program+'-'+label, 'program': 'vendor-'+program,
                              'stage': stage, 'ids': ids, 'argv': ['-display', '127.0.0.1:99'], 'trace': True})
    cases += [{'name': 'asa-after', 'program': 'vendor-asa', 'expect': {**normal, 'stdout': 'XIRI_VENDOR_O32\n'}},
              {'name': 'echo-after', 'program': 'vendor-echo', 'ids': [0,0,0,0], 'argv': ['XIRI_VENDOR_N32'],
               'expect': {**normal, 'stdout': 'XIRI_VENDOR_N32\n'}},
              {'name': 'native-after', 'program': 'native-o32', 'expect': native}]
    try:
        for name in ['disk.raw', 'nvram.bin']:
            probe.run(['cp', '--reflink=auto', '--sparse=always', seed/name, directory/name], timeout=120)
        media = directory / 'media'
        media.mkdir()
        for name, source, sha in inputs:
            probe.run(['cp', source, media/name])
            if probe.sha256(media/name) != sha:
                raise RuntimeError('input changed: ' + name)
        (media/'SHA256').write_text(''.join(f'SHA256 ({n}) = {s}\n' for n, _, s in inputs))
        for source, name in [(native_kernel, 'netbsd'), (ROOT/'lab/indy-netbsd/probe.sh', 'probe.sh'),
                             (ROOT/'lab/irix-lp64/runner.c', 'runner.c')]:
            probe.run(['cp', source, media/name])
        (media/'input.txt').write_text(' XIRI_VENDOR_O32\n')
        (media/'payload.bin').write_bytes(bytes(range(256))*512)
        lines = ['#!/bin/sh', 'set -eu', 'cd /root/irix-desktop', 'ulimit -c 0']
        installed = False
        for case in cases:
            if case.get('stage') == 'closure' and not installed:
                for path, name in library_inputs.items():
                    target = '/emul/irix' + path
                    lines += ['mkdir -p ' + shlex.quote(str(Path(target).parent)),
                              'cp ' + name + ' ' + shlex.quote(target+'.new'),
                              'chmod 755 ' + shlex.quote(target+'.new'),
                              'mv ' + shlex.quote(target+'.new') + ' ' + shlex.quote(target)]
                installed = True
            command = './runner ./' + case['program']
            if 'ids' in case:
                command += ' ' + ' '.join(map(str, case['ids']))
            if 'argv' in case:
                command += ' -- ' + shlex.join(case['argv'])
            if case.get('trace'):
                command = 'ktrace -i -t un -f ' + case['name'] + '.ktrace ' + command
            lines += ['echo STARTCASE '+case['name'], command, 'echo ENDCASE '+case['name']]
        for case in cases:
            if case.get('trace'):
                lines += ['echo STARTTRACE '+case['name'], 'kdump -f '+case['name']+'.ktrace -t un',
                          'echo ENDTRACE '+case['name']]
        lines += ['sha256 -c SHA256', 'echo DESKTOP_DONE']
        (media/'run.sh').write_text('\n'.join(lines)+'\n')
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-V', 'XIRI_DESKTOP', '-o', directory/'probe.iso', media])
        lab.start()
        if lab.command('mkdir -p /cdrom /root/irix-desktop /emul/irix/usr/lib /emul/irix/lib /emul/irix/lib32 /emul/irix/usr/lib32 && '
                       'mount -t cd9660 -o ro /dev/cd0a /cdrom && cp /cdrom/* /root/irix-desktop/ && '
                       'cp /cdrom/netbsd /netbsd && cd /root/irix-desktop && sha256 -c SHA256 && '
                       'chmod 755 native-o32 vendor-* library-* && '
                       'cp vendor-o32-libc /emul/irix/usr/lib/libc.so.1 && cp vendor-o32-rld /emul/irix/lib/rld && '
                       'cp vendor-n32-libc /emul/irix/lib32/libc.so.1 && cp vendor-n32-libc /emul/irix/usr/lib32/libc.so.1 && '
                       'cp vendor-n32-rld /emul/irix/lib32/rld && chmod 755 /emul/irix/*/rld /emul/irix/*/libc.so.1 /emul/irix/usr/*/libc.so.1 && '
                       'cc -O2 -Wall -Wextra -Werror runner.c -o runner', 180):
            raise RuntimeError('desktop inputs or native runner failed')
        if lab.command(shlex.join(['sh', '/cdrom/probe.sh', pin['ident'], pin['native_kernel_sha256'],
                                  probe.sha256(media/'payload.bin')]), 60):
            raise RuntimeError('native kernel/file/swap controls failed')
        before = len(lab.serial_text())
        rc = lab.command('sh /root/irix-desktop/run.sh', 180)
        output = lab.serial_text()[before:]
        (directory/'desktop-serial.txt').write_text(output)
        result['traces'] = {}
        failures = []
        for case in cases:
            name = case['name']
            match = re.search(r'^STARTCASE '+name+r'\n(.*?)^ENDCASE '+name+r'$', output, re.M|re.S)
            if not match:
                raise RuntimeError('missing case '+name)
            actual = runtime.observation(match[1])
            expected = case.get('expect')
            if expectations and case.get('stage'):
                expected = expectations['cases'][name]['actual']
            passed = actual == expected if expected is not None else None
            console = '\n'.join(line for line in match[1].splitlines() if line and not line.startswith(('OBS ', 'STDOUT ', 'STDERR ')))
            result['observations'].append({'name': name, 'actual': actual, 'console': console, 'passed': passed})
            if passed is False:
                failures.append(name)
            if case.get('trace'):
                trace = re.search(r'^STARTTRACE '+name+r'\n(.*?)^ENDTRACE '+name+r'$', output, re.M|re.S)
                if not trace:
                    raise RuntimeError('missing trace '+name)
                result['traces'][name] = {
                    'calls': [bytes.fromhex(x).decode() for x in re.findall(r'irix_o32: \d+, ([0-9a-f]+)', trace[1])],
                    'paths': re.findall(r'NAMI\s+"([^"]+)"', trace[1])}
                signature = trace_signature(result['traces'][name])
                result['traces'][name]['signature'] = signature
                if expectations:
                    trace_ok = signature == expectations['cases'][name]['trace_signature']
                    console_ok = console == expectations['cases'][name]['console']
                    result['observations'][-1]['passed'] = passed and trace_ok and console_ok
                    if not trace_ok or not console_ok:
                        failures.append(name + '-trace-or-console')
                if not result['traces'][name]['calls']:
                    raise RuntimeError('desktop never entered foreign dispatcher: '+name)
        if rc or '\nDESKTOP_DONE\n' not in output or failures:
            raise RuntimeError('desktop boundary qualification failed: '+', '.join(failures))
        if lab.command('test "$(cksum /root/xiri-probe)" = "3540535338 33 /root/xiri-probe"', 30):
            raise RuntimeError('native post-run file control failed')
        result['status'] = 'passed' if expectations else 'observed'
        if expectations:
            result['expectations_sha256'] = probe.sha256(expectations_path)
        print(f'{len(cases)} desktop/control cases {result["status"]}', flush=True)
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
        result['seconds'] = round(time.monotonic()-started, 3)
        (directory/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['status'] in ['observed', 'passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
