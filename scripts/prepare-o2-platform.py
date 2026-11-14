#!/usr/bin/env python3
"""Prepare an isolated O2/R10000 candidate from the native reference and versioned packages.

This is a platform qualification fixture, not the clean-target installer.
A separate graphical cold-boot probe must qualify the resulting disk.
"""
import argparse
import json
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
from types import SimpleNamespace

from xiri_lab import ROOT, Guest, load_probe, sha256
from xiri_lab.kernel_log import KernelLog
from xiri_lab.xdm_image import support_files


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('base','kernel-build','native-package','payload','emulator','nvram','output'):
        parser.add_argument('--'+name,required=True,type=Path)
    args=parser.parse_args()
    base,build,package,payload,emu,nvram,out=[getattr(args,k).resolve() for k in
        ('base','kernel_build','native_package','payload','emulator','nvram','output')]
    baseline=json.loads((base/'manifest.json').read_text())
    seed=json.loads((base/'seed-result.json').read_text())
    assert sha256(base/'seed-result.json')==baseline['source_result_sha256']
    native=json.loads((package/'manifest.json').read_text())
    vendor=json.loads((payload/'manifest.json').read_text())
    kernel=json.loads((build/'module.json').read_text())
    emulator=json.loads((emu/'manifest.json').read_text())
    assert native['status']=='native-package-built' and vendor['status']=='payload-verified'
    assert native['target']['kernel_sha256']==kernel['artifacts']['netbsd']['sha256']
    assert native['artifacts']['module']['sha256']==kernel['artifacts']['compat_irix_o32.kmod']['sha256']
    assert sha256(base/'netbsd-xiri.chd')==baseline['chd_sha256']
    assert sha256(package/'native.tar.gz')==native['archive_sha256']
    assert sha256(payload/'payload.tar.gz')==vendor['payload_sha256']
    assert sha256(emu/'iris')==emulator['iris_sha256'] and sha256(emu/'iris-ci')==emulator['ci_sha256']
    for key in ('netbsd','netbsd.boot','compat_irix_o32.kmod'):
        assert sha256(build/kernel['artifacts'][key]['path'])==kernel['artifacts'][key]['sha256']
    symbols=subprocess.check_output(['nm',str(build/'kernel-media/netbsd')],text=True)
    msgbuf=int(re.search(r'^([0-9a-f]+) B msgbufp$',symbols,re.M)[1],16)
    out.mkdir(parents=True,exist_ok=False);media=out/'media';media.mkdir()
    shutil.copyfile(__file__,out/'probe-used.py')
    subprocess.run(['cp','--reflink=auto','--sparse=always','--',str(base/'netbsd-xiri.chd'),str(out/'disk.chd')],check=True)
    shutil.copyfile(nvram,out/'nvram.bin')
    for source,dest in [(package/'native.tar.gz','native.tgz'),(payload/'payload.tar.gz','vendor.tgz'),
                        (ROOT/'lab/native-package/install-fixture.sh','install-native.sh')]:
        shutil.copyfile(source,media/dest)
    (media/'VENDOR').write_text(''.join('SHA256 ('+name+') = '+row['sha256']+'\n'
        for name,row in sorted(vendor['files'].items()) if row['type']=='file'))
    native_files={p:h for p,h in support_files(base,seed).items()
        if not p.startswith(('/emul/','/usr/local/share/xiri/fonts/')) and p!='/etc/ttys'}
    for row in native['files'].values():
        if row['type']=='file' and row['policy']!='preserve-config':
            native_files[row['destination']]=row['sha256']
    (media/'NATIVE').write_text(''.join('SHA256 ('+p+') = '+h+'\n' for p,h in sorted(native_files.items())))
    (media/'SHA256').write_text(''.join('SHA256 ('+p.name+') = '+sha256(p)+'\n' for p in sorted(media.iterdir())))
    subprocess.run([shutil.which('genisoimage') or 'mkisofs','-quiet','-R','-J','-V','XIRI_O2',
                    '-o',str(out/'probe.iso'),str(media)],check=True)
    config=f'''nvram = "nvram.bin"
banks = [256, 0, 0, 0]
headless = true
no_audio = true
ci = true
scsi_deferred_int = true
nat_subnet = "192.168.231.0/24"
[machine]
profile = "o2_ip32"
cpu = "r10000"
[scsi.1]
path = {json.dumps(str(out/'disk.chd'))}
cdrom = false
overlay = true
[scsi.4]
path = {json.dumps(str(out/'probe.iso'))}
cdrom = true
[network]
mode = "nat"
mac = "08:00:69:12:34:58"
tftp_dir = {json.dumps(str(build/'tftp'))}
'''
    probe=load_probe()
    if not shutil.which('toolbox'):probe.TOOLBOX=[]
    probe.IRIS,probe.CI=emu/'iris',emu/'iris-ci'
    lab=probe.Lab(SimpleNamespace(mode='ci',debugger=False,boot_timeout=600),out,config_text=config)
    launch=lab.launch
    def own_launch(command,name):
        if name=='emulator':
            command=list(command);command[command.index('--scsi1')+1]=str(out/'disk.chd')
        return launch(command,name)
    lab.launch=own_launch
    guest=Guest(lab);cmd,get=guest.command,guest.read_text
    result=dict(schema=1,status='incomplete',scope=__doc__.strip(),base_chd_sha256=baseline['chd_sha256'],
        kernel_build=kernel,native_package_sha256=native['archive_sha256'],native_manifest_sha256=sha256(package/'manifest.json'),
        payload_sha256=vendor['payload_sha256'],payload_manifest_sha256=sha256(payload/'manifest.json'),
        profile=vendor['profile'],effective_emulator=emulator,nvram_source_sha256=sha256(nvram),
        kernel_msgbuf_symbol=hex(msgbuf),script_sha256=sha256(__file__),commands=[],graphical_qualification=False)
    def checkpoint(stage):
        (out/'checkpoint.json').write_text(json.dumps(dict(result,stage=stage),indent=2)+'\n');print(stage,flush=True)
    def run(command,timeout=180):
        result['commands'].append(command);return cmd(command,timeout)
    def prom(command):
        lab.send(command);lab.wait(r'(?:^|\n)> ',30)
    def interrupted(signum,frame):raise RuntimeError('Interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM,interrupted)
    try:
        lab.start(boot=False)
        lab.wait(r'Option\?',120);lab.send('5');lab.wait(r'(?:^|\n)> ',30)
        for command in ['setenv console d','setenv AutoLoad No',
                        'setenv SystemPartition scsi(0)disk(1)rdisk(0)partition(8)',
                        'setenv OSLoadPartition scsi(0)disk(1)rdisk(0)partition(0)','setenv osloader boot',
                        'setenv osloadfilename netbsd.boot','setenv osloadoptions auto']:
            prom(command)
        checkpoint('o2-prom-ready')
        lab.send('boot -f bootp():netbsd-XIRI_O2 --s')
        boot=lab.wait(r'Enter pathname of shell|Stopped in pid|panic:',600)
        if boot[0]!='Enter pathname of shell':
            raise RuntimeError('Native O2 kernel stopped before single-user login: '+boot[0])
        lab.send('');lab.wait(r'# ',30)
        lab.send("export PS1='xiri-indy# '; export PATH=/sbin:/usr/sbin:/bin:/usr/bin:/usr/local/sbin:/usr/local/bin:/usr/X11R7/bin")
        lab.wait(r'xiri-indy# ',30);lab.logged_in=True
        run('mount -u -w / && mkdir -p /cdrom /root/o2-platform && mount -t cd9660 -o ro /dev/cd0a /cdrom')
        result['identity']=get('uname -a; sysctl hw.model; dmesg',300)
        checkpoint('o2-native-single-user')
        run('cd /cdrom && sha256 -c SHA256 > /root/o2-media.log && cd /root/o2-platform',1200)
        run('pax -rz -pe -f /cdrom/native.tgz && install -m 444 kernel/netbsd /netbsd && install -m 444 kernel/netbsd.boot /netbsd.boot')
        run('sh preflight.sh > /root/o2-preflight.log',600)
        run('sh /cdrom/install-native.sh /root/o2-platform && sh preflight.sh --verify-installed > /root/o2-installed.log',600)
        run('sha256 -c /cdrom/NATIVE > /root/o2-native-files.log',600)
        result['native_files_verified']=native_files
        module=native['artifacts']['module']['destination']
        run('modload '+shlex.quote(module)+' && modstat | grep compat_irix')
        result['module']=get('modstat')
        checkpoint('o2-native-package-installed')
        run('rm -rf /emul/irix /usr/local/share/xiri/fonts && cd / && pax -rz -pe -f /cdrom/vendor.tgz && cd /root',1200)
        run('sha256 -c /cdrom/VENDOR > /root/o2-vendor.log',1200)
        run('mount -t ptyfs -o group=0,mode=0600 ptyfs /dev/pts && '
            '/usr/local/sbin/xiri-sync-users && rm -f /var/run/xiri-pty-ready && /etc/rc.d/xiri_devices start && '
            '/usr/X11R7/bin/mkfontdir /usr/local/share/xiri/fonts && /usr/local/sbin/xiri-update-filetypes',600)
        run('sgivol -w boot /usr/mdec/ip3xboot /dev/rsd0c',180)
        # The reference was an Indy; this disposable candidate uses O2 Ethernet.
        run('if test -f /etc/ifconfig.sq0; then mv /etc/ifconfig.sq0 /etc/ifconfig.mec0; fi; '
            'printf "inet 192.168.231.2 netmask 255.255.255.0\n" > /etc/ifconfig.mec0')
        run("sed -e '/^ttyC0[[:space:]]/s/[[:space:]]off[[:space:]]/ on /' "
            "-e '/^ttyZ0[[:space:]]/s/[[:space:]]on[[:space:]]/ off /' "
            '/etc/ttys > /root/ttys.o2 && install -m 644 /root/ttys.o2 /etc/ttys')
        run('/emul/irix/bin/sh -c "echo IRIX_6530_SHELL_OK" > /root/o2-irix-shell.log')
        result['irix_shell']=get('cat /root/o2-irix-shell.log');assert 'IRIX_6530_SHELL_OK' in result['irix_shell']
        result['ttys']=get('cat /etc/ttys')
        result['native_files_verified']['/etc/ttys']=get('sha256 -q /etc/ttys').strip()
        checkpoint('o2-vendor-prepared')
        result['status']='prepared'
    except BaseException as error:
        result.update(status='failed',error=str(error))
        try:lab.ci('screenshot',str(out/'failure.png'))
        except Exception as capture_error:result['capture_error']=str(capture_error)
        raise
    finally:
        if lab.logged_in:
            try:
                KernelLog(lab,msgbuf).halt()
                if result['status']=='prepared':
                    lab.wait(r'Option\?',60);lab.send('5');lab.wait(r'(?:^|\n)> ',30)
                    prom('setenv AutoLoad Yes');prom('setenv console g')
                    result['graphics_nvram_sha256']=sha256(out/'nvram.bin')
            except Exception as error:result['shutdown_error']=str(error)
        lab.close()
        result['clean_shutdown']=lab.clean_shutdown
        result['base_unchanged']=sha256(base/'netbsd-xiri.chd')==baseline['chd_sha256']
        result['donor_nvram_unchanged']=sha256(nvram)==result['nvram_source_sha256']
        if result['status']=='prepared' and not (result['clean_shutdown'] and result['base_unchanged']
                and result['donor_nvram_unchanged'] and result.get('graphics_nvram_sha256')
                and not result.get('shutdown_error')):
            result.update(status='failed',error='Shutdown or source preservation check failed')
        (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('Result:',result['status'],flush=True)


if __name__=='__main__':main()
