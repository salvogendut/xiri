#!/usr/bin/env python3
"""Check an IRIS refresh against an existing Xiri desktop preview, on a private COW disk."""
import argparse
import json
import os
from pathlib import Path
import re
import resource
import shlex
import shutil
import signal
import struct
import subprocess
import time
from types import SimpleNamespace

from xiri_lab import Guest, load_probe, sha256, source_hashes
from xiri_lab.kernel_log import KernelLog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview', required=True, type=Path)
    parser.add_argument('--emulator', required=True, type=Path)
    parser.add_argument('--kernel-manifest', required=True, type=Path,
                        help='native base manifest with the matching kernel hash and msgbuf symbol')
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.environ.pop('IRIS_CHD_DIFF_DIR', None)
    preview, emulator, out = (p.resolve() for p in (args.preview, args.emulator, args.output))
    base = json.loads((preview/'manifest.json').read_text())
    source = json.loads((preview/'verification/source-qualification.json').read_text())
    kernel = json.loads(args.kernel_manifest.read_text())
    binary = json.loads((emulator/'manifest.json').read_text())
    assert base['status'] == 'packaged-from-qualified-state'
    assert source['status'] == 'passed' and source['clean_shutdown']
    assert sha256(preview/'verification/source-qualification.json') == base['source_result_sha256']
    assert sha256(preview/'netbsd-xiri.chd') == base['chd_sha256']
    assert sha256(preview/'verification/initial-nvram.bin') == base['nvram_sha256']
    assert kernel['pin']['native_kernel_sha256'] == source['pin']['native_kernel_sha256']
    assert sha256(emulator/'iris') == binary['iris_sha256']
    assert sha256(emulator/'iris-ci') == binary['ci_sha256']
    out.mkdir(parents=True, exist_ok=False)
    subprocess.run(['cp', '--reflink=auto', '--sparse=always', preview/'netbsd-xiri.chd', out/'disk.chd'], check=True)
    shutil.copyfile(preview/'verification/initial-nvram.bin', out/'nvram.bin')
    shutil.copyfile(__file__, out/'probe-used.py')
    config = (preview/'iris.toml').read_text()
    config = config.replace('path = "netbsd-xiri.chd"', 'path = '+json.dumps(str(out/'disk.chd')))
    probe = load_probe()
    probe.TOOLBOX = []  # Run this script inside the build container when needed.
    probe.IRIS, probe.CI = emulator/'iris', emulator/'iris-ci'
    lab = probe.Lab(SimpleNamespace(mode='ordinary', debugger=False, boot_timeout=600),
                    out, config_text=config, working_directory=out)
    original_launch = lab.launch

    def launch(command, name):
        if name == 'emulator':
            command = list(command)
            command[command.index('--scsi1')+1] = str(out/'disk.chd')
        return original_launch(command, name)

    lab.launch = launch
    guest = Guest(lab)
    cmd, get, wait = guest.command, guest.read_text, guest.wait_for
    result = dict(status='incomplete', preview=str(preview), emulator=binary,
                  profile=base['profile'], chd_sha256=base['chd_sha256'],
                  sources={**source_hashes(), str(Path(__file__).name): sha256(__file__)},
                  screenshots={}, clean_shutdown=False)

    def capture(name):
        guest.monitor('disp compositor gl')
        guest.monitor('screen wait 500 10000')
        path = out/(name+'.png')
        guest.monitor('screen shot '+str(path))
        size = struct.unpack('>II', path.read_bytes()[16:24])
        assert size == (1282, 1024), size
        result['screenshots'][name] = dict(sha256=sha256(path), size=size)
        print(name, flush=True)

    def greeter():
        wait('test -s /tmp/.X0-lock && kill -0 "$(cat /tmp/.X0-lock)"', 120)
        cmd('export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | '
            'awk \'$1 == "/usr/X11R7/bin/Xorg" {for (i=1;i<NF;i++) if ($i == "-auth") print $(i+1)}\'); '
            'export XAUTHORITY; test -s "$XAUTHORITY"')
        wait('xwininfo -root -tree | grep \'"xlogin"\' >/dev/null', 120)

    def login(user):
        # Public credentials of the disposable preview images.
        for text in (user, user):
            guest.monitor('key type '+text)
            guest.monitor('key Return')

    def type_winterm(text):
        # The existing helper only focuses the window. Send the command through
        # the emulated PS/2 controller, including shifted keys and releases.
        cmd(shlex.join(['/root/import-test/type', '127.0.0.1:0', 'winterm', '']))
        # `key type` queues an entire string without pacing. Let wscons and X
        # consume each key before sending the next one.
        for char in text:
            guest.monitor('key Space' if char == ' ' else 'key type '+char)
            time.sleep(.025)
        guest.monitor('key Return')

    def interrupted(signum, frame):
        raise RuntimeError('Interrupted by signal '+str(signum))

    signal.signal(signal.SIGTERM, interrupted)
    try:
        lab.start(boot=False)
        lab.wait('login: ', 600)
        lab.send('root')
        lab.wait('xiri-indy# ', 30)
        lab.logged_in = True
        cmd('test "$(sha256 -q /netbsd)" = '+source['pin']['native_kernel_sha256'])
        cmd('test -x /root/import-test/type && test -x /root/import-test/place')
        result['module'] = get('modstat | grep compat_irix_o32')
        assert re.search(r'^compat_irix_o32\s+exec\s+filesys\b', result['module'], re.M)
        greeter()
        capture('greeter')
        cmd('rm -f /usr/people/xiritest/.xsession-errors')
        login('xiritest')
        wait('grep -q "Logs: " /usr/people/xiritest/.xsession-errors', 150)
        cmd('job=$(sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors | head -1); '
            'test -d "$job"; XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
            'test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; '
            'export DISPLAY=127.0.0.1:0 XAUTHORITY; test -r "$XAUTHORITY"')
        wait('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready', 180)
        wait("xwininfo -root -tree | grep 'Icon Catalog:' >/dev/null", 180)
        type_winterm('(id -un; echo "$HOME"; pwd; /emul/irix/bin/sh -c "echo IRIX_SHELL_OK") > "$XIRI_SESSION_DIR/refresh-proof"')
        capture('keyboard-input')
        wait('test -s "$job/refresh-proof"', 60)
        result['shell'] = get('cat "$job/refresh-proof"').splitlines()
        assert result['shell'] == ['xiritest', '/usr/people/xiritest', '/usr/people/xiritest', 'IRIX_SHELL_OK']
        result['dimensions'] = get('xdpyinfo | grep dimensions:').strip()
        assert re.search(r'dimensions:\s+1280x1024 pixels', result['dimensions'])
        result['tree'] = get('xwininfo -root -tree')
        for title in ('Toolchest', 'Icon Catalog:', 'winterm', 'xclock'):
            assert title in result['tree'], title
        cmd('/root/import-test/place winterm 140 50 640 300')
        capture('irix-desktop')
        type_winterm('/usr/local/bin/xiri-logout')
        greeter()
        cmd("! pgrep -u xiritest -f '^/emul/irix/usr/(bin/X11/4Dwm|sbin/xwsh|sbin/iconcatalog)( |$)'")
        result['logout'] = True
        login('netbsdtest')
        wait("pgrep -u netbsdtest -f '^/usr/X11R7/bin/ctwm( |$)' >/dev/null", 120)
        wait('xwininfo -root -tree | grep \'"UXTerm"\' >/dev/null', 120)
        result['native_session'] = get('ps -U netbsdtest -o pid,comm')
        capture('native-ctwm')
        cmd('/etc/rc.d/xdm stop', 90)
        result['status'] = 'passed'
    except BaseException as error:
        result.update(status='failed', error=str(error))
        try:
            capture('failure')
        except Exception as capture_error:
            result['capture_error'] = str(capture_error)
        raise
    finally:
        if lab.logged_in:
            try:
                lab.offset = len(lab.serial_text())
                lab.send('\x03', newline=False)
                lab.send('')
                lab.wait('xiri-indy# ', 10)
                KernelLog(lab, int(kernel['kernel_msgbuf_symbol'], 16)).halt()
            except Exception as error:
                result['shutdown_error'] = str(error)
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        result['base_unchanged'] = sha256(preview/'netbsd-xiri.chd') == base['chd_sha256']
        if not (result['clean_shutdown'] and result['base_unchanged']):
            result['status'] = 'failed'
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
        print('Result:', result['status'], out, flush=True)
    if result['status'] != 'passed':
        raise RuntimeError('Desktop qualification failed; see result.json')


if __name__ == '__main__':
    main()
