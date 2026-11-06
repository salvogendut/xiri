#!/usr/bin/env python3
"""Qualify native service ownership and unprivileged desktop sessions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import tempfile
import time
from types import SimpleNamespace

from xiri_lab import Guest, ROOT, load_probe, sha256, source_hashes


def record_result(path, result):
    cleanup_error = None
    if result['status'] == 'passed' and not (result['clean_shutdown'] and result['base_raw_unchanged']):
        cleanup_error = 'Qualification requires a clean halt and unchanged source disk'
        result.update(status='error', error=cleanup_error)
    path.write_text(json.dumps(result, indent=2)+'\n')
    if cleanup_error:
        raise RuntimeError(cleanup_error)


def main():
    harness_source = Path(__file__).read_bytes()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, default=ROOT/'.work/xiri-image/prepared-seed-20261103-module')
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--guard-only', action='store_true')
    scope.add_argument('--services-only', action='store_true')
    parser.add_argument('--debug-failure', action='store_true')
    args = parser.parse_args()
    seed = args.seed.resolve()
    origin = json.loads((seed/'image-source.json').read_text())
    previous = json.loads((seed/'result.json').read_text())
    assert previous['status'] == 'observed' and previous['clean_shutdown']
    assert sha256(seed/'disk.raw') == origin['raw_sha256']
    bundle = Path(origin['bundle'])
    p = load_probe()
    p.IRIS, p.CI = bundle/'emulator/iris', bundle/'emulator/iris-ci'
    for binary, key in [(p.IRIS,'emulator_sha256'), (p.CI,'ci_client_sha256')]:
        assert sha256(binary) == previous['pin'][key]
    runs = ROOT/'.work/irix-session/runs'; runs.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='ordinary-', dir=runs))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    media = d/'media'; media.mkdir()
    (d/'harness.py').write_bytes(harness_source)
    shutil.copytree(ROOT/'runtime', media/'runtime', ignore=shutil.ignore_patterns('build'))
    sources = {str(f.relative_to(ROOT)):sha256(f) for f in (ROOT/'runtime').rglob('*') if f.is_file() and 'build' not in f.parts}
    for src, dest in {
        'lab/irix-session/descendants.c':'descendants.c',
        'lab/irix-session/guard-tests.sh':'guard-tests.sh',
        'lab/irix-4dwm/type-ready.c':'type.c',
        'lab/irix-filelocks/place-window.c':'place.c',
        'lab/irix-vendor-shell/catalog-input.c':'catalog-input.c',
        'lab/newport-xaa/render-probe.c':'render-probe.c',
    }.items():
        shutil.copyfile(ROOT/src, media/dest); sources[src] = sha256(ROOT/src)
    text = (ROOT/'lab/irix-toolchest-input/inputcheck.c').read_text().replace('XOpenDisplay("127.0.0.1:98")','XOpenDisplay(getenv("DISPLAY"))')
    (media/'input.c').write_text(text)
    sources['lab/irix-toolchest-input/inputcheck.c'] = sha256(ROOT/'lab/irix-toolchest-input/inputcheck.c')
    sources['scripts/probe-xiri-session.py'] = hashlib.sha256(harness_source).hexdigest()
    (media/'SHA256').write_text(''.join(f'SHA256 ({f.relative_to(media)}) = {sha256(f)}\n' for f in sorted(media.rglob('*')) if f.is_file()))
    p.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',media])
    for name in ['disk.raw','nvram.bin']:
        p.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name])
    config = (ROOT/'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(bundle/'tftp')),config,flags=re.M)
    lab = p.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600),d,config_text=config)
    guest = Guest(lab)
    cmd, get, wait_for = guest.command, guest.read_text, guest.wait_for
    r = dict(schema=1,status='error',clean_shutdown=False,scope='services' if args.services_only else 'guard' if args.guard_only else 'services-and-sessions',
        seed=origin,pin=previous['pin'],sources={**source_hashes(),**sources})
    def reboot():
        lab.offset = len(lab.serial_text()); lab.send('shutdown -h now')
        lab.wait('unmounting done',120); lab.wait(r'Option\?',30)
        lab.logged_in = False
        lab.send('5'); lab.wait('>> ',15)
        lab.send('boot -f bootp()/netbsd-XIRI_INDY')
        lab.wait('login: ',600); lab.send('root'); lab.wait('xiri-indy# ',30)
        lab.logged_in = True
        cmd('cd /root/session; export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; ulimit -c 0')

    def capture(name):
        guest.capture(d/(name+'.png'))
        r.setdefault('screenshots',{})[name] = sha256(d/(name+'.png'))

    def survivors(label):
        cmd('test "$(cat /var/run/xiri_famd.pid)" = "$fam_pid" && '
            'test "$(cat /var/run/rpcbind.pid)" = "$rpc_pid" && '
            'kill -0 "$fam_pid" && kill -0 "$rpc_pid" && kill -0 "$side_pid"')
        cmd('printf '+shlex.quote('echo '+label+' > /tmp/xiri-side-shell/'+label+'\n')+' >&9')
        wait_for('test -s /tmp/xiri-side-shell/'+label,20)
        assert get('cat /tmp/xiri-side-shell/'+label).strip() == label
        r.setdefault('survivors',[]).append(label)

    def ready(log):
        wait_for('grep -q "Logs: " '+log)
        cmd('job=$(sed -n "s/.*Logs: //p" '+log+' | head -1); test -d "$job"; '
            'export DISPLAY=127.0.0.1:0')
        if log.startswith('manual-'):
            cmd('export XAUTHORITY="$job/Xauthority"')
        wait_for('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready')
        wait_for("xwininfo -root -tree | grep 'of 18)' >/dev/null")
        cmd("shell_pid=$(sed -n 's/^NATIVE_HANDOFF pid=\\([0-9][0-9]*\\).*/\\1/p' \"$job/handoff\")")
        wait_for('ps -p "$shell_pid" -o comm= | grep -Eq \'^[[:space:]]*sh[[:space:]]*$\'')
        cmd('./place winterm 10 180 983 504')
        cmd(shlex.join(['./type','127.0.0.1:0','winterm',
                       '(id -un; echo "$HOME"; pwd; id -G; echo "$XAUTHORITY") > "$XIRI_SESSION_DIR/shell-proof"\n']))
        wait_for('test -s "$job/shell-proof"')
        proof = get('cat "$job/shell-proof"').splitlines()
        assert proof[:3] == ['xiritest','/usr/people/xiritest','/usr/people/xiritest'], proof
        assert '1235' in proof[3].split(), proof
        assert proof[4] == get('printf "%s" "$XAUTHORITY"'), proof
        # The same display must reject a client that lacks the session cookie.
        cmd('if XAUTHORITY=/dev/null xdpyinfo >auth-rejected.log 2>&1; then exit 1; fi')
        render = cmd('./render-probe',120)
        assert 'RENDER_PASS pixels=8536 mismatches=0' in render
        return dict(identity=get('cat "$job/identity"'),shell=proof,render=render,
                    tree=get('xwininfo -root -tree'),job=get('printf "%s" "$job"'))

    def verify_guard(entry):
        entry['guard'] = get('cat "$job/guard.log"')
        assert re.search(r'GUARD .*absent=1 valid=1 .*remaining=0 ',entry['guard'])
        owners = {int(x) for x in re.findall(r'^OWN pid=(\d+) ',entry['guard'],re.M)}
        assert not owners.intersection(r['service_and_side_pids'].values())

    def service_checks():
        cmd('/etc/rc.d/xiri_devices onestart && /etc/rc.d/rpcbind onestart && /etc/rc.d/xiri_famd start')
        absent = "rpcinfo -p 127.0.0.1 | awk '$1 == 391002 && $2 == 1 {found=1} END {exit found}'"
        r['cycles'] = []
        for _ in range(2):
            r['cycles'].append(cmd('/etc/rc.d/xiri_famd status && /etc/rc.d/xiri_famd stop && '
                '! pgrep -x famd && '+absent+' && /etc/rc.d/xiri_famd start && /etc/rc.d/xiri_famd status'))
        r['restart'] = cmd('old=$(cat /var/run/xiri_famd.pid); /etc/rc.d/xiri_famd restart && '
            'test "$old" != "$(cat /var/run/xiri_famd.pid)" && /etc/rc.d/xiri_famd status')
        # An external daemon must not be adopted or have its registration removed.
        cmd('owned=$(cat /var/run/xiri_famd.pid); mv /var/run/xiri_famd.pid /var/run/xiri_famd.saved; '
            'if /etc/rc.d/xiri_famd onestart >unowned.log 2>&1; then exit 1; fi; '
            'kill -0 "$owned" && test ! -f /var/run/xiri_famd.pid && '
            'rpcinfo -p 127.0.0.1 | grep 391002')
        r['unowned_refusal'] = get('cat unowned.log')
        assert 'already running outside' in r['unowned_refusal']
        cmd('mv /var/run/xiri_famd.saved /var/run/xiri_famd.pid && /etc/rc.d/xiri_famd stop && '
            '! pgrep -x famd && '+absent+' && /etc/rc.d/rpcbind stop && ! pgrep -x rpcbind')
        r['service_script_sha256'] = get('sha256 /etc/rc.d/xiri_famd').strip().split(' = ')[1]
        assert r['service_script_sha256'] == sources['runtime/rc.d/xiri_famd']
        print('Service stop/start, restart, unregistration and external-owner refusal passed',flush=True)

    def desktop_checks():
        cmd('for name in type place catalog-input input; do '
            'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include "$name.c" '
            '-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o "$name" || exit; done; '
            'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include render-probe.c '
            '-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lXrender -lX11 -o render-probe',300)
        cmd('groupadd -g 1235 xiritest-extra && usermod -G xiritest-extra xiritest')
        reboot()
        # These must already be running from rc.d; do not start them here.
        r['boot_services'] = cmd('/etc/rc.d/rpcbind status && /etc/rc.d/xiri_famd status && '
            'test -f /var/run/xiri-pty-ready && '
            'modstat | grep -E "^compat_irix_o32[[:space:]]+exec[[:space:]]+filesys"')
        cmd('fam_pid=$(cat /var/run/xiri_famd.pid); rpc_pid=$(cat /var/run/rpcbind.pid); '
            'mkdir -p /tmp/xiri-side-shell && chown xiritest:xiritest /tmp/xiri-side-shell && '
            'mkfifo /tmp/xiri-side-shell/input && chown xiritest:xiritest /tmp/xiri-side-shell/input')
        # su's PAM supervisor changes the foreground group of its stderr tty.
        # This independent background login must not acquire the test console.
        cmd("su -l xiritest -c 'echo $$ >/tmp/xiri-side-shell/pid; exec /bin/sh </tmp/xiri-side-shell/input >/tmp/xiri-side-shell/output 2>&1' </dev/null >/tmp/xiri-side-shell/login.log 2>&1 & side_su=$!; exec 9>/tmp/xiri-side-shell/input; side_pid=$(cat /tmp/xiri-side-shell/pid)")
        r['service_and_side_pids'] = dict(zip(['fam','rpcbind','shell'],map(int,get('printf "%s\\n" "$fam_pid" "$rpc_pid" "$side_pid"').split())))
        survivors('before')
        r['idempotent_start'] = cmd('/etc/rc.d/xiri_devices onestart && /etc/rc.d/xiri_famd onestart')
        survivors('after-service-start')
        r['manual_sessions'] = {}
        for route in ['toolchest','root-menu']:
            cmd('xiri-desktop >manual-'+route+'.log 2>&1 & manual=$!')
            entry = ready('manual-'+route+'.log')
            survivors('during-'+route)
            if route == 'toolchest':
                # An overlapping session must fail without touching the live one.
                cmd("if su -l xiritest -c \"env DISPLAY='$DISPLAY' XAUTHORITY='$XAUTHORITY' /usr/local/bin/xiri-session\" >overlap.log 2>&1; then exit 1; fi; grep -q 'already has a window manager' overlap.log")
                # Start the game explicitly for the launch/relaunch regression.
                cmd(shlex.join(['./type', '127.0.0.1:0', 'winterm',
                    '/emul/irix/usr/freeware/bin/xmahjongg >"$XIRI_SESSION_DIR/xmahjongg.out" '
                    '2>"$XIRI_SESSION_DIR/xmahjongg.err" & echo $! >"$XIRI_SESSION_DIR/xmahjongg.pid"\n']))
                wait_for('test -s "$job/xmahjongg.pid" && xwininfo -name xmahjongg >/dev/null',60)
                old_pid = get('cat "$job/xmahjongg.pid"').strip()
                cmd('kill '+old_pid)
                wait_for('! pgrep -x xmahjongg >/dev/null',30)
                tree = get('xwininfo -root -tree')
                match = re.search(r'(0x[0-9a-f]+) "Icon Catalog: [^"\n]*\(Page (\d+) of 18\)',tree)
                assert match, tree
                wid, page = match[1],int(match[2])
                cmd('xset r off')
                for _ in range(abs(9-page)):
                    cmd(shlex.join(['./catalog-input','127.0.0.1:0',wid,'key','Next' if page<9 else 'Prior'])+'; sleep 1')
                cmd('xset r on; ./place "Icon Catalog: Freeware (Page 9 of 18)" 372 450 900 500; sleep 2')
                cmd(shlex.join(['./catalog-input','127.0.0.1:0',wid,'double','1070','682']))
                wait_for("pgrep -u 1234 -f '^/usr/lib/desktop/iconcatalog/pages/C/Freeware/xmahjongg( |$)' >catalog-game.pid",60)
                new_pid = get('cat catalog-game.pid').strip()
                assert new_pid.isdigit() and new_pid != old_pid
                cmd('./place xmahjongg 10 30 1006 614')
                entry['catalog_launch'] = dict(old_pid=int(old_pid),new_pid=int(new_pid))
                capture('catalog-desktop')
                # Uncover Toolchest without changing its menu coordinates.
                cmd('kill '+new_pid)
                wait_for('! pgrep -x xmahjongg >/dev/null',30)
                cmd('./input click 14 39; sleep 1; ./input click 189 243')
            else:
                capture('second-manual-desktop')
                guest.monitor('ptr move 1150 250'); guest.monitor('ptr down right'); time.sleep(2)
                guest.monitor('ptr move 1180 294'); guest.monitor('ptr up right')
            wait_for('test ! -d /var/run/xiri-desktop.lock',90)
            cmd('wait "$manual" && ! pgrep -x Xorg')
            verify_guard(entry)
            survivors('after-'+route)
            r['manual_sessions'][route] = entry
            print('Manual '+route+' logout preserved services and the independent shell',flush=True)

        # Provide an already-running X server, as a future login manager will.
        cmd('mkdir -p /tmp/xiri-login-display && chmod 700 /tmp/xiri-login-display && '
            'export DISPLAY=127.0.0.1:0 XAUTHORITY=/tmp/xiri-login-display/Xauthority; '
            'cookie=$(od -An -N16 -tx1 /dev/urandom | tr -d " \\n"); '
            'xauth -f "$XAUTHORITY" add "$DISPLAY" MIT-MAGIC-COOKIE-1 "$cookie"; unset cookie; '
            'chown -R xiritest:xiritest /tmp/xiri-login-display; '
            'Xorg :0 -config /usr/local/share/xiri/xorg.conf -auth "$XAUTHORITY" -noreset >external-Xorg.log 2>&1 & external_x=$!')
        wait_for('xdpyinfo >/dev/null 2>&1',60)
        r['external_x_pid'] = int(get('printf "%s" "$external_x"'))
        cmd('if xiri-desktop >occupied.log 2>&1; then exit 1; fi; grep -q "already occupied" occupied.log')
        cmd("if su -l xiritest -c 'env DISPLAY=127.0.0.1:97 XAUTHORITY=/dev/null /usr/local/bin/xiri-session' >bad-display.log 2>&1; then exit 1; fi; grep -q 'Cannot connect' bad-display.log")
        # Exercise a failed client launch, then prove another login works.
        cmd("cp /usr/local/libexec/xiri/desktop-clients.sh clients.good; printf '#!/bin/sh\\nexit 7\\n' >/usr/local/libexec/xiri/desktop-clients.sh")
        cmd("su -l xiritest -c \"exec env DISPLAY='$DISPLAY' XAUTHORITY='$XAUTHORITY' /usr/local/bin/xiri-session\" >failed-session.log 2>&1; code=$?; cp clients.good /usr/local/libexec/xiri/desktop-clients.sh; test \"$code\" = 7")
        cmd('job=$(sed -n "s/.*Logs: //p" failed-session.log | head -1)')
        r['failed_startup'] = {}; verify_guard(r['failed_startup'])
        survivors('after-failed-startup')
        r['user_sessions'] = []
        for number in [1,2]:
            cmd("su -l xiritest -c \"exec env DISPLAY='$DISPLAY' XAUTHORITY='$XAUTHORITY' /usr/local/bin/xiri-session\" >user-"+str(number)+'.log 2>&1 & user_session=$!')
            entry = ready('user-'+str(number)+'.log')
            assert entry['job'].startswith('/usr/people/xiritest/.xiri/sessions/')
            capture('user-session-'+str(number))
            cmd('touch "$job/logout"; wait "$user_session"; test "$?" = 0',90)
            verify_guard(entry)
            cmd('kill -0 "$external_x" && xdpyinfo >/dev/null && /usr/local/libexec/xiri/x11-check vacant')
            survivors('after-user-'+str(number))
            r['user_sessions'].append(entry)
            print('User session '+str(number)+' left the existing X server and other login alive',flush=True)
        cmd('kill "$external_x"; wait "$external_x" || :; printf "exit\\n" >&9; exec 9>&-; wait "$side_su"')
        r['service_stop'] = cmd('/etc/rc.d/xiri_famd stop && ! pgrep -x famd && '
            '/etc/rc.d/rpcbind stop && ! pgrep -x rpcbind')
        cmd('! pgrep -x Xorg && ! pgrep -u 1234 && test ! -d /var/run/xiri-desktop.lock')
        # Record the install and generated boot configuration for reuse.
        paths = ['/usr/local/bin/'+x for x in ['xiri-desktop','xiri-session','xiri-launch','xiri-logout']]
        paths += ['/usr/local/libexec/xiri/'+x for x in ['session-guard','x11-check','desktop-clients.sh','setup-pty.sh']]
        paths += ['/usr/libexec/xiri-shell','/etc/xiri/session.conf','/etc/xiri/fam.conf']
        paths += ['/etc/rc.d/'+x for x in ['xiri_devices','xiri_famd']]
        paths += ['/etc/rc.conf.d/'+x for x in ['xiri_devices','xiri_famd','rpcbind']]
        listing = get('sha256 '+shlex.join(paths))
        r['installed_files'] = dict(re.findall(r'^SHA256 \((.+)\) = ([0-9a-f]{64})$',listing,re.M))
        assert len(r['installed_files']) == len(paths)
        r['service_log'] = get('tail -100 /var/log/xiri-fam.log')
        r['native_after'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')

    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 >/root/session-media.log && mkdir -p /root/session && cp -R runtime /root/session/ && cp *.c *.sh /root/session/ && cd /root/session')
        cmd('cd runtime && make && sh install.sh --enable-services && cd ..',300)
        if args.services_only:
            service_checks()
            r['status'] = 'passed'
            return 0
        cmd('cc -O2 -Wall -Wextra -Werror descendants.c -o descendants && mkdir -p /tmp/xiri-guard-tests && cp descendants guard-tests.sh /tmp/xiri-guard-tests/ && chown -R xiritest:xiritest /tmp/xiri-guard-tests && chmod 755 /tmp/xiri-guard-tests/descendants && chmod 644 /tmp/xiri-guard-tests/guard-tests.sh',180)
        cmd("su -l xiritest -c 'sh /tmp/xiri-guard-tests/guard-tests.sh /tmp/xiri-guard-tests' >guard-tests.log 2>&1",180)
        r['guard_tests'] = get('cat guard-tests.log; cat /tmp/xiri-guard-tests/*.log')
        assert 'SESSION_GUARD_TESTS_OK' in r['guard_tests']
        print('Descendant guard lifecycle checks passed',flush=True)
        if not args.guard_only:
            desktop_checks()
        r['status'] = 'passed'
    except Exception as error:
        r['error'] = str(error)
        print('Failed: '+str(error),flush=True)
        if args.debug_failure and lab.logged_in:
            (d/'ready').write_text('ready\n')
            print('Debug requests: '+str(d/'request.json'),flush=True)
            last = time.monotonic()
            while time.monotonic()-last < 600:
                request = d/'request.json'
                if not request.exists(): time.sleep(.2); continue
                item = json.loads(request.read_text()); request.unlink(); last=time.monotonic()
                if item['command'] == 'SHUTDOWN': break
                try:
                    output = guest.monitor(item['command']) if item.get('monitor') else (get if item.get('read') else cmd)(item['command'],item.get('timeout',120))
                    reply = dict(code=0,output=output)
                except Exception as failure:
                    reply = dict(error=str(failure))
                (d/('response-'+item['id']+'.json')).write_text(json.dumps(reply))
        raise
    finally:
        lab.close()
        r['clean_shutdown'] = lab.clean_shutdown
        r['base_raw_unchanged'] = sha256(seed/'disk.raw') == origin['raw_sha256']
        record_result(d/'result.json', r)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
