#!/usr/bin/env python3
"""Update a disposable prepared guest and exercise actual Toolchest launches."""
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
spec = importlib.util.spec_from_file_location('base', ROOT/'scripts/probe-netbsd.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
FILES = {
    'xiri-desktop.sh': '/usr/local/bin/xiri-desktop',
    'xiri-launch.sh': '/usr/local/bin/xiri-launch',
    'manual-session.sh': '/usr/local/libexec/xiri/manual-session.sh',
    'toolchest.chestrc': '/usr/local/share/xiri/toolchest.chestrc',
    'xorg.conf': '/usr/local/share/xiri/xorg.conf',
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed', type=Path, default=ROOT/'.work/xiri-image/prepared-seed')
    p.add_argument('--debug-failure', action='store_true',
                   help='Keep a failed guest available through the diagnostic request queue')
    a = p.parse_args()
    seed = a.seed.resolve()
    previous = json.loads((seed/'result.json').read_text())
    provenance = json.loads((seed/'image-source.json').read_text())
    assert previous['status'] == 'observed' and previous['clean_shutdown']
    assert previous['guest_payload_verified'] and previous['persistent_helpers_installed']
    assert probe.sha256(seed/'disk.raw') == provenance['raw_sha256']
    pin = json.loads((ROOT/'lab/irix-signal/baseline.json').read_text())
    assert previous['pin'] == pin
    probe.IRIS = ROOT/'.work/target-netbsd64/release/iris'
    probe.CI = ROOT/'.work/target-netbsd64/release/iris-ci'
    assert probe.sha256(probe.IRIS) == pin['emulator_sha256']
    runs = ROOT/'.work/desktop-launch'
    runs.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='ordinary-', dir=runs))
    print('Results: '+str(directory.relative_to(ROOT)), flush=True)
    media = directory/'media'
    media.mkdir()
    for name in FILES:
        shutil.copyfile(ROOT/'lab/irix-installed-desktop'/name, media/name)
    shutil.copyfile(ROOT/'lab/irix-4dwm/type-ready.c', media/'type.c')
    # Keep the old fixed-display input qualification reproducible.
    source = (ROOT/'lab/irix-toolchest-input/inputcheck.c').read_text()
    source = source.replace('XOpenDisplay("127.0.0.1:98")', 'XOpenDisplay(getenv("DISPLAY"))')
    source = source.replace('XSetInputFocus(d, strtoul(argv[2], NULL, 0),',
                            'XRaiseWindow(d, strtoul(argv[2], NULL, 0));\n        XSetInputFocus(d, strtoul(argv[2], NULL, 0),')
    (media/'input.c').write_text(source)
    staged = dict(previous['staged'])
    ledger = json.loads((ROOT/'lab/irix-installed-desktop/copy-ledger.json').read_text())
    staged.update({r['netbsd_destination']: r['sha256'] for r in ledger['files'] if r['type'] == 'file'})
    (media/'STAGED').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in sorted(staged.items())))
    perms = json.loads((ROOT/'lab/irix-installed-desktop/permissions.json').read_text())
    (media/'permissions.sh').write_text('set -eu\n'+''.join('test -x '+shlex.quote(path)+'\n' for path in perms['files']))
    installed = {dest: probe.sha256(media/name) for name,dest in FILES.items()}
    (media/'INSTALLED').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in installed.items()))
    sources = {str(path.relative_to(ROOT)):probe.sha256(path) for path in [Path(__file__),
        ROOT/'scripts/probe-netbsd.py', ROOT/'lab/irix-4dwm/type-ready.c',
        ROOT/'lab/irix-toolchest-input/inputcheck.c',
        *[ROOT/'lab/irix-installed-desktop'/name for name in FILES]]}
    (media/'SHA256').write_text(''.join(f'SHA256 ({path.name}) = {probe.sha256(path)}\n' for path in sorted(media.iterdir())))
    probe.run(['genisoimage','-quiet','-R','-J','-o',directory/'probe.iso',media])
    for name in ['disk.raw','nvram.bin']:
        probe.run(['cp','--reflink=auto','--sparse=always',seed/name,directory/name])
    config = (ROOT/'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(ROOT/'.work/netbsd-irix-signal-build/tftp')), config, flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600),directory,config_text=config)
    result = dict(status='error',clean_shutdown=False,pin=pin,staged=staged,
        base_image=provenance,base_seed_result_sha256=probe.sha256(seed/'result.json'),
        sources=sources,installed_files=installed,launches={},desktop_dimensions=[1280,1024],
        payload_manifest_sha256=previous['payload_manifest_sha256'])

    def cmd(command, timeout=120):
        before = len(lab.serial_text())
        code = lab.command(command,timeout)
        text = lab.serial_text()[before:]
        if code:
            raise RuntimeError('guest command failed: '+command+'\n'+text[-3000:])
        return text

    def get(command):
        text = cmd('echo HEX_START; { '+command+'; } 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END',240)
        match = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',text,re.M)
        if not match:
            raise RuntimeError('missing compressed payload')
        return gzip.decompress(bytes.fromhex(match[1]))

    def capture(name):
        reply = lab.monitor_command('screen shot '+str(directory/(name+'.png')))
        result[name+'_capture'] = reply
        print(name+': captured',flush=True)

    def remove_closed_terminals():
        # The current xwsh can retain its window after the native shell exits.
        # Remove only this guest's reserved-UID xwsh processes before selecting
        # the next identically named terminal; do not call this normal exit.
        cmd("for pid in $(ps -axo pid,uid,args | awk '$2 == 1234 && $3 == \"/emul/irix/usr/sbin/xwsh\" {print $1}'); do kill -KILL \"$pid\"; done; sleep 1")

    def menu(row, item_y):
        info = cmd('xwininfo -name Toolchest')
        x = int(re.search(r'Absolute upper-left X:\s+(\d+)',info)[1])
        y = int(re.search(r'Absolute upper-left Y:\s+(\d+)',info)[1])
        wid = re.search(r'Window id: (0x[0-9a-f]+)',info)[1]
        cmd(f'./input focus {wid}; ./input click {x+40} {y+14+row*26}; sleep 1; ./input click {x+180} {y+item_y}; sleep 3')

    try:
        lab.start()
        result['compositor'] = lab.monitor_command('disp compositor sw')
        assert 'Compositor: sw' in result['compositor']
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 > /root/update-media.log && sh permissions.sh && mkdir -p /root/desktop-launch && cd /root/desktop-launch',300)
        result['inherited_payload_verified_by_raw_hash'] = True
        result['executable_permissions_applied'] = True
        for name,dest in FILES.items():
            cmd('install -m '+('555' if name.endswith('.sh') else '444')+' /cdrom/'+name+' '+dest)
        cmd('ln -sf /bin/sh /usr/local/libexec/xiri/command-shell && sha256 -c /cdrom/INSTALLED && test "$(readlink /usr/local/libexec/xiri/command-shell)" = /bin/sh')
        result['persistent_helpers_installed'] = True
        cmd('cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/input.c -lXtst -lX11 -o input && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/type.c -lXtst -lX11 -o type',180)
        result['native_before'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        cmd('export PATH=/usr/X11R7/bin:$PATH DISPLAY=127.0.0.1:0; /usr/local/bin/xiri-desktop >desktop.log 2>&1 & manual=$!; tries=0; until ./type "$DISPLAY" xmahjongg "" >game-focus.log 2>&1; do tries=$((tries+1)); test "$tries" -lt 120 || break; sleep 2; done; ./type "$DISPLAY" xmahjongg "" >game-focus.log 2>&1 && job=$(sed -n "s/.*Logs: //p" desktop.log | head -1); test -d "$job"',360)
        result['display'] = get('xdpyinfo').decode()
        assert 'dimensions:    1280x1024 pixels' in result['display']
        # Show that pixels beyond both old bounds reach the composed framebuffer.
        result['edge_pixels'] = {}
        for color,expected in [('red','fe0000'),('blue','0000fe')]:
            cmd('xsetroot -solid '+color+'; sleep 1')
            for x,y in [(1278,1022),(1100,1000)]:
                for attempt in range(20):
                    value = lab.monitor_command(f'screen pix {x} {y}')
                    if '= '+expected in value:
                        break
                    time.sleep(.25)
                assert '= '+expected in value, value
                result['edge_pixels'][f'{color}-{x}-{y}'] = value
        cmd('xsetroot -solid "#556677"')
        capture('full-desktop')
        # Leave the WM and Toolchest alive, then open every tested app from a menu.
        cmd('./type "$DISPLAY" winterm "exit" && ./input key Return; sleep 2; kill "$(cat "$job/xclock.pid")" "$(cat "$job/iconcatalog.pid")" "$(cat "$job/xmahjongg.pid")"; sleep 2')
        remove_closed_terminals()
        result['terminal_exit_policy'] = 'Native shell exit followed by explicit reserved-UID xwsh cleanup; automatic terminal close remains unqualified.'
        for i in range(2):
            menu(0,218)
            marker = f'XIRI_MENU_SHELL_{i+1}_OK'
            cmd('./type "$DISPLAY" winterm '+shlex.quote('echo '+marker+' > "$XIRI_SESSION_DIR/menu-proof-'+str(i)+'"')+' && ./input key Return; sleep 1')
            proof = get('cat "$job/menu-proof-'+str(i)+'"').decode().strip()
            assert proof == marker, (marker, proof)
            result['launches']['winterm-'+str(i+1)] = dict(proof=proof,handoffs=get('cat "$job"/launch-winterm.*/handoff').decode())
            print(marker,flush=True)
            if i == 0:
                cmd('./type "$DISPLAY" winterm "exit" && ./input key Return; sleep 2')
                remove_closed_terminals()
        # Applications follows the six original top-level rows.
        for app,index,title in [('xclock',1,'xclock'),('iconcatalog',2,'Icon Catalog'),('xmahjongg',3,'xmahjongg')]:
            menu(6,170+22*index)
            tree = get('xwininfo -root -tree').decode()
            assert '"'+title+'"' in tree, (app,tree)
            logs = get('for d in "$job"/launch-'+app+'.*; do echo "$d"; cat "$d/stderr"; done').decode()
            result['launches'][app] = dict(tree=tree,logs=logs)
            print('MENU_'+app+'_OK',flush=True)
        cmd('./type "$DISPLAY" winterm "echo Toolchest launch works" && ./input key Return; sleep 1')
        capture('menu-desktop')
        result['native_x11_after'] = 'dimensions:' in cmd('xdpyinfo | grep dimensions')
        cmd('kill -TERM "$manual"; wait "$manual" || test "$?" = 130; ps -axo uid,pid,comm >remaining.txt; ! awk \'$1 == 1234 { found=1 } END { exit !found }\' remaining.txt')
        result['session_logs'] = get('cat desktop.log; for f in "$job"/*.err "$job"/guard.log "$job"/launch-*/*; do test ! -f "$f" || { echo "$f"; cat "$f"; }; done').decode(errors='backslashreplace')
        result['native_after'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        cmd('sha256 -c /cdrom/STAGED >/root/update-vendor-after.log && sha256 -c /cdrom/INSTALLED >/root/update-files-after.log',900)
        result['guest_payload_verified'] = True
        result['status'] = 'observed'
    except Exception as error:
        result['error'] = str(error)
        print('Failed: '+str(error), flush=True)
        if a.debug_failure and lab.logged_in:
            (directory/'ready').write_text('ready\n')
            (ROOT/'.work/desktop-fixes/active').write_text(str(directory))
            print('Debug request queue ready', flush=True)
            last = time.monotonic()
            while time.monotonic()-last < 1200:
                request = directory/'request.json'
                if not request.exists():
                    time.sleep(.2)
                    continue
                item = json.loads(request.read_text())
                request.unlink()
                last = time.monotonic()
                if item['command'] == 'SHUTDOWN':
                    break
                before = len(lab.serial_text())
                try:
                    if item.get('monitor'):
                        code, output = 0, lab.monitor_command(item['command'])
                    else:
                        code = lab.command(item['command'],item.get('timeout',120))
                        output = lab.serial_text()[before:]
                    reply = dict(code=code,output=output)
                except Exception as failure:
                    reply = dict(error=str(failure),output=lab.serial_text()[before:])
                (directory/('response-'+item['id']+'.json')).write_text(json.dumps(reply))
        raise
    finally:
        if lab.logged_in:
            try:
                lab.command('test -z "$manual" || { kill -TERM "$manual" 2>/dev/null; wait "$manual"; }; true',30)
            except Exception:
                pass
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        result['base_raw_unchanged'] = probe.sha256(seed/'disk.raw') == provenance['raw_sha256']
        (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='observed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
