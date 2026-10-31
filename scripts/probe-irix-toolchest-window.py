#!/usr/bin/env python3
"""Inspect sustained Toolchest visibility and Expose handling on the pinned kernel."""
import argparse,gzip,hashlib,importlib.util,json,re,shlex,shutil,tempfile,time
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent

def module(name,filename):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/filename)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
probe=module('probe','probe-netbsd.py');runtime=module('runtime','probe-irix-runtime.py');tcp=module('tcp','probe-irix-tcp.py')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seed-directory',type=Path,required=True);args=p.parse_args()
    seed=args.seed_directory.resolve();sr=json.loads((seed/'result.json').read_text())
    pin=json.loads((ROOT/'lab/irix-siocnread/baseline.json').read_text())
    if not(sr['status']=='observed' and sr['clean_shutdown'] and sr['pin']==pin and sr['native_x11_after'] and not sr['failures']):p.error('need a clean passing LP64 SIOCNREAD run with resources')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    build=ROOT/'.work/netbsd-irix-siocnread-build'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256')]:
        if probe.sha256(path)!=pin[key]:p.error('changed pinned input')
    out=ROOT/'.work/irix-siocnread/window-runs';out.mkdir(parents=True,exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix='ci-',dir=out));print('Results: '+str(directory.relative_to(ROOT)),flush=True)
    media=directory/'media';media.mkdir()
    xcomp=ROOT/'.work/netbsd-11.0/sgimips/binary/sets/xcomp.tgz'
    expected=re.search(r'^([0-9a-f]{128})  sgimips/binary/sets/xcomp.tgz$',(ROOT/'lab/netbsd-11.0/SHA512SUMS').read_text(),re.M)[1]
    if hashlib.sha512(xcomp.read_bytes()).hexdigest()!=expected:p.error('changed X development set')
    shutil.copyfile(xcomp,media/'xcomp.tgz')
    sources=['lab/irix-siocnread/windowcheck.c','lab/irix-lp64/runner.c']
    for path in sources:shutil.copyfile(ROOT/path,media/Path(path).name)
    inherited={'/netbsd':pin['native_kernel_sha256'],'/root/irix-desktop/native-o32':pin['native_o32_sha256'],'/root/irix-desktop/session.c':probe.sha256(ROOT/'lab/irix-toolchest/session.c')}
    inventory=json.loads((ROOT/'lab/irix-desktop/manifest.json').read_text())
    for path,info in inventory['files'].items():
        if path=='/usr/bin/X11/toolchest':inherited['/root/irix-desktop/vendor-toolchest']=info['sha256']
        elif not path.startswith('/usr/bin/'):inherited['/emul/irix'+path]=info['sha256']
    for path in ['/usr/lib/X11/system.chestrc','/usr/lib/X11/app-defaults/Toolchest','/usr/lib/X11/locale/locale.alias','/usr/lib/X11/locale/locale.dir']:
        inherited['/emul/irix'+path]=inventory['resource_candidates'][path]['sha256']
    for item in pin['runtimes']:inherited['/emul/irix'+item['path']]=item['sha256']
    for c in json.loads((ROOT/'lab/irix-reference/manifest.json').read_text())['candidates']:inherited['/root/irix-desktop/'+c['fixture_name']]=c['sha256']
    (media/'INHERITED').write_text(''.join(f'SHA256 ({path}) = {sha}\n' for path,sha in inherited.items()))
    (media/'SHA256').write_text(''.join(f'SHA256 ({x.name}) = {probe.sha256(x)}\n' for x in sorted(media.iterdir())))
    for name in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/name,directory/name],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',directory/'probe.iso',media])
    config=(ROOT/'lab/indy-netbsd/iris.toml').read_text();config=re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),config,flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode='ci',debugger=False,boot_timeout=600),directory,config_text=config)
    result=dict(status='error',clean_shutdown=False,xcomp_sha512=expected,pin=pin,seed=str(seed.relative_to(ROOT)),seed_result_sha256=probe.sha256(seed/'result.json'),sources={n:probe.sha256(ROOT/n) for n in sources+['scripts/probe-irix-toolchest-window.py','scripts/probe-netbsd.py','scripts/probe-irix-runtime.py','scripts/probe-irix-tcp.py','lab/irix-toolchest/session.c']},controls=[],toolchest=[],started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()))
    def command(cmd,timeout=120):
        before=len(lab.serial_text());rc=lab.command(cmd,timeout)
        if rc:raise RuntimeError('guest command failed: '+cmd)
        return lab.serial_text()[before:]
    def download(cmd):
        text=command('echo HEX_START; '+cmd+' 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END')
        m=re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',text,re.M)
        if not m:raise RuntimeError('missing compressed payload')
        return gzip.decompress(bytes.fromhex(m[1]))
    def frame(name):
        command('xwd -display 127.0.0.1:98 -root -silent >window.xwd')
        path=directory/(name+'.xwd');path.write_bytes(download('cat window.xwd'));return probe.sha256(path)
    def native(phase):
        command('./windowcheck control >native-control.log 2>&1 & npid=$!; sleep 2; ./windowcheck redraw >native-redraw.log; kill "$npid"; wait "$npid" 2>/dev/null || true')
        log=download('cat native-redraw.log').decode();m=re.search(r'REDRAW visible=(\d+) before=(\w+) cleared=(\w+) after=(\w+)',log)
        if not m or int(m[1])<1 or m[2]!=m[4] or m[2]==m[3]:raise RuntimeError('native Expose control failed')
        result['controls'].append(dict(phase=phase,log=log))
    try:
        lab.start()
        command('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && tar xzpf /cdrom/xcomp.tgz -C / && cd /root/irix-desktop && cp /cdrom/*.c . && '
                'cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=60000 -DRUNNER_TIMING runner.c -o window-runner && '
                'cc -O2 -Wall -Wextra -Werror session.c -o session && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib windowcheck.c -lX11 -o windowcheck && '
                'export PATH=/usr/X11R7/bin:$PATH && { Xvfb :98 -screen 0 640x480x24 -ac -noreset >window-xvfb.log 2>&1 & xpid=$!; } && sleep 2 && xdpyinfo -display 127.0.0.1:98 >/dev/null',240)
        native('before');result['empty_frame']=frame('empty')
        for uid in [0,1234]:
            name='toolchest-'+str(uid)
            cmd='ktrace -i -t un -f window.ktrace '+shlex.join(['./window-runner','./session',*[str(uid)]*4,'--','home.env','./vendor-toolchest','-display','127.0.0.1:98'])
            command(cmd+' >window-parent.log 2>&1 & tpid=$!; sleep 8; ./windowcheck >window-tree.log; ./windowcheck redraw >window-redraw.log',120)
            tree=download('cat window-tree.log').decode();redraw=download('cat window-redraw.log').decode();sha=frame(name)
            command('wait "$tpid"',90)
            actual=runtime.observation(download('cat window-parent.log').decode());raw=download('kdump -x -f window.ktrace').decode();(directory/(name+'.kdump')).write_text(raw)
            result['toolchest'].append(dict(uid=uid,actual=actual,window_tree=tree,redraw=redraw,frame_sha256=sha,calls=tcp.trace_records(raw,'irix_o32',True),returns=tcp.trace_records(raw,'irix_ret',True)))
            print(name+': '+json.dumps(dict(actual=actual,tree=tree,redraw=redraw)),flush=True)
        native('after');command('xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"');result['native_x11_after']=True
        result['status']='observed'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='observed' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
