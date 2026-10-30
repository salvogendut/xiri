#!/usr/bin/env python3
"""Measure direct ELF-map calls on a disposable original IRIX reference."""
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tarfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


probe = module('netbsd_probe', 'probe-netbsd.py')
runtime = module('runtime_probe', 'probe-irix-runtime.py')


def main(suite='elfmap'):
    if suite not in ['elfmap', 'dispatch']:
        raise ValueError('unsupported reference suite')
    reference = ROOT / '.work/irix-reference'
    raw = reference / 'media/irix65.raw'
    firmware = reference / 'media/ip24prom.070-9101-011.bin'
    manifest = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    fixture_dir = ROOT / f'.work/irix-o32-{suite}'
    query_manifest = json.loads((fixture_dir / 'manifest.json').read_text())
    if raw.stat().st_size != manifest['logical_disk_bytes'] or \
            probe.sha256(firmware) != manifest['firmware']['sha256']:
        raise RuntimeError('prepare the pinned reference media and query probe first')
    output_root = reference / f'{suite}-runs'
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='ci-', dir=output_root))
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    result = {'status': 'error', 'clean_shutdown': False, 'mode': 'ci', 'observations': [],
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'manifest': query_manifest, 'harness_sha256': probe.sha256(Path(__file__).resolve()),
              'decoder_sha256': probe.sha256(ROOT / 'scripts/probe-irix-runtime.py'),
              'emulator_sha256': probe.sha256(probe.IRIS), 'raw_disk_size': raw.stat().st_size,
              'raw_disk_validation': 'Size checked here; SHA-256 established during media intake, not recomputed',
              'firmware_sha256': probe.sha256(firmware)}
    args = SimpleNamespace(mode='ci', debugger=False)
    lab = probe.Lab(args, directory)
    started = time.monotonic()
    logged_in = False

    def ci(*arguments):
        timeout = int(arguments[-1]) + 15 if '--timeout' in arguments else 30
        r = subprocess.run([str(probe.CI), '--socket', str(directory / 'iris.sock'), *map(str, arguments)],
                           capture_output=True, text=True, timeout=timeout)
        with (directory / 'commands.log').open('a') as stream:
            stream.write(repr(arguments) + '\n' + r.stdout + r.stderr + '\n')
        if r.returncode:
            raise RuntimeError(f'iris-ci {arguments[0]}: {r.stderr.strip()}')
        return r.stdout

    def wait(pattern, attempts):
        for attempt in range(attempts):
            try:
                ci('serial-wait', pattern, '--timeout', '50')
                return
            except RuntimeError:
                if attempt + 1 == attempts:
                    raise
                print(f'Waiting for {pattern}', flush=True)

    try:
        # Freeze this run's inputs before the long reference boot.
        fixtures = directory / 'fixtures'
        fixtures.mkdir()
        for name, info in query_manifest['files'].items():
            if not re.fullmatch(r'[A-Za-z0-9-]+', name):
                raise RuntimeError('unsafe fixture name')
            source = fixture_dir / name
            shutil.copy2(source, fixtures / name)
            if probe.sha256(fixtures / name) != info['sha256']:
                raise RuntimeError('fixture changed: ' + name)
        probe.run(['cp', '--reflink=auto', '--sparse=always', raw, directory / 'disk.raw'], timeout=120)
        seed = reference / 'boot-ci/nvram.bin'
        result['seed_nvram_sha256'] = probe.sha256(seed)
        probe.run(['cp', seed, directory / 'nvram.bin'])
        config = (ROOT / 'lab/irix-reference/iris.toml').read_text()
        config = config.replace('.work/irix-reference/boot-ci', str(directory))
        config = config.replace('.work/irix-reference/media/ip24prom.070-9101-011.bin', str(firmware))
        for name, port in zip(['monitor_port', 'serial_port_a', 'serial_port_b'], probe.free_ports(3)):
            config = re.sub(r'^' + name + r' = .*$', f'{name} = {port}', config, flags=re.M)
        (directory / 'iris.toml').write_text(config)
        lab.process = lab.launch([str(probe.IRIS), '--config', str(directory / 'iris.toml')], 'emulator')
        deadline = time.monotonic() + 30
        while not (directory / 'iris.sock').exists():
            if time.monotonic() >= deadline or lab.process.poll() is not None:
                raise RuntimeError('reference launch failed')
            time.sleep(.1)
        ci('start')
        ci('serial-wait', 'Option', '--timeout', '30')
        ci('serial-send', '5')
        ci('serial-wait', '>>', '--timeout', '30')
        ci('serial-send', 'boot')
        wait('IRIX console login:', 6)
        ci('serial-send', 'root')
        ci('serial-wait', 'TERM =', '--timeout', '15')
        ci('serial-send', '')
        ci('serial-wait', 'root@IRIX:', '--timeout', '15')
        logged_in = True
        print('Reference logged in', flush=True)
        result['identity'] = ci('run', 'uname -R; id; getconf CAP', '--shell', 'sh', '--timeout', '30')
        if '6.5 6.5.22m' not in result['identity']:
            raise RuntimeError('unexpected reference release')
        result['runtime_checksums'] = ci('run', 'cksum /usr/bin/asa /usr/lib/libc.so.1 /lib/rld',
                                         '--shell', 'sh', '--timeout', '30')
        checked = 0
        for line in result['runtime_checksums'].splitlines():
            match = re.fullmatch(r'(\d+) (\d+) (/.+)', line)
            if match:
                local = reference / 'vendor' / match[3].lstrip('/')
                local_sum = subprocess.check_output(['cksum', str(local)], text=True).split()[:2]
                if local_sum != [match[1], match[2]]:
                    raise RuntimeError('native runtime checksum differs: ' + match[3])
                checked += 1
        if checked != 3:
            raise RuntimeError('missing native runtime checksums')
        cases = query_manifest['cases']
        lines = ['#!/bin/sh', 'set -u', 'ulimit -c 0', 'cd /tmp/xiri-elfmap']
        for case in cases:
            name = case['name']
            if not re.fullmatch(r'[A-Za-z0-9-]+', name):
                raise RuntimeError('unsafe case name')
            if suite == 'elfmap':
                lines += [f'cp {case["input"]} elfmap-input.new',
                          f'chmod {case["mode"]:o} elfmap-input.new',
                          'mv elfmap-input.new elfmap-input']
            program = 'elfmap' if suite == 'elfmap' else name
            lines += [f'./{program} >{name}.out 2>{name}.err; rc=$?; echo CASE {name} "$rc"']
        if suite == 'elfmap':
            lines += ['cp elfmap-partial elfmap-input.new; chmod 755 elfmap-input.new; mv elfmap-input.new elfmap-input',
                      './elfmap unprivileged >elfmap-user.out 2>elfmap-user.err; rc=$?; echo CASE elfmap-user "$rc"']
        else:
            lines += ["printf ' XIRI_VENDOR_O32\\n' | /usr/bin/asa >asa.out 2>asa.err; "
                      'rc=$?; echo CASE asa "$rc"']
            for case in query_manifest['asa_cases']:
                name, source = case['name'], case['input']
                if not all(re.fullmatch(r'[A-Za-z0-9-]+', n) for n in [name, source]):
                    raise RuntimeError('unsafe asa case')
                lines += [f'/usr/bin/asa <{source} >{name}.out 2>{name}.err; '
                          f'rc=$?; echo CASE {name} "$rc"']
        script = directory / 'run.sh'
        script.write_text('\n'.join(lines) + '\n')
        bundle = directory / 'probes.tar'
        with tarfile.open(bundle, 'w') as tar:
            for name, info in query_manifest['files'].items():
                if not re.fullmatch(r'[A-Za-z0-9-]+', name) or probe.sha256(fixtures / name) != info['sha256']:
                    raise RuntimeError('fixture changed: ' + name)
                tar.add(fixtures / name, arcname=name)
            tar.add(script, arcname='run.sh')
        ci('put', bundle, '--to', '/tmp/xiri-elfmap.tar', '--timeout', '60')
        ci('run', 'mkdir -p /tmp/xiri-elfmap; cd /tmp/xiri-elfmap; tar xf /tmp/xiri-elfmap.tar; chmod 755 ' +
           ('elfmap' if suite == 'elfmap' else 'dispatch-*'),
           '--shell', 'sh', '--timeout', '30')
        result['probe_checksums'] = ci('run', 'cd /tmp/xiri-elfmap; cksum ' + ' '.join(query_manifest['files']),
                                       '--shell', 'sh', '--timeout', '30')
        checked = set()
        for line in result['probe_checksums'].splitlines():
            match = re.fullmatch(r'(\d+) (\d+) ([A-Za-z0-9-]+)', line)
            if match and match[3] in query_manifest['files']:
                local = subprocess.check_output(['cksum', str(fixtures / match[3])], text=True).split()[:2]
                if local != [match[1], match[2]]:
                    raise RuntimeError('uploaded fixture differs: ' + match[3])
                checked.add(match[3])
        if checked != set(query_manifest['files']):
            raise RuntimeError('missing uploaded fixture checksums')
        ci('run', 'sh /tmp/xiri-elfmap/run.sh >/tmp/xiri-elfmap/status.txt; '
           'cd /tmp/xiri-elfmap; cat status.txt; tar cf /tmp/xiri-elfmap-results.tar status.txt *.out *.err',
           '--shell', 'sh', '--timeout', '120')
        archive = directory / 'outputs.tar'
        ci('get', '/tmp/xiri-elfmap-results.tar', '--to', archive, '--timeout', '60')
        with tarfile.open(archive) as tar:
            status = tar.extractfile('status.txt').read().decode()
            statuses = dict((name, int(code)) for name, code in re.findall(r'^CASE ([A-Za-z0-9-]+) (\d+)$', status, re.M))
            names = [case['name'] for case in cases] + (['elfmap-user'] if suite == 'elfmap' else ['asa'])
            if suite == 'dispatch':
                names += [case['name'] for case in query_manifest['asa_cases']]
            if set(statuses) != set(names):
                raise RuntimeError('incomplete reference execution')
            for name in names:
                data = tar.extractfile(name + '.out').read()
                stderr = tar.extractfile(name + '.err').read().decode(errors='backslashreplace')
                record = (runtime.elfmap_record(data) if len(data) == 48 else None) if suite == 'elfmap' else \
                    (runtime.dispatch_record(data) if len(data) == 32 else None)
                result['observations'].append({'name': name, 'exit_status': statuses[name],
                                               'stdout_hex': data.hex(), 'stderr': stderr, 'record': record})
        pin_path = ROOT / f'lab/irix-o32/{suite}-reference.json'
        if pin_path.exists():
            pin = json.loads(pin_path.read_text())
            if pin['files'] != {name: info['sha256'] for name, info in query_manifest['files'].items()}:
                raise RuntimeError('reference pin belongs to different fixtures')
            if len(pin['observations']) != len(result['observations']):
                raise RuntimeError('reference pin has different case count')
            for actual, expected in zip(result['observations'], pin['observations']):
                fields = ['name', 'exit_status', 'stderr']
                passed = all(actual[k] == expected[k] for k in fields)
                got, want = actual['record'], expected['record']
                if expected.get('relocated_second') and got is not None:
                    passed = passed and 0x00400000 <= got['second_v0'] < 0x80000000 and \
                        got['second_v0'] != 0x0e010000 and got['second_v0'] % 4096 == 0
                    got = {**got, 'second_v0': want['second_v0']}
                if suite == 'dispatch' and expected.get('mapping') and got is not None:
                    passed = passed and 4096 <= got['v0'] < 0x80000000 and got['v0'] % 4096 == 0
                    if expected.get('occupied'):
                        passed = passed and 4096 <= got['preserved'] < 0x80000000 and \
                            got['preserved'] % 4096 == 0 and got['preserved'] != got['v0']
                        got = {**got, 'preserved': want['preserved']}
                    got = {**got, 'v0': want['v0']}
                if suite == 'dispatch' and actual['name'].startswith('asa'):
                    passed = passed and actual['stdout_hex'] == expected['stdout_hex']
                if got is None:
                    passed = passed and actual['stdout_hex'] == expected['stdout_hex']
                passed = passed and got == want
                actual['passed'] = passed
                if not passed:
                    raise RuntimeError('reference differs: ' + actual['name'])
            result['status'] = 'passed'
            result['reference_pin_sha256'] = probe.sha256(pin_path)
        else:
            result['status'] = 'observed'
        print(f'{len(result["observations"])} reference cases {result["status"]}', flush=True)
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
        print(result['error'], flush=True)
    finally:
        if lab.process:
            if logged_in:
                try:
                    ci('serial-send', '/etc/shutdown -y -g0 -i0')
                    # Installed third-party shutdown services take over 50 s.
                    wait('Okay to power off the system now.', 6)
                    result['clean_shutdown'] = True
                except Exception as error:
                    result['shutdown_error'] = str(error)
            try:
                ci('quit')
                lab.process.wait(timeout=15)
            except Exception:
                lab.terminate(lab.process, 'emulator')
        if not result['clean_shutdown']:
            result['status'] = 'error'
        result['seconds'] = round(time.monotonic() - started, 3)
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] in ['passed', 'observed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
