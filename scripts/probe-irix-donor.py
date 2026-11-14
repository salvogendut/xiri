#!/usr/bin/env python3
"""Cold-boot a disposable Indy donor CHD copy, capture 4Dwm, and halt IRIX."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import socket
import subprocess
import tempfile
import time

from xiri_lab.donor import sha256


def shutdown_observed(serial_text, emulator_text, returncode):
    if re.search(r'Okay to power off|System is shut down|System is powering down',
                 serial_text, re.I):
        return True
    return (returncode == 0 and 'Shutdown started.' in serial_text and
            'Machine: soft power-off' in emulator_text)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--chd', required=True, type=Path)
    parser.add_argument('--nvram', required=True, type=Path)
    parser.add_argument('--iris', required=True, type=Path)
    parser.add_argument('--ci', required=True, type=Path)
    parser.add_argument('--login-golden', required=True, type=Path,
                        help='visually checked screenshot of this donor\'s graphical login')
    parser.add_argument('--output-directory', required=True, type=Path)
    parser.add_argument('--timeout', type=int, default=1200,
                        help='maximum seconds to wait for IRIX login')
    parser.add_argument('--start-system-after', type=float,
                        help='select Start System after this many seconds for a seed that stops at PROM')
    args = parser.parse_args()
    out = args.output_directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    iris, client = args.iris.resolve(), args.ci.resolve()
    result = {'schema': 1, 'status': 'incomplete', 'clean_shutdown': False,
              'chd_sha256': sha256(args.chd), 'nvram_source_sha256': sha256(args.nvram),
              'iris': str(iris), 'iris_sha256': sha256(iris),
              'ci': str(client), 'ci_sha256': sha256(client),
              'login_golden_sha256': sha256(args.login_golden),
              'script_sha256': sha256(__file__), 'commands': []}
    subprocess.run(['cp', '--reflink=auto', '--sparse=always', '--', str(args.chd.resolve()),
                    str(out/'boot.chd')], check=True)
    shutil.copyfile(args.nvram, out/'nvram.bin')
    sockets = [socket.socket() for _ in range(3)]
    for stream in sockets:
        stream.bind(('127.0.0.1', 0))
    ports = [s.getsockname()[1] for s in sockets]
    for stream in sockets:
        stream.close()
    control_dir = Path(tempfile.mkdtemp(prefix='xiri-donor-ci-'))
    config = f'''nvram = {json.dumps(str(out/'nvram.bin'))}
banks = [128, 0, 0, 0]
headless = false
no_audio = true
ci = true
ci_socket = {json.dumps(str(control_dir/'iris.sock'))}
serial_log = {json.dumps(str(out/'serial.log'))}
monitor_port = {ports[0]}
serial_port_a = {ports[1]}
serial_port_b = {ports[2]}
scsi_deferred_int = true
nat_subnet = "192.168.0.0/24"
[machine]
profile = "indy_ip24"
cpu = "r4400"
[graphics]
board = "newport"
[scsi.1]
path = {json.dumps(str(out/'boot.chd'))}
cdrom = false
overlay = true
[network]
mode = "nat"
mac = "08:00:69:12:34:56"
'''
    (out/'iris.toml').write_text(config)
    result['config_sha256'] = sha256(out/'iris.toml')
    process = monitor = None
    env = dict(os.environ, IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(out/'rex-jit-profile.bin'))

    def ci(*arguments, check=True, timeout=45):
        command = [str(client), '--socket', str(control_dir/'iris.sock'), *arguments]
        r = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        result['commands'].append({'arguments': list(arguments), 'status': r.returncode,
                                   'stdout': r.stdout, 'stderr': r.stderr})
        if check and r.returncode:
            raise RuntimeError('iris-ci '+str(arguments)+': '+r.stderr)
        return r

    def reply():
        data = b''
        while not re.search(rb'(^|\n)> $', data):
            part = monitor.recv(65536)
            if not part:
                raise RuntimeError('monitor disconnected')
            data += part
        return data.decode('latin1')

    def command(text):
        monitor.sendall((text+'\n').encode())
        text_out = reply()
        with (out/'monitor.log').open('a') as log:
            log.write(text+'\n'+text_out+'\n')
        return text_out

    try:
        with (out/'emulator.log').open('wb') as log:
            process = subprocess.Popen([str(iris), '--config', str(out/'iris.toml')],
                cwd=out, env=env, stdin=subprocess.DEVNULL, stdout=log,
                stderr=subprocess.STDOUT, start_new_session=True)
        (out/'emulator.pid').write_text(str(process.pid)+'\n')
        result['pid'] = process.pid
        deadline = time.monotonic()+45
        while not (control_dir/'iris.sock').exists():
            if process.poll() is not None or time.monotonic() > deadline:
                raise RuntimeError('emulator did not start; see emulator.log')
            time.sleep(.2)
        monitor = socket.create_connection(('127.0.0.1', ports[0]), timeout=20)
        monitor.settimeout(30)
        reply()
        ci('start')
        print('Cold boot started; emulator PID', process.pid, flush=True)
        if args.start_system_after is not None:
            time.sleep(args.start_system_after)
            ci('screenshot', str(out/'prom.png'))
            command('key type 1')
            command('key Return')
            result['prom_start_system'] = True
        logged_prompt = False
        for attempt in range(max(1, (args.timeout+29)//30)):
            if ci('serial-wait', 'login:', '--timeout', '30', check=False).returncode == 0:
                logged_prompt = True
                break
            ci('serial-send', '')
            print('Waiting for IRIX login', attempt+1, flush=True)
        if not logged_prompt:
            raise RuntimeError('IRIX login did not appear')
        ci('login', 'root', timeout=90)
        identity = ci('run', 'uname -R; hinv; nvram console; df -k /', '--timeout', '30').stdout
        result['identity'] = identity
        if '6.5 6.5.22f' not in identity:
            raise RuntimeError('unexpected donor release')
        print('IRIX 6.5.22f serial login passed', flush=True)
        ci('screen-wait', str(args.login_golden.resolve()), '--timeout', '180',
           '--actual', str(out/'login.png'), '--diff', str(out/'login-diff.png'),
           '--max-pixels', '512', timeout=200)
        result['graphical_login_verified'] = True
        # The native IRIX graphical login starts with the login-name field active.
        command('key type root')
        command('key Return')
        for _ in range(30):
            running = ci('run', 'ps -ef | grep -E "4Dwm|toolchest|fmserv|Xsgi"', '--timeout', '30').stdout
            if re.search(r'\s(?:/usr/bin/X11/)?4Dwm(?:\s|$)', running):
                result['desktop_processes'] = running
                break
            time.sleep(3)
        else:
            raise RuntimeError('graphical root login did not start 4Dwm')
        time.sleep(10)
        command('disp compositor gl')
        command('disp compositor sw')
        command('screen wait 500 10000')
        ci('screenshot', str(out/'desktop.png'))
        result['desktop_png_sha256'] = sha256(out/'desktop.png')
        print('4Dwm running; desktop PNG saved', flush=True)
        ci('serial-send', 'sync; shutdown -p -g0 -y')
        for _ in range(12):
            text = (out/'serial.log').read_text(errors='replace')
            if shutdown_observed(text, (out/'emulator.log').read_text(errors='replace'),
                                 process.poll()):
                result['clean_shutdown'] = True
                break
            if process.poll() is not None:
                break
            time.sleep(5)
        if not result['clean_shutdown']:
            # Indy may finish on its graphics console rather than serial.
            ci('screenshot', str(out/'shutdown.png'), check=False)
            result['shutdown_needs_visual_check'] = True
        result['status'] = 'booted'
    except BaseException as error:
        result.update(status='failed', error=str(error))
        raise
    finally:
        if monitor:
            monitor.close()
        if process and process.poll() is None:
            try:
                ci('quit', check=False, timeout=20)
                process.wait(timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=10)
        result['emulator_stopped'] = process is None or process.poll() is not None
        result['emulator_exit'] = None if process is None else process.returncode
        result['source_chd_unchanged'] = sha256(args.chd) == result['chd_sha256']
        result['source_nvram_unchanged'] = sha256(args.nvram) == result['nvram_source_sha256']
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        shutil.rmtree(control_dir)


if __name__ == '__main__':
    main()
