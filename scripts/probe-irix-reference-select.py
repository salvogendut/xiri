#!/usr/bin/env python3
"""Measure guarded select records and delayed TCP readiness on original IRIX."""
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


def archive_observations(archive, cases, checkpoint):
    result = {'observations': []}
    with tarfile.open(archive) as tar:
        for member in tar.getmembers():
            if member.name.startswith('./'): member.name = member.name[2:]
        statuses=dict((n,int(v)) for n,v in re.findall(r'^CASE (\S+) (\d+)$',tar.extractfile('status.txt').read().decode(),re.M))
        if set(statuses) != {c['name'] for c in cases}: raise RuntimeError('incomplete cases')
        for c in cases:
            n=c['name'];data=tar.extractfile(n+'.out').read();err=tar.extractfile(n+'.err').read().decode(errors='backslashreplace')
            result['observations'].append({'name':n,'exit':statuses[n],'stdout_hex':data.hex(),'stderr':err})
            if statuses[n] or len(data)!=512 or err:raise RuntimeError('incomplete fixture: '+n)
        result['server']={'exit':int(tar.extractfile('server.status').read()),'stdout_hex':tar.extractfile('server.out').read().hex(),'stderr':tar.extractfile('server.err').read().decode()}
        expected=b'RDY\n'+b''.join(struct.pack('>II',c['symbols']['CASE'],c['symbols']['MODE']) for c in cases if c['symbols']['SOCKET'])
        if result['server']!={'exit':0,'stdout_hex':expected.hex(),'stderr':''}:raise RuntimeError('reference readiness peer failed')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', choices=['select'], default='select')
    args = parser.parse_args()
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
    output_root = reference / (checkpoint+'-runs')
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
        cases = [c for c in desktop['cases'] if c['reference']]
        upload = directory/'inputs.tar'
        with tarfile.open(upload, 'w') as tar:
            for name in desktop['files']:
                tar.add(fixtures/name, arcname=name)
        ci('put', upload, '--to','/tmp/xiri-tcp-inputs.tar','--timeout','180')
        ci('run','mkdir -p /tmp/xiri-tcp; cd /tmp/xiri-tcp; tar xf /tmp/xiri-tcp-inputs.tar; printf XIRI_SELECT_INPUT >input.txt',
           '--shell','sh','--timeout','120')
        checksums = ci('run','cd /tmp/xiri-tcp; cksum o32-direct-*; cksum o32-indirect-*; '
                       'cksum n32-direct-*; cksum n32-indirect-*; cksum reference-*',
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
        lines = ['#!/bin/sh','set -u','ulimit -c 0','cd /tmp/xiri-tcp',
                 '(./reference-peer >server.out 2>server.err; peer_rc=$?; '
                 'echo "$peer_rc" >server.status.tmp; mv server.status.tmp server.status) & server=$!',
                 'sleep 1', 'grep RDY server.out || exit 2']
        last_echo = len(cases)-1
        for i,c in enumerate(cases):
            name=c['name']
            lines += ['./'+name+' >'+name+'.out 2>'+name+'.err; echo CASE '+name+' "$?"']
            # IRIX sh can discard an old background status after many children.
            # Each peer's own wrapper preserves its actual exit code atomically.
            if i == last_echo:
                lines += ['while test ! -f server.status; do sleep 1; done',
                          'wait "$server" 2>/dev/null || :']
        script=directory/'run.sh';script.write_text('\n'.join(lines)+'\n')
        ci('put',script,'--to','/tmp/xiri-tcp/run.sh','--timeout','30')
        ci('run','sh /tmp/xiri-tcp/run.sh >/tmp/xiri-tcp/status.txt; cd /tmp/xiri-tcp; '
           'tar cf /tmp/xiri-tcp-results.tar .', '--shell','sh','--timeout','300')
        archive=directory/'outputs.tar'
        ci('get','/tmp/xiri-tcp-results.tar','--to',archive,'--timeout','180')
        result.update(archive_observations(archive, cases, checkpoint))
        pin_path=ROOT/f'lab/irix-{checkpoint}/reference.json'
        if pin_path.exists():
            pin=json.loads(pin_path.read_text())
            if (pin['files'] != desktop['files'] or pin['observations'] != result['observations'] or pin['server'] != result['server']):
                raise RuntimeError('reference differs from pin')
            result['status']='passed'
            result['reference_pin_sha256']=probe.sha256(pin_path)
        else: result['status']='observed'
        print(f'{len(cases)} select reference cases {result["status"]}',flush=True)
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
        print(result['error'], flush=True)
        if logged_in:
            # A timed-out transfer or script can still own the console.
            # Interrupt it before queuing shutdown behind that command.
            try:
                ci('serial-send', '\x03', '--no-cr')
                result['interrupted_foreground_for_cleanup'] = True
            except Exception as cleanup_error:
                result['cleanup_interrupt_error'] = str(cleanup_error)
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
