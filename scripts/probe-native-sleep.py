#!/usr/bin/env python3
"""Observe native sleeps with/without memory pressure beside xdm and 4Dwm."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import signal
import re
import socket
import subprocess
import threading
import time
import tempfile
from types import SimpleNamespace

from xiri_lab import Guest, ROOT, load_probe, sha256
from xiri_lab.kernel_log import KernelLog
from xiri_lab.transfer import archive


def sleep_case_passed(case, iterations):
    # PAM su can mask a signalled child's status. Require the probe's own
    # completion record as well as the launcher's zero exit status.
    pattern=(r'SLEEP_RESULT method='+re.escape(case['method'])+
             r' iterations='+str(iterations)+
             r' child=[1-9][0-9]* rc=0 observer_failed=0 '
             r'minor_faults=[0-9]+ major_faults=[0-9]+ '
             r'voluntary=[0-9]+ involuntary=[0-9]+')
    return case['status']=='0' and re.fullmatch(pattern, case['summary']) is not None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle',required=True,type=Path)
    parser.add_argument('--kernel-build',type=Path)
    parser.add_argument('--seed',type=Path,help='reuse a halted matching-kernel diagnostic overlay')
    parser.add_argument('--check-swap-control',action='store_true')
    parser.add_argument('--swap-control-only',action='store_true')
    parser.add_argument('--swap-readback-only',action='store_true')
    parser.add_argument('--verify-memory',action='store_true',
                        help='Force and verify anonymous swap-in after the timing matrix')
    parser.add_argument('--iterations',type=int,default=100,choices=range(1,1001))
    parser.add_argument('--pressure-mib',type=int,default=96,choices=range(1,193))
    parser.add_argument('--methods',nargs='+',choices=['usleep','nanosleep','select'],
                        default=['usleep','nanosleep','select'])
    parser.add_argument('--sample-kernel',action='store_true',
                        help='Diagnostic only: pause briefly once a second to capture CPU state')
    parser.add_argument('--plaintext-swap',action='store_true',
                        help='Diagnostic only: disable swap encryption in this disposable clone')
    args=parser.parse_args()
    if args.seed and not args.kernel_build: parser.error('--seed requires --kernel-build')
    if args.swap_control_only and args.swap_readback_only: parser.error('select only one control-only mode')
    if args.plaintext_swap and (args.verify_memory or args.swap_readback_only):
        parser.error('the swap readback control requires encryption enabled')
    bundle=args.bundle.resolve()
    manifest=json.loads((bundle/'manifest.json').read_text())
    assert manifest['session_manager']=='xdm'
    for name,key in [('netbsd-xiri.chd','chd_sha256'),('iris.toml','config_sha256'),
                     ('seed-result.json','source_result_sha256')]:
        assert sha256(bundle/name)==manifest[key]
    p=load_probe(); p.IRIS=bundle/'emulator/iris'; p.CI=bundle/'emulator/iris-ci'
    for path,key in [(p.IRIS,'emulator_sha256'),(p.CI,'ci_client_sha256')]:
        assert sha256(path)==manifest['pin'][key]
    runs=ROOT/'.work/native-sleep'; runs.mkdir(exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix='native-',dir=runs))
    print('Results: '+str(d.relative_to(ROOT)),flush=True)
    shutil.copyfile(__file__,d/'harness.py')
    support=d/'support';support.mkdir()
    for name in ['__init__.py','guest.py','kernel_log.py','transfer.py']:
        shutil.copyfile(ROOT/'scripts/xiri_lab'/name,support/name)
    media=d/'media';media.mkdir()
    sources=['lab/system-stability/sleep-probe.c','lab/system-stability/memory.c',
             'lab/system-stability/swap-control.c','lab/system-stability/swap-readback.c']
    for source in sources: shutil.copyfile(ROOT/source,media/Path(source).name)
    candidate=None
    if args.kernel_build:
        build=args.kernel_build.resolve()
        candidate=json.loads((build/'module.json').read_text())
        kernel_media=media/'kernel';kernel_media.mkdir()
        for name,artifact in candidate['artifacts'].items():
            source=build/artifact['path']
            assert sha256(source)==artifact['sha256']
            shutil.copyfile(source,kernel_media/name)
        symbols=subprocess.check_output(['nm',str(kernel_media/'netbsd')],text=True)
        candidate['msgbuf_symbol']='0x'+re.search(r'^([0-9a-f]+) B msgbufp$',symbols,re.M)[1]
        candidate['build_manifest_sha256']=sha256(build/'module.json')
        shutil.copyfile(build/'source.patch',d/'kernel-source.patch')
    p.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',media])
    p.run(['cp','--reflink=auto',bundle/'netbsd-xiri.chd',d/'disk.chd'])
    seed_record=None
    if args.seed:
        previous=json.loads((args.seed/'result.json').read_text())
        assert previous['clean_shutdown'] and previous['source_unchanged']
        assert sha256(args.seed/'disk.chd')==manifest['chd_sha256']
        assert previous['candidate_kernel']['artifacts']==candidate['artifacts']
        overlay=args.seed/'disk.chd.diff.chd'
        seed_record=dict(path=str(args.seed),result_sha256=sha256(args.seed/'result.json'),overlay_sha256=sha256(overlay))
        p.run(['cp','--reflink=auto',overlay,d/'disk.chd.diff.chd'])
    profile=bundle/manifest['qualification_nvram']
    assert sha256(profile)==manifest['qualification_nvram_sha256']
    shutil.copyfile(profile,d/'nvram.bin')
    config=(bundle/'iris.toml').read_text().replace('tftp_dir = "tftp"',
        'tftp_dir = '+json.dumps(str(d/'no-tftp')))
    config+='\n[scsi.4]\npath = '+json.dumps(str(d/'probe.iso'))+'\ncdrom = true\n'
    def new_lab(directory):
        instance=p.Lab(SimpleNamespace(mode='ordinary',debugger=False,boot_timeout=600),directory,config_text=config)
        launch=instance.launch
        def disk_launch(command,name):
            if name=='emulator':
                command=list(command);command[command.index('--scsi1')+1]=str(d/'disk.chd')
            return launch(command,name)
        instance.launch=disk_launch
        return instance
    lab=new_lab(d)
    guest=Guest(lab);cmd,get,wait=guest.command,guest.read_text,guest.wait_for
    ring=KernelLog(lab,int(candidate['msgbuf_symbol'] if args.seed else manifest['kernel_msgbuf_symbol'],16))
    r=dict(schema=1,status='error',scope='native-sleep-diagnostic',bundle=str(bundle.relative_to(ROOT)),
        chd_sha256=manifest['chd_sha256'],manifest_sha256=sha256(bundle/'manifest.json'),
        pin=manifest['pin'],module=manifest['irix_module'],harness_sha256=sha256(d/'harness.py'),
        support_sources={path.name:sha256(path) for path in sorted(support.iterdir())},
        sources={source:sha256(ROOT/source) for source in sources},
        iterations=args.iterations,pressure_mib=args.pressure_mib,methods=args.methods,
        sampled=args.sample_kernel,plaintext_swap=args.plaintext_swap,
        check_swap_control=args.check_swap_control,swap_control_only=args.swap_control_only,
        swap_readback_only=args.swap_readback_only,
        verify_memory=args.verify_memory,cases=[],clean_shutdown=False)
    if candidate:r['candidate_kernel']=candidate
    if seed_record:r['seed']=seed_record
    def interrupted(sig,frame):
        raise RuntimeError('Interrupted by signal '+str(sig))
    signal.signal(signal.SIGINT,interrupted);signal.signal(signal.SIGTERM,interrupted)
    base='/tmp/xiri-sleep'
    def swap_readback():
        # Additional swap is confined to this disposable disk. Grow the
        # working set until mincore proves primary pages were actually evicted.
        swap=base+'/readback.swap'
        cmd('dd if=/dev/zero of='+swap+' bs=1m count=128 2>'+base+'/swap-file.log && '
            'chmod 600 '+swap+' && swapctl -a '+swap,180)
        r['readback_swap_config']=get('sysctl vm.swap_encrypt; swapctl -l')
        assert 'vm.swap_encrypt = 1' in r['readback_swap_config'], 'readback requires encrypted swap'
        # Keep a shell wait around the control: this guest's PAM su returns
        # WEXITSTATUS even for a signalled child, which can hide its failure.
        call='ktrace -i -t csw -f '+base+'/out/swap-readback.ktrace '+base+'/swap-readback'
        call+='; rc=$?; echo "$rc" >'+base+'/out/swap-readback.status; exit "$rc"'
        cmd('su -l xiritest -c '+shlex.quote(call)+
            ' >'+base+'/out/swap-readback.log 2>&1; rc=$?; echo "$rc" >'+base+'/out/swap-readback.launcher-status',1000)
        r['swap_readback']=get('cat '+base+'/out/swap-readback.log')
        r['swap_readback_status']=get('cat '+base+'/out/swap-readback.status').strip()
        r['swap_readback_launcher_status']=get('cat '+base+'/out/swap-readback.launcher-status').strip()
        print(r['swap_readback'],flush=True)
        assert r['swap_readback_status']==r['swap_readback_launcher_status']=='0' and 'valid=1' in r['swap_readback'], 'swap readback control failed'
        cmd('swapctl -d '+swap+' && rm -f '+swap,180)
    def checks(label):
        cmd('vmstat -s >'+base+'/'+label+'-vmstat.txt')
        for method in args.methods:
            name=label+'-'+method
            call='cd '+base+'/out; ktrace -i -t csw -f '+name+'.ktrace ../sleep-probe '+method+' '+str(args.iterations)
            cmd('su -l xiritest -c '+shlex.quote(call)+' >'+base+'/out/'+name+'.log 2>&1; '
                'rc=$?; echo "$rc" >'+base+'/out/'+name+'.status',300)
            status=get('cat '+base+'/out/'+name+'.status').strip()
            summary=get('tail -1 '+base+'/out/'+name+'.log').strip()
            r['cases'].append(dict(label=label,method=method,status=status,summary=summary))
            print(name+': '+summary,flush=True)
    sampling_done=threading.Event()
    sampler=None
    def sample_kernel():
        command=json.loads((lab.directory/'emulator-command.json').read_text())
        port=int(command[command.index('--monitor-port')+1])
        try:
            with socket.create_connection(('127.0.0.1',port),10) as connection, \
                    (d/'kernel-samples.jsonl').open('w') as output:
                connection.settimeout(20)
                def reply():
                    data=b''
                    while not data.endswith(b'> '):
                        chunk=connection.recv(65536)
                        if not chunk: raise RuntimeError('sampling monitor disconnected')
                        data+=chunk
                    return data.decode('latin1')
                def monitor(text):
                    connection.sendall((text+'\n').encode());return reply()
                reply()
                while not sampling_done.wait(1):
                    began=time.monotonic()
                    monitor('stop')
                    try:
                        registers=monitor('regs')
                        sp=re.search(r'sp\s+\(\$29\): (0x[0-9a-f]+)',registers)
                        stack=monitor('mem '+sp[1]+' 64 d') if sp else ''
                        item=dict(host_monotonic=began,registers=registers,stack=stack)
                    finally:
                        monitor('start')
                    item['pause_seconds']=time.monotonic()-began
                    output.write(json.dumps(item)+'\n');output.flush()
        except Exception as error:
            r['sampling_error']=str(error)
    try:
        lab.start(boot=False);lab.wait('login: ',600);lab.send('root');lab.wait('xiri-indy# ',30);lab.logged_in=True
        expected_kernel=manifest['pin']['native_kernel_sha256']
        expected_boot=manifest['pin']['boot_kernel_sha256']
        expected_module=manifest['irix_module']['sha256']
        if candidate and not args.seed:
            cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom')
            for name,destination in [('netbsd','/netbsd'),('netbsd.boot','/netbsd.boot'),
                                     ('compat_irix_o32.kmod',manifest['irix_module']['path'])]:
                digest=candidate['artifacts'][name]['sha256']
                cmd('test "$(sha256 -q /cdrom/kernel/'+name+')" = '+digest+
                    ' && install -m 444 /cdrom/kernel/'+name+' '+shlex.quote(destination))
            r['preparation_halt']=ring.halt();lab.close()
            reboot=d/'reboot';reboot.mkdir();shutil.copyfile(profile,reboot/'nvram.bin')
            lab=new_lab(reboot);guest=Guest(lab)
            cmd,get,wait=guest.command,guest.read_text,guest.wait_for
            ring=KernelLog(lab,int(candidate['msgbuf_symbol'],16))
            lab.start(boot=False);lab.wait('login: ',600);lab.send('root');lab.wait('xiri-indy# ',30);lab.logged_in=True
        if candidate:
            expected_kernel=candidate['artifacts']['netbsd']['sha256']
            expected_boot=candidate['artifacts']['netbsd.boot']['sha256']
            expected_module=candidate['artifacts']['compat_irix_o32.kmod']['sha256']
        cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; ulimit -c 0; '
            'mount -t cd9660 -o ro /dev/cd0a /cdrom; rm -rf '+base+'; mkdir -p '+base+'/out; cd '+base+'; '
            'cp /cdrom/*.c .; chown xiritest:xiritest out; '
            'cc -O2 -Wall -Wextra -Werror sleep-probe.c -o sleep-probe && '
            'cc -O2 -Wall -Wextra -Werror memory.c -o memory && '
            'cc -O2 -Wall -Wextra -Werror swap-control.c -o swap-control && '
            'cc -O2 -Wall -Wextra -Werror swap-readback.c -o swap-readback',180)
        r['guest_hashes']=get('sha256 /netbsd /netbsd.boot '+manifest['irix_module']['path']+
            ' /lib/libc.so.12 /usr/local/libexec/xiri/session-guard sleep-probe memory')
        for value in [expected_kernel,expected_boot,expected_module]: assert value in r['guest_hashes']
        r['installed_artifacts']=dict(native_kernel_sha256=expected_kernel,
            boot_kernel_sha256=expected_boot,module_sha256=expected_module)
        r['clock_config']=get('sysctl kern.clockrate kern.timecounter; vmstat -s')
        r['swap_before']=get('sysctl vm.swap_encrypt; swapctl -l')
        if args.check_swap_control or args.swap_control_only or args.plaintext_swap:
            cmd('swapctl -U && ./swap-control >out/swap-control.log 2>&1; '
                'rc=$?; echo "$rc" >out/swap-control.status; swapctl -A',120)
            r['swap_control']=get('cat out/swap-control.log')
            r['swap_control_status']=get('cat out/swap-control.status').strip()
            print(r['swap_control'],flush=True)
        if args.swap_control_only:
            r['status']='passed' if r['swap_control_status']=='0' else 'observed-failure'
        elif args.swap_readback_only:
            swap_readback()
            r['status']='passed'
        else:
            if args.check_swap_control or args.plaintext_swap:
                assert r['swap_control_status']=='0', 'swap control regression failed'
            if args.plaintext_swap:
                cmd('swapctl -U && sysctl -w vm.swap_encrypt=0 && swapctl -A',120)
            r['swap_test_config']=get('sysctl vm.swap_encrypt; swapctl -l')
            assert ('vm.swap_encrypt = '+('0' if args.plaintext_swap else '1')) in r['swap_test_config']
            cmd("su -l xiritest -c '"+base+"/sleep-probe exit-control 1' >out/exit-control.log 2>&1")
            r['exit_control']=get('cat out/exit-control.log')
            assert 'reaped=1 valid=1' in r['exit_control']
            checks('greeter-unloaded')
            cmd('su -l xiritest -c '+shlex.quote(base+'/memory '+str(args.pressure_mib))+' >memory.log 2>&1 & held=$!')
            wait('grep -q MEMORY_READY memory.log',180)
            r['memory_ready']=get('cat memory.log')
            checks('greeter-pressure')
            cmd('rm -f /usr/people/xiritest/.xsession-errors')
            for text in ['xiritest','xiritest']:
                guest.monitor('key type '+text);guest.monitor('key Return')
            wait('grep -q "Logs: " /usr/people/xiritest/.xsession-errors',120)
            cmd('job=$(sed -n "s/.*Logs: //p" /usr/people/xiritest/.xsession-errors | head -1); '
                'test -d "$job"')
            cmd('XAUTHORITY=$(sed -n "s/.* authority=//p" "$job/identity"); '
                'test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; '
                'export XAUTHORITY DISPLAY=127.0.0.1:0; test -r "$XAUTHORITY"')
            wait('test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready',180)
            if args.sample_kernel:
                sampler=threading.Thread(target=sample_kernel);sampler.start()
            checks('irix-pressure')
            sampling_done.set()
            if sampler: sampler.join(30)
            if args.verify_memory:
                pid=re.search(r'MEMORY_READY pid=(\d+)',r['memory_ready'])[1]
                cmd('kill -TERM '+pid+'; wait "$held"')
                swap_readback()
            cmd('ps -axlww >processes.txt; vmstat -s >vmstat-final.txt')
            r['status']='passed' if all(sleep_case_passed(c,args.iterations) for c in r['cases']) else 'observed-failure'
    except Exception as error:
        r['error']=str(error);print('Failed: '+str(error),flush=True)
        try:
            failure=ring.read()
            (d/'failure-kernel.log').write_text(failure)
            r['kernel_fault']=bool(re.search(r'trap:.*in kernel mode|panic:',failure))
            (d/'failure-registers.txt').write_text(guest.monitor('regs'))
            guest.monitor('screen shot '+str(d/'failure.png'))
        except Exception as capture_error:
            r['failure_capture_error']=str(capture_error)
    finally:
        sampling_done.set()
        if sampler: sampler.join(30)
        if lab.logged_in and not r.get('kernel_fault'):
            try:
                r['archive_sha256']=archive(guest,'tar czf - --exclude readback.swap -C /tmp xiri-sleep',d/'observations.tgz')
            except Exception as error:r['archive_error']=str(error)
            try:r['halt']=ring.halt()
            except Exception as error:r['halt_error']=str(error)
        elif r.get('kernel_fault'):
            # A trapped kernel cannot run shell collection or clean shutdown.
            # Preserve the disposable disk and stop only this owned emulator.
            lab.logged_in=False
        lab.close();r['clean_shutdown']=lab.clean_shutdown
        r['source_unchanged']=sha256(bundle/'netbsd-xiri.chd')==manifest['chd_sha256']
        if seed_record:
            r['seed_unchanged']=sha256(args.seed/'disk.chd.diff.chd')==seed_record['overlay_sha256']
        if (not r['clean_shutdown'] or not r['source_unchanged'] or
                r.get('seed_unchanged') is False or
                r.get('archive_error') or r.get('sampling_error')):
            r['status']='error'
        (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    print('Result: '+r['status']+'; clean shutdown='+str(r['clean_shutdown']),flush=True)
    return 0 if r['status']=='passed' else 1

if __name__=='__main__':
    raise SystemExit(main())
