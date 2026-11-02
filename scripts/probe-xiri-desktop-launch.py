#!/usr/bin/env python3
"""Upgrade a prepared guest with desktop services and test original menus."""
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
    'xiri-logout.sh': '/usr/local/bin/xiri-logout',
    'manual-session.sh': '/usr/local/libexec/xiri/manual-session.sh',
    'toolchest.chestrc': '/usr/local/share/xiri/toolchest.chestrc',
    'xorg.conf': '/usr/local/share/xiri/xorg.conf',
    'fam.conf': '/usr/local/share/xiri/fam.conf',
}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed', type=Path, default=ROOT/'.work/xiri-image/prepared-seed-20261102')
    p.add_argument('--debug-failure', action='store_true',
                   help='Keep a failed guest available through the diagnostic request queue')
    a = p.parse_args()
    seed = a.seed.resolve()
    previous = json.loads((seed/'result.json').read_text())
    provenance = json.loads((seed/'image-source.json').read_text())
    assert previous['status'] == 'observed' and previous['clean_shutdown']
    assert previous['guest_payload_verified'] and previous['persistent_helpers_installed']
    assert probe.sha256(seed/'disk.raw') == provenance['raw_sha256']
    pin = json.loads((ROOT/'lab/irix-lxstat/baseline.json').read_text())
    probe.IRIS = ROOT/'.work/target-netbsd64/release/iris'
    probe.CI = ROOT/'.work/target-netbsd64/release/iris-ci'
    assert probe.sha256(probe.IRIS) == pin['emulator_sha256']
    runs = ROOT/'.work/desktop-launch'
    runs.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix='ordinary-', dir=runs))
    print('Results: '+str(directory.relative_to(ROOT)), flush=True)
    shutil.copyfile(Path(__file__), directory/'harness.py')
    media = directory/'media'
    media.mkdir()
    for name in FILES:
        shutil.copyfile(ROOT/'lab/irix-installed-desktop'/name, media/name)
    shutil.copyfile(ROOT/'lab/irix-installed-desktop/manual-guard.c', media/'manual-guard.c')
    kernel = ROOT/'.work/netbsd-irix-desktop-build'
    extras = {
        'netbsd': (kernel/'kernel-media/netbsd', '/netbsd', pin['native_kernel_sha256']),
        'netbsd.boot': (kernel/'tftp/netbsd-XIRI_INDY', '/netbsd.boot', pin['boot_kernel_sha256']),
    }
    fam = json.loads((ROOT/'.work/native-fam/result.json').read_text())
    assert fam['status'] == 'built' and fam['btree_host_passed']
    assert fam['source_manifest_sha256'] == probe.sha256(ROOT/'lab/native-fam/source.json')
    extras['famd'] = (ROOT/'.work/native-fam/fam-2.7.0/src/famd', '/usr/local/sbin/famd', fam['files']['src/famd'])
    extras['btree-native'] = (ROOT/'.work/native-fam/btree-native', '/root/desktop-launch/btree-native', fam['btree_native_sha256'])
    for name,(source,dest,digest) in extras.items():
        assert probe.sha256(source) == digest
        shutil.copyfile(source,media/name)
    bitmaps = json.loads((ROOT/'lab/irix-desktop-bitmaps/copy-ledger.json').read_text())
    payload = ROOT/'.work/irix-desktop-bitmaps/payload.tgz'
    assert probe.sha256(payload) == bitmaps['payload_sha256']
    shutil.copyfile(payload,media/'bitmaps.tgz')
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
    staged.update({r['netbsd_destination']: r['sha256'] for r in bitmaps['files'] if r['type'] == 'file'})
    (media/'STAGED').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in sorted(staged.items())))
    perms = json.loads((ROOT/'lab/irix-installed-desktop/permissions.json').read_text())
    (media/'permissions.sh').write_text('set -eu\n'+''.join('test -x '+shlex.quote(path)+'\n' for path in perms['files']))
    installed = {dest: probe.sha256(media/name) for name,dest in FILES.items()}
    installed.update({dest:digest for source,dest,digest in extras.values()})
    (media/'INSTALLED').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in installed.items()))
    sources = {str(path.relative_to(ROOT)):probe.sha256(path) for path in [Path(__file__),
        ROOT/'scripts/probe-netbsd.py', ROOT/'lab/irix-4dwm/type-ready.c',
        ROOT/'lab/irix-toolchest-input/inputcheck.c',
        ROOT/'lab/irix-installed-desktop/manual-guard.c',
        *[ROOT/'lab/irix-installed-desktop'/name for name in FILES]]}
    (media/'SHA256').write_text(''.join(f'SHA256 ({path.name}) = {probe.sha256(path)}\n' for path in sorted(media.iterdir())))
    probe.run(['genisoimage','-quiet','-R','-J','-o',directory/'probe.iso',media])
    for name in ['disk.raw','nvram.bin']:
        probe.run(['cp','--reflink=auto','--sparse=always',seed/name,directory/name])
    config = (ROOT/'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(kernel/'tftp')), config, flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600),directory,config_text=config)
    def paced_send(text, newline=True):
        data = (text + ('\r' if newline else '')).encode('ascii')
        for byte in data:
            lab.serial.sendall(bytes([byte]))
            time.sleep(.005)
    lab.send = paced_send
    result = dict(status='error',clean_shutdown=False,pin=pin,staged=staged,
        base_image=provenance,base_seed_result_sha256=probe.sha256(seed/'result.json'),
        sources=sources,installed_files=installed,launches={},desktop_dimensions=[1280,1024],
        desktop_services=True,native_fam_build=fam,bitmap_ledger_sha256=probe.sha256(ROOT/'lab/irix-desktop-bitmaps/copy-ledger.json'),
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

    def wait_window(title):
        cmd('(tries=0; until xwininfo -root -tree | grep -F '+shlex.quote(title)+
            ' >/dev/null; do kill -0 "$manual" || exit 1; tries=$((tries+1)); '
            'test "$tries" -lt 60 || exit 1; sleep 2; done)',180)

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
        cmd(f'./input focus {wid}; ./input click {x+5} {y+14+row*26}; sleep 1; ./input click {x+180} {y+item_y}; sleep 3')

    try:
        lab.start()
        result['compositor'] = lab.monitor_command('disp compositor sw')
        assert 'Compositor: sw' in result['compositor']
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 > /root/update-media.log && sh permissions.sh && mkdir -p /root/desktop-launch && cd /root/desktop-launch',300)
        result['inherited_payload_verified_by_raw_hash'] = True
        result['executable_permissions_applied'] = True
        for name,dest in FILES.items():
            cmd('install -m '+('555' if name.endswith('.sh') else '444')+' /cdrom/'+name+' '+dest)
        cmd('cc -O2 -Wall -Wextra -Werror /cdrom/manual-guard.c -o /usr/local/libexec/xiri/manual-guard',180)
        installed['/usr/local/libexec/xiri/manual-guard'] = get('sha256 -q /usr/local/libexec/xiri/manual-guard').decode().strip()
        cmd('mkdir -p /usr/local/sbin; tar xzpf /cdrom/bitmaps.tgz -C /; test -d /emul/irix/usr/lib/desktop; if test ! -e /usr/lib/desktop && test ! -L /usr/lib/desktop; then ln -s /emul/irix/usr/lib/desktop /usr/lib/desktop; fi; test "$(readlink /usr/lib/desktop)" = /emul/irix/usr/lib/desktop')
        cmd('getent group xiritest >/dev/null || groupadd -g 1234 xiritest; id xiritest >/dev/null 2>&1 || useradd -u 1234 -g 1234 -d /usr/people/xiritest -s /bin/sh xiritest; test "$(id -u xiritest)" = 1234; test "$(id -g xiritest)" = 1234')
        for name,(source,dest,digest) in extras.items():
            cmd('install -m 555 /cdrom/'+name+' '+dest)
        result['btree_native'] = cmd('./btree-native')
        cmd('ln -sf /bin/sh /usr/local/libexec/xiri/command-shell && sha256 -c /cdrom/INSTALLED && test "$(readlink /usr/local/libexec/xiri/command-shell)" = /bin/sh')
        result['persistent_helpers_installed'] = True
        cmd('cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/input.c -lXtst -lX11 -o input && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/type.c -lXtst -lX11 -o type',180)
        result['native_before'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        cmd('export PATH=/usr/X11R7/bin:$PATH DISPLAY=127.0.0.1:0; /usr/local/bin/xiri-desktop >desktop.log 2>&1 & manual=$!; tries=0; until ./type "$DISPLAY" xmahjongg "" >game-focus.log 2>&1; do kill -0 "$manual" || break; tries=$((tries+1)); test "$tries" -lt 120 || break; sleep 2; done; ./type "$DISPLAY" xmahjongg "" >game-focus.log 2>&1 && job=$(sed -n "s/.*Logs: //p" desktop.log | head -1); test -d "$job"',360)
        result['display'] = get('xdpyinfo').decode()
        assert 'dimensions:    1280x1024 pixels' in result['display']
        result['fam_registration'] = cmd('rpcinfo -p 127.0.0.1 | awk \'$1 == 391002 && $2 == 1 && $3 == "tcp" {print; found=1} END {exit !found}\'')
        wait_window('Page 1 of 18')
        result['catalog_initial_tree'] = get('xwininfo -root -tree').decode()
        assert 'Page 1 of 18' in result['catalog_initial_tree']
        assert 'Trusted Path' not in result['catalog_initial_tree']
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
            menu(0,196)
            marker = f'XIRI_MENU_SHELL_{i+1}_OK'
            cmd('./type "$DISPLAY" winterm '+shlex.quote('echo '+marker+' > "$XIRI_SESSION_DIR/menu-proof-'+str(i)+'"')+' && ./input key Return; sleep 1')
            proof = get('cat "$job/menu-proof-'+str(i)+'"').decode().strip()
            assert proof == marker, (marker, proof)
            result['launches']['winterm-'+str(i+1)] = dict(proof=proof,handoffs=get('cat "$job"/launch-winterm.*/handoff').decode())
            print(marker,flush=True)
            if i == 0:
                cmd('./type "$DISPLAY" winterm "exit" && ./input key Return; sleep 2')
                remove_closed_terminals()
        # Original Find menu: Icon Catalog precedes its generated page list.
        menu(3,185)
        wait_window('Page 1 of 18')
        tree = get('xwininfo -root -tree').decode()
        assert re.search(r'"Icon Catalog(?::[^"\n]*)?"', tree), tree
        logs = get('for d in "$job"/launch-iconcatalog.*; do echo "$d"; cat "$d/stderr"; done').decode()
        result['launches']['iconcatalog'] = dict(tree=tree,logs=logs)
        result['toolchest_custom_applications_menu'] = False
        print('MENU_iconcatalog_OK',flush=True)
        wid = re.search(r'(0x[0-9a-f]+) "Icon Catalog:.*Page 1 of 18', tree)[1]
        # Synthetic key holds can repeat while an emulated client is busy.
        # Disable repeat for this bounded navigation test and observe every page.
        cmd('xset r off && ./input focus '+wid)
        for page in range(2,10):
            cmd('./input key Next')
            wait_window('Page '+str(page)+' of 18)')
        cmd('xset r on')
        wait_window('Icon Catalog: Freeware (Page 9 of 18)')
        result['catalog_freeware_tree'] = get('xwininfo -root -tree').decode()
        assert 'Icon Catalog: Freeware (Page 9 of 18)' in result['catalog_freeware_tree']
        result['freeware_notifications'] = get('grep -E \'"xmahjongg" Exists|Freeware" EndExist\' "$job/fam.log"').decode()
        assert '"xmahjongg" Exists' in result['freeware_notifications']
        cmd('mkdir -p /usr/people/xiritest/XiriTest/Examples; echo "Native NetBSD file viewed by IRIX FileManager." >/usr/people/xiritest/XiriTest/Readme.txt; chown -R 1234:1234 /usr/people/xiritest/XiriTest; su -m xiritest -c "cd /usr/people/xiritest; /usr/local/libexec/xiri/session $job/desktop.env /emul/irix/usr/sbin/fm /usr/people/xiritest/XiriTest" >fm.log 2>&1 & sleep 10')
        wait_window('xiri-indy:/usr/people/xiritest/XiriTest')
        result['filemanager_tree'] = get('xwininfo -root -tree').decode()
        assert 'xiri-indy:/usr/people/xiritest/XiriTest' in result['filemanager_tree']
        cmd('touch /usr/people/xiritest/.desktop-xiri-indy/xiri-event-probe; sleep 3; rm /usr/people/xiritest/.desktop-xiri-indy/xiri-event-probe; sleep 3')
        result['file_notifications'] = get('grep xiri-event-probe "$job/fam.log"').decode()
        assert 'Created' in result['file_notifications'] and 'Deleted' in result['file_notifications']
        (directory/'catalog-fm.xwd').write_bytes(get('xwd -root -silent'))
        result['catalog_fm_xwd_sha256'] = probe.sha256(directory/'catalog-fm.xwd')
        cmd('./type "$DISPLAY" winterm "echo Toolchest launch works" && ./input key Return; sleep 1')
        capture('menu-desktop')
        result['native_x11_after'] = 'dimensions:' in cmd('xdpyinfo | grep dimensions')
        cmd('kill -TERM "$manual"; wait "$manual" || test "$?" = 130; ps -axo uid,pid,comm >remaining.txt; ! awk \'$1 == 1234 { found=1 } END { exit !found }\' remaining.txt; ! pgrep -x famd; ! pgrep -x rpcbind; test ! -d /var/run/xiri-desktop.lock')
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
