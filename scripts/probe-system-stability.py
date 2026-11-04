#!/usr/bin/env python3
"""Repeat native input, descendant supervision, xdm sessions and clean halts.

Each boot uses a disposable clone of the named, hash-verified desktop bundle.
An optional candidate core/module is installed only in that clone. The source
bundle, installed runtime and pinned emulator remain unchanged.
"""
import argparse
import io
import json
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import tarfile
import tempfile
import time
from types import SimpleNamespace

from xiri_lab import Guest, ROOT, load_probe, sha256, source_hashes
from xiri_lab.kernel_log import KernelLog


def run_once(args, number):
    bundle = args.bundle.resolve()
    manifest = json.loads((bundle/'manifest.json').read_text())
    assert manifest['status'] == 'chd-roundtrip-verified' and manifest['session_manager'] == 'xdm'
    assert sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
    assert sha256(bundle/'seed-result.json') == manifest['source_result_sha256']
    previous = json.loads((bundle/'seed-result.json').read_text())
    assert previous['pin'] == manifest['pin']
    p = load_probe()
    p.IRIS, p.CI = bundle/'emulator/iris', bundle/'emulator/iris-ci'
    assert sha256(p.IRIS) == manifest['pin']['emulator_sha256']
    assert sha256(p.CI) == manifest['pin']['ci_client_sha256']
    runs = ROOT/'.work/system-stability'; runs.mkdir(exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='boot-', dir=runs))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    shutil.copyfile(__file__, d/'harness.py')
    if args.acrobat_replay:
        from xiri_lab.image_apps import check as check_image_apps
        shutil.copyfile(ROOT/'scripts/xiri_lab/image_apps.py', d/'image-apps.py')
    media = d/'media'; media.mkdir()
    for source in ['lab/system-stability/xinput.c', 'lab/system-stability/memory.c', 'lab/system-stability/guard-loop.sh',
                   'lab/system-stability/cd9660.c', 'lab/system-stability/cd9660_mount.h',
                   'lab/irix-catalog/guard-control.c', 'lab/irix-catalog/query-control.c',
                   'lab/irix-session/descendants.c', 'lab/irix-session/guard-tests.sh']:
        shutil.copyfile(ROOT/source, media/Path(source).name)
    if args.acrobat_replay:
        for source, name in {
            'lab/system-stability/click-original.c': 'click-original.c',
            'lab/system-stability/click-trace.c': 'click-trace.c',
            'lab/irix-4dwm/type-ready.c': 'type.c',
            'lab/irix-filelocks/place-window.c': 'place.c',
            'lab/irix-vendor-shell/catalog-input.c': 'catalog-input.c',
            'lab/irix-catalog/windows.c': 'windows.c',
        }.items():
            shutil.copyfile(ROOT/source, media/name)
    # Reproduce the survey's variant, which observes children after leader exit.
    guard = (ROOT/'runtime/libexec/session-guard.c').read_text()
    for old, new in [
        ('failed || requested || finished || now() >= deadline', 'failed || requested || now() >= deadline'),
        ('requested ? "signal" : finished ? "leader-exit" :', 'requested ? "signal" :'),
    ]:
        assert guard.count(old) == 1
        guard = guard.replace(old, new)
    (media/'app-guard.c').write_text(guard)
    candidate = None
    if args.kernel_build:
        build = args.kernel_build.resolve()
        candidate = json.loads((build/'module.json').read_text())
        kernel_media = media/'kernel'; kernel_media.mkdir()
        for name in ['netbsd', 'netbsd.boot', 'compat_irix_o32.kmod']:
            artifact = candidate['artifacts'][name]
            source = build/artifact['path']
            assert sha256(source) == artifact['sha256']
            shutil.copyfile(source, kernel_media/name)
        symbols = subprocess.check_output(['nm', str(kernel_media/'netbsd')], text=True)
        candidate['msgbuf_symbol'] = '0x'+re.search(r'^([0-9a-f]+) B msgbufp$', symbols, re.M)[1]
        candidate['build_manifest_sha256'] = sha256(build/'module.json')
        candidate['source_patch_sha256'] = sha256(build/'source.patch')
        shutil.copyfile(build/'source.patch', d/'kernel-source.patch')
    p.run(['genisoimage', '-quiet', '-R', '-J', '-o', d/'probe.iso', media])
    p.run(['cp', '--reflink=auto', '--sparse=always', bundle/'netbsd-xiri.chd', d/'disk.chd'])
    seed_record = None
    if args.seed:
        seed_result = json.loads((args.seed/'result.json').read_text())
        assert seed_result['clean_shutdown'] and seed_result['source_unchanged']
        assert sha256(args.seed/'disk.chd') == manifest['chd_sha256']
        assert seed_result['candidate_kernel']['artifacts'] == candidate['artifacts']
        overlay = args.seed/'disk.chd.diff.chd'
        seed_record = dict(path=str(args.seed), result_sha256=sha256(args.seed/'result.json'),
                           overlay_sha256=sha256(overlay))
        p.run(['cp', '--reflink=auto', overlay, d/'disk.chd.diff.chd'])
    profile = bundle/manifest['qualification_nvram']
    assert sha256(profile) == manifest['qualification_nvram_sha256']
    shutil.copyfile(profile, d/'nvram.bin')
    config = (bundle/'iris.toml').read_text().replace('tftp_dir = "tftp"',
        'tftp_dir = '+json.dumps(str(d/'no-tftp')))
    config += '\n[scsi.4]\npath = '+json.dumps(str(d/'probe.iso'))+'\ncdrom = true\n'
    def new_lab(directory):
        owner = p.Lab(SimpleNamespace(mode='ordinary', debugger=False, boot_timeout=600), directory, config_text=config)
        launch = owner.launch
        def disk_launch(command, name):
            if name == 'emulator':
                command = list(command); command[command.index('--scsi1')+1] = str(d/'disk.chd')
            return launch(command, name)
        owner.launch = disk_launch
        return owner
    lab = new_lab(d)
    guest = Guest(lab)
    cmd, get, wait = guest.command, guest.read_text, guest.wait_for
    ring = KernelLog(lab, int(candidate['msgbuf_symbol'] if args.seed else manifest['kernel_msgbuf_symbol'], 16))
    result = dict(schema=1, status='error', clean_shutdown=False, boot=number,
                  bundle=str(bundle.relative_to(ROOT)), manifest_sha256=sha256(bundle/'manifest.json'),
                  chd_sha256=manifest['chd_sha256'], pin=manifest['pin'], module=manifest['irix_module'],
                  harness_sha256=sha256(Path(__file__)), sources=source_hashes(),
                  media={str(f.relative_to(media)):sha256(f) for f in media.rglob('*') if f.is_file()}, phases=[], sessions=[])
    result['parameters'] = {key:(str(value) if isinstance(value, Path) else value)
                            for key,value in vars(args).items() if key != 'bundle'}
    if candidate: result['candidate_kernel'] = candidate
    if seed_record: result['seed'] = seed_record
    result['sources']['scripts/xiri_lab/kernel_log.py'] = sha256(ROOT/'scripts/xiri_lab/kernel_log.py')
    result['sources']['runtime/libexec/session-guard.c'] = sha256(ROOT/'runtime/libexec/session-guard.c')
    if args.acrobat_replay:
        result['sources']['scripts/xiri_lab/image_apps.py'] = sha256(d/'image-apps.py')
    started = time.monotonic()
    base = '/tmp/xiri-stability'

    def capture(name):
        guest.monitor('disp compositor gl')
        time.sleep(2)
        guest.monitor('screen shot '+str(d/(name+'.png')))
        assert (d/(name+'.png')).read_bytes()[:8] == b'\x89PNG\r\n\x1a\n'
        result.setdefault('screenshots', {})[name] = sha256(d/(name+'.png'))

    def greeter():
        cmd('export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | '
            'awk \'$1 == "/usr/X11R7/bin/Xorg" {for(i=1;i<NF;i++) if($i=="-auth") print $(i+1)}\'); '
            'export XAUTHORITY; test -s "$XAUTHORITY"')
        wait('xwininfo -root -tree | grep \'"xlogin"\' >/dev/null', 90)
        cmd('/usr/local/libexec/xiri/x11-check vacant')
        dimensions = get('xdpyinfo | grep dimensions:').strip()
        assert re.search(r'dimensions:\s+1280x1024 pixels', dimensions), dimensions
        return dimensions

    def login(user):
        home = '/usr/people/xiritest' if user == 'xiritest' else '/home/netbsdtest'
        cmd('rm -f '+home+'/.xsession-errors')
        for text in [user, user]:
            guest.monitor('key type '+text); guest.monitor('key Return')

    def irix_authority():
        cmd('job=$(sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors | head -1); '
            'XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
            'test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; '
            'export XAUTHORITY DISPLAY=127.0.0.1:0; test -r "$XAUTHORITY"')

    def input_checks(label, user):
        authority = get('printf "%s" "$XAUTHORITY"').strip()
        for display, transport in [(':0', 'unix'), ('127.0.0.1:0', 'tcp')]:
            path = base+'/'+label+'-'+transport+'.log'
            call = shlex.join([base+'/xinput', display, str(args.input_iterations), '10'])
            if user:
                call = 'su -l '+user+' -c '+shlex.quote('XAUTHORITY='+shlex.quote(authority)+' '+call)
            began = time.monotonic()
            # Store the status before asserting it, so failures retain evidence.
            cmd(call+' >'+path+' 2>&1; rc=$?; echo "$rc" >'+path+'.status; test "$rc" = 0',
                max(120, args.input_iterations*2))
            output = get('tail -1 '+path)
            assert f'XINPUT_PASS display={display} iterations={args.input_iterations} events={args.input_iterations*2}' in output
            result['phases'].append(dict(kind='input', label=label, user=user or 'root', display=display,
                iterations=args.input_iterations, events=args.input_iterations*2,
                host_seconds=round(time.monotonic()-began, 3), log_file=label+'-'+transport+'.log',
                log_sha256=get('sha256 -q '+path).strip()))
            print(label+' '+transport+': '+str(args.input_iterations)+' native input round trips passed', flush=True)

    def child_checks(label):
        directory = base+'/'+label+'-children'
        cmd('mkdir '+directory+' && chown xiritest:xiritest '+directory+' && '
            'ln -s '+base+'/app-guard '+base+'/guard-control '+base+'/descendants '+directory+'/')
        began = time.monotonic()
        call = shlex.join(['/bin/sh', base+'/guard-loop.sh', directory, str(args.child_iterations)])
        cmd('su -l xiritest -c '+shlex.quote(call)+' >'+directory+'/loop.log 2>&1',
            max(120, args.child_iterations*5))
        output = get('cat '+directory+'/loop.log')
        (d/(label+'-children.log')).write_text(output)
        assert f'CHILD_PASS iterations={args.child_iterations} launches={args.child_iterations*2}' in output
        cmd('su -l xiritest -c '+shlex.quote('/bin/sh '+base+'/guard-tests.sh '+directory)+
            ' >'+directory+'/adversarial.log 2>&1', 120)
        output = get('cat '+directory+'/adversarial.log')
        (d/(label+'-adversarial.log')).write_text(output)
        assert 'SESSION_GUARD_TESTS_OK' in output
        result['phases'].append(dict(kind='children', label=label, iterations=args.child_iterations,
            launches=args.child_iterations*2, adversarial=True, host_seconds=round(time.monotonic()-began,3)))
        print(label+': detached children and adversarial session cleanup passed', flush=True)

    def collect():
        # Logs include the last BEGIN/OWN even when the successful transfer path
        # was never reached. Do not infer native process health from a PID alone.
        cmd('ps -axlww >'+base+'/processes.txt; cp /var/log/Xorg.0.log '+base+'/Xorg.log; '
            'cp /var/log/xdm.log '+base+'/xdm.log', 20)
        archive = guest.read('tar -C '+base+' -czf - .', 300)
        (d/'guest-evidence.tgz').write_bytes(archive)
        # Transfer detailed input logs once. Keep them locally with the same
        # names and verify against the digest taken immediately after the test.
        with tarfile.open(fileobj=io.BytesIO(archive), mode='r:gz') as stream:
            for phase in result['phases']:
                if phase['kind'] != 'input': continue
                name = phase['log_file']
                (d/name).write_bytes(stream.extractfile('./'+name).read())
                assert sha256(d/name) == phase['log_sha256']

    def diagnostics():
        result['failure_diagnostics'] = {}
        try:
            guest.monitor('stop')
            for command in ['status', 'regs', 'cop0', 'bt 20', 'stack']:
                result['failure_diagnostics'][command] = guest.monitor(command)
        except Exception as error:
            result['failure_diagnostics']['monitor_error'] = str(error)
        finally:
            try: lab.monitor_command('start')
            except Exception as error: result['failure_diagnostics']['resume_error'] = str(error)
        try:
            (d/'failure-kernel.log').write_text(ring.read())
            capture('failure')
        except Exception as error:
            result['failure_diagnostics']['capture_error'] = str(error)

    def interrupted(signum, frame):
        result['interrupted'] = signum
        signal.signal(signum, signal.SIG_IGN)
        raise RuntimeError('Stability test interrupted')

    old_handler = signal.signal(signal.SIGTERM, interrupted)
    try:
        lab.start(boot=False)
        lab.wait('login: ', 600); lab.send('root'); lab.wait('xiri-indy# ', 30); lab.logged_in=True
        expected_pin = dict(manifest['pin'])
        module = dict(manifest['irix_module'])
        if candidate and not args.seed:
            cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom')
            for name, destination in [('netbsd', '/netbsd'), ('netbsd.boot', '/netbsd.boot'),
                                      ('compat_irix_o32.kmod', module['path'])]:
                digest = candidate['artifacts'][name]['sha256']
                cmd('test "$(sha256 -q /cdrom/kernel/'+name+')" = '+digest+
                    ' && install -m 444 /cdrom/kernel/'+name+' '+shlex.quote(destination))
            result['preparation_halt'] = ring.halt()
            lab.close()
            reboot = d/'reboot'; reboot.mkdir()
            shutil.copyfile(profile, reboot/'nvram.bin')
            lab = new_lab(reboot)
            guest = Guest(lab); cmd, get, wait = guest.command, guest.read_text, guest.wait_for
            ring = KernelLog(lab, int(candidate['msgbuf_symbol'], 16))
            lab.start(boot=False)
            lab.wait('login: ', 600); lab.send('root'); lab.wait('xiri-indy# ', 30); lab.logged_in=True
        if candidate:
            expected_pin['native_kernel_sha256'] = candidate['artifacts']['netbsd']['sha256']
            expected_pin['boot_kernel_sha256'] = candidate['artifacts']['netbsd.boot']['sha256']
            module['sha256'] = candidate['artifacts']['compat_irix_o32.kmod']['sha256']
            # The bundle's source/debug/build fields describe the input image,
            # not the replacement core. Keep that pin above and record only
            # the verified installed artifacts here; candidate_kernel owns
            # the replacement's complete build/source provenance.
            result['installed_kernel'] = {
                key: expected_pin[key]
                for key in ['native_kernel_sha256', 'boot_kernel_sha256']
            }
            result['installed_kernel']['build_manifest_sha256'] = candidate['build_manifest_sha256']
            result['installed_module'] = {
                'path': module['path'], 'sha256': module['sha256'],
                'build_manifest_sha256': candidate['build_manifest_sha256'],
            }
        cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; ulimit -c 0')
        cmd('test "$(sha256 -q /netbsd)" = '+expected_pin['native_kernel_sha256']+
            ' && test "$(sha256 -q /netbsd.boot)" = '+expected_pin['boot_kernel_sha256'])
        assert get('sha256 -q '+shlex.quote(module['path'])).strip() == module['sha256']
        cmd('/etc/rc.d/xdm status && /etc/rc.d/xiri_famd status && /etc/rc.d/rpcbind status')
        result['boot_services'] = get('modstat; cat /var/run/xiri_famd.pid /var/run/rpcbind.pid /var/run/xdm.pid')
        result['service_pids'] = get('cat /var/run/xiri_famd.pid /var/run/rpcbind.pid /var/run/xdm.pid').split()
        assert len(result['service_pids']) == 3 and all(x.isdigit() for x in result['service_pids'])
        if args.seed: cmd('rm -rf '+base)
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && mkdir '+base+' && chmod 755 '+base+
            ' && cp /cdrom/*.c /cdrom/*.h /cdrom/*.sh '+base+'/ && cd '+base+' && chmod 444 *.c *.h && chmod 555 *.sh')
        cmd('(set -e; for file in app-guard guard-control descendants memory cd9660; do cc -O2 -Wall -Wextra -Werror "$file.c" -o "$file"; done; '
            'for file in xinput query-control; do cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include "$file.c" '
            '-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o "$file"; done)', 180)
        cmd('chmod 555 app-guard guard-control descendants memory xinput query-control')
        if args.acrobat_replay:
            cmd('(set -e; for file in click-original click-trace type place catalog-input windows; do '
                'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include "$file.c" '
                '-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o "$file"; done)', 180)
        cmd('./cd9660 --diagnostic >cd9660.log 2>&1', 180)
        result['cd9660'] = get('cat cd9660.log')
        cd_result = re.search(r'CD9660_RESULT checks=(\d+) failures=(\d+)', result['cd9660'])
        assert cd_result, 'Missing CD ABI regression summary'
        require_cd9660 = candidate is not None or args.require_cd9660
        result['cd9660_regression'] = dict(checks=int(cd_result[1]), failures=int(cd_result[2]),
                                          expected_fixed=require_cd9660)
        if require_cd9660: assert int(cd_result[2]) == 0, 'Required CD mount ABI regression failed'
        result['guard_sha256'] = get('sha256 -q /usr/local/libexec/xiri/session-guard').strip()
        assert result['guard_sha256'] == previous['installed_files']['/usr/local/libexec/xiri/session-guard']
        result['greeter_dimensions'] = greeter(); capture('greeter')
        if args.pressure_mib:
            result['memory_before'] = get('vmstat -s')
            cmd('su -l xiritest -c '+shlex.quote(base+'/memory '+str(args.pressure_mib))+
                ' >memory.log 2>&1 & memory_su=$!')
            wait('grep -q MEMORY_READY memory.log', 180)
            result['memory_ready'] = get('cat memory.log')
            memory_pid = int(re.search(r'MEMORY_READY pid=(\d+) ', result['memory_ready'])[1])
            result['memory_under_load'] = get('vmstat -s; ps -p '+str(memory_pid)+' -o pid,uid,stat,vsz,rss,comm')
        # Known server grab must trigger the watchdog and then release normally.
        cmd('./query-control >held.log 2>&1 & held=$!')
        wait('grep -q SURVEY_SERVER_HELD held.log', 10)
        cmd('./xinput :0 1 2 >negative.log 2>&1; rc=$?; echo "$rc" >negative.status; test "$rc" = 124')
        result['negative_input'] = get('cat negative.log')
        assert 'XINPUT_TIMEOUT' in result['negative_input']
        cmd('wait "$held" && ./xinput :0 1 10 >recovered.log 2>&1', 40)
        input_checks('greeter', None)
        child_checks('greeter')
        for index in range(args.sessions):
            label = 'irix-'+str(index+1)
            login('xiritest')
            wait('grep -q "Logs: " /usr/people/xiritest/.xsession-errors', 120)
            irix_authority()
            wait('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready', 180)
            wait('xwininfo -root -tree | grep "of 18)" >/dev/null', 120)
            input_checks(label, 'xiritest'); child_checks(label)
            if args.acrobat_replay and index == 0:
                check_image_apps(guest, d, result, base, args.acrobat_replay)
            capture(label)
            cmd('touch "$job/logout"')
            greeter()
            guard_log = get('cat "$job/guard.log"')
            assert re.search(r'GUARD .*absent=1 valid=1 .*remaining=0 ', guard_log), guard_log
            result['sessions'].append(dict(user='xiritest', guard=guard_log))
            print(label+': logout returned to the full-size greeter', flush=True)
        login('netbsdtest')
        # Root can use Xorg's server cookie while the native user session starts.
        # Fetch the user's actual authority from its terminal environment; xdm
        # can select /tmp/.Xauth* instead of the home default for either user.
        cmd('export DISPLAY=:0')
        wait("pgrep -u 1236 -f '^/usr/X11R7/bin/ctwm( |$)' >native.pid && test \"$(wc -l <native.pid)\" -eq 1", 120)
        wait("pgrep -u 1236 -f '(^|/)xterm( |$)' >native-terminal.pid", 90)
        cmd('XAUTHORITY=$(ps eww -p "$(head -1 native-terminal.pid)" -o command= | '
            'tr " " "\\n" | sed -n "s/^XAUTHORITY=//p"); '
            'test -n "$XAUTHORITY" || XAUTHORITY=/home/netbsdtest/.Xauthority; '
            'export XAUTHORITY; test -s "$XAUTHORITY"')
        wait('xwininfo -root -tree | grep \'"xterm"\' >/dev/null', 90)
        input_checks('native-ctwm', 'netbsdtest'); capture('native-ctwm')
        cmd("pgrep -u 1236 -f '^/usr/X11R7/bin/ctwm( |$)' >native.pid && test \"$(wc -l <native.pid)\" -eq 1")
        cmd('kill -TERM "$(cat native.pid)"')
        greeter(); wait('! pgrep -u 1236', 30)
        result['sessions'].append(dict(user='netbsdtest', returned_to_greeter=True))
        cmd('/etc/rc.d/xdm status && /etc/rc.d/xiri_famd status && /etc/rc.d/rpcbind status')
        result['services_after'] = get('cat /var/run/xiri_famd.pid /var/run/rpcbind.pid /var/run/xdm.pid').split()
        assert result['services_after'] == result['service_pids']
        for pid in result['service_pids']: cmd('kill -0 '+pid)
        if args.pressure_mib:
            cmd('kill -0 '+str(memory_pid))
            result['memory_before_halt'] = get('cat memory.log; vmstat -s')
            if not args.halt_active:
                cmd('kill -TERM '+str(memory_pid)+'; wait "$memory_su"; grep -q MEMORY_RELEASED memory.log')
                result['memory_release'] = get('cat memory.log')
        result['shutdown_state'] = 'greeter'
        if args.halt_active:
            login('xiritest')
            wait('grep -q "Logs: " /usr/people/xiritest/.xsession-errors', 120)
            irix_authority()
            wait('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready', 180)
            cmd('./xinput 127.0.0.1:0 1 10 >pre-halt-input.log 2>&1')
            capture('active-before-halt')
            result['shutdown_state'] = 'active-irix-desktop'
        collect()
        result['status'] = 'passed'
    except Exception as error:
        result['error'] = str(error)
        print('Failed: '+str(error), flush=True)
        diagnostics()
        try: collect()
        except Exception as failure: result['evidence_error'] = str(failure)
        if args.debug_failure and not result.get('interrupted'):
            (d/'ready').write_text('debug\n')
            print('Debug requests: '+str(d/'request.json'), flush=True)
            last = time.monotonic()
            while time.monotonic()-last < 600:
                request = d/'request.json'
                if not request.exists(): time.sleep(.2); continue
                item = json.loads(request.read_text()); request.unlink(); last=time.monotonic()
                if item['command'] == 'SHUTDOWN': break
                try:
                    output = guest.monitor(item['command']) if item.get('monitor') else (
                        get if item.get('read') else cmd)(item['command'], item.get('timeout',30))
                    reply = dict(output=output)
                except Exception as failure: reply=dict(error=str(failure))
                (d/('response-'+item['id']+'.json')).write_text(json.dumps(reply))
    finally:
        try:
            if lab.logged_in: result['halt'] = ring.halt()
        except Exception as error:
            result['halt_error'] = str(error)
            diagnostics()
        finally:
            lab.close()
            result['clean_shutdown'] = lab.clean_shutdown
            result['host_seconds'] = round(time.monotonic()-started,3)
            result['source_unchanged'] = sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
            if seed_record:
                result['seed_unchanged'] = sha256(args.seed/'disk.chd.diff.chd') == seed_record['overlay_sha256']
                if not result['seed_unchanged']: result['status'] = 'error'
            if not result['clean_shutdown'] or not result['source_unchanged'] or result.get('halt_error'):
                result['status'] = 'error'
            (d/'result.json').write_text(json.dumps(result, indent=2)+'\n')
            signal.signal(signal.SIGTERM, old_handler)
    print('Result: '+result['status']+'; clean shutdown='+str(result['clean_shutdown']), flush=True)
    return result['status'] == 'passed'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--kernel-build', type=Path, help='install this core/module in the disposable clone and reboot before testing')
    parser.add_argument('--seed', type=Path, help='clone a cleanly halted candidate run; requires the matching --kernel-build')
    parser.add_argument('--runs', type=int, default=3)
    parser.add_argument('--sessions', type=int, default=2)
    parser.add_argument('--input-iterations', type=int, default=100)
    parser.add_argument('--child-iterations', type=int, default=20)
    parser.add_argument('--debug-failure', action='store_true')
    parser.add_argument('--halt-active', action='store_true', help='finish with shutdown during an active IRIX desktop')
    parser.add_argument('--pressure-mib', type=int, default=0, help='hold this many dirty native MiB during the checks (maximum 192)')
    parser.add_argument('--require-cd9660', action='store_true', help='require the CD regression to pass on the installed image too')
    parser.add_argument('--acrobat-replay', type=int, default=0, metavar='COUNT',
                        help='check the original GNOME shell/preferences and repeat the PDF/capture/focus/exit sequence')
    args = parser.parse_args()
    if args.seed and not args.kernel_build: parser.error('--seed requires --kernel-build')
    if not (1 <= args.runs <= 20 and 1 <= args.sessions <= 20 and
            1 <= args.input_iterations <= 1000 and 1 <= args.child_iterations <= 200 and
            0 <= args.pressure_mib <= 192 and 0 <= args.acrobat_replay <= 20):
        parser.error('invalid run/session/iteration count')
    for number in range(1, args.runs+1):
        if not run_once(args, number): return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
