#!/usr/bin/env python3
"""Qualify FAM execution feedback, granite and desktop icons on a cloned seed."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('probe', ROOT/'scripts/probe-netbsd.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


def events(output):
    phases = {}
    phase = None
    for line in output.splitlines():
        if line.startswith('PHASE '):
            phase = line[6:]
            assert phase not in phases
            phases[phase] = []
        elif line.startswith('EVENT '):
            m = re.fullmatch(r'EVENT code=(\d+) request=(\d+) path=(.+)', line)
            assert m and phase
            phases[phase].append([int(m[1]), int(m[2])])
    return {k: sorted(v) for k, v in phases.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, default=ROOT/'.work/xiri-image/prepared-seed-20261102-shell')
    parser.add_argument('--fam-build', type=Path, default=ROOT/'.work/native-fam-exec-20261102-v3')
    parser.add_argument('--resource-root', type=Path, default=ROOT/'.work/desktop-behavior/assets')
    args = parser.parse_args()
    seed, fam = args.seed.resolve(), args.fam_build.resolve()
    pin = json.loads((ROOT/'lab/irix-vendor-shell/baseline.json').read_text())
    provenance = json.loads((seed/'image-source.json').read_text())
    assert p.sha256(seed/'disk.raw') == provenance['raw_sha256']
    build = json.loads((fam/'result.json').read_text())
    assert build['source_manifest_sha256'] == p.sha256(ROOT/'lab/native-fam/source.json')
    assert build['builder_sha256'] == p.sha256(ROOT/'scripts/build-native-fam.py')
    resources = json.loads((ROOT/'lab/irix-desktop-behavior/resources.json').read_text())
    oracle = json.loads((ROOT/'lab/native-fam/exec-events-reference.json').read_text())
    runs = ROOT/'.work/desktop-behavior'; runs.mkdir(exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='qualified-', dir=runs))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    shutil.copyfile(__file__, d/'harness.py')
    media = d/'media'; media.mkdir()
    sources = [
        'lab/irix-installed-desktop/manual-session.sh',
        'lab/irix-installed-desktop/xiri-desktop.sh',
        'lab/irix-vendor-shell/catalog-input.c',
        'lab/irix-filelocks/place-window.c', 'lab/native-fam/exec-events.c']
    for source in sources:
        shutil.copyfile(ROOT/source, media/Path(source).name)
    for source, name in [('src/famd', 'famd'), ('lib/.libs/libfam.a', 'libfam.a')]:
        assert p.sha256(fam/'fam-2.7.0'/source) == build['files'][source]
        shutil.copyfile(fam/'fam-2.7.0'/source, media/name)
    shutil.copyfile(fam/'fam-2.7.0/include/fam.h', media/'fam.h')
    for name in ['btree-native', 'emul-path-native']:
        assert p.sha256(fam/name) == build[name.replace('-', '_')+'_sha256']
        shutil.copyfile(fam/name, media/name)
    for entry in resources['files']:
        source = args.resource_root/entry['source'].lstrip('/')
        assert source.stat().st_size == entry['bytes'] and p.sha256(source) == entry['sha256']
        shutil.copyfile(source, media/source.name)
    (media/'SHA256').write_text(''.join('SHA256 ('+f.name+') = '+p.sha256(f)+'\n' for f in sorted(media.iterdir())))
    p.run(['genisoimage', '-quiet', '-R', '-J', '-o', d/'probe.iso', media])
    for name in ['disk.raw', 'nvram.bin']:
        p.run(['cp', '--reflink=auto', '--sparse=always', seed/name, d/name])
    p.IRIS = ROOT/'.work/target-netbsd64/release/iris'
    p.CI = ROOT/'.work/target-netbsd64/release/iris-ci'
    assert p.sha256(p.IRIS) == pin['emulator_sha256']
    config = (ROOT/'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(
        ROOT/'.work/netbsd-irix-vendor-shell-clean-build/tftp')), config, flags=re.M)
    lab = p.Lab(SimpleNamespace(mode='ordinary', debugger=False, boot_timeout=600), d, config_text=config)
    def send(text, newline=True):
        for byte in (text+('\r' if newline else '')).encode('ascii'):
            lab.serial.sendall(bytes([byte])); time.sleep(.005)
    lab.send = send
    result = dict(status='error', clean_shutdown=False, pin=pin, seed=provenance,
        native_fam=build, sources={s:p.sha256(ROOT/s) for s in sources},
        harness_sha256=p.sha256(Path(__file__)), resources=resources, captures={},
        oracle_sha256=p.sha256(ROOT/'lab/native-fam/exec-events-reference.json'))
    def cmd(text, timeout=120):
        start = len(lab.serial_text())
        code = lab.command(text, timeout)
        output = lab.serial_text()[start:]
        assert code == 0, output
        return output
    def get(text, name):
        output = cmd('echo HEX_START; { '+text+'; } 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END', 240)
        m = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$', output, re.M)
        assert m, output
        data = gzip.decompress(bytes.fromhex(m[1])); (d/name).write_bytes(data)
        return data
    def capture(name):
        lab.monitor_command('disp compositor gl'); lab.monitor_command('disp compositor sw')
        lab.monitor_command('key shift'); lab.monitor_command('screen wait 500 10000')
        lab.monitor_command('screen shot '+str(d/(name+'.png')))
        count = int(subprocess.check_output(['magick', str(d/(name+'.png')), '-format', '%k', 'info:']))
        assert count > 32
        result['captures'][name] = dict(sha256=p.sha256(d/(name+'.png')), colors=count)
    def icon_pixels(name):
        return subprocess.check_output(['magick', str(d/(name+'.png')),
            '-crop', '64x64+1037+640', '+repage', '-depth', '8', 'RGB:-'])
    try:
        lab.start()
        lab.monitor_command('disp compositor sw')
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && mkdir -p /var/tmp/xiri-desktop-behavior && cp /cdrom/* /var/tmp/xiri-desktop-behavior/ && cd /var/tmp/xiri-desktop-behavior && export PATH=/usr/X11R7/bin:$PATH DISPLAY=127.0.0.1:0')
        result['native_before'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        cmd('cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include catalog-input.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o input && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include place-window.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -o place && cc -std=c99 -D_NETBSD_SOURCE -O2 -Wall -Wextra -Werror -I. exec-events.c libfam.a -lstdc++ -o exec-events', 180)
        cmd('install -m 555 famd /usr/local/sbin/famd && install -m 555 manual-session.sh /usr/local/libexec/xiri/manual-session.sh && install -m 555 xiri-desktop.sh /usr/local/bin/xiri-desktop && mkdir -p /emul/irix/usr/include/X11/bitmaps && install -m 444 granite /emul/irix/usr/include/X11/bitmaps/granite && chmod 555 btree-native emul-path-native && ./btree-native && mkdir path-test && ./emul-path-native "$PWD/path-test"')
        cmd('XIRI_SESSION_MS=0 /usr/local/bin/xiri-desktop >desktop.log 2>&1 & manual=$!; (n=0; until xwininfo -root -tree | grep "of 18)" >/dev/null; do kill -0 "$manual" || exit 1; n=$((n+1)); test "$n" -lt 120 || exit 1; sleep 2; done); job=$(sed -n "s/.*Logs: //p" desktop.log | head -1); test -d "$job"', 300)
        result['backdrop'] = get('xprop -root _SGI_DESKS_BACKGROUND_DESCRIPTION _SGI_DESKS_BACKGROUND', 'backdrop.txt').decode()
        assert 'granite' in result['backdrop'] and 'pixmap id #' in result['backdrop']
        result['home_layout'] = cmd('test "$(readlink /usr/people/xiritest/Desktop/UnixRoot)" = / && test "$(readlink /usr/people/xiritest/Desktop/xiritest)" = /usr/people/xiritest && test "$(readlink /usr/people/xiritest/Desktop/dumpster)" = ../dumpster && test -f /usr/people/xiritest/dumpster/.dumpster')
        cmd('ln /bin/sleep sleep-hardlink && ln -s /bin/sleep sleep-symlink')
        result['execution_events'] = {}
        for name, watch, user in [('regular', '/bin/sleep', False), ('hardlink', '/var/tmp/xiri-desktop-behavior/sleep-hardlink', False), ('symlink', '/var/tmp/xiri-desktop-behavior/sleep-symlink', False), ('user', '/bin/sleep', True)]:
            command = shlex.join(['./exec-events', watch, '/bin/sleep'])
            if user: command = 'su -m xiritest -c '+shlex.quote(command)
            cmd(command+' >events-'+name+'.log 2>&1', 90)
            observed = events(get('cat events-'+name+'.log', 'events-'+name+'.log').decode())
            assert observed == oracle['symlink' if name == 'symlink' else 'regular'], observed
            result['execution_events'][name] = observed
        print('FAM reference, hardlink, symlink and ordinary-user checks passed', flush=True)
        cmd('catalog=$(xwininfo -root -tree | awk \'/"Icon Catalog:/ {print $1; exit}\'); xset r off; n=0; while test "$n" -lt 8; do ./input "$DISPLAY" "$catalog" key Next; n=$((n+1)); sleep 1; done; xset r on; ./place "Icon Catalog: Freeware (Page 9 of 18)" 372 450 900 500; ./place winterm 10 180 600 230; (n=0; until grep -q \'"/usr/freeware/bin/xmahjongg" Executing\' "$job/fam.log"; do n=$((n+1)); test "$n" -lt 30 || exit 1; sleep 1; done); kill "$(cat "$job/xmahjongg.pid")"; (n=0; until grep -q \'"/usr/freeware/bin/xmahjongg" Exited\' "$job/fam.log"; do n=$((n+1)); test "$n" -lt 30 || exit 1; sleep 1; done); ./input "$DISPLAY" "$catalog" double 800 820; sleep 4')
        capture('catalog-closed')
        cmd('./input "$DISPLAY" "$catalog" double 1070 682; (n=0; until pgrep -u 1234 -f "^/usr/lib/desktop/iconcatalog/pages/C/Freeware/xmahjongg( |$)" >catalog-game.pid; do n=$((n+1)); test "$n" -lt 30 || exit 1; sleep 1; done); (n=0; until test "$(grep -c \'"/usr/freeware/bin/xmahjongg" Executing\' "$job/fam.log")" -ge 2; do n=$((n+1)); test "$n" -lt 30 || exit 1; sleep 1; done); ./place xmahjongg 10 30 1006 614; ./input "$DISPLAY" "$catalog" double 800 820; sleep 4')
        capture('catalog-running')
        assert icon_pixels('catalog-closed') != icon_pixels('catalog-running')
        cmd('kill "$(cat catalog-game.pid)"; (n=0; until test "$(grep -c \'"/usr/freeware/bin/xmahjongg" Exited\' "$job/fam.log")" -ge 2; do n=$((n+1)); test "$n" -lt 30 || exit 1; sleep 1; done); ./input "$DISPLAY" "$catalog" double 800 820; sleep 4')
        capture('catalog-closed-again')
        assert icon_pixels('catalog-closed') == icon_pixels('catalog-closed-again')
        result['catalog_state_cycle'] = 'double-click launches, opened artwork differs, closed artwork restored exactly'
        print('Catalog double-click and closed/opened/closed pixels passed', flush=True)
        # The workspace places ordinary folders before the special Dumpster.
        cmd('rootwin=$(xwininfo -root | awk \'/Window id:/ {print $4}\'); ./input "$DISPLAY" "$rootwin" double 1210 30; sleep 5; xwininfo -root -tree | grep \'"xiri-indy:/"\'')
        cmd('./input "$DISPLAY" "$rootwin" double 1210 185; sleep 5; xwininfo -root -tree | grep \'"xiri-indy:/usr/people/xiritest/dumpster"\'')
        result['desktop_actions'] = get('xwininfo -root -tree', 'desktop-actions.txt').decode()
        capture('desktop-icons')
        get('cat "$job/fam.log"', 'fam.log')
        get('cat "$job/wm.err" "$job/background.err"', 'desktop-errors.txt')
        cmd('touch "$job/logout"; wait "$manual"; unset manual; test ! -d /var/run/xiri-desktop.lock && ! pgrep -u 1234 && ! pgrep -x famd')
        result['logout_cleanup'] = True
        result['native_after'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = str(error)
        print('Failed: '+str(error), flush=True)
    finally:
        if lab.logged_in:
            try:
                cmd('if test -n "${manual:-}"; then kill -TERM "$manual" 2>/dev/null || true; wait "$manual" || true; fi; test ! -d /var/run/xiri-desktop.lock && ! pgrep -u 1234 && ! pgrep -x famd', 90)
            except Exception as error:
                result['cleanup_error'] = str(error)
        lab.close(); result['clean_shutdown'] = lab.clean_shutdown
        result['base_raw_unchanged'] = p.sha256(seed/'disk.raw') == provenance['raw_sha256']
        (d/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['status'] == 'passed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
