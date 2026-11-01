#!/usr/bin/env python3
"""Cold boot a disposable CHD copy from disk and exercise the manual launcher."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shutil
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('base', ROOT/'scripts/probe-netbsd.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path)
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
    staged = json.loads((bundle/'seed-result.json').read_text())['staged']
    support = {r['netbsd_destination']:r['sha256'] for r in ledger['files']
               if r['type'] == 'file' and r['netbsd_destination'] not in staged}
    (media/'SUPPORT').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in support.items()))
    (media/'SHA256').write_text(''.join(f'SHA256 ({path.name}) = {probe.sha256(path)}\n' for path in sorted(media.iterdir())))
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory/'probe.iso', media])
    probe.run(['cp', '--reflink=auto', '--sparse=always', bundle/'netbsd-xiri.chd', directory/'disk.chd'], timeout=120)
    shutil.copyfile(bundle/'nvram.bin', directory/'nvram.bin')
    config = (bundle/'iris.toml').read_text().replace('tftp_dir = "tftp"',
        'tftp_dir = '+json.dumps(str(bundle/'tftp')))
    config += '\n[scsi.4]\npath = '+json.dumps(str(directory/'probe.iso'))+'\ncdrom = true\n'
    lab = probe.Lab(SimpleNamespace(mode='ordinary', debugger=False, boot_timeout=600), directory, config_text=config)
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
        result['direct_disk_boot'] = True
        print('CHD disk boot reached NetBSD login', flush=True)
        cmd('uname -v | grep '+pin['ident'])
        cmd('test "$(sha256 -q /netbsd)" = '+pin['native_kernel_sha256']+
            ' && test "$(sha256 -q /netbsd.boot)" = '+pin['boot_kernel_sha256'])
        cmd('cd /root && test -x /usr/local/bin/xiri-desktop && test -r /usr/local/share/xiri/fonts/fonts.dir && test -d /usr/people/xiritest')
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c SUPPORT && cd /root && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/type.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o image-type', 180)
        result['support_files_verified'] = support
        result['native_control'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        assert 'XIRI_ABI_PROBE' in result['native_control']
        cmd('XIRI_SESSION_MS=300000 /usr/local/bin/xiri-desktop >manual-desktop.log 2>&1 & manual=$!; tries=0; until ./image-type 127.0.0.1:0 xmahjongg "" >game-focus.log 2>&1; do tries=$((tries+1)); test "$tries" -lt 120 || break; sleep 2; done; echo READY_TRIES=$tries; /usr/X11R7/bin/xdpyinfo -display 127.0.0.1:0 >manual-display 2>&1; /usr/X11R7/bin/xwininfo -display 127.0.0.1:0 -root -tree >manual-tree 2>&1; /usr/X11R7/bin/xwd -display 127.0.0.1:0 -root -silent >manual.xwd 2>manual-frame.err; sleep 2; /usr/X11R7/bin/xwd -display 127.0.0.1:0 -root -silent >game.xwd 2>game-frame.err; kill -TERM "$manual"; wait "$manual"; echo MANUAL_STATUS=$?', 420)
        result['launcher_log'] = get('cat manual-desktop.log').decode(errors='backslashreplace')
        result['display'] = get('cat manual-display').decode(errors='backslashreplace')
        result['tree'] = get('cat manual-tree').decode(errors='backslashreplace')
        result['newport_x11'] = 'dimensions:    1024x768 pixels' in result['display']
        frame = get('cat manual.xwd')
        if frame:
            (directory/'manual.xwd').write_bytes(frame)
            result['frame_sha256'] = probe.sha256(directory/'manual.xwd')
        game = get('cat game.xwd')
        if game:
            (directory/'game.xwd').write_bytes(game)
            result['game_frame_sha256'] = probe.sha256(directory/'game.xwd')
        result['game_focus'] = get('cat game-focus.log').decode(errors='backslashreplace')
        result['session_logs'] = get('for d in /var/tmp/xiri-desktop/session.*; do for f in "$d"/guard.log "$d"/*.err "$d"/*.exit "$d"/handoff "$d"/Xorg.log; do test ! -f "$f" || { echo "$f"; cat "$f"; }; done; done').decode(errors='backslashreplace')
        result['remaining_uid1234'] = get("ps -axo uid,pid,comm | awk '$1 == 1234 { print }'").decode().strip()
        assert not result['remaining_uid1234']
        result['native_after'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        assert 'XIRI_ABI_PROBE' in result['native_after']
        result['status'] = 'observed'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        result['base_chd_unchanged'] = probe.sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
        (directory/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['status'] == 'observed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
