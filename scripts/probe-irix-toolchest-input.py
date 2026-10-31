#!/usr/bin/env python3
"""Measure original Toolchest resources and menu input on isolated guest Xvfb."""
import argparse
import gzip
import hashlib
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
    parser.add_argument('--seed-directory', type=Path, required=True)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--combined-only', action='store_true')
    args = parser.parse_args()
    seed = args.seed_directory.resolve()
    sr = json.loads((seed / 'result.json').read_text())
    pin = json.loads((ROOT / 'lab/irix-siocnread/baseline.json').read_text())
    if not (sr['status'] == 'observed' and sr['clean_shutdown'] and sr['pin'] == pin
            and sr['native_x11_after'] and not sr['failures']):
        parser.error('need a clean passing LP64 SIOCNREAD run with resources')
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    build = ROOT / '.work/netbsd-irix-siocnread-build'
    for path, key in [(probe.IRIS, 'emulator_sha256'), (probe.CI, 'ci_client_sha256'),
                      (build / 'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256')]:
        if probe.sha256(path) != pin[key]:
            parser.error('changed pinned input')
    out = ROOT / '.work/irix-toolchest-input/runs'
    out.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=out))
    print('Results: ' + str(directory.relative_to(ROOT)), flush=True)
    media = directory / 'media'
    media.mkdir()
    xcomp = ROOT / '.work/netbsd-11.0/sgimips/binary/sets/xcomp.tgz'
    expected = re.search(r'^([0-9a-f]{128})  sgimips/binary/sets/xcomp.tgz$',
                         (ROOT / 'lab/netbsd-11.0/SHA512SUMS').read_text(), re.M)[1]
    if hashlib.sha512(xcomp.read_bytes()).hexdigest() != expected:
        parser.error('changed X development set')
    shutil.copyfile(xcomp, media / 'xcomp.tgz')
    sources = ['lab/irix-toolchest-input/inputcheck.c', 'lab/irix-siocnread/windowcheck.c',
               'lab/irix-lp64/runner.c', 'lab/irix-toolchest/session.c']
    for path in sources:
        shutil.copyfile(ROOT / path, media / Path(path).name)
    resources = json.loads((ROOT / 'lab/irix-toolchest-input/resources.json').read_text())
    for path, record in resources['files'].items():
        local = ROOT / '.work/irix-toolchest-input/root' / path.lstrip('/')
        if probe.sha256(local) != record['sha256']:
            parser.error('changed original resource: ' + path)
        shutil.copyfile(local, media / Path(path).name)
    inherited = {'/netbsd': pin['native_kernel_sha256'],
                 '/root/irix-desktop/native-o32': pin['native_o32_sha256']}
    inventory = json.loads((ROOT / 'lab/irix-desktop/manifest.json').read_text())
    for path, info in inventory['files'].items():
        if path == '/usr/bin/X11/toolchest':
            inherited['/root/irix-desktop/vendor-toolchest'] = info['sha256']
        elif not path.startswith('/usr/bin/'):
            inherited['/emul/irix' + path] = info['sha256']
    for path in ['/usr/lib/X11/system.chestrc', '/usr/lib/X11/app-defaults/Toolchest',
                 '/usr/lib/X11/locale/locale.alias', '/usr/lib/X11/locale/locale.dir']:
        inherited['/emul/irix' + path] = inventory['resource_candidates'][path]['sha256']
    for item in pin['runtimes']:
        inherited['/emul/irix' + item['path']] = item['sha256']
    for c in json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())['candidates']:
        inherited['/root/irix-desktop/' + c['fixture_name']] = c['sha256']
    (media / 'INHERITED').write_text(''.join(f'SHA256 ({path}) = {sha}\n' for path, sha in inherited.items()))
    (media / 'SHA256').write_text(''.join(f'SHA256 ({x.name}) = {probe.sha256(x)}\n' for x in sorted(media.iterdir())))
    for name in ['disk.raw', 'nvram.bin']:
        probe.run(['cp', '--reflink=auto', '--sparse=always', seed / name, directory / name], timeout=120)
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory / 'probe.iso', media])
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(build / 'tftp')), config, flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode=args.mode, debugger=False, boot_timeout=600), directory, config_text=config)
    tracked = sources + ['scripts/probe-irix-toolchest-input.py', 'scripts/probe-netbsd.py',
                         'scripts/probe-irix-runtime.py', 'scripts/probe-irix-tcp.py',
                         'lab/irix-toolchest-input/resources.json']
    result = dict(status='error', clean_shutdown=False, mode=args.mode, pin=pin,
                  xcomp_sha512=expected, resources=resources, seed=str(seed.relative_to(ROOT)),
                  seed_result_sha256=probe.sha256(seed / 'result.json'),
                  sources={n: probe.sha256(ROOT / n) for n in tracked}, controls=[], toolchest=[],
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
        command('./windowcheck >' + name + '.tree && '
                'xwd -display 127.0.0.1:98 -root -silent >' + name + '.xwd')

    def snapshot(name):
        tree = download('cat ' + name + '.tree').decode()
        frame = directory / (name + '.xwd')
        frame.write_bytes(download('cat ' + name + '.xwd'))
        return dict(tree=tree, visible=int(re.search(r'VISIBLE (\d+)', tree)[1]),
                    frame_sha256=probe.sha256(frame))

    def native(phase):
        command('./inputcheck control >native-input.log 2>&1 & npid=$!; sleep 1; '
                './inputcheck click 60 250 && ./inputcheck key a && ./inputcheck key Escape && wait "$npid"')
        log = download('cat native-input.log').decode()
        for marker in ['BUTTON type=4 button=1 send_event=0 x=40 y=30',
                       'BUTTON type=5 button=1 send_event=0 x=40 y=30',
                       'KEY type=2 keysym=0x61 send_event=0', 'KEY type=3 keysym=0xff1b send_event=0']:
            if marker not in log:
                raise RuntimeError('native XTEST control failed: ' + log)
        command('./windowcheck control >native-expose.log 2>&1 & npid=$!; sleep 1; '
                './windowcheck redraw >native-redraw.log; kill "$npid"; wait "$npid" 2>/dev/null || true')
        redraw = download('cat native-redraw.log').decode()
        match = re.search(r'REDRAW visible=(\d+) before=(\w+) cleared=(\w+) after=(\w+)', redraw)
        if not match or int(match[1]) < 1 or match[2] != match[4] or match[2] == match[3]:
            raise RuntimeError('native Expose control failed')
        result['controls'].append(dict(phase=phase, input=log, redraw=redraw))

    try:
        lab.start()
        command('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && '
                'sha256 -c INHERITED && tar xzpf /cdrom/xcomp.tgz -C / && cd /root/irix-desktop && cp /cdrom/*.c . && '
                'cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=90000 -DRUNNER_TIMING runner.c -o input-runner && '
                'cc -O2 -Wall -Wextra -Werror session.c -o session && '
                'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib windowcheck.c -lX11 -o windowcheck && '
                'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib inputcheck.c -lXtst -lX11 -o inputcheck && '
                'chmod 555 session input-runner windowcheck inputcheck && '
                'export PATH=/usr/X11R7/bin:$PATH && { Xvfb :98 -screen 0 640x480x24 -ac -noreset >input-xvfb.log 2>&1 & xpid=$!; } && '
                'sleep 2 && xdpyinfo -display 127.0.0.1:98 >/dev/null', 300)
        result['session_environment'] = download('cat home.env').decode()
        native('before')
        command('./inputcheck colors >input-colors.log')
        result['server_colors'] = download('cat input-colors.log').decode()
        stages = [] if args.combined_only else [('baseline', 1234), ('keysyms', 1234), ('colors', 1234)]
        stages += [('combined', 0), ('combined', 1234)]
        for stage, uid in stages:
            name = stage + '-' + str(uid)
            command('rm -f /emul/irix/usr/lib/X11/XKeysymDB /emul/irix/usr/lib/X11/rgb.txt; '
                    + ('install -m 444 /cdrom/XKeysymDB /emul/irix/usr/lib/X11/XKeysymDB && ' if stage in ['keysyms', 'combined'] else '')
                    + ('install -m 444 /cdrom/rgb.txt /emul/irix/usr/lib/X11/rgb.txt && ' if stage in ['colors', 'combined'] else '')
                    + './inputcheck move 600 400')
            argv = ['./input-runner', './session', *[str(uid)] * 4, '--', 'home.env', './vendor-toolchest', '-display', '127.0.0.1:98']
            if stage in ['colors', 'combined']:
                argv += ['-xrm', '*background: ' + resources['numeric_colors']['SGIGray76'],
                         '-xrm', '*decalForeground: ' + resources['numeric_colors']['SGIDarkGray']]
            cmd = 'ktrace -i -t un -f input.ktrace ' + shlex.join(argv)
            command(cmd + ' >input-parent.log 2>&1 & tpid=$!; sleep 8')
            capture(name + '-rest')
            rest_tree = download('cat ' + name + '-rest.tree').decode()
            phase_names = ['rest']
            window = re.search(r'WINDOW id=(0x[0-9a-f]+) depth=1 map=2 .* x=(\d+) y=(\d+) width=(\d+) height=(\d+) name=Toolchest\n', rest_tree)
            if not window:
                raise RuntimeError('no viewable Toolchest before input')
            x, y = int(window[2]) + 40, int(window[3]) + 14
            actions = [('posted', f'click {x} {y}'), ('down', 'key Down'),
                       ('right', 'key Right'), ('escape', 'key Escape'), ('dismissed', 'key Escape')]
            if stage == 'combined':
                actions += [('mouse-dismissed', 'click 600 400'),
                            ('keyboard-focus', 'focus ' + window[1]), ('keyboard-f10', 'key F10'),
                            ('keyboard-down', 'key Down'), ('keyboard-right', 'key Right'),
                            ('keyboard-escape', 'key Escape')]
            for phase, action in actions:
                command('./inputcheck ' + action + ' && sleep 1')
                capture(name + '-' + phase)
                phase_names.append(phase)
            command('./inputcheck key Escape && ./inputcheck click 600 400 && sleep 1 && ./windowcheck redraw >input-redraw.log')
            capture(name + '-final')
            phase_names.append('final')
            redraw = download('cat input-redraw.log').decode()
            command('wait "$tpid"', 120)
            # Serial frame transfers can exceed the bounded client lifetime.
            # Capture during input, but retrieve only after the parent exits.
            phases = {phase: snapshot(name + '-' + phase) for phase in phase_names}
            parent = download('cat input-parent.log').decode()
            (directory / (name + '.parent')).write_text(parent)
            raw = download('kdump -x -f input.ktrace').decode()
            (directory / (name + '.kdump')).write_text(raw)
            item = dict(stage=stage, uid=uid, argv=argv, actual=runtime.observation(parent),
                        phases=phases, redraw=redraw,
                        calls=tcp.trace_records(raw, 'irix_o32', True),
                        returns=tcp.trace_records(raw, 'irix_ret', True))
            result['toolchest'].append(item)
            print(name + ': ' + json.dumps(dict(actual=item['actual'], visible={k:v['visible'] for k,v in phases.items()})), flush=True)
        native('after')
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
