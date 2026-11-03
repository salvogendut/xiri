#!/usr/bin/env python3
"""Qualify IRIX module lifecycle and boot loading on a disposable desktop disk."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace

from xiri_lab import Guest, ROOT, load_probe, sha256, source_hashes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=Path, default=ROOT/'.work/netbsd-module-build')
    parser.add_argument('--seed', type=Path, default=ROOT/'.work/xiri-image/seed-1fa5c92ffac3')
    parser.add_argument('--desktop', action='store_true')
    args = parser.parse_args()
    build, seed = args.build.resolve(), args.seed.resolve()
    manifest = json.loads((build/'module.json').read_text())
    image = json.loads((ROOT/'lab/irix-installed-desktop/image.json').read_text())
    origin = json.loads((seed/'image-source.json').read_text())
    assert sha256(seed/'disk.raw') == origin['raw_sha256']
    p = load_probe()
    p.IRIS = ROOT/image['bundle']/'emulator/iris'
    p.CI = ROOT/image['bundle']/'emulator/iris-ci'
    assert sha256(p.IRIS) == image['emulator_files']['emulator/iris']
    assert sha256(p.CI) == image['emulator_files']['emulator/iris-ci']
    spec = importlib.util.spec_from_file_location('runtime', ROOT/'scripts/probe-irix-runtime.py')
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    runs = ROOT/'.work/irix-module/runs'
    runs.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='ordinary-', dir=runs))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    media = d/'media'
    media.mkdir()
    for name, record in manifest['artifacts'].items():
        source = build/record['path']
        assert sha256(source) == record['sha256']
        shutil.copyfile(source, media/name)
    for name, source in {
        'runner.c': ROOT/'lab/irix-lp64/runner.c',
        'lifecycle.c': ROOT/'lab/irix-module/lifecycle.c',
        'type.c': ROOT/'lab/irix-4dwm/type-ready.c',
    }.items():
        shutil.copyfile(source, media/name)
    vendor = json.loads((ROOT/'lab/irix-reference/manifest.json').read_text())
    for item in vendor['candidates']:
        if item['fixture_name'] in ('vendor-asa', 'vendor-echo'):
            source = ROOT/'.work/irix-reference/vendor'/item['path'].lstrip('/')
            assert sha256(source) == item['sha256']
            shutil.copyfile(source, media/item['fixture_name'])
    (media/'SHA256').write_text(''.join(f'SHA256 ({f.name}) = {sha256(f)}\n'
                                      for f in sorted(media.iterdir())))
    p.run(['genisoimage', '-quiet', '-R', '-J', '-o', d/'probe.iso', media])
    for name in ('disk.raw', 'nvram.bin'):
        p.run(['cp', '--reflink=auto', '--sparse=always', seed/name, d/name])
    config = (ROOT/'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')), config, flags=re.M)
    lab = p.Lab(SimpleNamespace(mode='ordinary', debugger=False, boot_timeout=600), d, config_text=config)
    guest = Guest(lab)
    cmd, get = guest.command, guest.read_text
    r = dict(status='error', clean_shutdown=False, build=manifest, seed=origin,
             emulator_sha256=sha256(p.IRIS), observations=[],
             sources={**source_hashes(), 'scripts/probe-irix-module.py':sha256(Path(__file__)),
                      'lab/irix-module/lifecycle.c':sha256(ROOT/'lab/irix-module/lifecycle.c'),
                      'lab/irix-lp64/runner.c':sha256(ROOT/'lab/irix-lp64/runner.c')})

    def observe(stage, loaded):
        for program, output in [('vendor-asa', 'XIRI_MODULE_OK\n'), ('vendor-echo', '\n')]:
            cmd('./runner ./'+program+' > observation.txt')
            seen = runtime.observation(get('cat observation.txt'))
            want = dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0,
                        stdout=output, stderr='') if loaded else dict(
                            errno_bytes=4, errno=8, exit=126, signal=0, killed=0, stdout='', stderr='')
            r['observations'].append(dict(stage=stage, program=program, observed=seen, expected=want))
            assert seen == want, r['observations'][-1]
        cmd('/bin/echo NATIVE_OK >native.txt; grep -qx NATIVE_OK native.txt')

    def reboot():
        lab.offset = len(lab.serial_text())
        lab.send('shutdown -h now')
        lab.wait('unmounting done', 120)
        lab.wait(r'Option\?', 30)
        lab.logged_in = False
        lab.send('5'); lab.wait('>> ', 15)
        lab.send('boot -f bootp()/netbsd-XIRI_INDY')
        lab.wait('login: ', 600); lab.send('root'); lab.wait('xiri-indy# ', 30)
        lab.logged_in = True
        cmd('cd /root/module; ulimit -c 0')

    try:
        # Run lifecycle tests before init raises securelevel for multiuser.
        lab.start(boot=False)
        lab.wait(r'Option\?', 30); lab.send('5'); lab.wait('>> ', 15)
        # PROM strips one leading dash before passing a flag to the kernel.
        lab.send('boot -f bootp()/netbsd-XIRI_INDY --s')
        lab.wait('Enter pathname of shell or RETURN for /bin/sh:', 600)
        lab.send(''); lab.wait(r'# ', 30)
        lab.send("export PATH=/bin:/sbin:/usr/bin:/usr/sbin; PS1='xiri-indy# '")
        lab.wait('xiri-indy# ', 30)
        lab.logged_in = True
        cmd('mount -u -w / && mount -a && test "$(sysctl -n kern.securelevel)" = 0')
        r['kernel'] = get('uname -a; sysctl kern.module.path')
        assert 'XIRI_IRIX_MODULE' in r['kernel']
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 >/root/module-media.log')
        cmd('mkdir -p /root/module && cp runner.c lifecycle.c type.c vendor-asa vendor-echo /root/module/ && cd /root/module && chmod 755 vendor-asa vendor-echo')
        cmd('install -m 444 /cdrom/netbsd /netbsd && install -m 444 /cdrom/netbsd.boot /netbsd.boot')
        cmd('cc -O2 -Wall -Wextra -Werror runner.c -o runner && cc -O2 -Wall -Wextra -Werror lifecycle.c -o lifecycle', 180)
        cmd("printf ' XIRI_MODULE_OK\\n' >input.txt; ulimit -c 0")
        r['modules_before'] = get('modstat')
        assert 'compat_irix_o32' not in r['modules_before']
        observe('absent', False)
        cmd('modload /cdrom/compat_irix_o32.kmod')
        r['modules_loaded'] = get('modstat')
        assert re.search(r'^compat_irix_o32\s+exec\s+filesys\s', r['modules_loaded'], re.M)
        observe('loaded', True)
        cmd('./lifecycle ./vendor-asa >lifecycle.txt')
        r['lifecycle'] = get('cat lifecycle.txt')
        assert 'BUSY result=-1 errno=16' in r['lifecycle']
        assert 'IDLE result=0 errno=0' in r['lifecycle']
        assert 'XIRI_MODULE_BUSY_OK\n' in r['lifecycle']
        observe('unloaded', False)
        cmd('modload /cdrom/compat_irix_o32.kmod')
        observe('reloaded', True)
        cmd('module_dir=$(sysctl -n kern.module.path)/compat_irix_o32; mkdir -p "$module_dir" && install -m 444 /cdrom/compat_irix_o32.kmod "$module_dir/compat_irix_o32.kmod"')
        cmd("printf 'compat_irix_o32\\n' >/etc/modules.conf; printf '\\nmodules=YES\\n' >>/etc/rc.conf")
        cmd('modunload compat_irix_o32')
        observe('final-unloaded', False)
        reboot()
        cmd('test "$(sysctl -n kern.securelevel)" = 1')
        r['modules_boot'] = get('modstat')
        assert re.search(r'^compat_irix_o32\s+exec\s+filesys\s', r['modules_boot'], re.M)
        observe('boot-loaded', True)
        if args.desktop:
            cmd('cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib type.c -lX11 -lXtst -o type', 180)
            cmd('export PATH=/usr/X11R7/bin:$PATH DISPLAY=127.0.0.1:0; xiri-desktop >desktop.log 2>&1 & desktop_pid=$!')
            guest.wait_for('grep -q "Logs: " desktop.log')
            cmd('job=$(sed -n "s/.*Logs: //p" desktop.log | head -1); test -d "$job"')
            guest.wait_for("xwininfo -root -tree | grep 'of 18)' >/dev/null")
            guest.wait_for('test -s "$job/handoff"')
            cmd('./type "$DISPLAY" winterm \'pwd > "$XIRI_SESSION_DIR/module-pwd"\n\'')
            guest.wait_for('test -s "$job/module-pwd"')
            r['desktop_pwd'] = get('cat "$job/module-pwd"').strip()
            assert r['desktop_pwd'] == '/usr/people/xiritest'
            r['desktop_windows'] = get('xwininfo -root -tree')
            cmd('if modunload compat_irix_o32 >desktop-unload.txt 2>&1; then exit 1; fi')
            r['desktop_unload'] = get('cat desktop-unload.txt')
            # Busy-process protection was verified at level 0 above. Here the
            # ordinary multiuser policy must refuse module administration.
            assert 'Operation not permitted' in r['desktop_unload']
            guest.capture(d/'desktop.png')
            r['desktop_png_sha256'] = sha256(d/'desktop.png')
            cmd('touch "$job/logout"; wait "$desktop_pid"', 120)
            cmd('! pgrep -x Xorg && ! pgrep -x famd')
        r['dmesg'] = get('dmesg')
        assert not re.search(r'panic:|WARNING: module error|fatal.*trap', r['dmesg'])
        r['status'] = 'passed'
    except BaseException as error:
        r['error'] = repr(error)
        try:
            if lab.logged_in:
                r['failure_dmesg'] = get('dmesg', 30)
        except BaseException:
            pass
        raise
    finally:
        lab.close()
        r['clean_shutdown'] = lab.clean_shutdown
        (d/'result.json').write_text(json.dumps(r, indent=2)+'\n')
    assert r['clean_shutdown']
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
