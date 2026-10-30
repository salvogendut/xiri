#!/usr/bin/env python3
"""Cold-boot a disposable Indy disk, run a NetBSD probe, and retain evidence."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import socket
import subprocess
import tempfile
import time
import uuid


ROOT = Path(__file__).resolve().parent.parent
# Allow regression runs against an isolated build without replacing the baseline.
IRIS_BIN_DIR = Path(os.environ.get('XIRI_IRIS_BIN_DIR', ROOT / '.work/target/release')).resolve()
IRIS = IRIS_BIN_DIR / 'iris'
CI = IRIS_BIN_DIR / 'iris-ci'
GDB = ROOT / '.work/netbsd-build/tools/bin/mipseb--netbsd-gdb'
SYMBOLS = ROOT / '.work/netbsd-build/obj/sys/arch/sgimips/compile/XIRI_INDY/netbsd.gdb'
TOOLBOX = ['toolbox', 'run', '-c', 'xiri-iris']


def sha256(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run(args, timeout=30, **kwargs):
    return subprocess.run([str(x) for x in args], cwd=ROOT, timeout=timeout,
                          check=True, **kwargs)


def free_ports(count):
    # Hold all reservations together to ensure distinct ports, then release
    # immediately before launch. Startup checks detect a bind race.
    sockets = [socket.socket() for _ in range(count)]
    try:
        for sock in sockets:
            sock.bind(('127.0.0.1', 0))
        return [sock.getsockname()[1] for sock in sockets]
    finally:
        for sock in sockets:
            sock.close()


class Lab:
    def __init__(self, args, directory, *, extra_iris_args=(), config_text=None,
                 working_directory=ROOT):
        self.args = args
        self.directory = directory
        self.extra_iris_args = list(extra_iris_args)
        self.config_text = config_text
        self.working_directory = working_directory
        self.serial_log = directory / 'serial.log'
        self.socket_path = directory / 'iris.sock'
        self.process = None
        self.debugger = None
        self.serial = None
        self.monitor = None
        self.monitor_buffer = b''
        self.logged_in = False
        self.clean_shutdown = False
        self.offset = 0

    def ci(self, *args):
        return run([CI, '--socket', self.socket_path, *args],
                   capture_output=True, text=True).stdout

    def log(self, message):
        print(message, flush=True)

    def launch(self, command, name):
        # Toolbox's host launcher is not the container process. Record a new
        # session leader inside the container so cleanup reaches its children.
        wrapper = ['setsid', '--wait', 'sh', '-c',
                   'printf "%s\\n" "$$" > "$1"; shift; exec "$@"',
                   'xiri-lab', str(self.directory / f'{name}.pid')]
        command = TOOLBOX + wrapper + command
        (self.directory / f'{name}-command.json').write_text(json.dumps(command, indent=2) + '\n')
        with (self.directory / f'{name}.log').open('wb') as log:
            return subprocess.Popen(command, cwd=self.working_directory, stdin=subprocess.DEVNULL,
                                    stdout=log, stderr=subprocess.STDOUT,
                                    start_new_session=True)

    def terminate(self, process, name):
        pidfile = self.directory / f'{name}.pid'
        if pidfile.exists():
            pid = int(pidfile.read_text().strip())
            if pid <= 1:
                raise RuntimeError('invalid container process group')
            for sig in ['TERM', 'KILL']:
                stopped = subprocess.run(TOOLBOX + ['kill', f'-{sig}', '--', f'-{pid}'],
                                         capture_output=True, timeout=10)
                if stopped.returncode and b'No such process' not in stopped.stderr:
                    raise RuntimeError(f'could not stop {name}: {stopped.stderr.decode()}')
                try:
                    process.wait(timeout=5)
                    return
                except subprocess.TimeoutExpired:
                    pass
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)

    def serial_text(self):
        if not self.serial_log.exists():
            return ''
        return self.serial_log.read_bytes().decode('latin1').replace('\r', '')

    def wait(self, pattern, timeout):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            text = self.serial_text()
            match = re.search(pattern, text[self.offset:])
            if match:
                self.offset += match.end()
                return match
            if self.process.poll() is not None:
                raise RuntimeError(f'emulator exited with {self.process.returncode}')
            # Drain the TCP stream; the independent emulator log is the evidence.
            if self.serial:
                try:
                    if not self.serial.recv(65536):
                        raise RuntimeError('serial connection closed')
                except BlockingIOError:
                    pass
            time.sleep(0.05)
        raise TimeoutError(f'timed out after {timeout}s waiting for {pattern!r}')

    def send(self, text, newline=True):
        if self.args.mode == 'ci':
            self.ci('serial-send', *([] if newline else ['--no-cr']), text)
        else:
            self.serial.sendall((text + ('\r' if newline else '')).encode('ascii'))

    def monitor_reply(self):
        while not re.search(rb'(^|\n)> $', self.monitor_buffer):
            chunk = self.monitor.recv(65536)
            if not chunk:
                raise RuntimeError('monitor connection closed')
            self.monitor_buffer += chunk
        result, self.monitor_buffer = self.monitor_buffer, b''
        return result.decode('latin1')

    def monitor_command(self, command):
        self.monitor.sendall((command + '\n').encode('ascii'))
        return self.monitor_reply()

    def command(self, command, timeout):
        # Match a complete output line, never a marker echoed as typed input.
        marker = 'XIRI_' + uuid.uuid4().hex + '_RC='
        self.offset = len(self.serial_text())
        self.send(command + "; xiri_rc=$?; printf '\\n" + marker + "%s\\n' \"$xiri_rc\"")
        match = self.wait(r'\n' + marker + r'(\d+)\n', timeout)
        self.wait(r'xiri-indy# ', 10)
        return int(match.group(1))

    def start(self, *, boot=True):
        monitor_port, serial_a, serial_b, gdb_port = free_ports(4)
        config = self.config_text
        if config is None:
            config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
        config = re.sub(r'^ci = true$', f'ci = {str(self.args.mode == "ci").lower()}',
                        config, flags=re.M)
        config = config.replace('".work/indy-netbsd/sets.iso"',
                                json.dumps(str(self.directory / 'probe.iso')))
        (self.directory / 'iris.toml').write_text(config)
        command = []
        if self.args.mode == 'ordinary':
            # A host virtual display preserves Newport and ordinary execution.
            command += ['env', '-u', 'WAYLAND_DISPLAY', '-u', 'WAYLAND_SOCKET', 'xvfb-run', '-a',
                        '-s', '-screen 0 1280x1024x24']
        command += [str(IRIS), '--config', str(self.directory / 'iris.toml'),
                    '--nvram', str(self.directory / 'nvram.bin'),
                    '--scsi1', str(self.directory / 'disk.raw'),
                    '--ci-socket', str(self.socket_path),
                    '--monitor-port', str(monitor_port),
                    '--serial-port-a', str(serial_a), '--serial-port-b', str(serial_b),
                    '--serial-log', str(self.serial_log)]
        if self.args.debugger:
            command += ['--gdb-port', str(gdb_port)]
        command += self.extra_iris_args
        self.process = self.launch(command, 'emulator')
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            try:
                self.monitor = socket.create_connection(('127.0.0.1', monitor_port), 1)
                self.monitor.settimeout(10)
                self.monitor_reply()
                break
            except OSError:
                if self.process.poll() is not None:
                    raise RuntimeError('emulator failed during startup; see emulator.log')
                time.sleep(0.1)
        else:
            raise TimeoutError('monitor did not become ready')
        if self.args.mode == 'ci':
            self.ci('status', '--wait-ready', '10')
            self.ci('start')
        else:
            self.serial = socket.create_connection(('127.0.0.1', serial_b), 10)
            self.serial.setblocking(False)
        if not boot:
            return
        self.wait(r'Option\?', 30)
        self.send('5')
        self.wait(r'>> ', 10)
        if self.args.debugger:
            script = (ROOT / 'lab/indy-netbsd/check-boot.gdb').read_text()
            script = script.replace('127.0.0.1:1234', f'127.0.0.1:{gdb_port}')
            script_path = self.directory / 'check-boot.gdb'
            script_path.write_text(script)
            gdb_log = self.directory / 'gdb.log'
            self.debugger = self.launch([str(GDB), '-q', '-nx', '-batch', str(SYMBOLS),
                                         '-x', str(script_path)], 'gdb')
            deadline = time.monotonic() + 20
            while 'XIRI_GDB_READY' not in gdb_log.read_text():
                if self.debugger.poll() is not None:
                    raise RuntimeError('debugger failed to attach; see gdb.log')
                if time.monotonic() >= deadline:
                    raise TimeoutError('debugger did not become ready')
                time.sleep(0.05)
        self.send('boot -f bootp()/netbsd-XIRI_INDY')
        if self.args.debugger:
            if self.debugger.wait(timeout=self.args.boot_timeout) != 0:
                raise RuntimeError('debugger check failed; see gdb.log')
            output = gdb_log.read_text()
            if not all(marker in output for marker in ['XIRI_GDB_MAIN', 'XIRI_GDB_ROOTCONF']):
                raise RuntimeError('debugger did not reach both kernel breakpoints')
            self.monitor_command('start')
            self.log('Debugger reached both kernel breakpoints; normal execution resumed')
        self.wait(r'login: ', self.args.boot_timeout)
        self.log('Cold boot reached login')
        self.send('root')
        self.wait(r'xiri-indy# ', 15)
        self.logged_in = True

    def close(self):
        if self.debugger and self.debugger.poll() is None:
            self.terminate(self.debugger, 'gdb')
        if not self.process:
            return
        if self.process.poll() is None and self.logged_in:
            try:
                self.monitor_command('start')
                self.offset = len(self.serial_text())
                self.send('\x03', newline=False)
                self.wait(r'xiri-indy# ', 10)
                self.send('shutdown -h now')
                self.wait(r'unmounting done', 60)
                self.wait(r'Option\?', 15)
                self.clean_shutdown = True
                self.log('Guest halted cleanly')
            except (OSError, TimeoutError, RuntimeError, subprocess.SubprocessError) as error:
                self.log(f'Guest cleanup failed: {error}')
        if self.process.poll() is None:
            try:
                if self.args.mode == 'ci':
                    self.ci('quit')
                else:
                    self.monitor_command('machine-stop')
                    self.terminate(self.process, 'emulator')
                self.process.wait(timeout=10)
            except (OSError, TimeoutError, RuntimeError, subprocess.SubprocessError):
                # Only this run's disposable disk can be left unclean.
                self.terminate(self.process, 'emulator')
        else:
            # A failed launcher can exit before its container children do.
            self.terminate(self.process, 'emulator')
        for sock in (self.serial, self.monitor):
            if sock:
                sock.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--debugger', action='store_true',
                        help='check two kernel breakpoints before continuing boot')
    parser.add_argument('--case', choices=['smoke', 'exit', 'timeout'], default='smoke',
                        help='exit and timeout deliberately fail to validate the harness')
    parser.add_argument('--boot-timeout', type=int, default=300)
    parser.add_argument('--probe-timeout', type=int, default=30)
    args = parser.parse_args()
    if args.boot_timeout < 1 or args.probe_timeout < 1:
        parser.error('timeouts must be positive')

    checkpoint = ROOT / '.work/indy-netbsd-kernel'
    kernel = ROOT / '.work/netbsd-11.0/tftp/netbsd-XIRI_INDY'
    for path in [IRIS, CI, checkpoint / 'disk.raw', checkpoint / 'nvram.bin', kernel]:
        if not path.is_file():
            parser.error(f'missing required artifact: {path}')
    if args.debugger and not all(path.is_file() for path in [GDB, SYMBOLS]):
        parser.error('build cross-GDB and the symbol-bearing kernel first')
    output_root = ROOT / '.work/netbsd-probes'
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=f'{args.mode}-{args.case}-', dir=output_root))
    lab = Lab(args, directory)
    result = {'mode': args.mode, 'case': args.case, 'status': 'error',
              'debugger': args.debugger,
              'clean_shutdown': False, 'guest_exit_status': None,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    started = time.monotonic()
    host_exit = 1
    lab.log(f'Results: {directory.relative_to(ROOT)}')
    try:
        # Each launch starts from the same clean, stopped disk; never mutate it.
        for name in ['disk.raw', 'nvram.bin']:
            run(['cp', '--reflink=auto', '--sparse=always', checkpoint / name,
                 directory / name], timeout=120)
        result['kernel_sha256'] = sha256(kernel)
        result['nvram_sha256'] = sha256(directory / 'nvram.bin')
        result['emulator_sha256'] = sha256(IRIS)
        result['harness_sha256'] = sha256(Path(__file__).resolve())
        media = directory / 'media'
        media.mkdir()
        run(['cp', ROOT / 'lab/indy-netbsd/probe.sh', media / 'probe.sh'])
        result['probe_sha256'] = sha256(media / 'probe.sh')
        payload = bytes(range(256)) * 512
        (media / 'payload.bin').write_bytes(payload)
        result['payload_sha256'] = hashlib.sha256(payload).hexdigest()
        run(['genisoimage', '-quiet', '-R', '-J', '-V', 'XIRI_PROBE',
             '-o', directory / 'probe.iso', media])
        lab.start()
        result['boot_seconds'] = round(time.monotonic() - started, 3)
        probe_started = time.monotonic()
        if args.case == 'exit':
            command = "printf 'XIRI_EXPECTED_FAILURE\\n'; (exit 23)"
        elif args.case == 'timeout':
            command = 'sleep 3600'
        else:
            ident = re.search(r'^ident "([^"]+)"',
                              (ROOT / 'lab/netbsd-11.0/XIRI_INDY').read_text(), re.M).group(1)
            if lab.command('mkdir -p /cdrom; mount -t cd9660 -o ro /dev/cd0a /cdrom', 15):
                raise RuntimeError('could not mount probe CD')
            command = shlex.join(['sh', '/cdrom/probe.sh', ident,
                                  result['kernel_sha256'], result['payload_sha256']])
        rc = lab.command(command, args.probe_timeout)
        result['probe_seconds'] = round(time.monotonic() - probe_started, 3)
        result['guest_exit_status'] = rc
        result['status'] = 'passed' if rc == 0 else 'guest_failed'
        if args.case == 'smoke' and rc == 0 and '\nXIRI_PROBE_OK\n' not in lab.serial_text():
            raise RuntimeError('guest returned zero without the expected probe output')
        host_exit = min(rc, 125)
        lab.log(f'Probe status: {result["status"]}; guest exit {rc}')
    except TimeoutError as error:
        result.update(status='timeout', error=str(error))
        host_exit = 124
        lab.log(str(error))
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        result.update(status='error', error=str(error))
        lab.log(str(error))
    finally:
        try:
            lab.close()
        except (OSError, RuntimeError, subprocess.SubprocessError) as error:
            result.update(status='error', cleanup_error=str(error))
            host_exit = 1
        result['clean_shutdown'] = lab.clean_shutdown
        result['elapsed_seconds'] = round(time.monotonic() - started, 3)
        if host_exit == 0 and not lab.clean_shutdown:
            result.update(status='error', error='guest did not shut down cleanly')
            host_exit = 1
        result['host_exit_status'] = host_exit
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return host_exit


if __name__ == '__main__':
    raise SystemExit(main())
