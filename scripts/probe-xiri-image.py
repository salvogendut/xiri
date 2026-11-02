#!/usr/bin/env python3
"""Cold boot a disposable CHD copy from disk and exercise the manual launcher."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import re
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
    a = p.parse_args()
    bundle = a.bundle.resolve()
    manifest = json.loads((bundle/'manifest.json').read_text())
    assert manifest['status'] == 'chd-roundtrip-verified'
    assert probe.sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
    pin = manifest['pin']
    probe.IRIS = ROOT/'.work/target-netbsd64/release/iris'
    probe.CI = ROOT/'.work/target-netbsd64/release/iris-ci'
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
        cmd('XIRI_SESSION_MS=300000 /usr/local/bin/xiri-desktop >manual-desktop.log 2>&1 & manual=$!; tries=0; until ./image-type 127.0.0.1:0 xmahjongg "" >game-focus.log 2>&1; do kill -0 "$manual" || break; tries=$((tries+1)); test "$tries" -lt 120 || break; sleep 2; done; ./image-type 127.0.0.1:0 xmahjongg "" >game-focus.log 2>&1', 360)
        if seed_result.get('desktop_services'):
            cmd('(tries=0; until /usr/X11R7/bin/xwininfo -display 127.0.0.1:0 -root -tree | grep "of 18)" >/dev/null; do kill -0 "$manual" || exit 1; tries=$((tries+1)); test "$tries" -lt 60 || exit 1; sleep 2; done)',180)
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
