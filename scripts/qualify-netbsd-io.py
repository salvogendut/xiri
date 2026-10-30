#!/usr/bin/env python3
"""Exercise disk persistence and local TCP/NFS transfers on disposable Indy disks."""

import argparse
import functools
import http.server
import importlib.util
import json
from pathlib import Path
import random
import shlex
import socketserver
import tempfile
import threading
import time


ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('netbsd_probe', ROOT / 'scripts/probe-netbsd.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class Services:
    def __init__(self, directory):
        self.directory = directory
        self.http_log = (directory / 'http.log').open('a', buffering=1)
        self.upload_done = threading.Event()
        self.upload_error = None
        owner = self

        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self, fmt, *args):
                owner.http_log.write(fmt % args + '\n')

        class Upload(socketserver.BaseRequestHandler):
            def handle(self):
                try:
                    self.request.settimeout(30)
                    with (directory / 'tcp-upload.bin').open('wb') as stream:
                        while chunk := self.request.recv(65536):
                            stream.write(chunk)
                    self.request.sendall(b'XIRI_UPLOAD_RECEIVED\n')
                except OSError as error:
                    owner.upload_error = str(error)
                finally:
                    owner.upload_done.set()

        handler = functools.partial(Handler, directory=directory / 'share')
        self.http = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        self.upload = socketserver.ThreadingTCPServer(('127.0.0.1', 0), Upload)
        self.upload.daemon_threads = True
        self.threads = []
        for server in [self.http, self.upload]:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.threads.append(thread)

    def close(self):
        for server in [self.http, self.upload]:
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join(timeout=5)
        self.http_log.close()


def guest(lab, result, label, command, timeout, marker=None):
    lab.log(label)
    before = len(lab.serial_text())
    started = time.monotonic()
    rc = lab.command(command, timeout)
    result.setdefault('checks', []).append({
        'name': label, 'guest_exit_status': rc,
        'seconds': round(time.monotonic() - started, 3),
    })
    if rc:
        raise RuntimeError(f'{label}: guest exited {rc}')
    if marker and '\n' + marker + '\n' not in lab.serial_text()[before:]:
        raise RuntimeError(f'{label}: missing expected output {marker}')


def diagnostics(lab, label):
    with (lab.directory / f'{label}-monitor.log').open('w') as log:
        for command in ['status', 'net status tcp', 'seeq status', 'pdma status']:
            log.write(command + '\n' + lab.monitor_command(command) + '\n')


def network(lab, services, hashes, result, args):
    gateway = '192.168.231.1'
    guest(lab, result, 'network counters before', 'netstat -i -d; netstat -s -p tcp', 15)
    diagnostics(lab, 'before-network')
    guest(lab, result, 'NFSv3 UDP mount',
          f'mkdir -p /nfs; mount_nfs -3 -u -U -s -t 10 -x 3 {gateway}:/ /nfs', 30)
    # Soft mounts keep an unavailable test share from preventing cleanup.
    guest(lab, result, 'NFS download and checksum',
          'cp /nfs/payload0.bin /root/nfs-download.bin && '
          f'test "$(sha256 -q /root/nfs-download.bin)" = {hashes[0]}', args.io_timeout)
    guest(lab, result, 'NFS upload and unmount',
          'cp /root/nfs-download.bin /nfs/nfs-upload.bin && sync && umount /nfs', args.io_timeout)
    upload_hash = probe.sha256(services.directory / 'share/nfs-upload.bin')
    result['nfs_upload_sha256'] = upload_hash
    if upload_hash != hashes[0]:
        raise RuntimeError('NFS upload checksum mismatch on host')
    for index in range(args.rounds):
        source = index % 2
        url = f'http://{gateway}:{services.http.server_port}/payload{source}.bin'
        guest(lab, result, f'HTTP download/checksum {index + 1}',
              f'ftp -q 30 -o /root/http-download.bin {url} && '
              f'test "$(sha256 -q /root/http-download.bin)" = {hashes[source]}', args.io_timeout)
    guest(lab, result, 'TCP upload',
          f'nc -N -w 30 {gateway} {services.upload.server_address[1]} < /root/http-download.bin',
          args.io_timeout, 'XIRI_UPLOAD_RECEIVED')
    if not services.upload_done.wait(timeout=5) or services.upload_error:
        raise RuntimeError(f'TCP receiver failed: {services.upload_error}')
    upload_hash = probe.sha256(services.directory / 'tcp-upload.bin')
    result['tcp_upload_sha256'] = upload_hash
    if upload_hash != hashes[(args.rounds - 1) % 2]:
        raise RuntimeError('TCP upload checksum mismatch on host')
    guest(lab, result, 'network counters after',
          'netstat -i -d; netstat -s -p tcp; nfsstat -c', 15)
    diagnostics(lab, 'after-network')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--case', choices=['all', 'disk', 'network'], default='all')
    parser.add_argument('--size-mib', type=int, default=16, help='size of each of two distinct payloads')
    parser.add_argument('--rounds', type=int, default=3)
    parser.add_argument('--io-timeout', type=int, default=300, help='host deadline for each I/O operation')
    args = parser.parse_args()
    if not 1 <= args.size_mib <= 256 or not 1 <= args.rounds <= 20 or args.io_timeout < 1:
        parser.error('size must be 1–256 MiB, rounds 1–20, and timeout positive')
    args.debugger = False
    args.boot_timeout = 300
    output = ROOT / '.work/netbsd-io'
    output.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=f'{args.mode}-{args.case}-', dir=output))
    result = {'status': 'error', 'mode': args.mode, 'case': args.case,
              'size_mib': args.size_mib, 'rounds': args.rounds,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'clean_shutdowns': []}
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    lab = services = None
    started = time.monotonic()
    exit_code = 1
    try:
        checkpoint = ROOT / '.work/indy-netbsd-kernel'
        for name in ['disk.raw', 'nvram.bin']:
            probe.run(['cp', '--reflink=auto', '--sparse=always', checkpoint / name,
                       directory / name], timeout=120)
        result['checkpoint_disk_sha256'] = probe.sha256(directory / 'disk.raw')
        result['checkpoint_nvram_sha256'] = probe.sha256(directory / 'nvram.bin')
        result['emulator_sha256'] = probe.sha256(probe.IRIS)
        result['kernel_sha256'] = probe.sha256(ROOT / '.work/netbsd-11.0/tftp/netbsd-XIRI_INDY')
        result['harness_sha256'] = probe.sha256(Path(__file__))
        result['boot_harness_sha256'] = probe.sha256(ROOT / 'scripts/probe-netbsd.py')
        result['disk_probe_sha256'] = probe.sha256(ROOT / 'lab/indy-netbsd/disk-probe.sh')
        media = directory / 'share'
        media.mkdir()
        hashes = []
        for index in range(2):
            path = media / f'payload{index}.bin'
            generator = random.Random(20261030 + index)
            with path.open('wb') as stream:
                for _ in range(args.size_mib):
                    stream.write(generator.randbytes(1024 * 1024))
            hashes.append(probe.sha256(path))
            path.with_suffix('.bin.sha256').write_text(hashes[-1] + '\n')
        result['payload_sha256'] = hashes
        probe.run(['cp', ROOT / 'lab/indy-netbsd/disk-probe.sh', media / 'disk-probe.sh'])
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-V', 'XIRI_IO',
                   '-o', directory / 'probe.iso', media])
        services = Services(directory) if args.case != 'disk' else None
        phases = ['write', 'verify'] if args.case != 'network' else ['network']
        for phase in phases:
            phase_dir = directory / phase
            phase_dir.mkdir()
            for name in ['disk.raw', 'nvram.bin', 'probe.iso']:
                (phase_dir / name).symlink_to(directory / name)
            lab = probe.Lab(args, phase_dir, extra_iris_args=['--nfs-dir', str(media)] if services else [])
            lab.start()
            guest(lab, result, f'{phase}: kernel and baseline',
                  f'test "$(sha256 -q /netbsd)" = {result["kernel_sha256"]} && '
                  'test "$(cksum /root/xiri-probe)" = "3540535338 33 /root/xiri-probe"', 30)
            if phase != 'network':
                guest(lab, result, f'{phase}: mount CD',
                      'mkdir -p /cdrom; mount -t cd9660 -o ro /dev/cd0a /cdrom', 15)
                guest(lab, result, f'disk {phase}',
                      shlex.join(['sh', '/cdrom/disk-probe.sh', phase, str(args.rounds)]),
                      args.io_timeout * args.rounds if phase == 'write' else args.io_timeout,
                      'XIRI_DISK_WRITE_OK' if phase == 'write' else 'XIRI_DISK_COLD_READ_OK')
                if phase == 'verify' and '/dev/rsd0a: file system is clean; not checking' not in lab.serial_text():
                    raise RuntimeError('cold boot did not report a clean root filesystem')
            if services and phase in ['verify', 'network']:
                network(lab, services, hashes, result, args)
            lab.close()
            result['clean_shutdowns'].append(lab.clean_shutdown)
            if not lab.clean_shutdown:
                raise RuntimeError(f'{phase}: guest did not shut down cleanly')
            lab = None
        result['status'] = 'passed'
        exit_code = 0
    except (OSError, RuntimeError, TimeoutError, probe.subprocess.SubprocessError) as error:
        result['error'] = str(error)
        print(str(error), flush=True)
        if isinstance(error, TimeoutError):
            result['status'] = 'timeout'
            exit_code = 124
        if lab and lab.logged_in:
            try:
                diagnostics(lab, 'failure')
                lab.send('\x03', newline=False)
                lab.command('netstat -i -d; netstat -s -p tcp; vmstat -i; arp -a', 20)
            except Exception as diagnostic_error:
                result['diagnostic_error'] = str(diagnostic_error)
    finally:
        if lab:
            try:
                lab.close()
            except Exception as cleanup_error:
                result['cleanup_error'] = str(cleanup_error)
            result['clean_shutdowns'].append(lab.clean_shutdown)
        if services:
            services.close()
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        result['host_exit_status'] = exit_code
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
