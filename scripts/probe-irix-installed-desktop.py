#!/usr/bin/env python3
"""Observe installed-image xmahjongg and the original populated Icon Catalog."""
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
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('shell', ROOT/'scripts/probe-irix-shell.py')
shell = importlib.util.module_from_spec(spec)
spec.loader.exec_module(shell)
probe = shell.probe


def disk_sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ordinary')
    parser.add_argument('--staged-seed', type=Path,
                        help='Reuse a cleanly halted, payload-verified import guest')
    args = parser.parse_args()
    seed = args.staged_seed.resolve() if args.staged_seed else ROOT/'.work/irix-desktop-pipe/runs/ordinary-cg_e3vdl'
    previous = json.loads((seed/'result.json').read_text())
    pin = json.loads((ROOT/'lab/irix-signal/baseline.json').read_text())
    assert previous['clean_shutdown']
    if args.staged_seed:
        assert previous['guest_payload_verified'] and previous['pin'] == pin
    else:
        assert previous['status'] == 'observed' and previous['native_x11_after']
        assert previous['pin'] == json.loads((ROOT/'lab/irix-pipe/baseline.json').read_text())
    build = ROOT/'.work/netbsd-irix-signal-build'
    probe.IRIS = ROOT/'.work/target-netbsd64/release/iris'
    probe.CI = ROOT/'.work/target-netbsd64/release/iris-ci'
    for path, key in [(probe.IRIS, 'emulator_sha256'), (probe.CI, 'ci_client_sha256'),
                      (build/'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256'),
                      (build/'kernel-media/netbsd', 'native_kernel_sha256')]:
        assert probe.sha256(path) == pin[key], path
    payload_dir = ROOT/'.work/irix-installed-desktop'
    payload = json.loads((payload_dir/'payload.json').read_text())
    assert probe.sha256(payload_dir/'payload.tgz') == payload['payload_sha256']
    if args.staged_seed:
        assert previous['payload_manifest_sha256'] == probe.sha256(payload_dir/'payload.json')
    out = payload_dir/'runs'
    out.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.mode+'-', dir=out))
    print('Results: '+str(directory.relative_to(ROOT)), flush=True)
    media = directory/'media'
    media.mkdir()
    sources = ['scripts/probe-irix-installed-desktop.py', 'scripts/stage-irix-installed-desktop.py',
               'lab/irix-installed-desktop/session.sh', 'lab/irix-pipe/guard.c',
               'lab/irix-toolchest/session.c', 'lab/irix-lp64/runner.c',
               'lab/irix-installed-desktop/manual-guard.c',
               'lab/irix-installed-desktop/manual-session.sh',
               'lab/irix-installed-desktop/xiri-desktop.sh',
               'lab/irix-4dwm/setup-pty.sh', 'lab/irix-installed-desktop/xorg.conf',
               'lab/irix-installed-desktop/xiri-launch.sh',
               'lab/irix-installed-desktop/toolchest.chestrc',
               'lab/irix-shell/handoff.c']
    for name in sources[2:]:
        shutil.copyfile(ROOT/name, media/Path(name).name)
    for name in (['payload.json'] if args.staged_seed else ['payload.tgz', 'payload.json']):
        shutil.copyfile(payload_dir/name, media/name)
    fonts = json.loads((ROOT/'lab/irix-x11-fonts/manifest.json').read_text())
    font_files = {}
    for path, info in fonts['files'].items():
        if '/fonts/' not in path:
            continue
        source = ROOT/'.work/irix-x11-fonts/root'/path.lstrip('/')
        assert probe.sha256(source) == info['sha256']
        shutil.copyfile(source, media/Path(path).name)
        font_files[Path(path).name] = info['sha256']
    shutil.copyfile(build/'kernel-media/netbsd', media/'netbsd')
    shutil.copyfile(build/'tftp/netbsd-XIRI_INDY', media/'netbsd.boot')
    permissions_path = ROOT/'lab/irix-installed-desktop/permissions.json'
    permissions = json.loads(permissions_path.read_text())
    (media/'permissions.sh').write_text('#!/bin/sh\nset -eu\n' + ''.join(
        'chmod 555 '+shlex.quote(path)+'\ntest -x '+shlex.quote(path)+'\n'
        for path in sorted(permissions['files'])))
    inherited = {'/netbsd':previous['pin']['native_kernel_sha256'],
                 '/root/irix-desktop/native-o32':pin['native_o32_sha256']}
    if not args.staged_seed:
        inherited.update(previous['staged'])
    staged = dict(previous['staged'])
    links = ['#!/bin/sh', 'set -eu']
    for path, info in payload['paths'].items():
        if info['type'] == 'file':
            if path in staged:
                assert staged[path] == info['sha256'], path
            staged[path] = info['sha256']
        elif info['type'] == 'symlink':
            assert path not in staged, path
            links.append('test "$(readlink '+shlex.quote(path)+')" = '+shlex.quote(info['target']))
    (media/'links.sh').write_text('\n'.join(links)+'\n')
    for name, files in [('INHERITED', inherited), ('STAGED', staged)]:
        (media/name).write_text(''.join(f'SHA256 ({p}) = {h}\n' for p,h in files.items()))
    (media/'desktop.env').write_text('\n'.join([
        'HOME=/usr/people/xiritest', 'USER=xiritest', 'LOGNAME=xiritest', 'SHELL=/bin/sh',
        'DISPLAY=127.0.0.1:98', 'LANG=C', 'LC_ALL=C', 'TZ=UTC0',
        'PATH=/bin:/usr/bin:/usr/X11R7/bin:/emul/irix/usr/freeware/bin:/emul/irix/usr/bin:/emul/irix/usr/sbin'])+'\n')
    (media/'SHA256').write_text(''.join(f'SHA256 ({p.name}) = {probe.sha256(p)}\n' for p in sorted(media.iterdir())))
    for name in ['disk.raw', 'nvram.bin']:
        probe.run(['cp', '--reflink=auto', '--sparse=always', seed/name, directory/name], timeout=120)
    seed_disk = None
    if args.staged_seed:
        seed_disk = disk_sha(seed/'disk.raw')
        assert disk_sha(directory/'disk.raw') == seed_disk
        print('Verified complete staged-seed disk clone', flush=True)
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory/'probe.iso', media])
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),
                    (ROOT/'lab/indy-netbsd/iris.toml').read_text(), flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode=args.mode, debugger=False, boot_timeout=600), directory, config_text=config)
    result = dict(status='error', clean_shutdown=False, mode=args.mode, pin=pin,
        seed=str(seed.relative_to(ROOT)), seed_result_sha256=probe.sha256(seed/'result.json'),
        payload_manifest_sha256=probe.sha256(media/'payload.json'), staged=staged,
        staged_seed=bool(args.staged_seed), font_files=font_files,
        seed_disk_sha256=seed_disk, clone_disk_sha256=seed_disk,
        font_manifest_sha256=probe.sha256(ROOT/'lab/irix-x11-fonts/manifest.json'),
        permission_manifest_sha256=probe.sha256(permissions_path),
        sources={s:probe.sha256(ROOT/s) for s in sources}, controls=[], components=[])

    def cmd(command, timeout=120):
        before = len(lab.serial_text())
        if lab.command(command, timeout):
            raise RuntimeError('guest command failed: '+command)
        return lab.serial_text()[before:]

    def get(command):
        output = cmd('echo HEX_START; { '+command+'; } 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END', 240)
        match = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$', output, re.M)
        if not match:
            raise RuntimeError('missing transfer')
        return gzip.decompress(bytes.fromhex(match[1]))

    def controls(phase):
        actual = shell.r.runtime.observation(cmd('./runner /root/irix-desktop/native-o32 0 0 0 0'))
        assert actual == dict(errno_bytes=0, errno=0, exit=37, signal=0, killed=0, stdout='XIRI_ABI_PROBE\n', stderr='')
        result['controls'].append(dict(phase=phase, actual=actual))
        cmd('xclock -display 127.0.0.1:98 -name NativeClock -title NativeClock >native-clock.err 2>&1 & npid=$!; sleep 2; xwininfo -display 127.0.0.1:98 -name NativeClock >native-window; kill "$npid"; wait "$npid" || true')
        result['native_x11_'+phase] = 'Map State: IsViewable' in get('cat native-window').decode()
        assert result['native_x11_'+phase]

    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED > /tmp/import-inherited.log && cp netbsd /netbsd', 900 if args.staged_seed else 300)
        if args.staged_seed:
            # The complete pre-boot disk equals the previously verified,
            # cleanly halted seed; also check its link layout in the guest.
            cmd('sh /cdrom/links.sh')
        else:
            cmd('cd / && tar xzf /cdrom/payload.tgz && sha256 -c /cdrom/STAGED > /tmp/import-staged.log && sh /cdrom/links.sh', 900)
        result['guest_payload_verified'] = True
        cmd('sh /cdrom/permissions.sh')
        result['executable_permissions_applied'] = True
        cmd('mkdir -p /usr/people/xiritest /tmp/xiri-import/job && chown 1234:1234 /usr/people/xiritest /tmp/xiri-import/job && chmod 700 /usr/people/xiritest /tmp/xiri-import/job && cd /tmp/xiri-import && cp /cdrom/*.c /cdrom/session.sh /cdrom/desktop.env . && chmod 555 session.sh && chmod 444 desktop.env && : >input.txt && chmod 444 input.txt && cc -O2 -Wall -Wextra -Werror guard.c -o guard && cc -O2 -Wall -Wextra -Werror session.c -o session && cc -O2 -Wall -Wextra -Werror runner.c -o runner && chmod 555 guard session runner && ulimit -c 0', 240)
        cmd('uname -v | grep '+shlex.quote(pin['ident']))
        cmd('mkdir -p /usr/local/libexec/xiri /usr/local/share/xiri/fonts /usr/local/bin && install -m 444 /cdrom/*.pcf* /usr/local/share/xiri/fonts/ && /usr/X11R7/bin/mkfontdir /usr/local/share/xiri/fonts && install -m 444 /cdrom/xorg.conf /usr/local/share/xiri/xorg.conf && install -m 555 /cdrom/manual-session.sh /cdrom/setup-pty.sh /usr/local/libexec/xiri/ && install -m 555 /cdrom/xiri-desktop.sh /usr/local/bin/xiri-desktop && install -m 555 /cdrom/xiri-launch.sh /usr/local/bin/xiri-launch && install -m 444 /cdrom/toolchest.chestrc /usr/local/share/xiri/toolchest.chestrc && ln -sf /bin/sh /usr/local/libexec/xiri/command-shell && install -m 555 session /usr/local/libexec/xiri/session && cc -O2 -Wall -Wextra -Werror manual-guard.c -o /usr/local/libexec/xiri/manual-guard && cc -O2 -Wall -Wextra -Werror handoff.c -o /usr/libexec/xiri-shell && chmod 555 /usr/local/libexec/xiri/manual-guard /usr/libexec/xiri-shell && install -m 444 /cdrom/netbsd.boot /netbsd.boot', 240)
        result['manual_guard_control'] = shell.guard(cmd('/usr/local/libexec/xiri/manual-guard 0 /bin/sleep 30 >manual-guard.log 2>&1 & mgpid=$!; sleep 2; kill -TERM "$mgpid"; wait "$mgpid"; cat manual-guard.log'))
        assert result['manual_guard_control']['absent'] == result['manual_guard_control']['valid'] == result['manual_guard_control']['killed'] == 1
        result['persistent_helpers_installed'] = True
        result['desktop_dimensions'] = [1280, 1024]
        result['installed_files'] = {dest: probe.sha256(media/name) for name, dest in {
            'xorg.conf': '/usr/local/share/xiri/xorg.conf',
            'toolchest.chestrc': '/usr/local/share/xiri/toolchest.chestrc',
            'xiri-launch.sh': '/usr/local/bin/xiri-launch',
            'xiri-desktop.sh': '/usr/local/bin/xiri-desktop',
            'manual-session.sh': '/usr/local/libexec/xiri/manual-session.sh',
        }.items()}
        cmd('export PATH=/usr/X11R7/bin:$PATH; install -d -m 755 /tmp/irix-screen-fonts && install -m 444 /cdrom/*.pcf* /tmp/irix-screen-fonts/ && mkfontdir /tmp/irix-screen-fonts')
        cmd('Xvfb :98 -screen 0 1024x768x24 -ac -noreset >xvfb.log 2>&1 & xpid=$!; sleep 3; xdpyinfo -display 127.0.0.1:98 >/dev/null && xset -display 127.0.0.1:98 +fp /tmp/irix-screen-fonts && xset -display 127.0.0.1:98 fp rehash && xsetroot -display 127.0.0.1:98 -solid "#556677"')
        controls('before')
        cmd('ktrace -i -t usn -f desktop.ktrace ./guard 90000 ./session desktop.env /bin/sh /tmp/xiri-import/session.sh >desktop.guard 2>&1 & job=$!; sleep 30; xwininfo -display 127.0.0.1:98 -root -tree >desktop.tree; xwd -display 127.0.0.1:98 -root -silent >desktop.xwd; ps -axo pid,ppid,uid,comm >desktop.ps; wait "$job"', 180)
        raw = get('cat desktop.guard').decode()
        (directory/'desktop.guard').write_text(raw)
        result['guard'] = shell.guard(raw)
        assert result['guard']['absent'] == result['guard']['valid'] == 1
        for name in ['desktop.tree', 'desktop.xwd', 'desktop.ps']:
            (directory/name).write_bytes(get('cat '+name))
        result['tree'] = (directory/'desktop.tree').read_text()
        result['frame_sha256'] = probe.sha256(directory/'desktop.xwd')
        for name in ['wm', 'xmahjongg', 'iconcatalog']:
            pid = get('cat job/'+name+'.pid || true').decode().strip()
            component = dict(name=name, pid=int(pid) if pid.isdigit() else None,
                exit_status=get('cat job/'+name+'.exit || true').decode().strip(),
                stdout=get('cat job/'+name+'.out || true').decode(errors='backslashreplace'),
                stderr=get('cat job/'+name+'.err || true').decode(errors='backslashreplace'))
            if component['pid']:
                cmd(f'kdump -x -p {component["pid"]} -f desktop.ktrace >{name}.dump && {{ head -n 3000 {name}.dump; tail -n 5000 {name}.dump; }} >{name}.capture', 240)
                trace = directory/(name+'.kdump')
                trace.write_bytes(get('cat '+name+'.capture'))
                component['trace_sha256'] = probe.sha256(trace)
            result['components'].append(component)
            print(name+': '+json.dumps(component), flush=True)
        result['user_layout'] = get('find /usr/people/xiritest -type f -o -type d').decode()
        controls('after')
        cmd('kill "$xpid"')
        result['status'] = 'observed'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        (directory/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['status'] == 'observed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
