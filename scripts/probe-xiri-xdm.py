#!/usr/bin/env python3
"""Qualify native xdm authentication and repeated IRIX desktop sessions."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import signal
import struct
import subprocess
import tempfile
import time
from types import SimpleNamespace

from xiri_lab import Guest, ROOT, load_probe, sha256, source_hashes


def main():
    snapshot = Path(__file__).read_bytes()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, default=ROOT/'.work/xiri-image/prepared-seed-20261103-module')
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
    assert sha256(p.IRIS) == previous['pin']['emulator_sha256']
    assert sha256(p.CI) == previous['pin']['ci_client_sha256']
    runs = ROOT/'.work/irix-xdm/runs'; runs.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='ordinary-', dir=runs))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    media = d/'media'; media.mkdir()
    (d/'harness.py').write_bytes(snapshot)
    shutil.copytree(ROOT/'runtime', media/'runtime', ignore=shutil.ignore_patterns('build'))
    sources = {str(f.relative_to(ROOT)):sha256(f) for f in (ROOT/'runtime').rglob('*') if f.is_file() and 'build' not in f.parts}
    for src, dest in {
        'lab/irix-4dwm/type-ready.c':'type.c',
        'lab/irix-filelocks/place-window.c':'place.c',
        'lab/newport-xaa/render-probe.c':'render-probe.c',
    }.items():
        shutil.copyfile(ROOT/src, media/dest); sources[src] = sha256(ROOT/src)
    sources['scripts/probe-xiri-xdm.py'] = hashlib.sha256(snapshot).hexdigest()
    (media/'SHA256').write_text(''.join(f'SHA256 ({f.relative_to(media)}) = {sha256(f)}\n' for f in sorted(media.rglob('*')) if f.is_file()))
    p.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',media])
    for name in ['disk.raw','nvram.bin']:
        p.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name])
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(bundle/'tftp')),
                    (ROOT/'lab/indy-netbsd/iris.toml').read_text(), flags=re.M)
    lab = p.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600), d, config_text=config)
    guest = Guest(lab)
    cmd, get, wait = guest.command, guest.read_text, guest.wait_for
    r = dict(schema=1,status='error',clean_shutdown=False,seed=origin,pin=previous['pin'],
             sources={**source_hashes(),**sources},sessions=[],screenshots={})

    def capture(name):
        # Capture the ordinary GL scanout, including the graphical greeter.
        guest.monitor('disp compositor gl')
        guest.monitor('screen wait 500 10000')
        guest.monitor('screen shot '+str(d/(name+'.png')))
        # This pinned IRIS exposes two extra scanout columns; active X is 1280.
        assert struct.unpack('>II', (d/(name+'.png')).read_bytes()[16:24]) == (1282,1024)
        r['screenshots'][name] = sha256(d/(name+'.png'))

    def greeter_text(name, tree):
        # Exclude the logo, frame and cursor: a missing-glyph greeter must fail.
        match = re.search(r'"xlogin".*?\s(\d+)x(\d+)\+(\d+)\+(\d+)', tree)
        assert match, tree
        width,height,x,y = map(int,match.groups())
        crop = f'{width//2}x{height-30}+{x+20}+{y+15}'
        pixels = subprocess.check_output(['magick',str(d/(name+'.png')),'-crop',crop,
                                          '+repage','-depth','8','RGB:-'])
        dark = sum(max(pixels[i:i+3]) < 80 for i in range(0,len(pixels),3))
        light = sum(min(pixels[i:i+3]) > 200 for i in range(0,len(pixels),3))
        assert 500 < dark < len(pixels)//12 and light > len(pixels)//6, ('Missing greeter text/background',dark,light)
        r.setdefault('greeter_text',{})[name] = dict(crop=crop,dark_pixels=dark,light_pixels=light)

    def greeter():
        # xdm supplies an absolute argv[0], also used as NetBSD's process name.
        wait('test -s /tmp/.X0-lock && kill -0 "$(cat /tmp/.X0-lock)"',60)
        cmd('export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | '
            'awk \'$1 == "/usr/X11R7/bin/Xorg" {for (i=1;i<NF;i++) if ($i == "-auth") print $(i+1)}\'); '
            'export XAUTHORITY; test -s "$XAUTHORITY"')
        wait("xwininfo -root -tree | grep '\"xlogin\"' >/dev/null",60)
        cmd("! pgrep -u 1234 -f '^/emul/irix/usr/bin/X11/4Dwm( |$)' && /usr/local/libexec/xiri/x11-check vacant")
        return get('xwininfo -root -tree')

    def login(password='xiritest', user='xiritest'):
        # Public disposable lab password; do not use a personal credential here.
        home = {'xiritest':'/usr/people/xiritest','netbsdtest':'/home/netbsdtest'}[user]
        cmd('rm -f '+home+'/.xsession-errors')
        guest.monitor('key type '+user); guest.monitor('key Return')
        guest.monitor('key type '+password); guest.monitor('key Return')

    def survivors(label):
        cmd('test "$(cat /var/run/xiri_famd.pid)" = "$fam_pid" && '
            'test "$(cat /var/run/rpcbind.pid)" = "$rpc_pid" && '
            'test "$(cat /var/run/xdm.pid)" = "$xdm_pid" && '
            'kill -0 "$fam_pid" && kill -0 "$rpc_pid" && kill -0 "$side_pid"')
        cmd('printf '+shlex.quote('echo '+label+' > /tmp/xiri-side-shell/'+label+'\n')+' >&9')
        wait('test -s /tmp/xiri-side-shell/'+label,20)
        assert get('cat /tmp/xiri-side-shell/'+label).strip() == label
        r.setdefault('survivors',[]).append(label)

    def ready():
        wait('grep -q "Logs: " /usr/people/xiritest/.xsession-errors',120)
        cmd('job=$(sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors | head -1); '
            'test -d "$job"; XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
            'test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; '
            'export XAUTHORITY DISPLAY=127.0.0.1:0; test -r "$XAUTHORITY"')
        wait('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready',180)
        wait("xwininfo -root -tree | grep 'of 18)' >/dev/null",180)
        cmd("shell_pid=$(sed -n 's/^NATIVE_HANDOFF pid=\\([0-9][0-9]*\\).*/\\1/p' \"$job/handoff\")")
        wait('ps -p "$shell_pid" -o comm= | grep -Eq \'^[[:space:]]*sh[[:space:]]*$\'')
        cmd('./place winterm 10 180 983 504')
        cmd(shlex.join(['./type','127.0.0.1:0','winterm',
            '(id -un; echo "$HOME"; pwd; id -G; echo "${XAUTHORITY:-$HOME/.Xauthority}") > "$XIRI_SESSION_DIR/shell-proof"\n']))
        wait('test -s "$job/shell-proof"')
        proof = get('cat "$job/shell-proof"').splitlines()
        assert proof[:3] == ['xiritest','/usr/people/xiritest','/usr/people/xiritest'], proof
        assert '1235' in proof[3].split(), proof
        assert proof[4] == get('printf "%s" "$XAUTHORITY"'), proof
        cmd('if XAUTHORITY=/dev/null xdpyinfo >auth-rejected.log 2>&1; then exit 1; fi')
        render = cmd('./render-probe',120)
        assert 'RENDER_PASS pixels=8536 mismatches=0' in render
        dimensions = get("xdpyinfo | grep dimensions:").strip()
        assert re.search(r'dimensions:\s+1280x1024 pixels',dimensions), dimensions
        return dict(identity=get('cat "$job/identity"'),shell=proof,render=render,
                    dimensions=dimensions, framebuffer=guest.monitor('screen info'),
                    tree=get('xwininfo -root -tree'),job=get('printf "%s" "$job"'))

    def guard(entry):
        entry['guard'] = get('cat "$job/guard.log"')
        assert re.search(r'GUARD .*absent=1 valid=1 .*remaining=0 ',entry['guard'])
        owners = {int(x) for x in re.findall(r'^OWN pid=(\d+) ',entry['guard'],re.M)}
        assert not owners.intersection(r['service_and_side_pids'].values())
        cmd("! pgrep -u 1234 -f '^/emul/irix/usr/(bin/X11/4Dwm|sbin/xwsh|sbin/iconcatalog)( |$)'")

    def native_login():
        # No Xiri session selection: exercise NetBSD's unchanged default Xsession.
        cmd('if ! id netbsdtest >/dev/null 2>&1; then groupadd -g 1236 netbsdtest && '
            'useradd -m -u 1236 -g netbsdtest -d /home/netbsdtest -s /bin/sh '
            '-p "$(pwhash -b 6 netbsdtest)" netbsdtest || exit; fi; '
            'test "$(id -u netbsdtest)" = 1236 && test "$(id -g netbsdtest)" = 1236 && '
            'test "$(getent passwd netbsdtest | cut -d: -f6)" = /home/netbsdtest && '
            'test ! -e /home/netbsdtest/.xsession && rm -f /home/netbsdtest/native-proof')
        login('netbsdtest',user='netbsdtest')
        wait("pgrep -u 1236 -f '^/usr/X11R7/bin/ctwm( |$)' >native-wm.pid",120)
        # Serial diagnostics use the display owner's authority, independently
        # of whichever authority pathname xdm supplied to the native user.
        cmd('export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | '
            'awk \'$1 == "/usr/X11R7/bin/Xorg" {for (i=1;i<NF;i++) if ($i == "-auth") print $(i+1)}\'); export XAUTHORITY')
        wait("xwininfo -root -tree | grep '\"UXTerm\"' >/dev/null",120)
        tree = get('xwininfo -root -tree')
        terminal = re.search(r'"([^"\n]+)": \("[^"\n]*" "UXTerm"\)',tree)
        assert terminal,tree
        cmd(shlex.join(['./type',':0',terminal[1],
            '(id -un; echo "$HOME"; pwd; id -u) > "$HOME/native-proof"\n']))
        wait('test -s /home/netbsdtest/native-proof',30)
        proof = get('cat /home/netbsdtest/native-proof').splitlines()
        assert proof == ['netbsdtest','/home/netbsdtest','/home/netbsdtest','1236'],proof
        cmd("! pgrep -u 1236 -f '^/emul/irix/' && ! pgrep -u 1234 -f '^/emul/irix/usr/bin/X11/4Dwm( |$)'")
        dimensions = get('xdpyinfo | grep dimensions:').strip()
        assert re.search(r'dimensions:\s+1280x1024 pixels',dimensions),dimensions
        capture('xdm-native-ctwm'); survivors('during-native-login')
        r['native_login'] = dict(user='netbsdtest',shell=proof,tree=tree,dimensions=dimensions,
                                wm_pid=int(get('cat native-wm.pid').strip()))
        # Let the keyboard helper disconnect before the user's WM exit resets X.
        cmd(shlex.join(['./type',':0',terminal[1],
            '(sleep 2; kill -TERM '+str(r['native_login']['wm_pid'])+') &\n']))
        r['native_login']['greeter_after'] = greeter()
        wait('! pgrep -u 1236',30)
        survivors('after-native-login')
        capture('xdm-after-native-login')
        greeter_text('xdm-after-native-login',r['native_login']['greeter_after'])
        print('Separate native user reached standard ctwm and returned to xdm',flush=True)

    def interrupted(signum, frame):
        r['interrupted'] = signum
        signal.signal(signum, signal.SIG_IGN)
        raise RuntimeError('Test supervisor interrupted by signal '+str(signum))

    signal.signal(signal.SIGTERM, interrupted)
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 >/root/xdm-media.log && mkdir -p /root/xdm-test && cp -R runtime /root/xdm-test/ && cp *.c /root/xdm-test/ && cd /root/xdm-test')
        cmd('cd runtime && make && sh install.sh --enable-xdm && cd ..',300)
        cmd('for name in type place; do cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include "$name.c" '
            '-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o "$name" || exit; done; '
            'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include render-probe.c '
            '-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lXrender -lX11 -o render-probe',300)
        # Account selection is explicit, outside the runtime installer.
        cmd('groupadd -g 1235 xiritest-extra && usermod -G xiritest-extra -p "$(pwhash -b 6 xiritest)" xiritest && '
            'install -o xiritest -g xiritest -m 700 /usr/local/share/xiri/xdm.xsession /usr/people/xiritest/.xsession && '
            'cp /etc/ttys /etc/ttys.before-xdm && '
            "sed '/^ttyE0[[:space:]]/s/[[:space:]]on[[:space:]]/ off /' /etc/ttys.before-xdm >/etc/ttys")
        r['ttys'] = get('cat /etc/ttys')
        lab.offset = len(lab.serial_text()); lab.send('shutdown -h now')
        lab.wait('unmounting done',120); lab.wait(r'Option\?',30); lab.logged_in = False
        lab.send('5'); lab.wait('>> ',15); lab.send('boot -f bootp()/netbsd-XIRI_INDY')
        lab.wait('login: ',600); lab.send('root'); lab.wait('xiri-indy# ',30); lab.logged_in = True
        cmd('cd /root/xdm-test; export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; ulimit -c 0')
        r['boot_services'] = cmd('/etc/rc.d/xdm status && /etc/rc.d/rpcbind status && /etc/rc.d/xiri_famd status && '
            'test -f /var/run/xiri-pty-ready && modstat | grep -E "^compat_irix_o32[[:space:]]+exec[[:space:]]+filesys"')
        r['initial_greeter'] = greeter(); capture('xdm-greeter')
        greeter_text('xdm-greeter',r['initial_greeter'])
        r['greeter_dimensions'] = get('xdpyinfo | grep dimensions:').strip()
        assert re.search(r'dimensions:\s+1280x1024 pixels',r['greeter_dimensions'])
        r['xorg_config'] = get('cat /usr/local/share/xiri/xorg.conf')
        r['xorg_log'] = get('cat /var/log/Xorg.0.log')
        assert 'Using XFree86 Acceleration Architecture (XAA)' in r['xorg_log']
        print('Native xdm greeter started at boot',flush=True)
        login('incorrect'); time.sleep(8)
        r['rejected_login_greeter'] = greeter()
        cmd('test ! -f /usr/people/xiritest/.xsession-errors')
        cmd('grep -q "pam_authenticate failure" /var/log/xdm.log')
        capture('xdm-rejected-login')
        print('Incorrect password rejected without starting a session',flush=True)
        cmd('fam_pid=$(cat /var/run/xiri_famd.pid); rpc_pid=$(cat /var/run/rpcbind.pid); xdm_pid=$(cat /var/run/xdm.pid); '
            'mkdir -p /tmp/xiri-side-shell && chown xiritest:xiritest /tmp/xiri-side-shell && '
            'mkfifo /tmp/xiri-side-shell/input && chown xiritest:xiritest /tmp/xiri-side-shell/input')
        cmd("su -l xiritest -c 'echo $$ >/tmp/xiri-side-shell/pid; exec /bin/sh </tmp/xiri-side-shell/input >/tmp/xiri-side-shell/output 2>&1' </dev/null >/tmp/xiri-side-shell/login.log 2>&1 & side_su=$!; exec 9>/tmp/xiri-side-shell/input; side_pid=$(cat /tmp/xiri-side-shell/pid)")
        r['service_and_side_pids'] = dict(zip(['fam','rpcbind','xdm','shell'],map(int,get('printf "%s\\n" "$fam_pid" "$rpc_pid" "$xdm_pid" "$side_pid"').split())))
        survivors('before-login')
        for route in ['toolchest','root-menu']:
            login(); entry = ready(); survivors('during-'+route); capture('xdm-desktop-'+route)
            if route == 'toolchest':
                cmd('kill $(cat "$job/xmahjongg.pid")')
                wait("! pgrep -u 1234 -f '^/emul/irix/usr/freeware/bin/xmahjongg( |$)'",30)
                guest.monitor('ptr click 14 39'); time.sleep(2); guest.monitor('ptr click 189 243')
            else:
                guest.monitor('ptr move 1150 250'); guest.monitor('ptr down right'); time.sleep(2)
                guest.monitor('ptr move 1180 294'); guest.monitor('ptr up right')
            entry['greeter_after'] = greeter(); guard(entry); survivors('after-'+route)
            entry['logout_route'] = route; r['sessions'].append(entry)
            capture('xdm-after-'+route)
            greeter_text('xdm-after-'+route,entry['greeter_after'])
            print(route+' logout returned to greeter and preserved services/other login',flush=True)
        # A failing desktop must return to authentication, then allow retry.
        cmd("cp /usr/local/libexec/xiri/desktop-clients.sh clients.good; printf '#!/bin/sh\\nexit 7\\n' >/usr/local/libexec/xiri/desktop-clients.sh; rm /usr/people/xiritest/.xsession-errors")
        login()
        wait('grep -q "Logs: " /usr/people/xiritest/.xsession-errors',120)
        cmd('job=$(sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors | head -1)')
        wait('grep -q "^GUARD " "$job/guard.log"',30)
        r['failed_startup'] = dict(greeter=greeter()); guard(r['failed_startup']); survivors('after-failure')
        assert re.search(r'^GUARD .* exit=7 .*reason=leader-exit ',r['failed_startup']['guard'],re.M)
        cmd('cp clients.good /usr/local/libexec/xiri/desktop-clients.sh; rm /usr/people/xiritest/.xsession-errors')
        native_login()
        login(); entry = ready(); capture('xdm-desktop-retry'); cmd('touch "$job/logout"')
        entry['greeter_after'] = greeter(); guard(entry); survivors('after-retry'); r['retry'] = entry
        cmd('printf "exit\\n" >&9; exec 9>&-; wait "$side_su"')
        r['xdm_log'] = get('cat /var/log/xdm.log')
        paths = ['/usr/local/bin/'+x for x in ['xiri-desktop','xiri-session','xiri-launch','xiri-logout']]
        paths += ['/usr/local/libexec/xiri/'+x for x in ['session-guard','x11-check','desktop-clients.sh','setup-pty.sh']]
        paths += ['/usr/libexec/xiri-shell','/etc/xiri/session.conf','/etc/xiri/fam.conf',
                  '/etc/xiri/xdm/Xservers','/etc/xiri/xdm/Xresources','/usr/people/xiritest/.xsession']
        paths += ['/etc/rc.d/'+x for x in ['xiri_devices','xiri_famd']]
        paths += ['/etc/rc.conf.d/'+x for x in ['xiri_devices','xiri_famd','rpcbind','xdm']]
        listing = get('sha256 '+shlex.join(paths))
        r['installed_files'] = dict(re.findall(r'^SHA256 \((.+)\) = ([0-9a-f]{64})$',listing,re.M))
        assert len(r['installed_files']) == len(paths)
        r['native_after'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        r['status'] = 'passed'
    except Exception as error:
        r['error'] = str(error); print('Failed: '+str(error),flush=True)
        if args.debug_failure and lab.logged_in and not r.get('interrupted'):
            (d/'ready').write_text('ready\n'); print('Debug requests: '+str(d/'request.json'),flush=True)
            last = time.monotonic()
            while time.monotonic()-last < 600:
                request = d/'request.json'
                if not request.exists(): time.sleep(.2); continue
                item = json.loads(request.read_text()); request.unlink(); last = time.monotonic()
                if item['command'] == 'SHUTDOWN': break
                try:
                    output = guest.monitor(item['command']) if item.get('monitor') else (get if item.get('read') else cmd)(item['command'],item.get('timeout',120))
                    reply = dict(code=0,output=output)
                except Exception as failure:
                    reply = dict(error=str(failure))
                (d/('response-'+item['id']+'.json')).write_text(json.dumps(reply))
        raise
    finally:
        lab.close(); r['clean_shutdown'] = lab.clean_shutdown
        r['base_raw_unchanged'] = sha256(seed/'disk.raw') == origin['raw_sha256']
        if r['status'] == 'passed' and not (r['clean_shutdown'] and r['base_raw_unchanged']):
            r.update(status='error',error='Qualification requires a clean halt and unchanged source disk')
        (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    if r['status'] != 'passed': raise RuntimeError(r['error'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
