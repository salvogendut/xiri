#!/usr/bin/env python3
"""Qualify quiescent NetBSD snapshots on disposable COW disks, then cold-boot."""

import argparse
import functools
import http.server
import importlib.util
import json
from pathlib import Path
import random
import re
import tempfile
import threading
import time
import tomllib


ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('netbsd_probe', ROOT / 'scripts/probe-netbsd.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
GUEST = '/root/xiri-snapshot'


class Http:
    def __init__(self, directory):
        self.log = (directory / 'http.log').open('a', buffering=1)
        owner = self

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, fmt, *args):
                owner.log.write(fmt % args + '\n')

        self.server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0), functools.partial(Handler, directory=directory / 'share'))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.log.close()


def guest(lab, result, name, command, timeout=60):
    print(name, flush=True)
    started = time.monotonic()
    check = {'name': name, 'guest_exit_status': None}
    result['checks'].append(check)
    before = len(lab.serial_text())
    try:
        check['guest_exit_status'] = lab.command(command, timeout)
    finally:
        check['seconds'] = round(time.monotonic() - started, 3)
    if check['guest_exit_status']:
        raise RuntimeError(f'{name}: guest exited {check["guest_exit_status"]}')
    return lab.serial_text()[before:]


def diagnostic(lab, name):
    with (lab.directory / f'{name}-monitor.log').open('w') as stream:
        for command in ['status', 'regs', 'cop0', 'phys map', 'serial status',
                        'cow status', 'ioc ticks', 'pit status',
                        'rtc status', 'net status tcp', 'seeq status', 'pdma status']:
            stream.write(command + '\n' + lab.monitor_command(command) + '\n')


def snapshot(lab, result, action):
    print(f'Snapshot {action}', flush=True)
    started = time.monotonic()
    if lab.args.mode == 'ci':
        output = lab.ci(action, *([] if action == 'rollback' else ['checkpoint']))
    else:
        command = 'save' if action == 'save' else 'load'
        output = lab.monitor_command(f'{command} checkpoint')
        expected = 'Saving' if action == 'save' else 'Loading'
        if f"{expected} snapshot 'checkpoint'" not in output or 'Error:' in output:
            raise RuntimeError(f'{action} failed: {output}')
    result['snapshots'].append({'action': action, 'phase': lab.directory.name,
                               'seconds': round(time.monotonic() - started, 3),
                               'response': output.strip()})
    # A restored shell is already waiting for input; no new prompt is guaranteed.
    lab.logged_in = True


def network(lab, result, directory, http, digest, label):
    url = f'http://192.168.231.1:{http.server.server_port}/payload0.bin'
    guest(lab, result, f'{label}: fresh HTTP transfer',
          f'ftp -q 15 -o {GUEST}/http.bin {url} && '
          f'test "$(sha256 -q {GUEST}/http.bin)" = {digest}')
    guest(lab, result, f'{label}: fresh NFS transfers',
          f'mkdir -p /nfs && mount_nfs -3 -u -U -s -t 10 -x 3 '
          f'-r {lab.args.nfs_size} -w {lab.args.nfs_size} 192.168.231.1:/ /nfs && '
          f'cp /nfs/payload0.bin {GUEST}/nfs.bin && '
          f'test "$(sha256 -q {GUEST}/nfs.bin)" = {digest} && '
          f'cp {GUEST}/nfs.bin /nfs/{label}.bin && sync && umount /nfs')
    if probe.sha256(directory / 'share' / f'{label}.bin') != digest:
        raise RuntimeError(f'{label}: NFS host checksum mismatch')


def verify(lab, result, digest, label):
    guest(lab, result, f'{label}: restored memory, files, and pending timer',
          'test "$XIRI_MEMORY" = before && test "$$" = "$XIRI_SHELL_PID" && '
          f'test -f {GUEST}/deleted && test ! -e {GUEST}/created && '
          f'test ! -e {GUEST}/timer && test "$(sha256 -q {GUEST}/saved.bin)" = {digest}')
    guest(lab, result, f'{label}: sleeping process resumes',
          f'xiri_wait=0; while test ! -f {GUEST}/timer && test "$xiri_wait" -lt 20; '
          'do sleep 1; xiri_wait=$((xiri_wait + 1)); done; '
          f'test "$(cat {GUEST}/timer)" = fired', 30)
    guest(lab, result, f'{label}: clock advances',
          'xiri_t0=$(date +%s); sleep 2; xiri_t1=$(date +%s); '
          'xiri_delta=$((xiri_t1 - xiri_t0)); printf "XIRI_CLOCK_DELTA %s\\n" "$xiri_delta"; '
          'test "$xiri_delta" -ge 1 && test "$xiri_delta" -le 15', 20)


def mutate(lab, result, digest, label):
    guest(lab, result, f'{label}: mutate memory and disk',
          f'XIRI_MEMORY=after; cp /cdrom/payload1.bin {GUEST}/saved.bin && '
          f'rm -f {GUEST}/deleted && printf created > {GUEST}/created && sync && '
          f'test "$(sha256 -q {GUEST}/saved.bin)" = {digest}')
    guest(lab, result, f'{label}: timer finishes before rewind',
          f'xiri_wait=0; while test ! -f {GUEST}/timer && test "$xiri_wait" -lt 20; '
          'do sleep 1; xiri_wait=$((xiri_wait + 1)); done; '
          f'test -f {GUEST}/timer', 30)


def new_lab(args, directory, phase, overlay=True):
    phase_dir = directory / phase
    phase_dir.mkdir()
    # A separate base for the final commit preserves the saved snapshot bundle.
    if phase == 'fresh':
        probe.run(['cp', '--reflink=auto', '--sparse=always', directory / 'disk.raw',
                   phase_dir / 'disk.raw'], timeout=120)
    else:
        disk = directory / ('fresh/disk.raw' if phase == 'cold' else 'disk.raw')
        (phase_dir / 'disk.raw').symlink_to(disk)
    for name in ['nvram.bin', 'probe.iso']:
        (phase_dir / name).symlink_to(directory / name)
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    if overlay:
        config = config.replace('overlay = false', 'overlay = true')
    return probe.Lab(args, phase_dir, config_text=config, working_directory=directory,
                     extra_iris_args=['--tftp-dir', str(ROOT / '.work/netbsd-11.0/tftp'),
                                      '--nfs-dir', str(directory / 'share')])


def close(lab, result):
    lab.close()
    result['clean_shutdowns'].append(lab.clean_shutdown)
    if lab.args.mode == 'ci' and (lab.directory / 'emulator.pid').is_file():
        pid = int((lab.directory / 'emulator.pid').read_text())
        if pid <= 1:
            raise RuntimeError('invalid emulator PID for overlay retention')
        # CI overlays are in the container's /tmp. Move only this stopped run's
        # files into its evidence directory, including the persisted dirty set.
        for suffix in ['.overlay', '.overlay.dirty']:
            source = f'/tmp/iris-ci-{pid}-scsi1{suffix}'
            probe.run(probe.TOOLBOX + ['sh', '-c',
                      'if test -f "$1"; then mv -- "$1" "$2"; fi', 'xiri-overlay',
                      source, str(lab.directory / f'live{suffix}')])
    if not lab.clean_shutdown:
        raise RuntimeError(f'{lab.directory.name}: guest did not shut down cleanly')


def halt_and_commit(lab, result):
    lab.offset = len(lab.serial_text())
    lab.send('shutdown -h now')
    lab.wait(r'unmounting done', 60)
    lab.wait(r'Option\?', 15)
    lab.clean_shutdown = True
    lab.logged_in = False
    output = lab.monitor_command('cow commit 1')
    result['cow_commit'] = output
    if not re.search(r'SCSI 1: committed [1-9][0-9]* sectors', output):
        raise RuntimeError(f'could not commit the stopped disposable disk: {output}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--rounds', type=int, default=2)
    parser.add_argument('--nfs-size', type=int, choices=[1024, 8192], default=1024,
                        help='NFS request size; 8192 reproduces the fragmented-transfer investigation')
    args = parser.parse_args()
    if not 1 <= args.rounds <= 10:
        parser.error('rounds must be 1–10')
    args.debugger = False
    args.boot_timeout = 300
    output = ROOT / '.work/netbsd-snapshots'
    output.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=f'{args.mode}-', dir=output))
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    result = {'status': 'error', 'mode': args.mode, 'rounds': args.rounds,
              'nfs_size': args.nfs_size,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'checks': [], 'snapshots': [], 'clean_shutdowns': []}
    lab = http = None
    host_exit = 1
    started = time.monotonic()
    try:
        checkpoint = ROOT / '.work/indy-netbsd-kernel'
        for name in ['disk.raw', 'nvram.bin']:
            probe.run(['cp', '--reflink=auto', '--sparse=always', checkpoint / name,
                       directory / name], timeout=120)
            result[f'checkpoint_{name}_sha256'] = probe.sha256(directory / name)
        for name, path in [('emulator', probe.IRIS), ('harness', Path(__file__)),
                           ('boot_harness', ROOT / 'scripts/probe-netbsd.py'),
                           ('kernel', ROOT / '.work/netbsd-11.0/tftp/netbsd-XIRI_INDY')]:
            result[f'{name}_sha256'] = probe.sha256(path)
        media = directory / 'share'
        media.mkdir()
        hashes = []
        for index in range(2):
            path = media / f'payload{index}.bin'
            path.write_bytes(random.Random(20261031 + index).randbytes(4 * 1024 * 1024))
            hashes.append(probe.sha256(path))
        result['payload_sha256'] = hashes
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-V', 'XIRI_SNAPSHOT',
                   '-o', directory / 'probe.iso', media])
        http = Http(directory)
        lab = new_lab(args, directory, 'initial')
        lab.start()
        guest(lab, result, 'kernel and baseline',
              f'test "$(sha256 -q /netbsd)" = {result["kernel_sha256"]} && '
              'test "$(cksum /root/xiri-probe)" = "3540535338 33 /root/xiri-probe"')
        guest(lab, result, 'prepare snapshot files',
              'mkdir -p /cdrom && mount -t cd9660 -o ro /dev/cd0a /cdrom && '
              f'mkdir {GUEST} && cp /cdrom/payload0.bin {GUEST}/saved.bin && '
              f'printf original > {GUEST}/deleted && sync')
        network(lab, result, directory, http, hashes[0], 'baseline')
        diagnostic(lab, 'before-save')
        guest(lab, result, 'prepare memory and sleeping process',
              'XIRI_MEMORY=before; XIRI_SHELL_PID=$$; '
              f'{{ (sleep 12; printf fired > {GUEST}/timer) >/dev/null 2>&1 & }}')
        snapshot(lab, result, 'save')
        saved = directory / 'saves/checkpoint'
        result['manifest'] = tomllib.loads((saved / 'snapshot.toml').read_text())
        if not (saved / 'scsi1.overlay').is_file() or not (saved / 'cow.toml').is_file():
            raise RuntimeError('snapshot did not capture the SCSI disk overlay')
        for action in ['restore'] + (['rollback'] if args.mode == 'ci' else []):
            for index in range(args.rounds):
                label = f'{action}-{index + 1}'
                mutate(lab, result, hashes[1], label)
                snapshot(lab, result, action)
                verify(lab, result, hashes[0], label)
                network(lab, result, directory, http, hashes[0], label)
                diagnostic(lab, label)
        close(lab, result)
        lab = None
        if probe.sha256(directory / 'disk.raw') != result['checkpoint_disk.raw_sha256']:
            raise RuntimeError('COW modified the base disk before commit')
        lab = new_lab(args, directory, 'fresh')
        lab.start(boot=False)
        snapshot(lab, result, 'restore')
        verify(lab, result, hashes[0], 'fresh')
        network(lab, result, directory, http, hashes[0], 'fresh')
        guest(lab, result, 'write after fresh-process restore',
              f'printf persisted > {GUEST}/final && sync')
        diagnostic(lab, 'before-commit')
        halt_and_commit(lab, result)
        close(lab, result)
        lab = None
        result['committed_disk_sha256'] = probe.sha256(directory / 'fresh/disk.raw')
        lab = new_lab(args, directory, 'cold', overlay=False)
        lab.start()
        guest(lab, result, 'cold-boot disk integrity',
              f'test "$(sha256 -q {GUEST}/saved.bin)" = {hashes[0]} && '
              f'test -f {GUEST}/deleted && test ! -e {GUEST}/created && '
              f'test "$(cat {GUEST}/final)" = persisted && '
              f'test "$(sha256 -q /netbsd)" = {result["kernel_sha256"]}')
        if '/dev/rsd0a: file system is clean; not checking' not in lab.serial_text():
            raise RuntimeError('cold boot did not report a clean root filesystem')
        close(lab, result)
        lab = None
        if probe.sha256(directory / 'disk.raw') != result['checkpoint_disk.raw_sha256']:
            raise RuntimeError('snapshot base changed during qualification')
        result['status'] = 'passed'
        host_exit = 0
    except (OSError, RuntimeError, TimeoutError, probe.subprocess.SubprocessError) as error:
        result['error'] = str(error)
        print(str(error), flush=True)
        if isinstance(error, TimeoutError):
            result['status'] = 'timeout'
            host_exit = 124
        if lab and lab.monitor:
            try:
                diagnostic(lab, 'failure')
            except Exception as diagnostic_error:
                result['diagnostic_error'] = str(diagnostic_error)
    finally:
        if lab:
            try:
                close(lab, result)
            except Exception as cleanup_error:
                result['cleanup_error'] = str(cleanup_error)
        if http:
            http.close()
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        result['host_exit_status'] = host_exit
        (directory / 'result.json').write_text(json.dumps(result, indent=2, default=str) + '\n')
    return host_exit


if __name__ == '__main__':
    raise SystemExit(main())
