#!/usr/bin/env python3
"""Observe original desktop clients after private AUTORESRV support."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import tarfile
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('shell', ROOT / 'scripts/probe-irix-shell.py')
shell = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shell)
probe = shell.probe
COMPONENTS = ['bgicons', 'fm-background', 'iconcatalog', 'fm-home']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--diagnostic-baseline', action='store_true')
    args = parser.parse_args()
    seed = ROOT / '.work/irix-4dwm/runs/session-ci-xb3cj1si'
    seed_result = json.loads((seed / 'result.json').read_text())
    old_pin = json.loads((ROOT / 'lab/irix-prda/baseline.json').read_text())
    pin = old_pin if args.diagnostic_baseline else json.loads((ROOT / 'lab/irix-mmap-autoresrv/baseline.json').read_text())
    assert seed_result['status'] == 'observed' and seed_result['clean_shutdown']
    assert seed_result['pin'] == old_pin and seed_result['native_x11_after']
    assert seed_result['cases'][0]['output'] == 'XIRI_4DWM_SHELL_OK\n'
    build = ROOT / ('.work/netbsd-irix-prda-build' if args.diagnostic_baseline else '.work/netbsd-irix-mmap-autoresrv-build')
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    for path, key in [(probe.IRIS, 'emulator_sha256'), (probe.CI, 'ci_client_sha256'),
                      (build / 'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256'),
                      (build / 'kernel-media/netbsd', 'native_kernel_sha256')]:
        assert probe.sha256(path) == pin[key], path
    manifest_path = ROOT / 'lab/irix-desktop-components/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert not manifest['unresolved']
    root = ROOT / '.work/irix-desktop-autoresrv/runs'
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=('baseline-' if args.diagnostic_baseline else '') + args.mode + '-', dir=root))
    print('Results: ' + str(directory.relative_to(ROOT)), flush=True)
    media = directory / 'media'
    media.mkdir()
    staged = dict(seed_result['staged'])
    install = ['#!/bin/sh', 'set -eu', 'cd /', 'tar xzf /cdrom/components.tgz']
    with tarfile.open(media / 'components.tgz', 'w:gz') as archive:
        for path, info in {**manifest['files'], **manifest['resources']}.items():
            source = ROOT / '.work/irix-desktop-components/root' / path.lstrip('/')
            assert probe.sha256(source) == info['sha256'], path
            dest = '/emul/irix' + path
            if dest in staged:
                assert staged[dest] == info['sha256'], dest
            staged[dest] = info['sha256']
            archive.add(source, arcname=dest.lstrip('/'), recursive=False)
            install.append('chmod ' + ('555' if path in manifest['files'] else '444') + ' ' + shlex.quote(dest))
    (media / 'install.sh').write_text('\n'.join(install) + '\n')
    fonts = json.loads((ROOT / 'lab/irix-x11-fonts/manifest.json').read_text())
    for path, info in fonts['files'].items():
        if '/fonts/' in path:
            source = ROOT / '.work/irix-x11-fonts/root' / path.lstrip('/')
            assert probe.sha256(source) == info['sha256']
            shutil.copyfile(source, media / Path(path).name)
    sources = ['scripts/probe-irix-desktop-autoresrv.py', 'lab/irix-shell/guard.c',
               'lab/irix-toolchest/session.c', 'lab/irix-lp64/runner.c',
               'lab/irix-desktop-components/wmcheck-settled.c', 'lab/irix-4dwm/type-ready.c',
               'lab/irix-shell/handoff.c', 'lab/irix-shell/ctty-control.c',
               'lab/irix-desktop-components/session.sh', 'lab/irix-4dwm/setup-pty.sh']
    for source in sources[1:]:
        shutil.copyfile(ROOT / source, media / Path(source).name)
    env = ['HOME=/tmp/xiri-home', 'USER=xiritest', 'LOGNAME=xiritest', 'SHELL=/bin/sh',
           'DISPLAY=127.0.0.1:98', 'LANG=C', 'LC_ALL=C',
           'PATH=/bin:/usr/bin:/usr/X11R7/bin:/emul/irix/usr/bin:/emul/irix/usr/bin/X11:/emul/irix/usr/sbin',
           'WINTERM=/emul/irix/usr/sbin/xwsh -name winterm', 'PS1=xiri$ ']
    (media / 'wm.env').write_text('\n'.join(env) + '\n')
    inherited = {'/netbsd': old_pin['native_kernel_sha256'],
                 '/root/irix-desktop/native-o32': pin['native_o32_sha256'], **seed_result['staged']}
    for label, files in [('INHERITED', inherited), ('STAGED', staged)]:
        (media / label).write_text(''.join(f'SHA256 ({p}) = {h}\n' for p, h in files.items()))
    shutil.copyfile(build / 'kernel-media/netbsd', media / 'netbsd')
    (media / 'SHA256').write_text(''.join(f'SHA256 ({p.name}) = {probe.sha256(p)}\n' for p in sorted(media.iterdir()) if p.is_file()))
    for name in ['disk.raw', 'nvram.bin']:
        probe.run(['cp', '--reflink=auto', '--sparse=always', seed / name, directory / name], timeout=120)
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory / 'probe.iso', media])
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(build / 'tftp')),
                    (ROOT / 'lab/indy-netbsd/iris.toml').read_text(), flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode=args.mode, debugger=False, boot_timeout=600), directory, config_text=config)
    result = dict(status='error', clean_shutdown=False, mode=args.mode, pin=pin, diagnostic_baseline=args.diagnostic_baseline,
                  seed=str(seed.relative_to(ROOT)), seed_result_sha256=probe.sha256(seed / 'result.json'),
                  manifest_sha256=probe.sha256(manifest_path), staged=staged,
                  sources={p: probe.sha256(ROOT / p) for p in sources}, controls=[], components=[])

    def cmd(command, timeout=120):
        before = len(lab.serial_text())
        if lab.command(command, timeout):
            raise RuntimeError('guest command failed: ' + command)
        return lab.serial_text()[before:]

    def get(command):
        output = cmd('echo HEX_START; { ' + command + '; } 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END', 240)
        match = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$', output, re.M)
        if not match:
            raise RuntimeError('missing transfer')
        return gzip.decompress(bytes.fromhex(match[1]))

    def controls(phase):
        actual = shell.r.runtime.observation(cmd('./runner /root/irix-desktop/native-o32 0 0 0 0'))
        assert actual == dict(errno_bytes=0, errno=0, exit=37, signal=0, killed=0, stdout='XIRI_ABI_PROBE\n', stderr='')
        result['controls'].append(dict(phase=phase, actual=actual))

    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd && sh install.sh && sha256 -c STAGED && mkdir -p /tmp/xiri-wm /tmp/xiri-home && chown 1234:1234 /tmp/xiri-home && chmod 700 /tmp/xiri-home && cd /tmp/xiri-wm && rm -rf job && mkdir job && chown 1234:1234 job && chmod 700 job && cp /cdrom/*.c /cdrom/wm.env /cdrom/session.sh . && chmod 444 wm.env && chmod 555 session.sh && : >input.txt && chmod 444 input.txt && sh /cdrom/setup-pty.sh && ulimit -c 0', 240)
        cmd('cc -O2 -Wall -Wextra -Werror guard.c -o guard && cc -O2 -Wall -Wextra -Werror session.c -o session && cc -O2 -Wall -Wextra -Werror runner.c -o runner && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include wmcheck-settled.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o wmcheck && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include type-ready.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o type && cc -O2 -Wall -Wextra -Werror handoff.c -o /usr/libexec/xiri-shell && chmod 555 guard session runner wmcheck type /usr/libexec/xiri-shell', 300)
        cmd('uname -v | grep ' + shlex.quote(pin['ident']))
        controls('before')
        cmd('export PATH=/usr/X11R7/bin:$PATH; install -d -m 755 /tmp/irix-screen-fonts && install -m 444 /cdrom/*.pcf* /tmp/irix-screen-fonts/ && mkfontdir /tmp/irix-screen-fonts; Xvfb :98 -screen 0 1024x768x24 -ac -noreset >xvfb.log 2>&1 & xpid=$!; sleep 3; xdpyinfo -display 127.0.0.1:98 >/dev/null && xset -display 127.0.0.1:98 +fp /tmp/irix-screen-fonts && xset -display 127.0.0.1:98 fp rehash', 120)
        cmd('xsetroot -display 127.0.0.1:98 -solid "#556677"')
        launch = ['./guard', '120000', './session', 'wm.env', '/bin/sh', '/tmp/xiri-wm/session.sh']
        cmd('ktrace -i -t usn -f desktop.ktrace ' + shlex.join(launch) + ' >desktop.guard 2>&1 & job=$!; sleep 8; ./wmcheck 127.0.0.1:98 >wmcheck.out 2>wmcheck.err; echo WMCHECK_STATUS=$? >wmcheck.status; touch job/launch-clients; chmod 444 job/launch-clients; tries=0; while test ! -s job/handoff && test "$tries" -lt 20; do sleep 1; tries=$((tries + 1)); done; sleep 2', 120)
        cookie = 'XIRI_DESKTOP_COMPONENTS_SHELL_OK'
        command = "printf '" + cookie + "\\n'; uname -s; id -u; printf '" + cookie + "\\n' > /tmp/xiri-wm/job/result"
        typing = cmd("suffix=$(printf '\\n_'); ./type 127.0.0.1:98 winterm " + shlex.quote(command) + '"${suffix%_}" >typing.out 2>&1; echo TYPE_STATUS=$?; sleep 2; xwininfo -display 127.0.0.1:98 -root -tree >before.tree; touch job/launch-components; chmod 444 job/launch-components; sleep 15; xwininfo -display 127.0.0.1:98 -root -tree >desktop.tree; xprop -display 127.0.0.1:98 -root >desktop.props; xwd -display 127.0.0.1:98 -root -silent >desktop.xwd; ps -axo pid,ppid,uid,comm >desktop.ps; wait "$job"; echo GUARD_STATUS=$?', 180)
        raw = get('cat desktop.guard').decode()
        (directory / 'desktop.guard').write_text(raw)
        result['guard'] = shell.guard(raw)
        result['baseline'] = dict(typing=typing, wmcheck=get('cat wmcheck.status wmcheck.out wmcheck.err').decode(),
                                  handoff=get('cat job/handoff || true').decode(), marker=get('cat job/result || true').decode(), type_output=get('cat typing.out').decode(),
                                  marker_owner=get("stat -f '%u' job/result || true").decode().strip(),
                                  before_tree=get('cat before.tree').decode())
        result['baseline']['passed'] = ('WM_CHECK passed\n' in result['baseline']['wmcheck'] and
                                        'WMCHECK_STATUS=0\n' in result['baseline']['wmcheck'] and
                                        'TYPE_STATUS=0' in typing and result['baseline']['marker'] == cookie + '\n' and
                                        result['baseline']['handoff'].startswith('NATIVE_HANDOFF '))
        for name in ['desktop.tree', 'desktop.props', 'desktop.ps', 'desktop.xwd']:
            (directory / name).write_bytes(get('cat ' + name))
        result['tree'] = (directory / 'desktop.tree').read_text()
        result['processes_before_cleanup'] = (directory / 'desktop.ps').read_text()
        result['frame_sha256'] = probe.sha256(directory / 'desktop.xwd')
        result['trace_info'] = get('sha256 desktop.ktrace').decode()
        for name in COMPONENTS:
            pid = get('cat job/' + name + '.pid || true').decode().strip()
            outcome = dict(name=name, pid=int(pid) if pid.isdigit() else None,
                           exit_status=get('cat job/' + name + '.exit || true').decode().strip(),
                           stdout=get('cat job/' + name + '.out || true').decode(errors='backslashreplace'),
                           stderr=get('cat job/' + name + '.err || true').decode(errors='backslashreplace'))
            if outcome['pid']:
                cmd(f'kdump -x -p {outcome["pid"]} -f desktop.ktrace >{name}.dump && {{ head -n 4000 {name}.dump; tail -n 4000 {name}.dump; }} >{name}.capture', 240)
                trace = directory / (name + '.kdump')
                trace.write_bytes(get('cat ' + name + '.capture'))
                outcome['trace_sha256'] = probe.sha256(trace)
            result['components'].append(outcome)
        result['baseline_logs'] = {name: get('cat job/' + name + '.out job/' + name + '.err').decode(errors='backslashreplace') for name in ['wm', 'toolchest', 'winterm']}
        cmd('xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"')
        result['native_x11_after'] = True
        controls('after')
        result['status'] = 'observed'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'baseline_passed': result['baseline']['passed'], 'components': result['components'], 'clean_shutdown': result['clean_shutdown']}), flush=True)
    return 0 if result['status'] == 'observed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
