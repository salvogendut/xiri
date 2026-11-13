#!/usr/bin/env python3
"""Install the maintained xdm runtime on a disposable, verified module seed."""
import argparse
import json
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import tempfile
from types import SimpleNamespace

from xiri_lab import Guest, ROOT, load_probe, sha256, source_hashes
from xiri_lab.xdm_image import runtime_files, support_files
from xiri_lab.kernel_log import KernelLog
from xiri_lab.gimp_resources import prepare as prepare_gimp_resources
from xiri_lab.application_resources import PACKAGES, prepare as prepare_application_resources


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, default=ROOT/'.work/xiri-image/prepared-seed-20261103-module')
    parser.add_argument('--kernel-build',type=Path,default=ROOT/'.work/netbsd-module-build')
    parser.add_argument('--baseline',type=Path,help='install a replacement kernel/module pair from --kernel-build')
    parser.add_argument('--keep-accounts',action='store_true',help='refresh an existing xdm image without changing accounts or passwords')
    parser.add_argument('--fam-build', type=Path, help='install a verified native FAM build')
    parser.add_argument('--multiuser', action='store_true', help='add the second disposable IRIX desktop account xiritest2')
    parser.add_argument('--refresh-xservers', action='store_true',
                        help='install the maintained Xorg command in this disposable image')
    parser.add_argument('--newport-driver', type=Path,
                        help='install the module pinned by lab/newport-text/build.json')
    parser.add_argument('--refresh-font-resources', action='store_true',
                        help='adopt the qualified Courier bitmap and greeter resources')
    parser.add_argument('--gimp-resources', type=Path, help='verified output directory from stage-irix-gimp.py')
    for name in PACKAGES:
        parser.add_argument('--'+name+'-resources', type=Path,
                            help='verified output directory from stage-irix-'+name+'.py')
    args = parser.parse_args()
    seed = args.seed.resolve()
    origin = json.loads((seed/'image-source.json').read_text())
    previous = json.loads((seed/'result.json').read_text())
    assert previous['status'] == 'observed' and previous['clean_shutdown']
    multiuser = args.multiuser or (args.keep_accounts and
        'xiritest2' in previous.get('xdm', {}).get('accounts', {}))
    newport_build = None
    if args.newport_driver:
        newport_build = json.loads((ROOT/'lab/newport-text/build.json').read_text())
        assert sha256(args.newport_driver) == newport_build['module_sha256']
    font_profile = None
    if args.refresh_font_resources:
        font_profile = json.loads((ROOT/'lab/newport-text/font-profile.json').read_text())
        assert sha256(ROOT/'runtime/etc/Xresources') == font_profile['resource_sha256']
        assert sha256(ROOT/'runtime/etc/xdm-Xresources') == font_profile['greeter_resource_sha256']
        driver_sha = newport_build['module_sha256'] if newport_build else previous['newport_driver']['sha256']
        assert driver_sha == font_profile['newport_module_sha256']
    pin=json.loads(args.baseline.read_text()) if args.baseline else previous['pin']
    symbols=args.kernel_build/'obj/sys/arch/sgimips/compile'/Path(pin['config_path']).name/'netbsd.gdb'
    assert sha256(symbols)==pin['debug_kernel_sha256']
    symbol_table=subprocess.check_output(['nm',str(symbols)],text=True)
    msgbuf_symbol=int(re.search(r'^([0-9a-f]+) [BbDd] msgbufp$',symbol_table,re.M)[1],16)
    assert sha256(seed/'disk.raw') == origin['raw_sha256']
    bundle = Path(origin['bundle'])
    p = load_probe()
    p.IRIS, p.CI = bundle/'emulator/iris', bundle/'emulator/iris-ci'
    for path,key in ((p.IRIS,'emulator_sha256'),(p.CI,'ci_client_sha256')):
        assert sha256(path) == previous['pin'][key]
    runs = ROOT/'.work/xdm-image/prepare'; runs.mkdir(parents=True,exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='ordinary-',dir=runs))
    (d/'harness.py').write_bytes(Path(__file__).read_bytes())
    print('Results: '+str(d.relative_to(ROOT)),flush=True)
    media = d/'media'; media.mkdir()
    fam_build = None
    if args.fam_build:
        fam_build = json.loads((args.fam_build/'result.json').read_text())
        assert fam_build['status'] == 'built'
        assert fam_build['source_manifest_sha256'] == sha256(ROOT/'lab/native-fam/source.json')
        source = args.fam_build/'fam-2.7.0/src/famd'
        assert sha256(source) == fam_build['files']['src/famd']
        shutil.copyfile(source, media/'famd')
    gimp = prepare_gimp_resources(args.gimp_resources.resolve(), media) if args.gimp_resources else None
    applications = {}
    for name in PACKAGES:
        directory = getattr(args, name+'_resources')
        if directory:
            applications[name] = prepare_application_resources(name, directory.resolve(), media)
    # Preserve resource provenance when refreshing an already imported image.
    inherited_resources = dict(previous.get('application_resources', {}))
    if previous.get('gimp_resources') and not gimp:
        inherited_resources['gimp'] = previous['gimp_resources']
    for name, resources in inherited_resources.items():
        if name not in applications:
            ledger = bundle/(name+'-resources.json')
            assert sha256(ledger) == resources['manifest_sha256']
            shutil.copyfile(ledger, media/ledger.name)
    replacement=None
    if args.baseline:
        build_path=ROOT/pin['module_build_manifest']
        assert sha256(build_path)==pin['module_build_manifest_sha256']
        replacement=json.loads(build_path.read_text())
        for name,record in replacement['artifacts'].items():
            source=args.kernel_build/record['path']
            assert sha256(source)==record['sha256']
            shutil.copyfile(source,media/name)
        assert sha256(media/'netbsd')==pin['native_kernel_sha256']
        assert sha256(media/'netbsd.boot')==pin['boot_kernel_sha256']
    shutil.copytree(ROOT/'runtime',media/'runtime',ignore=shutil.ignore_patterns('build'))
    if newport_build:
        shutil.copyfile(args.newport_driver, media/'newport_drv.so')
    support = support_files(bundle,previous)
    (media/'SUPPORT').write_text(''.join(f'SHA256 ({path}) = {digest}\n' for path,digest in sorted(support.items())))
    # Send a file list on the CD instead of a growing serial command line.
    installed_paths = sorted(set(previous['installed_files']) | set(runtime_files()) |
                             {'/emul/irix/etc/passwd', '/emul/irix/etc/group', '/etc/hosts'} |
                             ({'/usr/people/xiritest2/.xsession'} if multiuser else set()) |
                             ({font_profile['native_file']} if font_profile else set()))
    (media/'INSTALLED-PATHS').write_bytes(b''.join(path.encode()+b'\0' for path in installed_paths))
    (media/'motd').write_text('Xiri development image: native NetBSD xdm + original IRIX desktop\n'
        'Graphical login: xiritest / xiritest (IRIX); netbsdtest / netbsdtest (ctwm).\n'
        'These are public lab passwords. Root serial login is for administration.\n' +
        ('Second IRIX login: xiritest2 / xiritest2.\n' if multiuser else '') +
        'IRIX HOME: /usr/people/<username>. Logs: ~/.xiri/sessions/.\n'
        'Use shutdown -h now and wait for the PROM before closing IRIS.\n')
    (media/'SHA256').write_text(''.join(f'SHA256 ({f.relative_to(media)}) = {sha256(f)}\n'
        for f in sorted(media.rglob('*')) if f.is_file()))
    p.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',media])
    for name in ('disk.raw','nvram.bin'):
        p.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name])
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(args.kernel_build/'tftp' if replacement else bundle/'tftp')),
                    (ROOT/'lab/indy-netbsd/iris.toml').read_text(),flags=re.M)
    lab = p.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600),d,config_text=config)
    guest = Guest(lab); cmd,get = guest.command,guest.read_text
    # Keep imported-artifact provenance, not the old launcher's session results.
    keep = ('pin','staged','desktop_dimensions','desktop_services','native_fam_build',
            'bitmap_ledger_sha256','installed_files','native_rpcbind_build','desktop_behavior',
            'xorg_configuration','newport_driver','irix_module')
    r = {key:previous[key] for key in keep}
    for key in ('gimp_resources', 'application_resources'):
        if key in previous:
            r[key] = previous[key]
    if 'terminal_font' in previous:
        r['terminal_font'] = previous['terminal_font']
    r['pin']=pin
    r.update(status='error',clean_shutdown=False,base_image=origin,
             base_seed_result_sha256=sha256(seed/'result.json'),
             sources={**source_hashes(), 'scripts/prepare-xiri-xdm-image.py':sha256(Path(__file__)),
                      'scripts/xiri_lab/kernel_log.py':sha256(ROOT/'scripts/xiri_lab/kernel_log.py'),
                      'scripts/xiri_lab/gimp_resources.py':sha256(ROOT/'scripts/xiri_lab/gimp_resources.py'),
                      'scripts/xiri_lab/application_resources.py':sha256(ROOT/'scripts/xiri_lab/application_resources.py'),
                      'scripts/xiri_lab/xdm_image.py':sha256(ROOT/'scripts/xiri_lab/xdm_image.py')},
             runtime_sources={str(f.relative_to(media)):sha256(f) for f in (media/'runtime').rglob('*') if f.is_file()})
    r['kernel_msgbuf_symbol']=hex(msgbuf_symbol)

    def interrupted(signum, frame):
        signal.signal(signum,signal.SIG_IGN)
        raise RuntimeError('Preparation interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted)
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && '
            'sha256 -c SHA256 >/root/xdm-media.log && sha256 -c SUPPORT >/root/xdm-payload.log',1800)
        r['support_files_verified_before'] = support
        print('Base kernel, module and imported payload verified',flush=True)
        if fam_build:
            cmd('/etc/rc.d/xiri_famd stop && install -m 755 /cdrom/famd /usr/local/sbin/famd')
            r['native_fam_build'] = fam_build
        if newport_build:
            cmd('/etc/rc.d/xdm stop', 90)
            guest.wait_for('! pgrep -x Xorg >/dev/null', 90)
            cmd('install -m 755 /cdrom/newport_drv.so /usr/X11R7/lib/modules/drivers/newport_drv.so')
            r['newport_driver'] = dict(previous['newport_driver'],
                source=str(args.newport_driver.resolve()), sha256=newport_build['module_sha256'],
                fallback_build=newport_build,
                fallback_build_manifest='lab/newport-text/build.json',
                fallback_build_manifest_sha256=sha256(ROOT/'lab/newport-text/build.json'))
            driver_path = '/usr/X11R7/lib/modules/drivers/newport_drv.so'
            if driver_path in r['staged']:
                r['staged'] = dict(r['staged'], **{driver_path: newport_build['module_sha256']})
        if replacement:
            path=previous['irix_module']['path']
            cmd('install -m 444 /cdrom/netbsd /netbsd && install -m 444 /cdrom/netbsd.boot /netbsd.boot && '
                'install -m 444 /cdrom/compat_irix_o32.kmod '+shlex.quote(path))
            r['irix_module']=dict(name='compat_irix_o32',path=path,
                sha256=sha256(media/'compat_irix_o32.kmod'),build_manifest=pin['module_build_manifest'],
                build_manifest_sha256=pin['module_build_manifest_sha256'])
        if gimp:
            cmd('tar xzpf /cdrom/gimp-resources.tgz -C / && sh /cdrom/gimp-verify.sh >/root/gimp-resource-check.log', 600)
            r['gimp_resources'] = {k:v for k,v in gimp.items() if k != 'files'}
        for name, resources in applications.items():
            cmd(f'tar xzpf /cdrom/{name}-resources.tgz -C / && '
                f'sh /cdrom/{name}-verify.sh >/root/{name}-resource-check.log', 600)
            r.setdefault('application_resources', {})[name] = {
                key: value for key, value in resources.items() if key != 'files'}
        cmd('mkdir -p /root/xdm-image-build && cp -R /cdrom/runtime /root/xdm-image-build/ && '
            'cd /root/xdm-image-build/runtime && make && sh install.sh --enable-xdm',300)
        # The original File Manager resolves gethostname() before operating on
        # local files. Without an IPv4 host entry its fiHostCache is empty and
        # it misleadingly reports existing files as missing. Configure this
        # standalone lab image; the general runtime installer must not rewrite
        # an administrator's network configuration.
        hosts_before = get('sha256 -q /etc/hosts').strip()
        cmd('host=$(hostname); '
            'if ! awk -v host="$host" \'$1 ~ /^[0-9]+\\./ { '
            'for (i=2; i<=NF && $i !~ /^#/; i++) if ($i == host) found=1 } '
            'END { exit !found }\' /etc/hosts; then '
            'printf "\\n127.0.0.1\\t%s\\n" "$host" >>/etc/hosts; fi; '
            'getent hosts "$host" >/root/xdm-hostname-check.log')
        r['local_hostname'] = dict(name=get('hostname').strip(),
            before_sha256=hosts_before, after_sha256=get('sha256 -q /etc/hosts').strip(),
            lookup=get('cat /root/xdm-hostname-check.log'))
        if fam_build:
            cmd('install -m 644 /cdrom/runtime/etc/fam.conf /etc/xiri/fam.conf && '
                '/etc/rc.d/xiri_famd start')
        if args.refresh_xservers:
            # The general installer preserves administrator configuration.
            # Image preparation can explicitly adopt the new server command
            # after verifying the input image against its support inventory.
            before = get('sha256 -q /etc/xiri/xdm/Xservers').strip()
            cmd('install -m 644 /cdrom/runtime/etc/xdm-Xservers /etc/xiri/xdm/Xservers')
            after = get('sha256 -q /etc/xiri/xdm/Xservers').strip()
            assert after == sha256(media/'runtime/etc/xdm-Xservers')
            r['xserver_configuration_update'] = dict(before_sha256=before, after_sha256=after)
        if font_profile:
            updates = {}
            for source, destination, digest in [
                ('Xresources', font_profile['resource'], font_profile['resource_sha256']),
                ('xdm-Xresources', font_profile['greeter_resource'], font_profile['greeter_resource_sha256'])]:
                before = get('sha256 -q '+shlex.quote(destination)).strip()
                cmd('install -m 644 /cdrom/runtime/etc/'+source+' '+shlex.quote(destination))
                after = get('sha256 -q '+shlex.quote(destination)).strip()
                assert after == digest
                updates[destination] = dict(before_sha256=before, after_sha256=after)
            assert get('sha256 -q '+shlex.quote(font_profile['native_file'])).strip() == font_profile['native_file_sha256']
            r['font_configuration_update'] = updates
            r['terminal_font'] = font_profile
        if gimp:
            cmd('test "$(readlink /usr/freeware)" = /emul/irix/usr/freeware')
        if 'acrobat' in applications:
            cmd('test "$(readlink /usr/adobe)" = /emul/irix/usr/adobe')
        if args.keep_accounts:
            cmd('test "$(id -u xiritest)" = 1234 && test "$(id -g xiritest)" = 1234 && '
                'test "$(id -u netbsdtest)" = 1236 && test "$(id -g netbsdtest)" = 1236 && '
                'id -Gn netbsdtest | tr " " "\\n" | grep -qx wheel')
        else:
            cmd('groupadd -g 1235 xiritest-extra && usermod -G xiritest-extra '
                '-p "$(pwhash -b 6 xiritest)" xiritest && groupadd -g 1236 netbsdtest && '
                'useradd -m -u 1236 -g netbsdtest -G wheel -d /home/netbsdtest -s /bin/sh '
                '-p "$(pwhash -b 6 netbsdtest)" netbsdtest')
        if multiuser:
            cmd('if ! id xiritest2 >/dev/null 2>&1; then '
                'groupadd -g 1237 xiritest2 && useradd -m -u 1237 -g xiritest2 -G xiritest-extra '
                '-d /usr/people/xiritest2 -s /bin/ksh -p "$(pwhash -b 6 xiritest2)" xiritest2 || exit; fi; '
                'test "$(id -u xiritest2)" = 1237 && test "$(id -g xiritest2)" = 1237 && '
                'chmod 700 /usr/people/xiritest2 && '
                'install -o xiritest2 -g xiritest2 -m 700 /usr/local/share/xiri/xdm.xsession /usr/people/xiritest2/.xsession')
        # IRIX libc lookup data follows native users; authentication stays native.
        native_accounts = get('sha256 /etc/passwd /etc/master.passwd')
        before_accounts = get('cat /emul/irix/etc/passwd')
        cmd('/usr/local/sbin/xiri-sync-users')
        after_accounts = get('cat /emul/irix/etc/passwd')
        assert re.search(r'^xiritest:[^:]*:1234:1234:[^:]*:/usr/people/xiritest:/bin/sh$', after_accounts, re.M)
        assert re.search(r'^root:[^:]*:0:0:[^:]*:/:/bin/sh$', after_accounts, re.M)
        assert native_accounts == get('sha256 /etc/passwd /etc/master.passwd')
        r['emulation_accounts'] = dict(before=before_accounts, after=after_accounts,
                                      native_databases_unchanged=True)
        cmd('install -o xiritest -g xiritest -m 700 /usr/local/share/xiri/xdm.xsession /usr/people/xiritest/.xsession && '
            'cp /etc/ttys /etc/ttys.before-xdm && '
            "sed '/^ttyE0[[:space:]]/s/[[:space:]]on[[:space:]]/ off /' /etc/ttys.before-xdm >/etc/ttys && "
            'install -m 644 /cdrom/motd /etc/motd')
        # Leave legacy diagnostic tools for reproduction; only select the new runtime.
        r['vendor_shell'] = cmd("su -m xiritest -c '/emul/irix/bin/sh -c \"echo IRIX_SHELL_IMAGE_OK\"'")
        listing = get('xargs -0 sha256 </cdrom/INSTALLED-PATHS', 600)
        r['installed_files'] = dict(re.findall(r'^SHA256 \((.+)\) = ([0-9a-f]{64})$',listing,re.M))
        assert len(r['installed_files']) == len(installed_paths)
        if gimp:
            r['installed_files'].update(gimp['files'])
        for resources in applications.values():
            r['installed_files'].update(resources['files'])
        r['ttys'] = get('cat /etc/ttys')
        assert re.search(r'^ttyE0\s+.*\soff\s',r['ttys'],re.M)
        assert re.search(r'^ttyZ0\s+.*\son\s',r['ttys'],re.M)
        # Save serial automation state; generate a separate graphical AutoLoad profile.
        lab.offset=len(lab.serial_text());lab.send('shutdown -h now')
        lab.wait('unmounting done',90);lab.wait(r'Option\?',30);lab.logged_in=False
        lab.send('5');lab.wait('>> ',10)
        for setting in ['systempartition scsi(0)disk(1)rdisk(0)partition(8)',
                        'osloadpartition scsi(0)disk(1)rdisk(0)partition(0)',
                        'osloader boot','osloadfilename netbsd.boot','osloadoptions auto']:
            lab.offset=len(lab.serial_text());lab.send('setenv '+setting);lab.wait('>> ',10)
        guest.monitor('rtc save');shutil.copyfile(d/'nvram.bin',d/'nvram-serial.bin')
        for setting in ['AutoLoad Yes','-f console g']:
            lab.offset=len(lab.serial_text());lab.send('setenv '+setting);lab.wait('>> ',10)
        guest.monitor('rtc save');shutil.copyfile(d/'nvram.bin',d/'nvram-graphics.bin')
        r['graphics_nvram_sha256']=sha256(d/'nvram-graphics.bin')
        lab.offset=len(lab.serial_text());guest.monitor('reset');guest.monitor('start')
        lab.wait('login: ',600);lab.send('root');lab.wait('xiri-indy# ',30);lab.logged_in=True
        r['graphics_console']=cmd('sysctl kern.consdev | grep ttyE0 && tty | grep ttyZ0')
        cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin')
        r['boot_services']=cmd('/etc/rc.d/xdm status && /etc/rc.d/rpcbind status && /etc/rc.d/xiri_famd status && test -f /var/run/xiri-pty-ready')
        cmd('export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | '
            'awk \'$1 == "/usr/X11R7/bin/Xorg" {for (i=1;i<NF;i++) if ($i == "-auth") print $(i+1)}\'); export XAUTHORITY')
        guest.wait_for("xwininfo -root -tree | grep '\"xlogin\"' >/dev/null",90)
        r['display']=get('xdpyinfo | grep dimensions:'); assert '1280x1024 pixels' in r['display']
        guest.monitor('disp compositor gl');guest.monitor('screen wait 500 10000')
        guest.monitor('screen shot '+str(d/'xdm-greeter.png'))
        r['greeter_png_sha256']=sha256(d/'xdm-greeter.png')
        r['irix_module']['modstat']=get('modstat')
        r['irix_module']['securelevel']=int(get('sysctl -n kern.securelevel').strip())
        assert re.search(r'^compat_irix_o32\s+exec\s+filesys\s',r['irix_module']['modstat'],re.M)
        assert r['irix_module']['securelevel']==1
        r['native_after']=cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        r.update(status='observed',graphics_boot=True,guest_payload_verified=True,
                 executable_permissions_applied=previous['executable_permissions_applied'],
                 persistent_helpers_installed=True,native_x11_after=True,
                 session_manager='xdm',xdm={'greeter_boot_verified':True,
                    'accounts':{'xiritest':{'uid':1234,'home':'/usr/people/xiritest','desktop':'4Dwm'},
                                'netbsdtest':{'uid':1236,'home':'/home/netbsdtest','desktop':'ctwm',
                                              'supplementary_groups':['wheel']}},
                    'runtime_qualification':'docs/results/2026-11-03-xiri-xdm.json',
                    'runtime_qualification_sha256':sha256(ROOT/'docs/results/2026-11-03-xiri-xdm.json'),
                    'image_login_qualification':'pending direct CHD check'})
        if args.keep_accounts:
            r['xdm']['accounts'].update(previous.get('xdm', {}).get('accounts', {}))
        if multiuser:
            r['xdm']['accounts']['xiritest2'] = dict(uid=1237, home='/usr/people/xiritest2',
                desktop='4Dwm', supplementary_groups=['xiritest-extra'])
        print('Graphical disk autoboot reached full-screen xdm; ready to package',flush=True)
    finally:
        if lab.logged_in and 'graphics_console' in r:
            try:r['shutdown_log']=KernelLog(lab,msgbuf_symbol).halt()
            except Exception as error:r['cleanup_error']=str(error)
        lab.close();r['clean_shutdown']=lab.clean_shutdown
        r['base_raw_unchanged']=sha256(seed/'disk.raw')==origin['raw_sha256']
        if r['status']=='observed' and not (r['clean_shutdown'] and r['base_raw_unchanged']):r['status']='error'
        if (d/'nvram-serial.bin').exists():shutil.copyfile(d/'nvram-serial.bin',d/'nvram.bin')
        (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    assert r['status']=='observed'


if __name__=='__main__':
    main()
