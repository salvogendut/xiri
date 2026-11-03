#!/usr/bin/env python3
"""Add the requested wheel membership, or check it on a fresh CHD boot.

This is an account-only update of a qualified xdm image. Prior kernel,
runtime and imported-resource evidence stays explicitly inherited.
"""
import argparse
import copy
import json
from pathlib import Path
import re
import shlex
import shutil
import signal
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from xiri_lab import Guest, load_probe, sha256, source_hashes
from xiri_lab.kernel_log import KernelLog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--seed', type=Path, help='clone this raw seed and add wheel')
    choice.add_argument('--bundle', type=Path, help='verify an already packaged CHD')
    args = parser.parse_args()
    if args.seed:
        seed = args.seed.resolve()
        origin = json.loads((seed/'image-source.json').read_text())
        assert sha256(seed/'disk.raw') == origin['raw_sha256']
        bundle = Path(origin['bundle'])
    else:
        bundle = args.bundle.resolve()
    manifest = json.loads((bundle/'manifest.json').read_text())
    assert manifest['session_manager'] == 'xdm'
    assert sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
    assert sha256(bundle/'seed-result.json') == manifest['source_result_sha256']
    previous = json.loads((bundle/'seed-result.json').read_text())
    if args.seed:
        assert sha256(seed/'result.json') == manifest['source_result_sha256']
    profile = bundle/manifest['qualification_nvram']
    assert sha256(profile) == manifest['qualification_nvram_sha256']
    p = load_probe()
    p.IRIS, p.CI = bundle/'emulator/iris', bundle/'emulator/iris-ci'
    assert sha256(p.IRIS) == previous['pin']['emulator_sha256']
    assert sha256(p.CI) == previous['pin']['ci_client_sha256']
    runs = ROOT/'.work/xdm-wheel'; runs.mkdir(exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='prepare-' if args.seed else 'check-', dir=runs))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    shutil.copyfile(__file__, d/'harness.py')
    media = d/'media'; media.mkdir()
    shutil.copyfile(ROOT/'lab/irix-4dwm/type-ready.c', media/'type.c')
    p.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',media])
    disk = d/('disk.raw' if args.seed else 'disk.chd')
    source_disk = seed/'disk.raw' if args.seed else bundle/'netbsd-xiri.chd'
    source_digest = sha256(source_disk)
    p.run(['cp','--reflink=auto','--sparse=always',source_disk,disk])
    shutil.copyfile(profile,d/'nvram.bin')
    config = (bundle/'iris.toml').read_text().replace('tftp_dir = "tftp"',
        'tftp_dir = '+json.dumps(str(d/'no-tftp')))
    assert 'tftp_dir = '+json.dumps(str(d/'no-tftp')) in config
    if args.seed:
        # The builder packages disk.raw, so preparation must write that clone.
        assert 'overlay = true' in config
        config = config.replace('overlay = true', 'overlay = false')
    config += '\n[scsi.4]\npath = '+json.dumps(str(d/'probe.iso'))+'\ncdrom = true\n'
    lab = p.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600),d,config_text=config)
    launch = lab.launch
    def disk_launch(command,name):
        if name == 'emulator':
            command = list(command); command[command.index('--scsi1')+1] = str(disk)
        return launch(command,name)
    lab.launch = disk_launch
    guest = Guest(lab); cmd,get,wait = guest.command,guest.read_text,guest.wait_for
    evidence = dict(status='error',scope='xdm-wheel-prepare' if args.seed else 'xdm-wheel-chd',
        clean_shutdown=False,bundle=str(bundle.relative_to(ROOT)),source_disk_sha256=source_digest,
        input_manifest_sha256=sha256(bundle/'manifest.json'),
        inherited_seed_result_sha256=sha256(bundle/'seed-result.json'),
        sources={**source_hashes(),str(Path(__file__).relative_to(ROOT)):sha256(__file__),
                 'lab/irix-4dwm/type-ready.c':sha256(media/'type.c'),
                 'scripts/xiri_lab/kernel_log.py':sha256(ROOT/'scripts/xiri_lab/kernel_log.py')})
    def interrupted(signum,frame):
        signal.signal(signum,signal.SIG_IGN)
        raise RuntimeError('Interrupted: '+str(signum))
    signal.signal(signal.SIGTERM,interrupted)
    try:
        lab.start(boot=False)
        lab.wait('login: ',600);lab.send('root');lab.wait('xiri-indy# ',30);lab.logged_in=True
        cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin')
        evidence['console'] = cmd('sysctl kern.consdev | grep ttyE0 && tty | grep ttyZ0')
        before = get('cat /etc/group')
        passwd = get('sha256 /etc/master.passwd /etc/passwd')
        if args.seed: cmd('usermod -G wheel netbsdtest')
        after = get('cat /etc/group')
        if args.seed:
            expected = []
            for line in before.splitlines():
                if line.startswith('wheel:'):
                    fields = line.split(':'); members = fields[3].split(',') if fields[3] else []
                    if 'netbsdtest' not in members: members.append('netbsdtest')
                    fields[3] = ','.join(members); line = ':'.join(fields)
                expected.append(line)
            assert after.splitlines() == expected
        assert passwd == get('sha256 /etc/master.passwd /etc/passwd')
        evidence.update(group_before=before,group_after=after,passwd_sha256=passwd,
                        group_sha256=get('sha256 -q /etc/group').strip())
        evidence['account'] = get('id netbsdtest; getent group wheel')
        cmd('test "$(id -u netbsdtest)" = 1236 && test "$(id -g netbsdtest)" = 1236 && '
            'id -Gn netbsdtest | tr " " "\\n" | grep -qx wheel')
        cmd('export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | '
            'awk \'$1 == "/usr/X11R7/bin/Xorg" {for(i=1;i<NF;i++) if($i=="-auth") print $(i+1)}\'); export XAUTHORITY')
        wait('xwininfo -root -tree | grep \'"xlogin"\' >/dev/null',90)
        guest.monitor('disp compositor gl')
        evidence['dimensions'] = get('xdpyinfo | grep dimensions:')
        assert '1280x1024 pixels' in evidence['dimensions']
        evidence['services_before'] = get('cat /var/run/xdm.pid /var/run/xiri_famd.pid /var/run/rpcbind.pid')
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && mkdir -p /tmp/xiri-wheel-test && '
            'cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/type.c '
            '-L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o /tmp/xiri-wheel-test/type',180)
        cmd('rm -f /home/netbsdtest/wheel-login-proof /tmp/xiri-wheel-root-proof')
        guest.monitor('key type netbsdtest');guest.monitor('key Return')
        guest.monitor('key type netbsdtest');guest.monitor('key Return')
        # NetBSD pgrep matches argv[0], including its full pathname.
        wait("pgrep -u 1236 -f '^/usr/X11R7/bin/ctwm( |$)' > /tmp/xiri-wheel-test/wm.pid",120)
        cmd('XAUTHORITY=$(ps -axww -o args= | '
            'awk \'$1 == "/usr/X11R7/bin/Xorg" {for(i=1;i<NF;i++) if($i=="-auth") print $(i+1)}\'); export XAUTHORITY')
        wait('xwininfo -root -tree | grep \'"UXTerm"\' >/dev/null',120)
        tree = get('xwininfo -root -tree')
        terminal = re.search(r'"([^"\n]+)": \("[^"\n]*" "UXTerm"\)',tree)[1]
        def type_text(text):cmd(shlex.join(['/tmp/xiri-wheel-test/type',':0',terminal,text]))
        type_text('(id -un; id -u; id -Gn; pwd) > "$HOME/wheel-login-proof"\nsu -\n')
        wait('test -s /home/netbsdtest/wheel-login-proof',30)
        evidence['login_proof'] = get('cat /home/netbsdtest/wheel-login-proof').splitlines()
        assert evidence['login_proof'][:2] == ['netbsdtest','1236']
        assert 'wheel' in evidence['login_proof'][2].split()
        assert evidence['login_proof'][3] == '/home/netbsdtest'
        time.sleep(2)
        type_text('(id -un; id -u; echo "$HOME"; pwd) > /tmp/xiri-wheel-root-proof\nexit\n')
        wait('test -s /tmp/xiri-wheel-root-proof',30)
        evidence['su_login_proof'] = get('cat /tmp/xiri-wheel-root-proof').splitlines()
        assert evidence['su_login_proof'] == ['root','0','/root','/root']
        print('Fresh xdm login includes wheel; interactive su - reached root',flush=True)
        type_text('cat /tmp/xiri-wheel-root-proof; id\n')
        guest.monitor('disp compositor gl');guest.monitor('screen wait 500 10000')
        guest.monitor('screen shot '+str(d/'wheel-su.png'))
        evidence['png_sha256'] = sha256(d/'wheel-su.png')
        wm = int(get('cat /tmp/xiri-wheel-test/wm.pid').strip())
        type_text('(sleep 2; kill -TERM '+str(wm)+') &\n')
        wait('xwininfo -root -tree | grep \'"xlogin"\' >/dev/null',120)
        wait('! pgrep -u 1236',30)
        evidence['services_after'] = get('cat /var/run/xdm.pid /var/run/xiri_famd.pid /var/run/rpcbind.pid')
        assert evidence['services_before'] == evidence['services_after']
        evidence['kernel_files'] = get('sha256 /netbsd /netbsd.boot '+previous['irix_module']['path'])
        for key in ('native_kernel_sha256','boot_kernel_sha256'):
            assert previous['pin'][key] in evidence['kernel_files']
        assert previous['irix_module']['sha256'] in evidence['kernel_files']
        evidence['modstat'] = get('modstat | awk \'NR==1 || $1=="compat_irix_o32"\'')
        assert re.search(r'^compat_irix_o32\s+exec\s+filesys\s',evidence['modstat'],re.M)
        evidence['securelevel'] = int(get('sysctl -n kern.securelevel').strip())
        assert evidence['securelevel'] == 1
        evidence['native_after'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        cmd('rm -f /home/netbsdtest/wheel-login-proof /tmp/xiri-wheel-root-proof; rm -r /tmp/xiri-wheel-test')
        evidence['status'] = 'passed'
    except Exception as error:
        evidence['error'] = str(error)
        if lab.logged_in:
            try:
                evidence['failure_log'] = get('ps -axww -o uid,pid,args; tail -50 /var/log/xdm.log',30)
                guest.monitor('disp compositor gl')
                guest.monitor('screen shot '+str(d/'failure.png'))
            except Exception as capture_error:evidence['failure_capture_error']=str(capture_error)
        raise
    finally:
        if lab.logged_in:
            try:evidence['shutdown_log'] = KernelLog(lab,int(manifest['kernel_msgbuf_symbol'],16)).halt()
            except Exception as error:evidence['cleanup_error'] = str(error)
        lab.close();evidence['clean_shutdown'] = lab.clean_shutdown
        evidence['source_disk_unchanged'] = sha256(source_disk) == source_digest
        if not (evidence['clean_shutdown'] and evidence['source_disk_unchanged']):evidence['status']='error'
        (d/'wheel-result.json').write_text(json.dumps(evidence,indent=2)+'\n')
    assert evidence['status'] == 'passed'
    if args.seed:
        assert not Path(str(disk)+'.overlay').exists()
        assert sha256(disk) != source_digest, 'account update did not reach disk.raw'
        # Preserve the older qualification as provenance, not fresh observations.
        r = copy.deepcopy(previous)
        r.update(status='observed',clean_shutdown=True,base_raw_unchanged=True,
                 base_image=origin,base_seed_result_sha256=sha256(seed/'result.json'),
                 graphics_console=evidence['console'],display=evidence['dimensions'],
                 inherited_preparation=dict(bundle=str(bundle),result_sha256=manifest['source_result_sha256']),
                 account_update=evidence,sources=evidence['sources'],native_after=evidence['native_after'],
                 shutdown_log=evidence['shutdown_log'])
        r['installed_files']['/etc/group'] = evidence['group_sha256']
        r['xdm']['accounts']['netbsdtest']['supplementary_groups'] = ['wheel']
        r['xdm']['image_login_qualification'] = 'account update awaiting direct CHD check'
        r['irix_module'].update(modstat=evidence['modstat'],securelevel=evidence['securelevel'])
        shutil.copyfile(profile,d/'nvram-graphics.bin')
        shutil.copyfile(seed/'nvram.bin',d/'nvram.bin')
        r['graphics_nvram_sha256'] = sha256(d/'nvram-graphics.bin')
        (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    print('Passed; clean halt and source disk unchanged',flush=True)


if __name__ == '__main__':main()
