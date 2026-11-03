#!/usr/bin/env python3
"""Cold boot a disposable CHD copy from disk and exercise the manual launcher."""
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
spec = importlib.util.spec_from_file_location('base', ROOT/'scripts/probe-netbsd.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path)
    p.add_argument('--debug-failure', action='store_true')
    p.add_argument('--iris-bin-dir', type=Path, default=ROOT/'.work/target-netbsd64/release')
    p.add_argument('--console-size', nargs=2, type=int, metavar=('ROWS', 'COLS'),
                   help='check the text console dimensions before starting X')
    p.add_argument('--arrange-winterm', action='store_true',
                   help='record and resize winterm for diagnostic interaction checks')
    a = p.parse_args()
    bundle = a.bundle.resolve()
    manifest = json.loads((bundle/'manifest.json').read_text())
    assert manifest['status'] == 'chd-roundtrip-verified'
    assert probe.sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
    pin = manifest['pin']
    probe.IRIS = a.iris_bin_dir.resolve()/'iris'
    probe.CI = a.iris_bin_dir.resolve()/'iris-ci'
    assert probe.sha256(probe.IRIS) == pin['emulator_sha256']
    runs = ROOT/'.work/xiri-image/runs'
    runs.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='chd-', dir=runs))
    print('Results: '+str(directory.relative_to(ROOT)), flush=True)
    media = directory/'media'
    media.mkdir()
    shutil.copyfile(ROOT/'lab/irix-4dwm/type-ready.c', media/'type.c')
    ledger = json.loads((bundle/'copy-ledger.json').read_text())
    seed_result = json.loads((bundle/'seed-result.json').read_text())
    if seed_result.get('newport_driver'):
        shutil.copyfile(ROOT/'lab/newport-xaa/render-probe.c', media/'render-probe.c')
    shell_image = bool(seed_result.get('vendor_shell'))
    if shell_image:
        shutil.copyfile(ROOT/'lab/irix-vendor-shell/catalog-input.c', media/'catalog-input.c')
        shutil.copyfile(ROOT/'lab/irix-filelocks/place-window.c', media/'place.c')
    staged = seed_result['staged']
    dimensions = seed_result.get('desktop_dimensions', [1024, 768])
    support = {r['netbsd_destination']:r['sha256'] for r in ledger['files']
               if r['type'] == 'file' and r['netbsd_destination'] not in staged}
    support.update(seed_result.get('installed_files', {}))
    if seed_result.get('desktop_services'):
        assert probe.sha256(bundle/'bitmap-copy-ledger.json') == seed_result['bitmap_ledger_sha256']
        support.update({r['netbsd_destination']:r['sha256'] for r in
            json.loads((bundle/'bitmap-copy-ledger.json').read_text())['files'] if r['type']=='file'})
    (media/'SUPPORT').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in support.items()))
    (media/'SHA256').write_text(''.join(f'SHA256 ({path.name}) = {probe.sha256(path)}\n' for path in sorted(media.iterdir())))
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory/'probe.iso', media])
    probe.run(['cp', '--reflink=auto', '--sparse=always', bundle/'netbsd-xiri.chd', directory/'disk.chd'], timeout=120)
    shutil.copyfile(bundle/'nvram.bin', directory/'nvram.bin')
    config = (bundle/'iris.toml').read_text().replace('tftp_dir = "tftp"',
        'tftp_dir = '+json.dumps(str(bundle/'tftp')))
    config += '\n[scsi.4]\npath = '+json.dumps(str(directory/'probe.iso'))+'\ncdrom = true\n'
    lab = probe.Lab(SimpleNamespace(mode='ordinary', debugger=False, boot_timeout=600), directory, config_text=config)
    # Pace diagnostic commands while Xorg and foreign clients share the CPU.
    def paced_send(text, newline=True):
        data = (text + ('\r' if newline else '')).encode('ascii')
        for byte in data:
            lab.serial.sendall(bytes([byte]))
            time.sleep(.005)
    lab.send = paced_send
    original_launch = lab.launch
    def launch(command, name):
        if name == 'emulator':
            command = list(command)
            command[command.index('--scsi1')+1] = str(directory/'disk.chd')
        return original_launch(command, name)
    lab.launch = launch
    result = dict(status='error', clean_shutdown=False, bundle=str(bundle.relative_to(ROOT)),
        input_manifest_sha256=probe.sha256(bundle/'manifest.json'), pin=pin,
        chd_sha256=manifest['chd_sha256'], sources={
            'scripts/probe-xiri-image.py':probe.sha256(Path(__file__)),
            'lab/irix-4dwm/type-ready.c':probe.sha256(ROOT/'lab/irix-4dwm/type-ready.c')})
    if shell_image:
        for name in ['lab/irix-vendor-shell/catalog-input.c', 'lab/irix-filelocks/place-window.c']:
            result['sources'][name] = probe.sha256(ROOT/name)
    if seed_result.get('newport_driver'):
        result['sources']['lab/newport-xaa/render-probe.c'] = probe.sha256(ROOT/'lab/newport-xaa/render-probe.c')

    def cmd(command, timeout=120):
        before = len(lab.serial_text())
        if lab.command(command, timeout):
            raise RuntimeError('guest command failed: '+command)
        return lab.serial_text()[before:]

    def get(command):
        out = cmd('echo HEX_START; { '+command+'; } 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END', 240)
        match = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$', out, re.M)
        if not match:
            raise RuntimeError('missing payload')
        return gzip.decompress(bytes.fromhex(match[1]))

    try:
        lab.start(boot=False)
        lab.wait(r'Option\?', 30)
        lab.send('5')
        lab.wait(r'>> ', 10)
        for setting in ['systempartition scsi(0)disk(1)rdisk(0)partition(8)',
                        'osloadpartition scsi(0)disk(1)rdisk(0)partition(0)',
                        'osloadfilename netbsd.boot', 'osloadoptions auto', 'osloader boot']:
            lab.offset = len(lab.serial_text())
            lab.send('setenv '+setting)
            lab.wait(r'>> ', 10)
        lab.monitor_command('rtc save')
        lab.send('boot')
        lab.wait(r'login: ', 600)
        lab.send('root')
        lab.wait(r'xiri-indy# ', 15)
        lab.logged_in = True
        if seed_result.get('desktop_services'):
            # PROM/kernel boot can reset the renderer selection. Match the
            # qualified upgrade probe by selecting it after multiuser boot.
            result['compositor'] = lab.monitor_command('disp compositor sw')
            assert 'Compositor: sw' in result['compositor']
        result['direct_disk_boot'] = True
        print('CHD disk boot reached NetBSD login', flush=True)
        cmd('uname -v | grep '+pin['ident'])
        cmd('test "$(sha256 -q /netbsd)" = '+pin['native_kernel_sha256']+
            ' && test "$(sha256 -q /netbsd.boot)" = '+pin['boot_kernel_sha256'])
        cmd('cd /root && test -x /usr/local/bin/xiri-desktop && test -r /usr/local/share/xiri/fonts/fonts.dir && test -d /usr/people/xiritest')
        if a.console_size:
            size = get('stty -f /dev/ttyE0 size').decode().strip()
            assert size == ' '.join(map(str, a.console_size)), size
            result['console_size'] = a.console_size
        if seed_result.get('installed_files'):
            cmd('test "$(readlink /usr/local/libexec/xiri/command-shell)" = /bin/sh')
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c SUPPORT && cd /root && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/type.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o image-type', 180)
        result['support_files_verified'] = support
        result['native_control'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        assert 'XIRI_ABI_PROBE' in result['native_control']
        if seed_result.get('desktop_services'):
            cmd('test "$(readlink /usr/lib/desktop)" = /emul/irix/usr/lib/desktop && test "$(id -u xiritest)" = 1234 && test "$(id -g xiritest)" = 1234')
            result['desktop_services'] = True
        if seed_result.get('native_rpcbind_build'):
            cmd("rpc_errors_before=$(awk '/rpcbind: cannot bind/ {n++} END {print n+0}' /var/log/messages)")
        session_ms = 600000 if shell_image else 300000
        cmd('XIRI_SESSION_MS='+str(session_ms)+' /usr/local/bin/xiri-desktop >manual-desktop.log 2>&1 & manual=$!; tries=0; until ./image-type 127.0.0.1:0 xmahjongg "" >game-focus.log 2>&1; do kill -0 "$manual" || break; tries=$((tries+1)); test "$tries" -lt 120 || break; sleep 2; done; ./image-type 127.0.0.1:0 xmahjongg "" >game-focus.log 2>&1', 360)
        if seed_result.get('newport_driver'):
            cmd('cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/render-probe.c -lXrender -lX11 -o image-render-probe',180)
            result['render_probe'] = cmd('DISPLAY=127.0.0.1:0 ./image-render-probe',120)
            assert 'RENDER_PASS pixels=8536 mismatches=0' in result['render_probe']
        if seed_result.get('desktop_services'):
            cmd('(tries=0; until /usr/X11R7/bin/xwininfo -display 127.0.0.1:0 -root -tree | grep "of 18)" >/dev/null; do kill -0 "$manual" || exit 1; tries=$((tries+1)); test "$tries" -lt 60 || exit 1; sleep 2; done)',180)
            if shell_image:
                cmd('export PATH=/usr/X11R7/bin:$PATH DISPLAY=127.0.0.1:0; '
                    'job=$(sed -n "s/.*Logs: //p" manual-desktop.log | head -1); test -d "$job"; '
                    'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/catalog-input.c '
                    '-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o catalog-input && '
                    'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/place.c '
                    '-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -o image-place', 180)
                cmd('(n=0; until test -s "$job/handoff"; do n=$((n+1)); test "$n" -lt 30 || exit 1; sleep 1; done)')
                cmd("shell_pid=$(sed -n 's/^NATIVE_HANDOFF pid=\\([0-9][0-9]*\\).*/\\1/p' \"$job/handoff\"); test -n \"$shell_pid\"")
                cmd('(n=0; until ps -p "$shell_pid" -o comm= | grep -Eq \'^[[:space:]]*sh[[:space:]]*$\'; do n=$((n+1)); test "$n" -lt 30 || exit 1; sleep 1; done)')
                if a.arrange_winterm:
                    result['winterm_geometry_before_arrangement'] = get('xwininfo -name winterm; xprop -name winterm WM_NORMAL_HINTS').decode()
                    cmd('./image-place winterm 10 180 983 504')
                    result['winterm_arranged'] = [10, 180, 983, 504]
                cmd(shlex.join(['./image-type', '127.0.0.1:0', 'winterm',
                    'pwd > "$XIRI_SESSION_DIR/image-pwd"\n']))
                cmd('(n=0; until test -s "$job/image-pwd"; do n=$((n+1)); test "$n" -lt 20 || exit 1; sleep 1; done)')
                result['winterm_home'] = get('cat "$job/image-pwd"').decode().strip()
                assert result['winterm_home'] == '/usr/people/xiritest'
                result['native_null_device'] = cmd('test -c /emul/irix/dev/null && '
                    'test "$(stat -f %Hr /emul/irix/dev/null)" = "$(stat -f %Hr /dev/null)" && '
                    'test "$(stat -f %Lr /emul/irix/dev/null)" = "$(stat -f %Lr /dev/null)"')
                old_pid = get('cat "$job/xmahjongg.pid"').decode().strip()
                assert old_pid.isdigit()
                cmd('kill '+old_pid+'; (n=0; while pgrep -x xmahjongg >/dev/null; do '
                    'n=$((n+1)); test "$n" -lt 30 || exit 1; sleep 1; done)')
                tree = get('xwininfo -root -tree').decode()
                match = re.search(r'(0x[0-9a-f]+) "Icon Catalog: [^"\n]*\(Page (\d+) of 18\)', tree)
                assert match, tree
                wid, page = match[1], int(match[2])
                cmd('xset r off')
                for _ in range(abs(9-page)):
                    cmd(shlex.join(['./catalog-input', '127.0.0.1:0', wid, 'key',
                                    'Next' if page < 9 else 'Prior'])+'; sleep 1')
                cmd('xset r on; ./image-place "Icon Catalog: Freeware (Page 9 of 18)" 372 450 900 500; sleep 2')
                cmd(shlex.join(['./catalog-input', '127.0.0.1:0', wid, 'double', '1070', '682']))
                # Catalog launches retain the original symlink path as argv[0].
                # Match that path explicitly instead of assuming a basename.
                cmd("(n=0; until pgrep -u 1234 -f "
                    "'^/usr/lib/desktop/iconcatalog/pages/C/Freeware/xmahjongg( |$)' >catalog-game.pid; do "
                    'n=$((n+1)); test "$n" -lt 30 || exit 1; sleep 1; done)')
                new_pid = get('cat catalog-game.pid').decode().strip()
                assert new_pid.isdigit() and new_pid != old_pid
                cmd('./image-type "$DISPLAY" xmahjongg "" >game-focus.log; '
                    './image-place xmahjongg 10 30 1006 614; sleep 2')
                result['catalog_launch'] = dict(initial_pid=int(old_pid), launched_pid=int(new_pid),
                    input='XTEST double-click', page='Freeware', target='xmahjongg',
                    tree=get('xwininfo -root -tree').decode())
                assert '"xmahjongg"' in result['catalog_launch']['tree']
                if seed_result.get('desktop_behavior'):
                    cmd('(n=0; until grep -q \'"/usr/freeware/bin/xmahjongg" Executing\' "$job/fam.log"; do n=$((n+1)); test "$n" -lt 30 || exit 1; sleep 1; done)')
                    backdrop = get('xprop -root _SGI_DESKS_BACKGROUND_DESCRIPTION _SGI_DESKS_BACKGROUND').decode()
                    assert 'granite' in backdrop and 'pixmap id #' in backdrop
                    homes = cmd('test "$(readlink /usr/people/xiritest/Desktop/UnixRoot)" = / && test "$(readlink /usr/people/xiritest/Desktop/xiritest)" = /usr/people/xiritest && test "$(readlink /usr/people/xiritest/Desktop/dumpster)" = ../dumpster && test -f /usr/people/xiritest/dumpster/.dumpster')
                    result['desktop_behavior'] = dict(backdrop=backdrop, home_layout=homes,
                        execution_events=get('grep \'"/usr/freeware/bin/xmahjongg" Executing\' "$job/fam.log"').decode())
                print('CHD catalog double-click launched xmahjongg', flush=True)
            # Refresh the monitor compositor after Xorg changes display state.
            lab.monitor_command('disp compositor gl')
            lab.monitor_command('disp compositor sw')
            lab.monitor_command('screen shot '+str(directory/'before-input.png'))
            result['framebuffer_colors_before_input'] = int(subprocess.check_output(
                ['magick',str(directory/'before-input.png'),'-format','%k','info:']))
            # Exercise real keyboard input as on a manual console session.
            result['keyboard_wake'] = lab.monitor_command('key shift')
            lab.monitor_command('screen wait 500 10000')
            result['framebuffer_capture'] = lab.monitor_command('screen shot '+str(directory/'desktop.png'))
            result['framebuffer_png_sha256'] = probe.sha256(directory/'desktop.png')
            result['framebuffer_colors_after_input'] = int(subprocess.check_output(
                ['magick',str(directory/'desktop.png'),'-format','%k','info:']))
            assert result['framebuffer_colors_after_input'] > 32, 'blank desktop framebuffer'
        if seed_result.get('native_rpcbind_build'):
            result['rpcbind_warning_check'] = cmd("rpc_errors_after=$(awk '/rpcbind: cannot bind/ {n++} END {print n+0}' /var/log/messages); echo RPC_BIND_WARNINGS_BEFORE=$rpc_errors_before AFTER=$rpc_errors_after; test \"$rpc_errors_before\" = \"$rpc_errors_after\"")
        cmd('/usr/X11R7/bin/xdpyinfo -display 127.0.0.1:0 >manual-display 2>&1; /usr/X11R7/bin/xwininfo -display 127.0.0.1:0 -root -tree >manual-tree 2>&1; sleep 2; /usr/X11R7/bin/xwd -display 127.0.0.1:0 -root -silent >game.xwd 2>game-frame.err; kill -TERM "$manual"; wait "$manual"; echo MANUAL_STATUS=$?',180)
        result['launcher_log'] = get('cat manual-desktop.log').decode(errors='backslashreplace')
        result['display'] = get('cat manual-display').decode(errors='backslashreplace')
        result['tree'] = get('cat manual-tree').decode(errors='backslashreplace')
        result['desktop_dimensions'] = dimensions
        result['newport_x11'] = ('dimensions:    %dx%d pixels' % tuple(dimensions)) in result['display']
        assert result['newport_x11']
        if seed_result.get('xorg_configuration'):
            result['xorg_log'] = get('cat /var/log/Xorg.0.log').decode(errors='backslashreplace')
            result['xaa_enabled'] = 'Using XFree86 Acceleration Architecture (XAA)' in result['xorg_log']
            assert result['xaa_enabled'] == seed_result['xorg_configuration']['acceleration_requested']
        if not seed_result.get('desktop_services'):
            game = get('cat game.xwd')
            if game:
                (directory/'game.xwd').write_bytes(game)
                result['game_frame_sha256'] = probe.sha256(directory/'game.xwd')
        result['game_focus'] = get('cat game-focus.log').decode(errors='backslashreplace')
        result['session_logs'] = get('for d in /var/tmp/xiri-desktop/session.*; do for f in "$d"/guard.log "$d"/*.err "$d"/*.exit "$d"/handoff "$d"/Xorg.log; do test ! -f "$f" || { echo "$f"; cat "$f"; }; done; done').decode(errors='backslashreplace')
        result['remaining_uid1234'] = get("ps -axo uid,pid,comm | awk '$1 == 1234 { print }'").decode().strip()
        assert not result['remaining_uid1234']
        if seed_result.get('desktop_services'):
            cmd('! pgrep -x famd && ! pgrep -x rpcbind && test ! -d /var/run/xiri-desktop.lock')
            result['services_absent_after'] = True
            assert 'of 18)' in result['tree'] and 'Trusted Path' not in result['tree']
        result['native_after'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        assert 'XIRI_ABI_PROBE' in result['native_after']
        result['status'] = 'observed'
    except Exception as error:
        result['error'] = str(error)
        if a.debug_failure and lab.logged_in:
            (directory/'ready').write_text('ready\n')
            (ROOT/'.work/desktop-fixes/active').write_text(str(directory))
            print('Failed: '+str(error)+'; debug request queue ready',flush=True)
            last = time.monotonic()
            while time.monotonic()-last < 1200:
                request = directory/'request.json'
                if not request.exists(): time.sleep(.2); continue
                item = json.loads(request.read_text()); request.unlink(); last = time.monotonic()
                if item['command'] == 'SHUTDOWN': break
                try:
                    output = lab.monitor_command(item['command']) if item.get('monitor') else cmd(item['command'],item.get('timeout',120))
                    reply = dict(code=0,output=output)
                except Exception as failure:
                    reply = dict(error=str(failure),output='')
                (directory/('response-'+item['id']+'.json')).write_text(json.dumps(reply))
        raise
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        result['base_chd_unchanged'] = probe.sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
        (directory/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['status'] == 'observed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
