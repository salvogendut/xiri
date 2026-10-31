#!/usr/bin/env python3
"""Measure original o32/n32 TCP fixtures on a disposable IRIX reference."""
import argparse
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


def archive_observations(archive, cases, checkpoint):
    """Decode saved evidence, including each peer's own durable exit status."""
    result = {'observations': []}
    with tarfile.open(archive) as tar:
        # Archive the directory to stay below IRIX's small ARG_MAX.
        for member in tar.getmembers():
            if member.name.startswith('./'): member.name = member.name[2:]
        statuses=dict((n,int(v)) for n,v in re.findall(r'^CASE (\S+) (\d+)$',tar.extractfile('status.txt').read().decode(),re.M))
        if set(statuses) != {c['name'] for c in cases}: raise RuntimeError('incomplete cases')
        for c in cases:
            name=c['name']
            data=tar.extractfile(name+'.out').read()
            observation={'name':name,'exit':statuses[name], 'stdout_hex':data.hex(),
                         'stderr':tar.extractfile(name+'.err').read().decode(errors='backslashreplace')}
            result['observations'].append(observation)
            # The supplied IRIX traps delay-slot syscalls with SIGSYS (12).
            # Keep this observed difference explicit rather than calling it success.
            delayed = 'DELAY' in c['symbols']
            if (statuses[name] != (140 if delayed else 0) or
                    len(data) != (0 if delayed else c.get('record_bytes',32))):
                raise RuntimeError('incomplete fixture: '+name)
        result['server']={'exit':int(tar.extractfile('server.status').read()),'stdout':tar.extractfile('server.out').read().decode(),
                          'stderr':tar.extractfile('server.err').read().decode()}
        if result['server'] != {'exit':0,'stdout':'RDY\n','stderr':''}: raise RuntimeError('reference peer failed')
        if checkpoint in ['sockname','peername','xconnect']:
            result['peer']={'exit':int(tar.extractfile('peer.status').read()), 'stdout':tar.extractfile('peer.out').read().decode(),
                            'stderr':tar.extractfile('peer.err').read().decode()}
            if result['peer'] != {'exit':0,'stdout':'RDY\n','stderr':''}: raise RuntimeError('reference address peer failed')
        if checkpoint in ['peername','xconnect']:
            result['remote']={'exit':int(tar.extractfile('remote.status').read()),
                              'stdout':tar.extractfile('remote.out').read().decode(),
                              'stderr':tar.extractfile('remote.err').read().decode()}
            if result['remote'] != {'exit':0,'stdout':'RDY\n','stderr':''}: raise RuntimeError('reference server-address peer failed')
        if checkpoint == 'xconnect':
            result['message']={'exit':int(tar.extractfile('message.status').read()),
                               'stdout_hex':tar.extractfile('message.out').read().hex(),
                               'stderr':tar.extractfile('message.err').read().decode()}
            if result['message']['exit'] or result['message']['stderr']:raise RuntimeError('reference message peer failed')
            model = module('xconnect', 'irix-xconnect-records.py')
            result['message_records'] = model.message_records(bytes.fromhex(result['message']['stdout_hex']))
            expected = [model.expected_message(c, True) for c in cases if 'MESSAGE_CONNECTED' in c['symbols']]
            if result['message_records'] != expected:raise RuntimeError('reference peer received unexpected bytes')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkpoint', choices=['tcp','sockname','peername','xconnect'], default='tcp')
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
    if checkpoint == 'xconnect':
        result['xconnect_decoder_sha256'] = probe.sha256(ROOT/'scripts/irix-xconnect-records.py')
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
        ci('put', upload, '--to','/tmp/xiri-tcp-inputs.tar','--timeout','60')
        ci('run','mkdir -p /tmp/xiri-tcp; cd /tmp/xiri-tcp; tar xf /tmp/xiri-tcp-inputs.tar',
           '--shell','sh','--timeout','30')
        checksums = ci('run','cd /tmp/xiri-tcp; cksum o32-direct-*; cksum o32-indirect-*; '
                       'cksum n32-direct-*; cksum n32-indirect-*; cksum reference-*',
                       '--shell','sh','--timeout','60')
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
                 '(./reference-server >server.out 2>server.err; peer_rc=$?; '
                 'echo "$peer_rc" >server.status.tmp; mv server.status.tmp server.status) & server=$!',
                 'sleep 1', 'grep RDY server.out || exit 2']
        if checkpoint in ['sockname','peername','xconnect']:
            lines += ['(./reference-peer >peer.out 2>peer.err; peer_rc=$?; '
                      'echo "$peer_rc" >peer.status.tmp; mv peer.status.tmp peer.status) & peer=$!',
                      'sleep 1', 'grep RDY peer.out || exit 2']
        if checkpoint in ['peername','xconnect']:
            lines += ['(./reference-remote >remote.out 2>remote.err; peer_rc=$?; '
                      'echo "$peer_rc" >remote.status.tmp; mv remote.status.tmp remote.status) & remote=$!',
                      'sleep 1','grep RDY remote.out || exit 2']
        if checkpoint == 'xconnect':
            lines += ['(./reference-message >message.out 2>message.err; peer_rc=$?; '
                      'echo "$peer_rc" >message.status.tmp; mv message.status.tmp message.status) & message=$!',
                      'sleep 1','grep RDY message.out || exit 2']
        last_echo = max(i for i,c in enumerate(cases) if c['symbols']['KIND']==4)
        for i,c in enumerate(cases):
            name=c['name']
            lines += ['./'+name+' >'+name+'.out 2>'+name+'.err; echo CASE '+name+' "$?"']
            # IRIX sh can discard an old background status after many children.
            # Each peer's own wrapper preserves its actual exit code atomically.
            if i == last_echo:
                lines += ['while test ! -f server.status; do sleep 1; done',
                          'wait "$server" 2>/dev/null || :']
        if checkpoint in ['sockname','peername','xconnect']:
            lines += ['while test ! -f peer.status; do sleep 1; done',
                      'wait "$peer" 2>/dev/null || :']
        if checkpoint in ['peername','xconnect']:
            lines += ['while test ! -f remote.status; do sleep 1; done',
                      'wait "$remote" 2>/dev/null || :']
        if checkpoint == 'xconnect':
            lines += ['while test ! -f message.status; do sleep 1; done',
                      'wait "$message" 2>/dev/null || :']
        script=directory/'run.sh';script.write_text('\n'.join(lines)+'\n')
        ci('put',script,'--to','/tmp/xiri-tcp/run.sh','--timeout','30')
        ci('run','sh /tmp/xiri-tcp/run.sh >/tmp/xiri-tcp/status.txt; cd /tmp/xiri-tcp; '
           'tar cf /tmp/xiri-tcp-results.tar .', '--shell','sh','--timeout','360' if checkpoint=='xconnect' else '180')
        archive=directory/'outputs.tar'
        ci('get','/tmp/xiri-tcp-results.tar','--to',archive,'--timeout','60')
        result.update(archive_observations(archive, cases, checkpoint))
        pin_path=ROOT/f'lab/irix-{checkpoint}/reference.json'
        if pin_path.exists():
            pin=json.loads(pin_path.read_text())
            if (pin['files'] != desktop['files'] or pin['observations'] != result['observations'] or
                    (checkpoint == 'xconnect' and pin['message'] != result['message'])):
                raise RuntimeError('reference differs from pin')
            result['status']='passed'
            result['reference_pin_sha256']=probe.sha256(pin_path)
        else: result['status']='observed'
        print(f'{len(cases)} TCP reference cases {result["status"]}',flush=True)
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
