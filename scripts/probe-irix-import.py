#!/usr/bin/env python3
"""Qualify a new vendor payload on a disposable copy of a known native base.

This replaces /emul/irix in full. It qualifies the imported vendor tree, not a
fresh stock-NetBSD install: the manifest names the inherited native base.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import shutil
import signal
import struct
import subprocess
import tarfile
import time
from types import SimpleNamespace

from xiri_lab import ROOT, Guest, load_probe, sha256, source_hashes
from xiri_lab.kernel_log import KernelLog
from xiri_lab.xdm_image import support_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--payload', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--resume-import', type=Path, help='copy a cleanly halted import run and verify its persisted files')
    parser.add_argument('--debug-failure', action='store_true', help='allow bounded local diagnostic requests after a checksum failure')
    args = parser.parse_args()
    bundle, payload, out = (p.resolve() for p in (args.bundle, args.payload, args.output))
    base = json.loads((bundle/'manifest.json').read_text())
    seed = json.loads((bundle/'seed-result.json').read_text())
    imported = json.loads((payload/'manifest.json').read_text())
    assert imported['status'] == 'payload-verified'
    assert sha256(payload/'payload.tar.gz') == imported['payload_sha256']
    assert sha256(bundle/'netbsd-xiri.chd') == base['chd_sha256']
    assert sha256(bundle/'seed-result.json') == base['source_result_sha256']
    assert sha256(bundle/base['qualification_nvram']) == base['qualification_nvram_sha256']
    out.mkdir(parents=True, exist_ok=False)
    # Keep the exact executed test next to its evidence, even if development
    # continues in this checkout while the guest is running.
    shutil.copyfile(__file__, out/'probe-used.py')
    media = out/'media'
    media.mkdir()
    shutil.copyfile(payload/'payload.tar.gz', media/'payload.tgz')
    with tarfile.open(payload/'payload.tar.gz') as archive:
        (media/'expected-rld').write_bytes(archive.extractfile('emul/irix/lib/rld').read())
    shutil.copyfile(ROOT/'lab/irix-4dwm/type-ready.c', media/'type.c')
    shutil.copyfile(ROOT/'lab/irix-filelocks/place-window.c', media/'place.c')
    native = {p:h for p,h in support_files(bundle,seed).items()
              if not p.startswith('/emul/') and not p.startswith('/usr/local/share/xiri/fonts/')}
    (media/'NATIVE').write_text(''.join(f'SHA256 ({p}) = {h}\n' for p,h in sorted(native.items())))
    (media/'VENDOR').write_text(''.join(f'SHA256 ({p}) = {r["sha256"]}\n'
                                      for p,r in sorted(imported['files'].items()) if r['type']=='file'))
    (media/'SHA256').write_text(''.join(f'SHA256 ({p.name}) = {sha256(p)}\n' for p in sorted(media.iterdir())))
    iso_tool = shutil.which('genisoimage') or shutil.which('mkisofs')
    if not iso_tool:
        raise ValueError('Install genisoimage or mkisofs before running the qualification')
    subprocess.run([iso_tool,'-quiet','-R','-J','-o',out/'probe.iso',media], check=True)
    subprocess.run(['cp','--reflink=auto','--sparse=always',bundle/'netbsd-xiri.chd',out/'disk.chd'],check=True)
    shutil.copyfile(bundle/base['qualification_nvram'],out/'nvram.bin')
    resumed = None
    if args.resume_import:
        prior = args.resume_import.resolve()
        saved = json.loads((prior/'result.json').read_text())
        assert saved['clean_shutdown'] and saved['base_unchanged']
        assert saved['payload_sha256'] == imported['payload_sha256']
        assert sha256(prior/'disk.chd') == base['chd_sha256']
        delta = prior/'disk.chd.diff.chd'
        resumed = dict(run=str(prior),delta_sha256=sha256(delta))
        subprocess.run(['cp','--reflink=auto',delta,out/delta.name],check=True)
    config = (bundle/'iris.toml').read_text().replace('tftp_dir = "tftp"','tftp_dir = '+json.dumps(str(out/'no-tftp')))
    config += '\n[scsi.4]\npath = '+json.dumps(str(out/'probe.iso'))+'\ncdrom = true\n'
    probe = load_probe()
    # This command may already be running inside the development Toolbox.
    # The same process-group owner works directly when no host wrapper exists.
    if not shutil.which('toolbox'):
        probe.TOOLBOX = []
    probe.IRIS, probe.CI = bundle/'emulator/iris', bundle/'emulator/iris-ci'
    assert sha256(probe.IRIS) == base['pin']['emulator_sha256']
    assert sha256(probe.CI) == base['pin']['ci_client_sha256']
    lab = probe.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600),out,config_text=config)
    original_launch = lab.launch

    def launch(command,name):
        if name == 'emulator':
            command = list(command)
            command[command.index('--scsi1')+1] = str(out/'disk.chd')
        return original_launch(command,name)

    lab.launch = launch
    guest = Guest(lab)
    cmd, get, wait = guest.command, guest.read_text, guest.wait_for
    result = dict(schema=1,status='incomplete',scope=__doc__.strip(),
                  base_chd_sha256=base['chd_sha256'],base_manifest_sha256=sha256(bundle/'manifest.json'),
                  pin=base['pin'],payload_manifest_sha256=sha256(payload/'manifest.json'),
                  payload_sha256=imported['payload_sha256'],profile=imported['profile'],
                  sources={**source_hashes(), **{p:sha256(ROOT/p) for p in (
                      'scripts/probe-irix-import.py','scripts/xiri_lab/kernel_log.py',
                      'scripts/xiri_lab/xdm_image.py','lab/irix-4dwm/type-ready.c',
                      'lab/irix-filelocks/place-window.c')}},
                  native_files_verified=native,screenshots={},sessions=[])
    result['resumed_import'] = resumed

    def checkpoint(stage):
        (out/'checkpoint.json').write_text(json.dumps(dict(result,stage=stage),indent=2)+'\n')
        print(stage,flush=True)

    def capture(name):
        guest.monitor('disp compositor gl')
        guest.monitor('screen wait 500 10000')
        guest.monitor('screen shot '+str(out/(name+'.png')))
        dimensions = struct.unpack('>II',(out/(name+'.png')).read_bytes()[16:24])
        assert dimensions == (1282,1024), dimensions
        result['screenshots'][name] = sha256(out/(name+'.png'))

    def greeter():
        wait('test -s /tmp/.X0-lock && kill -0 "$(cat /tmp/.X0-lock)"',90)
        cmd('export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | '
            'awk \'$1 == "/usr/X11R7/bin/Xorg" {for (i=1;i<NF;i++) if ($i == "-auth") print $(i+1)}\'); '
            'export XAUTHORITY; test -s "$XAUTHORITY"')
        wait("xwininfo -root -tree | grep '\"xlogin\"' >/dev/null",90)

    def login(user):
        # Public disposable-image credentials, never personal credentials.
        home = '/home/netbsdtest' if user == 'netbsdtest' else '/usr/people/'+user
        cmd('rm -f '+home+'/.xsession-errors')
        guest.monitor('key type '+user)
        guest.monitor('key Return')
        guest.monitor('key type '+user)
        guest.monitor('key Return')

    def desktop(label):
        wait('grep -q "Logs: " /usr/people/xiritest/.xsession-errors',120)
        cmd('job=$(sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors | head -1); '
            'test -d "$job"; XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
            'test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; '
            'export DISPLAY=127.0.0.1:0 XAUTHORITY; test -r "$XAUTHORITY"')
        wait('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready',180)
        wait("xwininfo -root -tree | grep 'Icon Catalog:' >/dev/null",180)
        cmd(shlex.join(['/root/import-test/type','127.0.0.1:0','winterm',
                        '(id -un; echo "$HOME"; pwd; /emul/irix/bin/sh -c "echo IRIX_SHELL_OK") > "$XIRI_SESSION_DIR/import-proof"\n']))
        wait('test -s "$job/import-proof"',60)
        proof = get('cat "$job/import-proof"').splitlines()
        assert proof == ['xiritest','/usr/people/xiritest','/usr/people/xiritest','IRIX_SHELL_OK'],proof
        dimensions = get('xdpyinfo | grep dimensions:').strip()
        assert re.search(r'dimensions:\s+1280x1024 pixels',dimensions),dimensions
        tree = get('xwininfo -root -tree')
        for title in ['Toolchest','Icon Catalog:','winterm','xclock']:
            assert title in tree,(title,tree)
        cmd('test -d /emul/irix/usr/lib/desktop/iconcatalog/pages/C/Applications && '
            'test ! -e /emul/irix/usr/freeware/bin/gimp && test ! -e /emul/irix/usr/freeware/bin/xmahjongg')
        result['sessions'].append(dict(label=label,shell=proof,dimensions=dimensions,tree=tree,
                                       identity=get('cat "$job/identity"')))
        capture(label)
        checkpoint(label)

    def logout():
        cmd(shlex.join(['/root/import-test/type','127.0.0.1:0','winterm',
                        '/usr/local/bin/xiri-logout\n']))
        greeter()
        cmd("! pgrep -u xiritest -f '^/emul/irix/usr/(bin/X11/4Dwm|sbin/xwsh|sbin/iconcatalog)( |$)'")

    def interrupted(signum,frame):
        raise RuntimeError('Interrupted by signal '+str(signum))

    signal.signal(signal.SIGTERM,interrupted)
    try:
        lab.start(boot=False)
        lab.wait('login: ',600)
        lab.send('root')
        lab.wait('xiri-indy# ',30)
        lab.logged_in = True
        cmd('test "$(sha256 -q /netbsd)" = '+base['pin']['native_kernel_sha256'])
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && '
            'sha256 -c SHA256 >/root/import-media.log && sha256 -c NATIVE >/root/import-native.log && cd /root',1200)
        checkpoint('native-base-verified')
        cmd('/etc/rc.d/xdm stop && /etc/rc.d/xiri_famd stop',120)
        wait('! pgrep -x Xorg >/dev/null',90)
        # Only this disposable guest is changed. Delete the old vendor tree so
        # absolute IRIX fallback paths cannot pick up its libraries/resources.
        if not resumed:
            cmd('test "$(mount | grep -c "on /emul/irix/")" = 0 && '
                'rm -rf /emul/irix /usr/local/share/xiri/fonts && cd / && '
                'pax -rz -pe -f /cdrom/payload.tgz && cd /root',1200)
        checkpoint('new-vendor-tree-extracted')
        if args.debug_failure:
            result['rld_check'] = get('sha256 /emul/irix/lib/rld /cdrom/expected-rld; '
                                     'stat -f "%z %Lp %N" /emul/irix/lib/rld; '
                                     'cmp -l /emul/irix/lib/rld /cdrom/expected-rld | head -20; '
                                     'cat /root/import-vendor.log')
            print(result['rld_check'],flush=True)
            checkpoint('diagnostic-requests-ready')
            deadline = time.monotonic()+600
            requests = []
            result['diagnostic_requests'] = requests
            while time.monotonic() < deadline:
                request = out/'request.json'
                if not request.exists():
                    time.sleep(.2)
                    continue
                item = json.loads(request.read_text())
                request.unlink()
                if item['command'] == 'CONTINUE':
                    break
                try:
                    reply = dict(output=(get if item.get('read') else cmd)(item['command'],item.get('timeout',120)))
                except Exception as error:
                    reply = dict(error=str(error))
                requests.append(dict(request=item,reply=reply))
                (out/'response.json').write_text(json.dumps(reply,indent=2)+'\n')
            else:
                raise TimeoutError('Diagnostic request window expired')
        cmd('sha256 -c /cdrom/VENDOR >/root/import-vendor.log',1200)
        checkpoint('new-vendor-file-hashes-verified')
        cmd('mkdir -p /emul/irix/etc && /usr/local/sbin/xiri-sync-users && '
            'rm -f /var/run/xiri-pty-ready && /etc/rc.d/xiri_devices start && '
            '/usr/X11R7/bin/mkfontdir /usr/local/share/xiri/fonts && '
            '/usr/local/sbin/xiri-update-filetypes',240)
        cmd('mkdir -p /root/import-test && cp /cdrom/type.c /cdrom/place.c /root/import-test/ && '
            'cd /root/import-test && for name in type place; do cc -O2 -Wall -Wextra -Werror '
            '-I/usr/X11R7/include "$name.c" -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib '
            '-lX11 -lXtst -o "$name" || exit; done',240)
        cmd('/etc/rc.d/xiri_famd start && /etc/rc.d/xdm start',90)
        checkpoint('new-vendor-tree-installed')
        greeter()
        capture('greeter')
        login('xiritest')
        desktop('desktop-first')
        # Exercise File Manager through the terminal, retaining the user's
        # actual identity/environment rather than launching it as root.
        cmd(shlex.join(['/root/import-test/type','127.0.0.1:0','winterm',
                        '/emul/irix/usr/sbin/fm "$HOME" > "$XIRI_SESSION_DIR/import-fm.out" 2> "$XIRI_SESSION_DIR/import-fm.err" &\n']))
        wait("xwininfo -root -tree | grep -F '\"xiri-indy:/usr/people/xiritest\"' >/dev/null",120)
        result['filemanager_tree'] = get('xwininfo -root -tree')
        capture('desktop-filemanager')
        logout()
        checkpoint('logout-passed')
        cmd('rm -f /usr/people/xiritest/.xsession-errors')
        login('xiritest')
        desktop('desktop-relogin')
        logout()
        login('netbsdtest')
        wait("pgrep -u netbsdtest -f '^/usr/X11R7/bin/ctwm( |$)' >/dev/null",120)
        result['native_session'] = get('ps -u netbsdtest -o pid,comm')
        capture('native-ctwm')
        cmd('/etc/rc.d/xdm stop',90)
        result['status'] = 'passed'
    except BaseException as error:
        result.update(status='failed',error=str(error))
        if lab.logged_in:
            try:
                cmd('cd /root')
                result['failure_logs'] = get('cat /usr/people/xiritest/.xsession-errors; '
                    'test -z "$job" || tail -50 "$job"/*.err')
                result['failed_checksums'] = get('grep FAILED /root/import-vendor.log; '
                                                'sha256 /emul/irix/lib/rld')
                print(result['failed_checksums'],flush=True)
                capture('failure')
            except Exception as capture_error:
                result['capture_error'] = str(capture_error)
        raise
    finally:
        if lab.logged_in:
            try:
                KernelLog(lab,int(base['kernel_msgbuf_symbol'],16)).halt()
            except Exception as error:
                result['shutdown_error'] = str(error)
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        result['base_unchanged'] = sha256(bundle/'netbsd-xiri.chd') == base['chd_sha256']
        if result['status'] == 'passed' and not (result['clean_shutdown'] and result['base_unchanged']):
            result.update(status='failed',error='Cleanup or source integrity check failed')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
        print('Result:',result['status'],out,flush=True)
    if result['status'] != 'passed':
        raise RuntimeError(result.get('error','Qualification failed'))


if __name__ == '__main__':
    main()
