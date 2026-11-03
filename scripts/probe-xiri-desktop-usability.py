#!/usr/bin/env python3
"""Qualify graphical console login, desktop logout and native RPC binding."""
import argparse
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
from xiri_lab import Guest, load_probe, source_hashes
p = load_probe()
FILES = {
    'xiri-desktop.sh':'/usr/local/bin/xiri-desktop',
    'xiri-logout.sh':'/usr/local/bin/xiri-logout',
    'manual-session.sh':'/usr/local/libexec/xiri/manual-session.sh',
    'setup-pty.sh':'/usr/local/libexec/xiri/setup-pty.sh',
    'toolchest.chestrc':'/usr/local/share/xiri/toolchest.chestrc',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--debug-failure', action='store_true')
    parser.add_argument('--seed', type=Path, default=ROOT/'.work/xiri-image/prepared-seed-20261102-services')
    parser.add_argument('--kernel-build', type=Path, default=ROOT/'.work/netbsd-irix-desktop-build')
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--iris-bin-dir', type=Path, default=ROOT/'.work/target-netbsd64/release')
    parser.add_argument('--xorg-config', type=Path, help='install and qualify an alternate Xorg configuration')
    parser.add_argument('--newport-driver', type=Path, help='install a native Newport Xorg module and check its Render path')
    parser.add_argument('--check-xmahjongg', action='store_true', help='exercise the vendor game within the desktop')
    parser.add_argument('--arrange-winterm', action='store_true',
                        help='record and resize winterm for diagnostic interaction checks')
    args = parser.parse_args()
    seed = args.seed.resolve()
    kernel_build = args.kernel_build.resolve()
    old = json.loads((seed/'result.json').read_text())
    pin = json.loads(args.baseline.read_text()) if args.baseline else old['pin']
    provenance = json.loads((seed/'image-source.json').read_text())
    assert old['status'] == 'observed' and old['clean_shutdown']
    assert p.sha256(seed/'disk.raw') == provenance['raw_sha256']
    rpc = json.loads((ROOT/'.work/native-rpcbind/result.json').read_text())
    assert rpc['status'] == 'built'
    for name, digest in rpc['sources'].items():
        assert p.sha256(ROOT.parent/'NetBSD-nixbench'/name) == digest
    rpcbin = ROOT/'.work/native-rpcbind/rpcbind'
    assert p.sha256(rpcbin) == rpc['rpcbind_sha256']
    p.IRIS = args.iris_bin_dir.resolve()/'iris'
    p.CI = args.iris_bin_dir.resolve()/'iris-ci'
    assert p.sha256(p.IRIS) == pin['emulator_sha256']
    runs = ROOT/'.work/desktop-usability'
    runs.mkdir(exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='ordinary-', dir=runs))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    shutil.copyfile(Path(__file__), d/'harness.py')
    media = d/'media'; media.mkdir()
    for name in [*FILES, 'manual-guard.c']:
        source = ROOT/('lab/irix-4dwm' if name == 'setup-pty.sh' else
                       'lab/irix-installed-desktop')/name
        shutil.copyfile(source, media/name)
    shutil.copyfile(rpcbin, media/'rpcbind')
    if args.xorg_config:
        shutil.copyfile(args.xorg_config, media/'xorg.conf')
    if args.newport_driver:
        shutil.copyfile(args.newport_driver, media/'newport_drv.so')
        shutil.copyfile(ROOT/'lab/newport-xaa/render-probe.c', media/'render-probe.c')
    for name, source, key in [('netbsd',kernel_build/'kernel-media/netbsd','native_kernel_sha256'),
                             ('netbsd.boot',kernel_build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256')]:
        assert p.sha256(source)==pin[key]
        shutil.copyfile(source,media/name)
    # This helper injects X events; console login itself uses emulated PS/2 keys.
    input_source = (ROOT/'lab/irix-toolchest-input/inputcheck.c').read_text()
    input_source = input_source.replace('XOpenDisplay("127.0.0.1:98")', 'XOpenDisplay(getenv("DISPLAY"))')
    input_source = input_source.replace('&& argc == 4)', '&& (argc == 4 || argc == 5))')
    input_source = input_source.replace('XTestFakeButtonEvent(d, 1,', 'XTestFakeButtonEvent(d, argc == 5 ? atoi(argv[4]) : 1,')
    (media/'input.c').write_text(input_source)
    shutil.copyfile(ROOT/'lab/irix-4dwm/type-ready.c', media/'type.c')
    if args.arrange_winterm or args.check_xmahjongg:
        shutil.copyfile(ROOT/'lab/irix-filelocks/place-window.c', media/'place.c')
    installed = dict(old['installed_files'])
    installed.update({dest:p.sha256(media/name) for name,dest in FILES.items()})
    installed['/usr/sbin/rpcbind'] = rpc['rpcbind_sha256']
    installed.update({'/netbsd':pin['native_kernel_sha256'],'/netbsd.boot':pin['boot_kernel_sha256']})
    if args.xorg_config:
        installed['/usr/local/share/xiri/xorg.conf'] = p.sha256(media/'xorg.conf')
    if args.newport_driver:
        installed['/usr/X11R7/lib/modules/drivers/newport_drv.so'] = p.sha256(media/'newport_drv.so')
    (media/'SHA256').write_text(''.join(f'SHA256 ({f.name}) = {p.sha256(f)}\n' for f in sorted(media.iterdir())))
    p.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',media])
    for name in ['disk.raw','nvram.bin']:
        p.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name])
    config = (ROOT/'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(kernel_build/'tftp')), config, flags=re.M)
    lab = p.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600),d,config_text=config)
    guest = Guest(lab)
    cmd = guest.command
    get = guest.read_text
    r = dict(status='error',clean_shutdown=False,pin=pin,staged=old['staged'],
             base_image=provenance,base_seed_result_sha256=p.sha256(seed/'result.json'),
             payload_manifest_sha256=old['payload_manifest_sha256'],
             desktop_dimensions=[1280,1024],desktop_services=True,
             native_fam_build=old['native_fam_build'],bitmap_ledger_sha256=old['bitmap_ledger_sha256'],
             installed_files=installed,native_rpcbind_build=rpc,
             sources={**source_hashes(), str(Path(__file__).relative_to(ROOT)):p.sha256(Path(__file__)),
                      **{str(f.relative_to(ROOT)):p.sha256(f) for f in media.iterdir()}},
             artwork_source_run=str(seed.relative_to(ROOT)),
             artwork_source_result_sha256=p.sha256(seed/'result.json'),
             icon_artwork=bool(old.get('freeware_target_notifications')),
             logout={})
    if old.get('desktop_behavior'):
        r['desktop_behavior'] = old['desktop_behavior']
    if args.xorg_config:
        r['xorg_configuration'] = dict(source=str(args.xorg_config), sha256=p.sha256(media/'xorg.conf'),
            acceleration_requested='Option "NoAccel" "false"' in args.xorg_config.read_text())
    if args.newport_driver:
        r['newport_driver'] = dict(source=str(args.newport_driver.resolve()),
            sha256=p.sha256(media/'newport_drv.so'),
            source_pin=json.loads((ROOT/'lab/newport-xaa/source.json').read_text()),
            patch_sha256=p.sha256(ROOT/'lab/newport-xaa/texture-coordinates.patch'))

    def keytext(text):
        lab.monitor_command('key type '+text)
        lab.monitor_command('key Enter')

    def capture(name):
        guest.capture(d/(name+'.png'))
        r[name+'_png_sha256'] = p.sha256(d/(name+'.png'))

    wait_for = guest.wait_for

    symbols = kernel_build/'obj/sys/arch/sgimips/compile'/Path(pin['config_path']).name/'netbsd.gdb'
    assert p.sha256(symbols) == pin['debug_kernel_sha256']
    symbol_table = subprocess.check_output(['nm', str(symbols)], text=True)
    msgbuf_symbol = int(re.search(r'^([0-9a-f]+) [BbDd] msgbufp$',symbol_table,re.M)[1],16)

    def kernel_log():
        lab.monitor_command('stop')
        try:
            def words(address, count):
                out = lab.monitor_command(f'mem 0x{address:x} {count} d')
                values = [int(value,16) for value in re.findall(r'^0x[0-9a-f]+: (0x[0-9a-f]+)',out,re.M)]
                if len(values) != count: raise RuntimeError('short kernel memory read: '+out[:300])
                return values
            address = words(msgbuf_symbol,1)[0]
            # The PROM clears KX: use the equivalent sign-extended KSEG0
            # alias for this RAM buffer after halt, rather than XKPHYS.
            if address >> 62 == 2:
                physical = address & ((1 << 59)-1)
                assert physical < 0x20000000
                address = 0xffffffff80000000 | physical
            magic, write, read, size = words(address,4)
            assert magic == 0x63061 and 0 <= write < size <= 131072
            data = b''
            for offset in range(0,size,2048):
                values = words(address+32+offset,(min(2048,size-offset)+7)//8)
                data += b''.join(value.to_bytes(8,'big') for value in values)
            data = data[:size]
            return (data[write:]+data[:write]).replace(b'\0',b'').decode(errors='backslashreplace')
        finally:
            lab.monitor_command('start')

    def halt_graphical():
        before = kernel_log()
        lab.send('shutdown -h now')
        deadline = time.monotonic()+120
        while time.monotonic() < deadline:
            time.sleep(3)
            after = kernel_log()
            if after != before and 'unmounting done' in after[-2048:] and 'halting...' in after[-256:]:
                r['shutdown_log'] = after
                lab.logged_in = False
                lab.clean_shutdown = True
                return
        raise RuntimeError('graphical halt did not record clean unmount and halt')

    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 >/root/usability-media.log && mkdir -p /root/usability && cd /root/usability')
        cmd('rm -f graphics-login returned-toolchest returned-root-menu toolchest.log root-menu.log')
        cmd('install -m 444 /cdrom/netbsd /netbsd && install -m 444 /cdrom/netbsd.boot /netbsd.boot')
        if args.xorg_config:
            cmd('install -m 444 /cdrom/xorg.conf /usr/local/share/xiri/xorg.conf')
        if args.newport_driver:
            cmd('install -m 444 /cdrom/newport_drv.so /usr/X11R7/lib/modules/drivers/newport_drv.so')
            cmd('cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/render-probe.c -lXrender -lX11 -o render-probe',180)
        for name,dest in FILES.items():
            cmd('install -m '+('555' if name.endswith('.sh') else '444')+' /cdrom/'+name+' '+dest)
        cmd('install -m 555 /cdrom/rpcbind /usr/sbin/rpcbind && cc -O2 -Wall -Wextra -Werror /cdrom/manual-guard.c -o /usr/local/libexec/xiri/manual-guard',180)
        cmd('cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/input.c -lX11 -lXtst -o input && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/type.c -lX11 -lXtst -o type',180)
        if args.arrange_winterm or args.check_xmahjongg:
            cmd('cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/place.c -lX11 -o place',180)
        cmd("sed -e '/^constty/s/on secure/off secure/' -e '/^ttyE0/s/off secure/on secure/' -e '/^ttyZ0/s/off secure/on secure local softcar/' /etc/ttys >/etc/ttys.new && mv /etc/ttys.new /etc/ttys")
        # Allocate a text VT on serial diagnostic boots too; graphics boots
        # already have screen zero. init starts the gettys after rc finishes.
        cmd("grep -F '/usr/sbin/wsconscfg -f /dev/ttyEcfg 0' /etc/rc.local >/dev/null || printf '\\n# Xiri local display login.\\n/usr/sbin/wsconscfg -f /dev/ttyEcfg 0 2>/dev/null || true\\n' >>/etc/rc.local")
        for dest in ['/usr/local/libexec/xiri/manual-guard','/etc/ttys','/etc/rc.local']:
            installed[dest] = get('sha256 -q '+dest).strip()
        r['native_before'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        # Save the serial configuration before changing only the manual profile.
        lab.monitor_command('rtc save')
        shutil.copyfile(d/'nvram.bin',d/'nvram-serial.bin')
        lab.offset = len(lab.serial_text()); lab.send('shutdown -h now')
        lab.wait('unmounting done',90); lab.wait(r'Option\?',30)
        lab.logged_in = False
        lab.send('5'); lab.wait(r'>> ',10)
        for setting in ['AutoLoad Yes','-f console g']:
            lab.offset = len(lab.serial_text()); lab.send('setenv '+setting); lab.wait(r'>> ',10)
        lab.monitor_command('rtc save')
        shutil.copyfile(d/'nvram.bin',d/'nvram-graphics.bin')
        r['graphics_nvram_sha256'] = p.sha256(d/'nvram-graphics.bin')
        lab.offset = len(lab.serial_text())
        lab.monitor_command('reset'); lab.monitor_command('start')
        lab.wait('login: ',600); lab.send('root'); lab.wait('xiri-indy# ',30)
        lab.logged_in = True
        r['graphics_console'] = cmd('sysctl kern.consdev | grep ttyE0 && tty | grep ttyZ0')
        lab.monitor_command('disp compositor sw')
        keytext('root')
        wait_for("who | awk '$1 == \"root\" && $2 == \"ttyE0\" {found=1} END {exit !found}'")
        keytext('tty > /root/usability/graphics-login')
        wait_for('test -s /root/usability/graphics-login')
        assert get('cat /root/usability/graphics-login').strip() == '/dev/ttyE0'
        capture('graphics-login')
        cmd('cd /root/usability; export PATH=/usr/X11R7/bin:$PATH DISPLAY=127.0.0.1:0')
        rpc_errors_before = int(get("awk '/rpcbind: cannot bind/ {n++} END {print n+0}' /var/log/messages").strip())
        cmd('tail -n 0 -F /var/log/messages >rpc-watch.log 2>rpc-watch.err & '
            'rpc_watch=$!; sleep 2; kill -0 "$rpc_watch"; logger -t xiri-rpc-watch XIRI_RPC_WATCH_START')
        wait_for('grep -q XIRI_RPC_WATCH_START rpc-watch.log',30)
        for route in ['toolchest','root-menu']:
            keytext('xiri-desktop >/root/usability/'+route+'.log 2>&1')
            wait_for('grep -q "Logs: " '+route+'.log')
            cmd('job=$(sed -n "s/.*Logs: //p" '+route+'.log | head -1); test -d "$job"')
            wait_for("xwininfo -root -tree | grep 'of 18)' >/dev/null")
            # A mapped xwsh window can precede its PTY and shell. Typing then
            # loses the beginning of a command, even though the window is ready.
            wait_for('test -s "$job/handoff"')
            cmd("shell_pid=$(sed -n 's/^NATIVE_HANDOFF pid=\\([0-9][0-9]*\\).*/\\1/p' \"$job/handoff\"); test -n \"$shell_pid\"")
            wait_for('ps -p "$shell_pid" -o comm= | grep -Eq \'^[[:space:]]*sh[[:space:]]*$\'')
            winterm_geometry = None
            if args.arrange_winterm:
                winterm_geometry = get('xwininfo -name winterm; xprop -name winterm WM_NORMAL_HINTS')
                cmd('./place winterm 10 180 983 504')
            for command, output in [
                    ('echo GRAPHICAL_SHELL_OK', 'shell-proof'), ('pwd', 'shell-pwd'),
                    ('id -un', 'shell-user'), ('echo "$HOME"', 'shell-home')]:
                cmd('./type "$DISPLAY" winterm '+shlex.quote(
                    command+' > "$XIRI_SESSION_DIR/'+output+'"\n'))
                wait_for('test -s "$job/'+output+'"')
            assert get('cat "$job/shell-proof"').strip() == 'GRAPHICAL_SHELL_OK'
            assert get('cat "$job/shell-pwd"').strip() == '/usr/people/xiritest'
            assert get('cat "$job/shell-user"').strip() == 'xiritest'
            assert get('cat "$job/shell-home"').strip() == '/usr/people/xiritest'
            if old.get('vendor_shell') or pin['ident'] == 'XIRI_IRIX_VENDOR_SHELL_20261102':
                proof = cmd(shlex.join(['su', '-m', 'xiritest', '-c',
                    shlex.join(['/emul/irix/bin/sh', '-c',
                        'echo NULL_OK >/dev/null && echo IRIX_SHELL_IMAGE_OK'])]))
                assert '\nIRIX_SHELL_IMAGE_OK\n' in proof and '_RC=0' in proof
                r['vendor_shell'] = proof
            entry = dict(tree=get('xwininfo -root -tree'),rpc_log=get('cat "$job/rpcbind.log"'),
                         bindings=get('netstat -an -f inet | grep 111'),
                         registration=get('rpcinfo -p 127.0.0.1'))
            if args.xorg_config:
                entry['xorg_log'] = get('cat /var/log/Xorg.0.log')
                entry['xaa_enabled'] = 'Using XFree86 Acceleration Architecture (XAA)' in entry['xorg_log']
                if 'Option "NoAccel" "false"' in args.xorg_config.read_text():
                    assert entry['xaa_enabled']
            if args.arrange_winterm:
                entry['winterm_geometry_before_arrangement'] = winterm_geometry
                entry['winterm_arranged'] = [10, 180, 983, 504]
            entry['identity'] = dict(user='xiritest', home='/usr/people/xiritest', cwd='/usr/people/xiritest')
            assert 'cannot bind' not in entry['rpc_log']
            assert '127.0.0.1.111' in entry['bindings'] and '*.111' not in entry['bindings']
            assert re.search(r'391002\s+1\s+tcp',entry['registration'])
            capture(route+'-desktop')
            if args.newport_driver:
                entry['render_probe'] = cmd('./render-probe',120)
                assert 'RENDER_PASS pixels=8536 mismatches=0' in entry['render_probe']
            if args.check_xmahjongg and route == 'toolchest':
                # The session starts a demonstration game. Close it before
                # creating the fixed board so window-name lookup is unambiguous.
                cmd('./type "$DISPLAY" xmahjongg q')
                wait_for('! xwininfo -name xmahjongg >/dev/null 2>&1',30)
                cmd('./type "$DISPLAY" winterm '+shlex.quote(
                    '/emul/irix/usr/freeware/bin/xmahjongg --number 12345 > "$XIRI_SESSION_DIR/xmahjongg.log" 2>&1 &\n'))
                wait_for('xwininfo -name xmahjongg > /root/usability/xmahjongg-window')
                cmd('./place xmahjongg 150 270 1006 614; sleep 5')
                entry['xmahjongg'] = dict(window=get('xwininfo -name xmahjongg'),
                    extensions=get('xdpyinfo | grep -E "Composite|RENDER"'),
                    board=12345)
                assert 'Depth: 32' in entry['xmahjongg']['window']
                assert 'Composite' in entry['xmahjongg']['extensions']
                capture('xmahjongg-initial')
                cmd('./type "$DISPLAY" xmahjongg h; sleep 1')
                cmd('./type "$DISPLAY" xmahjongg '+shlex.quote('\n')+'; sleep 3')
                capture('xmahjongg-move')
                cmd('./type "$DISPLAY" xmahjongg u; sleep 2')
                capture('xmahjongg-undo')
                cmd('./place xmahjongg 170 290 1050 650; sleep 2; ./place xmahjongg 150 270 1006 614; sleep 2')
                capture('xmahjongg-redraw')
                entry['xmahjongg']['log'] = get('cat "$job/xmahjongg.log"')
                cmd('./type "$DISPLAY" xmahjongg q')
                wait_for('! xwininfo -name xmahjongg >/dev/null 2>&1',30)
            if route == 'toolchest':
                cmd('./input click 14 39; sleep 1; ./input click 189 243')
            else:
                # The vendor root menu uses press-drag-release. A complete
                # click dismisses it before a later keyboard selection.
                lab.monitor_command('ptr move 1150 250')
                lab.monitor_command('ptr down right')
                time.sleep(2)
                capture('root-menu-open')
                lab.monitor_command('ptr move 1180 294')
                lab.monitor_command('ptr up right')
            wait_for('test ! -d /var/run/xiri-desktop.lock',60)
            cmd('! pgrep -x Xorg && ! pgrep -x famd && ! pgrep -x rpcbind')
            assert not get("ps -axo uid,pid,comm | awk '$1 == 1234 {print}'").strip()
            entry['guard'] = get('cat "$job/guard.log"')
            assert 'absent=1 valid=1' in entry['guard']
            keytext('echo '+route+' > /root/usability/returned-'+route)
            wait_for('test -s returned-'+route)
            entry['returned_to_graphics_shell'] = get('cat returned-'+route).strip() == route
            assert entry['returned_to_graphics_shell']
            r['logout'][route] = entry
            print(route+' logout returned to graphical shell',flush=True)
        capture('graphics-after-logout')
        rpc_errors_after = int(get("awk '/rpcbind: cannot bind/ {n++} END {print n+0}' /var/log/messages").strip())
        cmd('kill -0 "$rpc_watch" && logger -t xiri-rpc-watch XIRI_RPC_WATCH_END')
        wait_for('grep -q XIRI_RPC_WATCH_END rpc-watch.log',30)
        cmd('kill "$rpc_watch"; wait "$rpc_watch" || :')
        r['rpcbind_warning_events'] = get('cat rpc-watch.log')
        assert 'rpcbind: cannot bind' not in r['rpcbind_warning_events']
        r['rpcbind_warning_check'] = dict(before=rpc_errors_before,after=rpc_errors_after,new_warnings=0)
        r['native_after'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        all_files = dict(old['staged']); all_files.update(installed)
        # Verify unchanged vendor payload and every installed helper in the guest.
        (d/'verified-files.json').write_text(json.dumps(all_files,indent=2)+'\n')
        for dest,digest in installed.items():
            cmd('test "$(sha256 -q '+shlex.quote(dest)+')" = '+digest)
        # The seed raw hash proves inherited resources; this cycle writes only
        # the enumerated native helpers/configuration, never vendor resources.
        r.update(guest_payload_verified=True,executable_permissions_applied=True,
                 persistent_helpers_installed=True,native_x11_after=True,graphics_boot=True)
        halt_graphical()
        r['status'] = 'observed'
    except Exception as error:
        r['error'] = str(error)
        print('Failed: '+str(error),flush=True)
        if args.debug_failure and lab.logged_in:
            (d/'ready').write_text('ready\n')
            (ROOT/'.work/desktop-fixes/active').write_text(str(d))
            print('Debug request queue ready',flush=True)
            last = time.monotonic()
            while time.monotonic()-last < 1200:
                request = d/'request.json'
                if not request.exists(): time.sleep(.2); continue
                item = json.loads(request.read_text()); request.unlink(); last = time.monotonic()
                if item['command'] == 'SHUTDOWN': break
                try:
                    output = lab.monitor_command(item['command']) if item.get('monitor') else cmd(item['command'],item.get('timeout',120))
                    reply = dict(code=0,output=output)
                except Exception as failure:
                    reply = dict(error=str(failure),output='')
                (d/('response-'+item['id']+'.json')).write_text(json.dumps(reply))
        raise
    finally:
        if lab.logged_in and 'graphics_console' in r:
            try:
                lab.send('\x03', newline=False)
                cmd('for job in /var/tmp/xiri-desktop/session.*; do touch "$job/logout"; done; sleep 3',30)
                halt_graphical()
            except Exception as error:
                r['cleanup_error'] = str(error)
        lab.close()
        r['clean_shutdown'] = lab.clean_shutdown
        if (d/'nvram-serial.bin').exists(): shutil.copyfile(d/'nvram-serial.bin',d/'nvram.bin')
        r['base_raw_unchanged'] = p.sha256(seed/'disk.raw') == provenance['raw_sha256']
        (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
