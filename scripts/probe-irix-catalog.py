#!/usr/bin/env python3
"""Observe catalog program startup in a disposable copy of the qualified CHD."""
import json,re,shlex,shutil,signal,sys,tempfile,time,threading
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'scripts'))
from xiri_lab import Guest,load_probe,sha256
from xiri_lab.kernel_log import KernelLog

def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--partition",type=int,choices=(0,1,2),required=True)
    parser.add_argument("--interactive",action="store_true")
    parser.add_argument("--limit",type=int)
    parser.add_argument("--after-case",help="Resume after this case in the partition's fixed order")
    parser.add_argument("--extra-file",type=Path,action="append",default=[],
        help="Add a diagnostic file to the read-only probe CD")
    parser.add_argument("--module-build",type=Path,
        help="Install a candidate module in the disposable disk and reboot before login")
    parser.add_argument("--seed",type=Path,
        help="Clone an earlier cleanly halted catalog guest, including its disk overlay")
    args=parser.parse_args()
    bundle=ROOT/'.work/images/xiri-netbsd-desktop-20261103-gimp'
    manifest = json.loads((bundle/'manifest.json').read_text())
    assert manifest['session_manager'] == 'xdm'
    assert sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
    assert sha256(bundle/'seed-result.json') == manifest['source_result_sha256']
    previous = json.loads((bundle/'seed-result.json').read_text())
    profile = bundle/manifest['qualification_nvram']
    assert sha256(profile) == manifest['qualification_nvram_sha256']
    p = load_probe()
    p.IRIS, p.CI = bundle/'emulator/iris', bundle/'emulator/iris-ci'
    assert sha256(p.IRIS) == previous['pin']['emulator_sha256']
    assert sha256(p.CI) == previous['pin']['ci_client_sha256']
    runs = ROOT/'.work/catalog-cycle'; runs.mkdir(exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='survey-'+str(args.partition)+'-', dir=runs))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    shutil.copyfile(__file__, d/'harness.py')
    media = d/'media'; media.mkdir()
    shutil.copyfile(ROOT/'lab/irix-4dwm/type-ready.c', media/'type.c')
    shutil.copyfile(ROOT/'lab/irix-filelocks/place-window.c', media/'place.c')
    shutil.copyfile(ROOT/'lab/irix-vendor-shell/catalog-input.c', media/'catalog-input.c')
    for name in ['app.sh','observe.sh','guard-control.c','windows.c','window-control.c','query-control.c']:
        shutil.copyfile(ROOT/'lab/irix-catalog'/name,media/name)
    guard=(ROOT/'runtime/libexec/session-guard.c').read_text()
    guard_source_sha256=sha256(ROOT/'runtime/libexec/session-guard.c')
    old='failed || requested || finished || now() >= deadline'
    assert guard.count(old)==1
    guard=guard.replace(old,'failed || requested || now() >= deadline')
    old='requested ? "signal" : finished ? "leader-exit" :'
    assert guard.count(old)==1
    guard=guard.replace(old,'requested ? "signal" :')
    (media/'app-guard.c').write_text(guard)
    inventory=json.loads((ROOT/'lab/irix-catalog/inventory.json').read_text())
    cases=[c for c in inventory['cases'] if c['partition']==args.partition]
    cases.sort(key=lambda c:(c['target']!='/usr/adobe/Acrobat4.0/bin/acroread',c['pages'][0],c['target']))
    if args.after_case:
        ids=[c['id'] for c in cases]
        if args.after_case not in ids:parser.error('--after-case is not in this partition')
        cases=cases[ids.index(args.after_case)+1:]
    if args.limit:cases=cases[:args.limit]
    (media/'inventory.json').write_text(json.dumps(inventory,indent=2)+'\n')
    for source in args.extra_file:
        destination=media/source.name
        if not source.is_file() or destination.exists():
            parser.error('extra file missing or collides with probe media: '+str(source))
        shutil.copyfile(source,destination)
    candidate=None
    if args.module_build:
        candidate=json.loads((args.module_build/'module.json').read_text())
        artifact=candidate['artifacts']['compat_irix_o32.kmod']
        source=args.module_build/artifact['path']
        assert sha256(source)==artifact['sha256']
        assert candidate['artifacts']['netbsd']['sha256']==manifest['pin']['native_kernel_sha256']
        assert candidate['artifacts']['netbsd.boot']['sha256']==manifest['pin']['boot_kernel_sha256']
        assert not (media/'compat_irix_o32.kmod').exists()
        shutil.copyfile(source,media/'compat_irix_o32.kmod')
    p.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',media])
    disk = d/'disk.chd'
    source_disk = bundle/'netbsd-xiri.chd'
    source_digest = sha256(source_disk)
    p.run(['cp','--reflink=auto','--sparse=always',source_disk,disk])
    shutil.copyfile(profile,d/'nvram.bin')
    if args.seed:
        seed=json.loads((args.seed/'result.json').read_text())
        assert seed['clean_shutdown'] and seed['source_unchanged']
        assert sha256(args.seed/'disk.chd')==source_digest
        p.run(['cp','--reflink=auto',args.seed/'disk.chd.diff.chd',d/'disk.chd.diff.chd'])
    config = (bundle/'iris.toml').read_text().replace('tftp_dir = "tftp"',
        'tftp_dir = '+json.dumps(str(d/'no-tftp')))
    assert 'tftp_dir = '+json.dumps(str(d/'no-tftp')) in config
    config += '\n[scsi.4]\npath = '+json.dumps(str(d/'probe.iso'))+'\ncdrom = true\n'
    lab = p.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600),d,config_text=config)
    launch = lab.launch
    def disk_launch(command,name):
        if name == 'emulator':
            command = list(command); command[command.index('--scsi1')+1] = str(disk)
        return launch(command,name)
    lab.launch = disk_launch
    guest=Guest(lab);cmd,get,wait=guest.command,guest.read_text,guest.wait_for
    record=dict(status='diagnostic',bundle=str(bundle),pin=manifest['pin'],module=manifest['irix_module'],harness_sha256=sha256(Path(__file__)),clean_shutdown=False)
    if args.seed:
        record['seed']=dict(path=str(args.seed),result_sha256=sha256(args.seed/'result.json'),
            overlay_sha256=sha256(args.seed/'disk.chd.diff.chd'))
    def interrupted(signum,frame):raise RuntimeError('Interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    try:
        lab.start(boot=False)
        lab.wait('login: ',600);lab.send('root');lab.wait('xiri-indy# ',30);lab.logged_in=True
        if candidate:
            installed=get('sha256 -q '+manifest['irix_module']['path']).strip()
            if installed!=candidate['artifacts']['compat_irix_o32.kmod']['sha256']:
                cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom')
                assert get('sha256 -q /cdrom/compat_irix_o32.kmod').strip()==candidate['artifacts']['compat_irix_o32.kmod']['sha256']
                cmd('install -m 444 /cdrom/compat_irix_o32.kmod '+manifest['irix_module']['path'])
                record['install_shutdown']=KernelLog(lab,int(manifest['kernel_msgbuf_symbol'],16)).halt()
                # The graphical PROM does not print its menu to the serial port.
                # Preserve the install boot's logs and cold-start the same private
                # disk/NVRAM with a new owned emulator process.
                lab.close()
                reboot=d/'boot-after-install';reboot.mkdir()
                shutil.copyfile(d/'nvram.bin',reboot/'nvram.bin')
                lab=p.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600),reboot,config_text=config)
                launch=lab.launch;lab.launch=disk_launch
                guest=Guest(lab);cmd,get,wait=guest.command,guest.read_text,guest.wait_for
                lab.start(boot=False)
                lab.wait('login: ',600);lab.send('root');lab.wait('xiri-indy# ',30)
                lab.logged_in=True;lab.clean_shutdown=False
            record['candidate_module']=candidate
        cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; ulimit -c 0')
        cmd('export DISPLAY=:0; XAUTHORITY=$(ps -axww -o args= | awk \'$1 == "/usr/X11R7/bin/Xorg" {for(i=1;i<NF;i++) if($i=="-auth") print $(i+1)}\'); export XAUTHORITY')
        wait('xwininfo -root -tree | grep \'"xlogin"\' >/dev/null',120)
        guest.monitor('disp compositor gl')
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom; mkdir -p /tmp/xiri-catalog; cd /tmp/xiri-catalog; cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/type.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o type; cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/place.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -o place; cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/catalog-input.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o catalog-input; cc -O2 -Wall -Wextra -Werror /cdrom/app-guard.c -o app-guard; cc -O2 -Wall -Wextra -Werror /cdrom/guard-control.c -o guard-control; cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/windows.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -o windows; cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/window-control.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -o window-control',180)
        cmd('install -m 555 /cdrom/app.sh /cdrom/observe.sh /tmp/xiri-catalog/')
        guest.monitor('key type xiritest');guest.monitor('key Return');guest.monitor('key type xiritest');guest.monitor('key Return')
        wait('grep -q "Logs: " /usr/people/xiritest/.xsession-errors',120)
        cmd('job=$(sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors | head -1); XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; export XAUTHORITY DISPLAY=127.0.0.1:0')
        wait('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready',180)
        expected_module=candidate['artifacts']['compat_irix_o32.kmod']['sha256'] if candidate else manifest['irix_module']['sha256']
        assert get('sha256 -q '+manifest['irix_module']['path']).strip()==expected_module
        cmd('mkdir -p /usr/people/xiritest/.xiri-catalog && chown xiritest:xiritest /usr/people/xiritest/.xiri-catalog; xset r off')
        cmd("su -l xiritest -c '/tmp/xiri-catalog/app-guard 10000 /tmp/xiri-catalog/guard-control' >guard-control.log; test \"$?\" = 37; grep -q CATALOG_NATIVE_CHILD_FINISHED guard-control.log; grep -q 'absent=1 valid=1' guard-control.log")
        cmd("su -l xiritest -c '/tmp/xiri-catalog/app-guard 1000 /tmp/xiri-catalog/guard-control linger' >guard-timeout.log; test \"$?\" = 0; grep -q 'absent=1 valid=1' guard-timeout.log; grep -q 'reason=timeout' guard-timeout.log")
        record['guard_controls']=get('cat guard-control.log guard-timeout.log')
        cmd('./window-control & control=$!; sleep 1; ./windows >windows-control.log; kill "$control"; wait "$control" || :')
        cmd('grep -q 5355525645595f56495349424c45 windows-control.log && ! grep -q 5355525645595f48494444454e windows-control.log')
        record['window_control']=get('cat windows-control.log')
        cmd('cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include /cdrom/query-control.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -o query-control')
        cmd('./query-control >query-control.log & control=$!; sleep 1; ./windows >query-blocked.log; rc=$?; printf "QUERY_STATUS=%s\\n" "$rc" >>query-control.log; wait "$control" && ./windows >query-recovered.log && test "$rc" = 142 && test -s query-recovered.log',50)
        record['query_timeout_control']=get('cat query-control.log')
        record['media_sources']={p.name:sha256(p) for p in media.iterdir() if p.is_file()}

        authority=get('printf %s \"$XAUTHORITY\"').strip()
        record['inventory_sha256']=sha256(ROOT/'lab/irix-catalog/inventory.json')
        record['partition']=args.partition
        record['after_case']=args.after_case
        record['cases']=[]
        record['probe_sources']={
            'lab/irix-catalog/app.sh':sha256(media/'app.sh'),
            'lab/irix-catalog/observe.sh':sha256(media/'observe.sh'),
            'runtime/libexec/session-guard.c':guard_source_sha256}
        record['app_guard_sha256']=sha256(media/'app-guard.c')
        record['manifest_sha256']=sha256(bundle/'manifest.json')
        record['resources']=manifest['gimp_resources']
        record['tree']=get('xwininfo -root -tree');record['initial']=get('cat "$job/identity" "$job/handoff";  modstat | grep irix')
        guest.monitor('screen shot '+str(d/'initial.png'))
        (d/'initial.json').write_text(json.dumps(record,indent=2)+'\n')
        print('Ready: '+str(d),flush=True);(d/'ready').touch()
        if not args.interactive:
            for case in cases:
                record['active_case']=case
                target=case['target'];name=case['id'];out='/usr/people/xiritest/.xiri-catalog/'+name
                checked=get('sha256 -q '+shlex.quote('/emul/irix'+target)).strip()
                assert checked==case['sha256'],target
                invocation='/usr/bin/env DISPLAY=127.0.0.1:0 XAUTHORITY='+shlex.quote(authority)+' /bin/sh /tmp/xiri-catalog/observe.sh '+shlex.join([name,target])
                done=threading.Event();captured={}
                def photograph():
                    if done.wait(12):return
                    try:
                        frame=d/(name+'.png');guest.capture(frame)
                        captured.update(path=frame.name,sha256=sha256(frame))
                    except Exception as error:captured['error']=str(error)
                photographer=threading.Thread(target=photograph,daemon=True);photographer.start()
                try:observation=cmd(shlex.join(['su','-l','xiritest','-c',invocation]),200)
                finally:done.set();photographer.join(45)
                assert not photographer.is_alive(),'screenshot worker did not stop'
                record['cases'].append(dict(case=case,observation=observation,screenshot=captured))
                detail=get('printf \"STDOUT\\n\"; head -c 4096 '+shlex.quote(out+'/stdout')+'; printf \"\\nSTDERR\\n\"; head -c 4096 '+shlex.quote(out+'/stderr'))
                record['cases'][-1]['output']=detail
                print('Observed '+name+' '+target+' '+detail[:240].replace('\n',' | '),flush=True)
                # Advance only when the tracker verified complete cleanup.
                cmd('/usr/local/libexec/xiri/x11-check ready')
                del record['active_case']
                (d/'progress.json').write_text(json.dumps(record,indent=2)+'\n')
            guest.read_text('find /usr/people/xiritest/.desktop* -type d 2>/dev/null > /usr/people/xiritest/.xiri-catalog/user-directories; true')
            data=guest.read('tar czf - -C /usr/people/xiritest .xiri-catalog',600)
            (d/'observations.tgz').write_bytes(data)
            record['observations_sha256']=sha256(d/'observations.tgz')
            record['status']='observed'
            return
        last=time.monotonic()
        while time.monotonic()-last<900:
            request=d/'request.json'
            if not request.exists():time.sleep(.2);continue
            item=json.loads(request.read_text());request.unlink();last=time.monotonic()
            if item['command']=='SHUTDOWN':break
            try:
                if item.get('save'):
                    Path(item['save']).write_bytes(guest.read(item['command'],item.get('timeout',120)));output='Saved '+item['save']
                else:
                    output=guest.monitor(item['command']) if item.get('monitor') else (get if item.get('read') else cmd)(item['command'],item.get('timeout',120))
                reply=dict(code=0,output=output)
            except Exception as error:reply=dict(error=str(error))
            (d/('response-'+item['id']+'.json')).write_text(json.dumps(reply))
    except Exception as error:
        record['error']=str(error);raise
    finally:
        if lab.logged_in and record.get('cases') and not record.get('observations_sha256'):
            try:
                (d/'observations.tgz').write_bytes(guest.read('tar czf - -C /usr/people/xiritest .xiri-catalog',600))
                record['observations_sha256']=sha256(d/'observations.tgz')
            except Exception as error:record['observation_transfer_error']=str(error)
        if lab.logged_in:
            try:record['shutdown_log']=KernelLog(lab,int(manifest['kernel_msgbuf_symbol'],16)).halt()
            except Exception as error:record['cleanup_error']=str(error)
        lab.close();record['clean_shutdown']=lab.clean_shutdown
        record['source_unchanged']=sha256(bundle/'netbsd-xiri.chd')==manifest['chd_sha256']
        (d/'result.json').write_text(json.dumps(record,indent=2)+'\n')
if __name__=='__main__':main()
