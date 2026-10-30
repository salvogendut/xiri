#!/usr/bin/env python3
"""Measure desktop dependency resolution and bounded startup on original IRIX."""
import importlib.util
import json
from pathlib import Path
import re
import shlex
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


def main():
    reference = ROOT / '.work/irix-reference'
    raw = reference / 'media/irix65.raw'
    firmware = reference / 'media/ip24prom.070-9101-011.bin'
    manifest = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    desktop = json.loads((ROOT / 'lab/irix-desktop/manifest.json').read_text())
    if raw.stat().st_size != manifest['logical_disk_bytes'] or \
            probe.sha256(firmware) != manifest['firmware']['sha256']:
        raise RuntimeError('prepare the pinned reference media and query probe first')
    output_root = reference / 'desktop-runs'
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='ci-', dir=output_root))
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    result = {'status': 'error', 'clean_shutdown': False, 'mode': 'ci', 'observations': [],
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'manifest': desktop, 'harness_sha256': probe.sha256(Path(__file__).resolve()),
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
            # The CI cursor can pass a shutdown message while a command is
            # completing. This fresh run's serial log remains authoritative.
            if re.search(pattern, lab.serial_text()):
                return
            try:
                ci('serial-wait', pattern, '--timeout', '50')
                return
            except RuntimeError:
                if re.search(pattern, lab.serial_text()):
                    return
                if attempt + 1 == attempts:
                    raise
                print(f'Waiting for {pattern}', flush=True)

    try:
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
        checksums = ci('run', 'cksum ' + ' '.join(shlex.quote(n) for n in desktop['files']),
                       '--shell', 'sh', '--timeout', '30')
        checked = set()
        for line in checksums.splitlines():
            match = re.fullmatch(r'(\d+) (\d+) (/.+)', line)
            if match and match[3] in desktop['files']:
                local = ROOT / '.work/irix-desktop/root' / match[3].lstrip('/')
                if probe.sha256(local) != desktop['files'][match[3]]['sha256']:
                    raise RuntimeError('local input differs: ' + match[3])
                expected = subprocess.check_output(['cksum', str(local)], text=True).split()[:2]
                if expected != [match[1], match[2]]:
                    raise RuntimeError('original input differs: ' + match[3])
                checked.add(match[3])
        if checked != set(desktop['files']):
            raise RuntimeError('missing reference checksum')
        result['checked_files'] = sorted(checked)
        result['ldd'] = {}
        for name in ['4Dwm', 'toolchest']:
            result['ldd'][name] = ci('run', '/usr/bin/ldd /usr/bin/X11/' + name + '; echo LDD_RC=$?',
                                     '--shell', 'sh', '--timeout', '30')
        result['ldd_resolution'] = {}
        for name, output in result['ldd'].items():
            resolved = dict(re.findall(r'^\s*(\S+)\s+=>\s+(\S+)', output, re.M))
            wanted = set(desktop['static_analysis']['/usr/bin/X11/'+name]['needed_closure'])
            if 'LDD_RC=0' not in output or set(resolved.values()) != wanted:
                raise RuntimeError('native ldd differs from static closure: '+name)
            result['ldd_resolution'][name] = resolved
        script = directory / 'run.sh'
        lines = ['#!/bin/sh', 'set -u', 'ulimit -c 0', 'mkdir -p /tmp/xiri-desktop',
                 'cd /tmp/xiri-desktop', 'unset DISPLAY LD_LIBRARY_PATH LD_LIBRARYN32_PATH _RLD_ROOT _RLDN32_ROOT _RLD_ARGS _RLDN32_ARGS']
        names = []
        for name in ['4Dwm', 'toolchest']:
            for traced in [False, True]:
                case = name + ('-par' if traced else '')
                names.append(case)
                program = '/usr/bin/env - /usr/bin/X11/' + name + ' -display 127.0.0.1:99'
                if traced:
                    program = '/usr/sbin/par -s -SS -t 20 -o ' + case + '.trace ' + program
                lines += [program + ' >' + case + '.out 2>' + case + '.err & child=$!',
                          '(sleep 30; kill -9 "$child" 2>/dev/null) & watchdog=$!',
                          'wait "$child"; rc=$?; kill "$watchdog" 2>/dev/null; wait "$watchdog" 2>/dev/null',
                          'echo CASE ' + case + ' "$rc"']
        lines += ['/usr/bin/env - /sbin/echo XIRI_REFERENCE_AFTER >echo.out 2>echo.err; echo CASE echo "$?"']
        names.append('echo')
        script.write_text('\n'.join(lines) + '\n')
        ci('put', script, '--to', '/tmp/xiri-desktop-run.sh', '--timeout', '30')
        ci('run', 'sh /tmp/xiri-desktop-run.sh >/tmp/xiri-desktop-status; '
           'cd /tmp/xiri-desktop; cp /tmp/xiri-desktop-status status.txt; '
           'tar cf /tmp/xiri-desktop-results.tar status.txt *.out *.err *.trace',
           '--shell', 'sh', '--timeout', '180')
        archive = directory / 'outputs.tar'
        ci('get', '/tmp/xiri-desktop-results.tar', '--to', archive, '--timeout', '60')
        result['traces'] = {}
        with tarfile.open(archive) as tar:
            statuses = dict((n,int(code)) for n,code in re.findall(r'^CASE (\S+) (\d+)$',
                tar.extractfile('status.txt').read().decode(), re.M))
            if set(statuses) != set(names):
                raise RuntimeError('incomplete reference cases')
            for name in names:
                result['observations'].append({'name': name, 'exit_status': statuses[name],
                    'stdout': tar.extractfile(name+'.out').read().decode(errors='backslashreplace'),
                    'stderr': tar.extractfile(name+'.err').read().decode(errors='backslashreplace')})
                if name.endswith('-par'):
                    result['traces'][name] = tar.extractfile(name+'.trace').read().decode(errors='backslashreplace')
        if any(o['exit_status'] == 137 for o in result['observations']):
            raise RuntimeError('reference startup exceeded watchdog; not a complete observation')
        pin_path = ROOT / 'lab/irix-desktop/reference.json'
        if pin_path.exists():
            pin = json.loads(pin_path.read_text())
            if result['ldd_resolution'] != pin['ldd_resolution']:
                raise RuntimeError('reference library resolution differs from pin')
            for name, trace in result['traces'].items():
                if not all(marker in trace for marker in pin['trace_markers']):
                    raise RuntimeError('incomplete native transport trace: '+name)
            if result['observations'] != pin['observations']:
                raise RuntimeError('reference startup differs from pin')
            result['status'] = 'passed'
            result['reference_pin_sha256'] = probe.sha256(pin_path)
        else:
            result['status'] = 'observed'
        print(f'{len(result["observations"])} desktop reference cases {result["status"]}', flush=True)
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
