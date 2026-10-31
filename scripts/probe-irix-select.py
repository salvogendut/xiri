#!/usr/bin/env python3
"""Compare select with the IRIX oracle, then test Toolchest at normal priority."""
import argparse,gzip,importlib.util,json,re,shlex,shutil,struct,tempfile,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent

def module(name,filename):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/filename)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
probe=module('probe','probe-netbsd.py')
runtime=module('runtime','probe-irix-runtime.py')
tcp=module('tcp','probe-irix-tcp.py')
RESOURCES=['system.chestrc','app-defaults/Toolchest','locale/locale.alias','locale/locale.dir']

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['ci','ordinary'],default='ci')
    p.add_argument('--kernel-abi',choices=['lp64','o32'],default='lp64')
    p.add_argument('--seed-directory',type=Path,required=True)
    args=p.parse_args();seed=args.seed_directory.resolve()
    parent=json.loads((ROOT/'lab/irix-recvmsg/baseline.json').read_text())
    sr=json.loads((seed/'qualified-result.json').read_text())
    if not (sr['status']=='passed' and sr['clean_shutdown'] and sr['x11'] and sr['pin']==parent):p.error('need a clean qualified recvmsg LP64 X11 seed')
    pin=json.loads((ROOT/'lab/irix-select'/('o32-baseline.json' if args.kernel_abi=='o32' else 'baseline.json')).read_text())
    build=ROOT/('.work/netbsd-irix-select'+('-o32' if args.kernel_abi=='o32' else '')+'-build')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256'),(build/'kernel-media/netbsd','native_kernel_sha256')]:
        if probe.sha256(path)!=pin[key]:p.error('changed input: '+str(path))
    fixtures=ROOT/'.work/irix-select/probes';manifest=json.loads((fixtures/'manifest.json').read_text())
    oracle=json.loads((ROOT/'lab/irix-select/reference.json').read_text())
    if manifest['files']!=oracle['files']:p.error('reference uses different fixture bytes')
    for path,h in manifest['sources'].items():
        if probe.sha256(ROOT/path)!=h:p.error('stale fixture source: '+path)
    out=ROOT/'.work/irix-select/runs';out.mkdir(parents=True,exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix=args.kernel_abi+'-'+args.mode+'-',dir=out));print('Results: '+str(directory),flush=True)
    media=directory/'media';media.mkdir()
    sources=['lab/irix-lp64/runner.c','lab/irix-toolchest/session.c','lab/irix-select/peer.c']
    for name in sources:shutil.copyfile(ROOT/name,media/Path(name).name)
    shutil.copyfile(build/'kernel-media/netbsd',media/'netbsd')
    inventory=json.loads((ROOT/'lab/irix-desktop/manifest.json').read_text())
    for path in RESOURCES:
        full='/usr/lib/X11/'+path;info=inventory['resource_candidates'][full]
        src=ROOT/'.work/irix-desktop/root'/full.lstrip('/')
        if probe.sha256(src)!=info['sha256']:p.error('changed resource')
        shutil.copyfile(src,media/Path(path).name)
    cases=[c for c in manifest['cases'] if args.kernel_abi=='lp64' or c['abi']=='o32']
    for c in cases:
        n=c['name']
        if probe.sha256(fixtures/n)!=manifest['files'][n]['sha256']:p.error('changed fixture '+n)
        shutil.copyfile(fixtures/n,media/n)
    # Verify inherited controls/libraries before using the stopped disk.
    inherited={'/netbsd':parent['native_kernel_sha256'],'/root/irix-desktop/native-o32':pin['native_o32_sha256']}
    vendor=json.loads((ROOT/'lab/irix-reference/manifest.json').read_text())
    for c in vendor['candidates']:inherited['/root/irix-desktop/'+c['fixture_name']]=c['sha256']
    for path,info in inventory['files'].items():
        if path=='/usr/bin/X11/toolchest':inherited['/root/irix-desktop/vendor-toolchest']=info['sha256']
        elif not path.startswith('/usr/bin/'):inherited['/emul/irix'+path]=info['sha256']
    for r in pin['runtimes']:inherited['/emul/irix'+r['path']]=r['sha256']
    (media/'INHERITED').write_text(''.join(f'SHA256 ({n}) = {h}\n' for n,h in inherited.items()))
    lines=['#!/bin/sh','set -eu','cd /root/irix-desktop','ulimit -c 0',f'./select-peer {2*sum(c["symbols"]["SOCKET"] for c in cases)} >select-peer.out 2>select-peer.err & peer=$!','sleep 1','grep RDY select-peer.out']
    for uid in [0,1234]:
        for c in cases:
            n=c['name']+'-'+str(uid)
            lines += ['echo STARTCASE '+n,shlex.join(['./select-runner','./'+c['name'],*[str(uid)]*4]),'echo ENDCASE '+n]
    lines+=['wait "$peer"','echo PEER_OK']
    (media/'select-run.sh').write_text('\n'.join(lines)+'\n')
    (media/'SHA256').write_text(''.join(f'SHA256 ({x.name}) = {probe.sha256(x)}\n' for x in sorted(media.iterdir())))
    for n in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/n,directory/n],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',directory/'probe.iso',media])
    config=(ROOT/'lab/indy-netbsd/iris.toml').read_text();config=re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),config,flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode=args.mode,debugger=False,boot_timeout=600),directory,config_text=config)
    result={'status':'error','mode':args.mode,'kernel_abi':args.kernel_abi,'clean_shutdown':False,'pin':pin,'manifest':manifest,'reference_sha256':probe.sha256(ROOT/'lab/irix-select/reference.json'),'seed':str(seed.relative_to(ROOT)),'seed_result_sha256':probe.sha256(seed/'qualified-result.json'),'sources':{n:probe.sha256(ROOT/n) for n in sources+['scripts/probe-irix-select.py','scripts/probe-netbsd.py','scripts/probe-irix-runtime.py','scripts/probe-irix-tcp.py']},'observations':[],'toolchest':[],'started_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
    def command(cmd,timeout=90):
        before=len(lab.serial_text());rc=lab.command(cmd,timeout);s=lab.serial_text()[before:]
        if rc:raise RuntimeError('guest command failed: '+cmd)
        return s
    def download(command_text):
        # Compress raw text on the guest, then carry its hex over the existing console.
        s=command('echo HEX_START; '+command_text+' 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END',120)
        m=re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',s,re.M)
        if not m:raise RuntimeError('missing compressed serial payload')
        return gzip.decompress(bytes.fromhex(m[1]))
    normal=dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout='',stderr='')
    def controls(phase):
        for uid in [0,1234]:
            for exe,argv,expected in [('native-o32',[],dict(normal,exit=37,stdout='XIRI_ABI_PROBE\n')),('vendor-asa',[],dict(normal,stdout='XIRI_VENDOR_O32\n'))]+([('vendor-echo',['XIRI_VENDOR_N32'],dict(normal,stdout='XIRI_VENDOR_N32\n'))] if args.kernel_abi=='lp64' else []):
                actual=runtime.observation(command(shlex.join(['./select-runner','./session',*[str(uid)]*4,'--','home.env','./'+exe,*argv])))
                if actual!=expected:raise RuntimeError('control failed: '+exe)
                result.setdefault('controls',[]).append({'name':phase+'-'+exe+'-'+str(uid),'actual':actual})
    try:
        lab.start()
        command('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && '
                'cp netbsd /netbsd && cd /root/irix-desktop && cp /cdrom/*.c /cdrom/*direct-* . && chmod 755 *direct-* && '
                'ls -l input.txt && chmod 644 input.txt && '
                'cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=5000 -DRUNNER_TIMING runner.c -o select-runner && '
                'cc -O2 -Wall -Wextra -Werror session.c -o session && cc -O2 -Wall -Wextra -Werror peer.c -o select-peer && '
                'printf "HOME=/tmp/xiri-home\\n" >home.env && mkdir -p /tmp/xiri-home && chmod 777 /tmp/xiri-home && ulimit -c 0 && '
                'uname -v | grep '+shlex.quote(pin['ident']),240)
        controls('before')
        command('sh /cdrom/select-run.sh >select-fixtures.log 2>&1',600)
        data=download('cat select-fixtures.log');(directory/'fixtures.txt').write_bytes(data);text=data.decode()
        if '\nPEER_OK\n' not in text:raise RuntimeError('readiness peer failed')
        reference={o['name']:bytes.fromhex(o['stdout_hex']) for o in oracle['observations']}
        failures=[]
        for uid in [0,1234]:
            for c in cases:
                n=c['name']+'-'+str(uid);m=re.search(r'^STARTCASE '+n+r'\n(.*?)^ENDCASE '+n+r'$',text,re.M|re.S)
                if not m:raise RuntimeError('missing case '+n)
                actual=runtime.observation(m[1]);raw=re.search(r'^STDOUT bytes=512 hex=([0-9a-f]+)$',m[1],re.M)
                expected=bytearray(reference[c['name']])
                if 'POLICY' in c['symbols'] or c['name'].endswith('bad-bit31'):
                    struct.pack_into('>I',expected,8,22 if 'POLICY' in c['symbols'] else 9);struct.pack_into('>I',expected,16,1)
                elapsed=int(re.search(r'^ELAPSED_MS (\d+)$',m[1],re.M)[1])
                passed=raw is not None and bytes.fromhex(raw[1])==expected and actual==dict(normal,stdout=actual['stdout'])
                if c['symbols']['SOCKET'] and c['symbols']['MODE']!=2:passed=passed and elapsed>=150
                if c['name'].endswith(('timeout','socket-timeout')):passed=passed and elapsed>=90
                result['observations'].append({'name':n,'record_hex':raw[1] if raw else None,'actual':actual,'elapsed_ms':elapsed,'passed':passed})
                if not passed:failures.append(n)
        peer=download('cat select-peer.out');expected=b'RDY\n'+b''.join(struct.pack('>II',c['symbols']['CASE'],c['symbols']['MODE']) for uid in [0,1234] for c in cases if c['symbols']['SOCKET'])
        if peer!=expected:raise RuntimeError('readiness peer records differ')
        result['peer_stdout_hex']=peer.hex();result['failures']=failures
        print(str(len(result['observations']))+' select cases; differences: '+str(failures),flush=True)
        if args.kernel_abi=='lp64':
            command('test ! -e /emul/irix/usr/lib/X11/system.chestrc')
            command('export PATH=/usr/X11R7/bin:$PATH; '
                    '{ Xvfb :98 -screen 0 640x480x24 -ac -noreset >select-xvfb.log 2>&1 & xpid=$!; }; '
                    'sleep 2; xdpyinfo -display 127.0.0.1:98 >/dev/null')
            result['native_x11_before']=True
            for stage in ['library','resources']:
                if stage=='resources':
                    command('mkdir -p /emul/irix/usr/lib/X11/app-defaults /emul/irix/usr/lib/X11/locale && '+' && '.join(shlex.join(['cp','/cdrom/'+Path(x).name,'/emul/irix/usr/lib/X11/'+x])+' && '+shlex.join(['chmod','644','/emul/irix/usr/lib/X11/'+x]) for x in RESOURCES))
                for uid in [0,1234]:
                    for i in range(3):
                        cmd='ktrace -i -t un -f select-toolchest.ktrace '+shlex.join(['./select-runner','./session',*[str(uid)]*4,'--','home.env','./vendor-toolchest','-display','127.0.0.1:98'])
                        actual=runtime.observation(command(cmd));raw=download('kdump -x -f select-toolchest.ktrace').decode();name=stage+'-'+str(uid)+'-'+str(i)
                        (directory/(name+'.kdump')).write_text(raw)
                        calls=tcp.trace_records(raw,'irix_o32',True);returns=tcp.trace_records(raw,'irix_ret',True)
                        if not calls:raise RuntimeError('missing foreign trace')
                        expected=dict(normal,exit=1,stderr='./vendor-toolchest: Cannot open configuration file /usr/lib/X11/system.chestrc\n')
                        passed=actual==expected and all('a3=0' in x for x in returns if x.startswith('syscall=1100 '))
                        result['toolchest'].append({'name':name,'actual':actual,'calls':calls,'returns':returns,'passed':passed})
                        if not passed:failures.append('toolchest-'+name)
                        print(name+': '+json.dumps(actual),flush=True)
            command('xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"');result['native_x11_after']=True
        controls('after')
        result['status']='observed' if not failures else 'different'
    except Exception as e:
        result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='observed' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
