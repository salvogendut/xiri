#!/usr/bin/env python3
"""Check SGI-to-XDND negotiation on an owned, disposable host X server."""
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    for command in ('cc', 'Xvfb', 'xauth'):
        if not shutil.which(command):
            raise RuntimeError('Required host tool: '+command)
    parent = ROOT/'.work/drag-drop'; parent.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='protocol-', dir=parent))
    print(directory, flush=True)
    inputs = ['runtime/libexec/drop-bridge.c', 'runtime/libexec/drop-files.h',
              'lab/drag-drop/protocol.c', 'scripts/probe-xiri-drag-protocol.py']
    result = dict(status='error', sources={p:digest(ROOT/p) for p in inputs}, cases={})
    for source, name in [(inputs[0], 'bridge'), (inputs[2], 'protocol')]:
        subprocess.run(['cc', '-O2', '-Wall', '-Wextra', '-Werror', str(ROOT/source),
                        '-lX11', '-o', str(directory/name)], check=True)
    number = next(n for n in range(220, 500) if not Path('/tmp/.X'+str(n)+'-lock').exists()
                  and not Path('/tmp/.X11-unix/X'+str(n)).exists())
    auth = directory/'authority'; auth.touch(mode=0o600)
    subprocess.run(['xauth', '-f', str(auth), 'add', ':'+str(number), '.', secrets.token_hex(16)], check=True)
    env = dict(os.environ, DISPLAY=':'+str(number), XAUTHORITY=str(auth))
    processes = []
    def interrupted(*unused):
        raise RuntimeError('Protocol probe interrupted')
    signal.signal(signal.SIGTERM, interrupted)
    try:
        with (directory/'xvfb.log').open('w') as log:
            server = subprocess.Popen(['Xvfb', ':'+str(number), '-screen', '0', '1280x1024x24',
                '-auth', str(auth), '-nolisten', 'tcp', '-noreset'], stdout=log, stderr=log, start_new_session=True)
        processes.append(server)
        until = time.monotonic()+15
        while not Path('/tmp/.X11-unix/X'+str(number)).exists():
            if server.poll() is not None or time.monotonic()>until:
                raise RuntimeError('Private X server did not start')
            time.sleep(.05)
        with (directory/'bridge.log').open('w') as log:
            bridge = subprocess.Popen([str(directory/'bridge')], env=env, stdout=log, stderr=log, start_new_session=True)
        processes.append(bridge)
        until = time.monotonic()+10
        while 'Ready:' not in (directory/'bridge.log').read_text():
            if bridge.poll() is not None or time.monotonic()>until:
                raise RuntimeError('Bridge did not start')
            time.sleep(.05)
        duplicate = subprocess.run([str(directory/'bridge')], env=env, capture_output=True, text=True, timeout=5)
        assert duplicate.returncode == 1 and 'already owns' in duplicate.stderr
        result['singleton'] = 'passed'
        for name in ('v5-big', 'v3-little', 'native', 'cancel', 'cancel-drop', 'drop-help',
                     'reject', 'target-gone', 'passthrough', 'drop-only', 'restore'):
            command = [str(directory/'protocol'), name]
            if name == 'restore':
                command.append(str(bridge.pid))
            run = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
            result['cases'][name] = dict(exit=run.returncode, stdout=run.stdout, stderr=run.stderr)
            assert run.returncode == 0 and 'PASS '+name in run.stdout, (name, result['cases'][name])
            print('PASS '+name, flush=True)
        assert bridge.wait(timeout=5) == 0
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = repr(error)
        raise
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL); process.wait(timeout=5)
        result['processes_stopped'] = all(p.poll() is not None for p in processes)
        auth.unlink(missing_ok=True)
        (directory/'result.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
