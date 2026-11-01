#!/usr/bin/env python3
"""Measure private/fixed/local mmap behavior on original IRIX."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import struct
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


def archive_observations(archive, cases, identities):
    result = {'observations': []}
    with tarfile.open(archive) as tar:
        members = {m.name.removeprefix('./'): m for m in tar.getmembers()}
        def read(name): return tar.extractfile(members[name]).read()
        statuses = {n: int(v) for n, v in re.findall(r'^CASE (\S+) (\d+)$', read('status.txt').decode(), re.M)}
        names = {c['name']+'-'+str(i) for c in cases for i in c['identities']}
        if set(statuses) != names: raise RuntimeError('incomplete cases')
        for c in cases:
            for i in c['identities']:
                n = c['name']+'-'+str(i)
                data, err = read(n+'.out'), read(n+'.err').decode(errors='backslashreplace')
                result['observations'].append(dict(name=n, identity=i, exit=statuses[n], stdout_hex=data.hex(), stderr=err))
                if err:
                    raise RuntimeError('unexpected stderr: '+n+' '+err)
                if len(data)==256 and data[:4]==bytes.fromhex('584d4c43'):
                    w=struct.unpack('>64I',data)
                    if statuses[n] != (139 if c['symbols']['FAULT'] and not w[4] else 0) or w[:2]!=(0x584d4c43,c['symbols']['CASE']) or w[56:60]!=tuple(identities[i]) or w[62]:
                        raise RuntimeError('damaged record or identity: '+n)
                else:
                    raise RuntimeError('unexpected exec outcome: '+n+' exit='+str(statuses[n])+' bytes='+str(len(data)))
        result['setup'] = read('setup.txt').decode()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', choices=['mmap-local'], default='mmap-local')
    parser.add_argument('--smoke',action='store_true')
    args = parser.parse_args()
    smoke = args.smoke
    checkpoint = args.checkpoint
    reference = ROOT / '.work/irix-reference'
    raw = reference / 'media/irix65.raw'
    firmware = reference / 'media/ip24prom.070-9101-011.bin'
    manifest = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    fixtures = ROOT/f'.work/irix-{checkpoint}/probes'
    desktop = json.loads((fixtures/'manifest.json').read_text())
    for name, info in desktop['files'].items():
        if probe.sha256(fixtures/name) != info['sha256']:
            raise RuntimeError('fixture differs: '+name)
    if any(probe.sha256(ROOT/p) != h for p,h in desktop['sources'].items()):
        raise RuntimeError('stale fixtures')
    if raw.stat().st_size != manifest['logical_disk_bytes'] or \
            probe.sha256(firmware) != manifest['firmware']['sha256']:
        raise RuntimeError('prepare the pinned reference media and query probe first')
    output_root = reference / (checkpoint+'-records-runs')
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='ci-', dir=output_root))
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    result = {'scope': 'smoke' if smoke else 'full', 'status': 'error', 'clean_shutdown': False, 'mode': 'ci', 'observations': [],
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
    transferred = False

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
        frozen = directory/'fixtures'
        frozen.mkdir()
        for name, info in desktop['files'].items():
            shutil.copy2(fixtures/name, frozen/name)
            if probe.sha256(frozen/name) != info['sha256']:
                raise RuntimeError('fixture changed: '+name)
        fixtures = frozen
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
        cases = desktop['cases']
        if smoke: cases = [c for c in cases if any(c['name'].endswith('-'+x) for x in ['private','fixed-local-zero','fixed-local-replace','fixed-local-halfpage'])]
        upload = directory/'inputs.tar'
        with tarfile.open(upload, 'w') as tar:
            for name in desktop['files']:
                tar.add(fixtures/name, arcname=name)
        ci('put', upload, '--to','/tmp/xiri-process-records-inputs.tar','--timeout','180')
        ci('run','mkdir -p /tmp/xiri-process-records; cd /tmp/xiri-process-records; tar xf /tmp/xiri-process-records-inputs.tar; sh setup.sh && ls -ldin . mapping >setup.txt',
           '--shell','sh','--timeout','120')
        checksums = ci('run','cd /tmp/xiri-process-records; cksum o32-direct-*; cksum o32-indirect-*; '
                       'cksum n32-direct-*; cksum n32-indirect-*; cksum setup.sh mapping',
                       '--shell','sh','--timeout','180')
        checked = set()
        for line in checksums.splitlines():
            m = re.fullmatch(r'(\d+) (\d+) (\S+)', line)
            if m and m[3] in desktop['files']:
                expected = subprocess.check_output(['cksum',str(fixtures/m[3])],text=True).split()[:2]
                if expected != [m[1],m[2]]: raise RuntimeError('upload differs: '+m[3])
                checked.add(m[3])
        if checked != set(desktop['files']): raise RuntimeError('missing upload checksums')
        result['checked_files'] = sorted(checked)
        lines=['#!/bin/sh','set -u','ulimit -c 0','cd /tmp/xiri-process-records']
        for c in cases:
            for i in c['identities']:
                n=c['name']+'-'+str(i)
                lines.extend(['sh setup.sh',
                    '(sleep 10; if test -s '+n+'.pid; then kill -9 `cat '+n+'.pid` 2>/dev/null; fi) & guard=$!',
                    './'+c['name']+' '+str(i)+' </dev/null >'+n+'.out 2>'+n+'.err & pid=$!',
                    'printf "%s\\n" "$pid" >'+n+'.pid',
                    'rc=0; wait "$pid" || rc=$?; kill "$guard" 2>/dev/null || true; wait "$guard" 2>/dev/null || true',
                    'echo CASE '+n+' "$rc"'])
        script=directory/'run.sh';script.write_text('\n'.join(lines)+'\n')
        ci('put',script,'--to','/tmp/xiri-process-records/run.sh','--timeout','30')
        ci('run','sh /tmp/xiri-process-records/run.sh >/tmp/xiri-process-records/status.txt', '--shell','sh','--timeout','1800')
        # IRIX's argument limit is smaller than the whole per-ABI glob.
        # Keep each tar invocation below 8 KiB and failures inside a script;
        # an `exit` in the interactive login shell would lose the RC marker.
        names=[c['name']+'-'+str(i)+ext for c in cases for i in c['identities'] for ext in ['.out','.err']]
        lines=['#!/bin/sh','set -eu','cd /tmp/xiri-process-records',
               'tar cf /tmp/xiri-process-records-results.tar status.txt setup.txt']
        for start in range(0,len(names),64):
            lines.append('tar rf /tmp/xiri-process-records-results.tar '+' '.join(names[start:start+64]))
        script=directory/'archive.sh';script.write_text('\n'.join(lines)+'\n')
        ci('put',script,'--to','/tmp/xiri-process-records/archive.sh','--timeout','60')
        ci('run','sh /tmp/xiri-process-records/archive.sh','--shell','sh','--timeout','180')
        archive=directory/'outputs.tar'
        ci('get','/tmp/xiri-process-records-results.tar','--to',archive,'--timeout','180')
        transferred = True
        result.update(archive_observations(archive, cases, desktop['identities']))
        result['status']='observed'
        print(f'{len(result["observations"])} mmap executions observed',flush=True)
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
        print(result['error'], flush=True)
        if logged_in and not transferred:
            # A timed-out transfer or script can still own the console.
            # Interrupt it before queuing shutdown behind that command.
            try:
                ci('serial-send', '\x03', '--no-cr')
                ci('serial-send', '')
                result['interrupted_foreground_for_cleanup'] = True
            except Exception as cleanup_error:
                result['cleanup_interrupt_error'] = str(cleanup_error)
    finally:
        if lab.process:
            if logged_in:
                try:
                    # Synchronize after a possible Ctrl-C before queuing shutdown.
                    ci('run','sync','--shell','sh','--timeout','30')
                    time.sleep(1)
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
