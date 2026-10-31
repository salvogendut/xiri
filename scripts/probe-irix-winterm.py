#!/usr/bin/env python3
"""Try original winterm/xwsh on NetBSD, with a native terminal control."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


probe = module('probe', 'probe-netbsd.py')
runtime = module('runtime', 'probe-irix-runtime.py')
tcp = module('tcp', 'probe-irix-tcp.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-directory', required=True, type=Path)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--font', help='Also repeat each launch with this explicit X font')
    args = parser.parse_args()
    seed = args.seed_directory.resolve()
    sr = json.loads((seed / 'result.json').read_text())
    pin = json.loads((ROOT / 'lab/irix-siocnread/baseline.json').read_text())
    if not (sr['status'] == 'observed' and sr['clean_shutdown'] and sr['pin'] == pin
            and sr['native_x11_after'] and not sr['failures']):
        parser.error('need a clean passing LP64 SIOCNREAD seed')
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    build = ROOT / '.work/netbsd-irix-siocnread-build'
    for path, key in [(probe.IRIS, 'emulator_sha256'), (probe.CI, 'ci_client_sha256'),
                      (build / 'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256')]:
        if probe.sha256(path) != pin[key]:
            parser.error('changed pinned input')
    manifest = json.loads((ROOT / 'lab/irix-winterm/manifest.json').read_text())
    output = ROOT / '.work/irix-winterm/runs'
    output.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=output))
    print('Results: ' + str(directory.relative_to(ROOT)), flush=True)
    media = directory / 'media'
    media.mkdir()
    copied = {}
    for kind in ['files', 'launchers', 'resources']:
        for path, info in manifest[kind].items():
            if '/catman/' in path:
                continue
            source = ROOT / '.work/irix-winterm/root' / path.lstrip('/')
            if probe.sha256(source) != info['sha256']:
                parser.error('changed vendor input: ' + path)
            target = media / 'vendor' / path.lstrip('/')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            copied[path] = info['sha256']
    source_paths = ['lab/irix-lp64/runner.c', 'lab/irix-toolchest/session.c']
    for path in source_paths:
        shutil.copyfile(ROOT / path, media / Path(path).name)
    environment = ('HOME=/tmp/xiri-home\nDISPLAY=127.0.0.1:98\nSHELL=/bin/sh\n'
                   'PATH=/emul/irix/usr/sbin:/emul/irix/usr/bin:/usr/X11R7/bin:/bin:/usr/bin\n'
                   'WINTERM=/emul/irix/usr/sbin/xwsh -name winterm\n')
    (media / 'winterm.env').write_text(environment)
    setup = ['set -eu']
    directories = sorted({str(parent) for path in copied for parent in Path('/emul/irix' + path).parents
                          if str(parent).startswith('/emul/irix/')})
    for path in directories:
        setup.append(shlex.join(['install', '-d', '-m', '755', path]))
    for path in copied:
        mode = '555' if path in manifest['files'] or path in manifest['launchers'] else '444'
        setup.append(shlex.join(['install', '-m', mode, '/cdrom/vendor' + path, '/emul/irix' + path]))
    (media / 'stage.sh').write_text('\n'.join(setup) + '\n')
    (media / 'INHERITED').write_text('SHA256 (/netbsd) = ' + pin['native_kernel_sha256'] + '\n')
    (media / 'SHA256').write_text(''.join(f'SHA256 ({p.relative_to(media)}) = {probe.sha256(p)}\n'
                                       for p in sorted(media.rglob('*')) if p.is_file()))
    for name in ['disk.raw', 'nvram.bin']:
        probe.run(['cp', '--reflink=auto', '--sparse=always', seed / name, directory / name], timeout=120)
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory / 'probe.iso', media])
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(build / 'tftp')), config, flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode=args.mode, debugger=False, boot_timeout=600), directory, config_text=config)
    sources = source_paths + ['scripts/probe-irix-winterm.py', 'scripts/probe-netbsd.py',
                              'scripts/probe-irix-runtime.py', 'scripts/probe-irix-tcp.py',
                              'lab/irix-winterm/manifest.json']
    result = dict(status='error', clean_shutdown=False, mode=args.mode, pin=pin,
                  manifest_sha256=probe.sha256(ROOT / 'lab/irix-winterm/manifest.json'), staged=copied,
                  environment=environment, font=args.font, seed=str(seed.relative_to(ROOT)),
                  seed_result_sha256=probe.sha256(seed / 'result.json'),
                  sources={p:probe.sha256(ROOT / p) for p in sources}, controls=[], cases=[],
                  started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))

    def command(cmd, timeout=120):
        before = len(lab.serial_text())
        if lab.command(cmd, timeout):
            raise RuntimeError('guest command failed: ' + cmd)
        return lab.serial_text()[before:]

    def download(cmd):
        text = command('echo HEX_START; ' + cmd + ' 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END')
        match = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$', text, re.M)
        if not match:
            raise RuntimeError('missing compressed payload')
        return gzip.decompress(bytes.fromhex(match[1]))

    def capture(name):
        command('xwininfo -display 127.0.0.1:98 -root -tree >' + name + '.tree && '
                'xwd -display 127.0.0.1:98 -root -silent >' + name + '.xwd')

    def retrieve(name):
        tree = download('cat ' + name + '.tree').decode()
        path = directory / (name + '.xwd')
        path.write_bytes(download('cat ' + name + '.xwd'))
        return dict(tree=tree, frame_sha256=probe.sha256(path))

    def native(phase, uid):
        name = 'native-' + phase
        argv = ['./winterm-runner', './session', *[str(uid)] * 4, '--', 'winterm.env',
                '/usr/X11R7/bin/xterm', '-name', 'XiriNativeTerminal', '-title', 'XiriNativeTerminal',
                '-display', '127.0.0.1:98', '-geometry', '40x8+150+60', '-e', '/bin/sh', '-c',
                'printf "Xiri native NetBSD shell\\n"; sleep 30']
        command(shlex.join(argv) + ' >native-parent.log 2>&1 & npid=$!; sleep 4')
        capture(name)
        command('xwininfo -display 127.0.0.1:98 -name XiriNativeTerminal >native-window.log && wait "$npid"', 60)
        window = download('cat native-window.log').decode()
        if 'Map State: IsViewable' not in window:
            raise RuntimeError('native terminal not viewable')
        result['controls'].append(dict(phase=phase, uid=uid, window=window,
                                      actual=runtime.observation(download('cat native-parent.log').decode()),
                                      **retrieve(name)))

    try:
        lab.start()
        command('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && '
                '/bin/sh /cdrom/stage.sh && '
                'cd /root/irix-desktop && cp /cdrom/runner.c /cdrom/session.c /cdrom/winterm.env . && '
                'cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=15000 -DRUNNER_TIMING runner.c -o winterm-runner && '
                'cc -O2 -Wall -Wextra -Werror session.c -o session && chmod 555 session winterm-runner && '
                'chmod 444 winterm.env && mkdir -p /tmp/xiri-home && chmod 777 /tmp/xiri-home && ulimit -c 0', 240)
        command('export PATH=/usr/X11R7/bin:$PATH; Xvfb :98 -screen 0 640x480x24 -ac -noreset >winterm-xvfb.log 2>&1 & xpid=$!; '
                'sleep 2; xdpyinfo -display 127.0.0.1:98 >/dev/null')
        result['shells'] = download('{ ls -l /bin/sh /bin/ksh /bin/csh; grep ^root: /etc/passwd; }').decode()
        native('before', 0)
        for uid in [0, 1234]:
            for font in ([None, args.font] if args.font else [None]):
                for kind in ['xwsh', 'winterm']:
                    name = kind + ('-font' if font else '') + '-' + str(uid)
                    app = ['/emul/irix/usr/sbin/xwsh', '-name', 'winterm'] if kind == 'xwsh' else ['/bin/sh', '/emul/irix/usr/sbin/winterm']
                    argv = ['./winterm-runner', './session', *[str(uid)] * 4, '--', 'winterm.env',
                            *app, '-display', '127.0.0.1:98']
                    if font:
                        argv += ['-fn', font]
                    command('ktrace -i -t un -f winterm.ktrace ' + shlex.join(argv) + ' >winterm-parent.log 2>&1 & wpid=$!; sleep 4')
                    capture(name)
                    command('wait "$wpid"; ps -ax -o pid,comm >winterm-processes.log; '
                            'pkill -KILL -x xwsh 2>/dev/null || true', 60)
                    parent = download('cat winterm-parent.log').decode()
                    (directory / (name + '.parent')).write_text(parent)
                    raw = download('kdump -x -f winterm.ktrace').decode()
                    (directory / (name + '.kdump')).write_text(raw)
                    result['cases'].append(dict(kind=kind, uid=uid, font=font, argv=argv, actual=runtime.observation(parent),
                                                processes=download('cat winterm-processes.log').decode(),
                                                calls=tcp.trace_records(raw, 'irix_o32', True),
                                                returns=tcp.trace_records(raw, 'irix_ret', True), **retrieve(name)))
                    print(name + ': ' + json.dumps(result['cases'][-1]['actual']), flush=True)
        native('after', 1234)
        command('xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"')
        result['native_x11_after'] = True
        result['status'] = 'observed'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] == 'observed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
