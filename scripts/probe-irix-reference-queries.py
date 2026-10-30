#!/usr/bin/env python3
"""Measure the same direct-trap query probe on a disposable IRIX reference."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
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


def main():
    reference = ROOT / '.work/irix-reference'
    raw = reference / 'media/irix65.raw'
    firmware = reference / 'media/ip24prom.070-9101-011.bin'
    manifest = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    query_manifest = json.loads((ROOT / '.work/irix-o32-queries/manifest.json').read_text())
    query = ROOT / '.work/irix-o32-queries/queries'
    if raw.stat().st_size != manifest['logical_disk_bytes'] or \
            probe.sha256(firmware) != manifest['firmware']['sha256'] or \
            probe.sha256(query) != query_manifest['files']['queries']['sha256']:
        raise RuntimeError('prepare the pinned reference media and query probe first')
    output_root = reference / 'query-runs'
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='ci-', dir=output_root))
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    result = {'status': 'error', 'clean_shutdown': False, 'mode': 'ci', 'queries': [],
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'query_manifest': query_manifest, 'harness_sha256': probe.sha256(Path(__file__).resolve()),
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
        ci('put', query, '--to', '/tmp/xiri-queries', '--timeout', '30')
        qsum = subprocess.check_output(['cksum', str(query)], text=True).split()[:2]
        uploaded = ci('run', 'chmod 755 /tmp/xiri-queries; cksum /tmp/xiri-queries', '--shell', 'sh', '--timeout', '30')
        if not re.search(r'^' + ' '.join(qsum) + r' /tmp/xiri-queries$', uploaded, re.M):
            raise RuntimeError('uploaded probe checksum differs')
        for name, argument, ids in [('root', '', [0, 0, 0, 0]),
                                    ('user', ' unprivileged', [60001] * 4)]:
            guest_output = f'/tmp/xiri-queries-{name}.bin'
            ci('run', f'ulimit -c 0; /tmp/xiri-queries{argument} >{guest_output}; '
               'query_rc=$?; echo QUERY_EXIT=$query_rc; test "$query_rc" -eq 0',
               '--shell', 'sh', '--timeout', '30')
            host_output = directory / f'{name}.bin'
            ci('get', guest_output, '--to', host_output, '--timeout', '30')
            data = host_output.read_bytes()
            records = runtime.query_records(f'STDOUT bytes={len(data)} hex={data.hex()}\n', ids,
                                            cap_mode=1, unknown_syssgi=22)
            result['queries'].append({'name': name, 'ids': ids, 'sha256': probe.sha256(host_output),
                                       'records': records})
            if not all(r['passed'] for r in records):
                raise RuntimeError('reference query mismatch: ' + name)
        ci('run', "printf ' XIRI_VENDOR_O32\\n' | /usr/bin/asa >/tmp/xiri-asa.out; "
           'asa_rc=$?; echo ASA_EXIT=$asa_rc; test "$asa_rc" -eq 0', '--shell', 'sh', '--timeout', '30')
        ci('get', '/tmp/xiri-asa.out', '--to', directory / 'asa.out', '--timeout', '30')
        result['asa_stdout'] = (directory / 'asa.out').read_text()
        if result['asa_stdout'] != 'XIRI_VENDOR_O32\n':
            raise RuntimeError('reference asa output differs')
        result['status'] = 'passed'
        print('32 reference queries and native asa passed', flush=True)
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
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
