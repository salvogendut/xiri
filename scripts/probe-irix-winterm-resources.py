#!/usr/bin/env python3
"""Test imported IRIX Screen fonts, then locale data, on a stopped winterm seed."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('winterm', ROOT / 'scripts/probe-irix-winterm.py')
winterm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(winterm)
probe, runtime, tcp = winterm.probe, winterm.runtime, winterm.tcp
FONT = '-sgi-screen-medium-r-normal--15-150-72-72-m-80-iso8859-1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-directory', required=True, type=Path)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    args = parser.parse_args()
    seed = args.seed_directory.resolve()
    sr = json.loads((seed / 'result.json').read_text())
    pin = json.loads((ROOT / 'lab/irix-siocnread/baseline.json').read_text())
    if not (sr['status'] == 'observed' and sr['clean_shutdown'] and sr['native_x11_after']
            and sr['pin'] == pin and sr['manifest_sha256'] == probe.sha256(ROOT / 'lab/irix-winterm/manifest.json')):
        parser.error('need a stopped, observed winterm run on the pinned kernel')
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    build = ROOT / '.work/netbsd-irix-siocnread-build'
    for path, key in [(probe.IRIS, 'emulator_sha256'), (probe.CI, 'ci_client_sha256'),
                      (build / 'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256')]:
        if probe.sha256(path) != pin[key]:
            parser.error('changed pinned input')
    output = ROOT / '.work/irix-x11-fonts/runs'
    output.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=output))
    print('Results: ' + str(directory.relative_to(ROOT)), flush=True)
    media = directory / 'media'
    media.mkdir()
    manifest = json.loads((ROOT / 'lab/irix-x11-fonts/manifest.json').read_text())
    for path, info in manifest['files'].items():
        source = ROOT / '.work/irix-x11-fonts/root' / path.lstrip('/')
        if probe.sha256(source) != info['sha256']:
            parser.error('changed original font/locale input')
        destination = media / 'vendor' / path.lstrip('/')
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    sources = ['lab/irix-toolchest/session.c', 'lab/irix-lp64/runner.c']
    for path in sources:
        shutil.copyfile(ROOT / path, media / Path(path).name)
    # Synthetic account data is separate from imported vendor resources. The
    # bare numerical uid used in earlier probes has no login database entry.
    (media / 'passwd').write_text('root:*:0:0:root:/root:/bin/sh\nxiritest:*:1234:1234:Xiri test user:/tmp/xiri-home:/bin/sh\n')
    (media / 'group').write_text('root:*:0:\nxiritest:*:1234:\n')
    inherited = {'/netbsd':pin['native_kernel_sha256'], **{'/emul/irix' + p:s for p,s in sr['staged'].items()}}
    (media / 'INHERITED').write_text(''.join(f'SHA256 ({p}) = {s}\n' for p,s in inherited.items()))
    (media / 'SHA256').write_text(''.join(f'SHA256 ({p.relative_to(media)}) = {probe.sha256(p)}\n'
                                       for p in sorted(media.rglob('*')) if p.is_file()))
    for name in ['disk.raw', 'nvram.bin']:
        probe.run(['cp', '--reflink=auto', '--sparse=always', seed / name, directory / name], timeout=120)
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory / 'probe.iso', media])
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(build / 'tftp')),
                    (ROOT / 'lab/indy-netbsd/iris.toml').read_text(), flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode=args.mode, debugger=False, boot_timeout=600), directory, config_text=config)
    sources += ['scripts/probe-irix-winterm-resources.py', 'scripts/probe-irix-winterm.py',
                'scripts/probe-netbsd.py', 'scripts/probe-irix-runtime.py', 'scripts/probe-irix-tcp.py',
                'lab/irix-x11-fonts/manifest.json']
    result = dict(status='error', clean_shutdown=False, mode=args.mode, pin=pin, manifest=manifest,
                  seed=str(seed.relative_to(ROOT)), seed_result_sha256=probe.sha256(seed / 'result.json'),
                  sources={p:probe.sha256(ROOT / p) for p in sources}, font=FONT,
                  synthetic_accounts={p:probe.sha256(media / p) for p in ['passwd','group']},
                  controls=[], cases=[])

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
        path = directory / (name + '.xwd')
        path.write_bytes(download('cat ' + name + '.xwd'))
        return dict(tree=download('cat ' + name + '.tree').decode(), frame_sha256=probe.sha256(path))

    def native(phase, uid):
        name = 'native-' + phase
        argv = ['./resource-runner', './session', *[str(uid)] * 4, '--', 'winterm.env',
                '/usr/X11R7/bin/xterm', '-name', 'XiriIRIXFont', '-title', 'XiriIRIXFont',
                '-display', '127.0.0.1:98', '-fn', FONT, '-geometry', '40x8+150+60',
                '-e', '/bin/sh', '-c', 'printf "Native NetBSD shell, original SGI font\\n"; sleep 30']
        command(shlex.join(argv) + ' >native-parent.log 2>&1 & npid=$!; sleep 4')
        capture(name)
        command('xwininfo -display 127.0.0.1:98 -name XiriIRIXFont >native-window.log && wait "$npid"', 60)
        window = download('cat native-window.log').decode()
        if 'Map State: IsViewable' not in window:
            raise RuntimeError('native terminal could not open imported font')
        result['controls'].append(dict(phase=phase, uid=uid, window=window,
                                      actual=runtime.observation(download('cat native-parent.log').decode()),
                                      **retrieve(name)))

    try:
        lab.start()
        command('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && '
                'cd /root/irix-desktop && cp /cdrom/*.c . && '
                'cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=15000 -DRUNNER_TIMING runner.c -o resource-runner && '
                'cc -O2 -Wall -Wextra -Werror session.c -o session && chmod 555 session resource-runner && '
                'install -d -m 755 /emul/irix/etc /tmp/irix-screen-fonts && '
                'install -m 444 /cdrom/passwd /emul/irix/etc/passwd && install -m 444 /cdrom/group /emul/irix/etc/group && ulimit -c 0', 240)
        command('export PATH=/usr/X11R7/bin:$PATH; Xvfb :98 -screen 0 640x480x24 -ac -noreset >fonts-xvfb.log 2>&1 & xpid=$!; '
                'sleep 2; xdpyinfo -display 127.0.0.1:98 >/dev/null')
        command('xlsfonts -display 127.0.0.1:98 -fn ' + shlex.quote(FONT) + ' >fonts-before.log 2>&1 || true')
        result['fonts_before'] = download('cat fonts-before.log').decode()
        command('install -m 444 /cdrom/vendor/usr/lib/X11/fonts/misc/* /tmp/irix-screen-fonts/ && '
                'mkfontdir /tmp/irix-screen-fonts && xset -display 127.0.0.1:98 +fp /tmp/irix-screen-fonts && '
                'xset -display 127.0.0.1:98 fp rehash && xlsfonts -display 127.0.0.1:98 -ll -fn ' + shlex.quote(FONT) + ' >fonts-after.log')
        result['fonts_after'] = download('cat fonts-after.log').decode()
        result['generated_index'] = download('cat /tmp/irix-screen-fonts/fonts.dir').decode()
        native('before', 0)
        for stage in ['fonts', 'fonts-locale']:
            if stage == 'fonts-locale':
                for path in manifest['files']:
                    if '/locale/' not in path:
                        continue
                    destination = '/emul/irix' + path
                    command(shlex.join(['install', '-d', '-m', '755', str(Path(destination).parent)]) + ' && '
                            + shlex.join(['install', '-m', '444', '/cdrom/vendor' + path, destination]))
            for uid in [0, 1234]:
                for font in [None, 'fixed']:
                    name = stage + ('-fixed' if font else '-default') + '-' + str(uid)
                    argv = ['./resource-runner', './session', *[str(uid)] * 4, '--', 'winterm.env',
                            '/emul/irix/usr/sbin/xwsh', '-name', 'winterm', '-display', '127.0.0.1:98']
                    if font:
                        argv += ['-fn', font]
                    command('ktrace -i -t un -f resources.ktrace ' + shlex.join(argv) + ' >resources-parent.log 2>&1 & rpid=$!; sleep 4')
                    capture(name)
                    command('wait "$rpid"', 60)
                    parent = download('cat resources-parent.log').decode()
                    (directory / (name + '.parent')).write_text(parent)
                    raw = download('kdump -x -f resources.ktrace').decode()
                    (directory / (name + '.kdump')).write_text(raw)
                    actual = runtime.observation(parent)
                    result['cases'].append(dict(name=name, stage=stage, uid=uid, font=font, actual=actual,
                                                calls=tcp.trace_records(raw, 'irix_o32', True),
                                                returns=tcp.trace_records(raw, 'irix_ret', True), **retrieve(name)))
                    print(name + ': ' + json.dumps(actual), flush=True)
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
