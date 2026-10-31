#!/usr/bin/env python3
"""Observe original xwsh after access support, with native font/ptrace controls."""
import argparse,gzip,importlib.util,json,re,shlex,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('resources',ROOT/'scripts/probe-irix-winterm-resources.py')
r=importlib.util.module_from_spec(s);s.loader.exec_module(r)
probe=r.probe

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed-directory',type=Path,required=True)
    p.add_argument('--lookups',action='store_true')
    p.add_argument('--mode',choices=['ci','ordinary'],default='ci')
    a=p.parse_args();seed=a.seed_directory.resolve();sr=json.loads((seed/'result.json').read_text())
    old=json.loads((ROOT/'lab/irix-siocnread/baseline.json').read_text())
    pin=json.loads((ROOT/'lab/irix-access/baseline.json').read_text())
    if not(sr['status']=='observed' and sr['clean_shutdown'] and sr['native_x11_after'] and sr['pin']==old and len(sr['cases'])==8):p.error('need a stopped font/locale winterm seed')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    build=ROOT/'.work/netbsd-irix-access-build'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256'),(build/'kernel-media/netbsd','native_kernel_sha256')]:
        if probe.sha256(path)!=pin[key]:p.error('changed pinned input')
    out=ROOT/'.work/irix-winterm-access/runs';out.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix=a.mode+'-',dir=out));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    m=d/'media';m.mkdir()
    sources=['lab/irix-winterm/trace.c','lab/irix-toolchest/fault.c','lab/irix-lp64/runner.c','lab/irix-toolchest/session.c','scripts/probe-irix-winterm-access.py']
    for src in sources[:4]:shutil.copyfile(ROOT/src,m/Path(src).name)
    inventory=json.loads((ROOT/'lab/irix-winterm/manifest.json').read_text())
    shutil.copyfile(build/'kernel-media/netbsd',m/'netbsd')
    inherited={'/netbsd':old['native_kernel_sha256'],'/root/irix-desktop/native-o32':pin['native_o32_sha256']}
    # Verify all original terminal inputs, not just the executable.
    for path,info in inventory['files'].items():inherited['/emul/irix'+path]=info['sha256']
    staged_fonts={}
    for path,info in sr['manifest']['files'].items():
        if '/fonts/' in path:
            src=ROOT/'.work/irix-x11-fonts/root'/path.lstrip('/')
            if probe.sha256(src)!=info['sha256']:p.error('changed font')
            shutil.copyfile(src,m/Path(path).name)
            staged_fonts['/tmp/irix-screen-fonts/'+Path(path).name]=info['sha256']
        else:inherited['/emul/irix'+path]=info['sha256']
    (m/'FONTS').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in staged_fonts.items()))
    (m/'INHERITED').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in inherited.items()))
    (m/'SHA256').write_text(''.join(f'SHA256 ({path.name}) = {probe.sha256(path)}\n' for path in sorted(m.iterdir())))
    for name in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',m])
    config=re.sub(r'^tftp_dir = .*$','tftp_dir = '+json.dumps(str(build/'tftp')),(ROOT/'lab/indy-netbsd/iris.toml').read_text(),flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode=a.mode,debugger=False,boot_timeout=600),d,config_text=config)
    result=dict(status='error',clean_shutdown=False,mode=a.mode,lookups=a.lookups,pin=pin,seed=str(seed.relative_to(ROOT)),seed_result_sha256=probe.sha256(seed/'result.json'),sources={x:probe.sha256(ROOT/x) for x in sources},controls=[],cases=[])
    def cmd(c,t=120):
        before=len(lab.serial_text())
        if lab.command(c,t):raise RuntimeError('guest command failed: '+c)
        return lab.serial_text()[before:]
    def get(c):
        x=cmd('echo HEX_START; '+c+' 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END')
        match=re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',x,re.M)
        if not match:raise RuntimeError('missing payload')
        return gzip.decompress(bytes.fromhex(match[1]))
    def controls(phase):
        for uid in [0,1234]:
            raw=cmd(f'./fault-tracer {uid} {uid} empty.env ./native-o32')
            if 'pc=0000000000400090' not in raw or 'END exit=37 signal=0' not in raw:raise RuntimeError('native entry control '+str(uid))
        fault=cmd('nm fault | fgrep xiri_fault_site; ./fault-tracer 0 0 empty.env ./fault')
        site=re.search(r'^([0-9a-f]+) T xiri_fault_site$',fault,re.M)
        pc=re.search(r'phase=fault signal=11 code=1 address=00000000 pc=([0-9a-f]+)',fault)
        if not site or not pc or int(site[1],16)!=int(pc[1],16) or 'END exit=-1 signal=9' not in fault:raise RuntimeError('native fault control')
        cmd('xterm -display 127.0.0.1:98 -name FaultControl -title FaultControl -fn '+shlex.quote(r.FONT)+' -fb '+shlex.quote(r.FONT)+' -e /bin/sh -c "sleep 30" >native-x.err 2>&1 & npid=$!; sleep 3; xwininfo -display 127.0.0.1:98 -name FaultControl >native-window; kill "$npid"; wait "$npid" || true')
        window=get('cat native-window').decode();stderr=get('cat native-x.err').decode()
        result.setdefault('native_font_controls',[]).append(dict(phase=phase,window=window,stderr=stderr))
        if 'Map State: IsViewable' not in window or stderr:raise RuntimeError('native font/window control')
        result['controls'].append(dict(phase=phase,entry_exit=37,fault_pc=hex(int(pc[1],16)),guards_intact=True,window=window,stderr=stderr))
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd && cd /root/irix-desktop && cp /cdrom/*.c . && cc -O2 -Wall -Wextra -Werror trace.c -o fault-tracer && cc -O0 -Wall -Wextra -Werror fault.c -o fault && cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=15000 runner.c -o access-runner && cc -O2 -Wall -Wextra -Werror session.c -o session && chmod 555 fault-tracer fault access-runner session && : >empty.env && install -d -m 755 /tmp/irix-screen-fonts && mkdir -p /tmp/xiri-home && chmod 777 /tmp/xiri-home && install -m 444 /cdrom/*.pcf* /tmp/irix-screen-fonts/ && /usr/X11R7/bin/mkfontdir /tmp/irix-screen-fonts && ulimit -c 0',240)
        cmd('export PATH=/usr/X11R7/bin:$PATH; Xvfb :98 -screen 0 640x480x24 -ac -noreset >fault-xvfb.log 2>&1 & xpid=$!; sleep 2; xdpyinfo -display 127.0.0.1:98 >/dev/null && xset -display 127.0.0.1:98 +fp /tmp/irix-screen-fonts && xset -display 127.0.0.1:98 fp rehash')
        cmd('sha256 -c /cdrom/FONTS && xlsfonts -display 127.0.0.1:98 -ll -fn '+shlex.quote(r.FONT)+' >native-font-info',120)
        result['native_font_info']=get('cat native-font-info').decode()
        cmd('uname -v | grep '+shlex.quote(pin['ident']))
        controls('before')
        for uid in [0,1234]:
            for font in [None,'fixed']:
                name=str(uid)+('-fixed' if font else '-default')
                args=['/emul/irix/usr/sbin/xwsh','-name','winterm','-display','127.0.0.1:98']+(['-fn',font] if font else [])
                argv=['./access-runner','./session',*[str(uid)]*4,'--','winterm.env',*args]
                cmd('ktrace -i -t un -f winterm.ktrace '+shlex.join(argv)+' >winterm.log 2>&1 & wpid=$!; sleep 3; xwininfo -display 127.0.0.1:98 -root -tree >winterm.tree; xwd -display 127.0.0.1:98 -root -silent >winterm.xwd; wait "$wpid"',90)
                parent=get('cat winterm.log').decode();(d/(name+'.parent')).write_text(parent)
                actual=r.runtime.observation(parent)
                raw=get('kdump -x -f winterm.ktrace').decode();(d/(name+'.kdump')).write_text(raw)
                obs=dict(name=name,uid=uid,font=font,actual=actual,tree=get('cat winterm.tree').decode())
                frame=d/(name+'.xwd');frame.write_bytes(get('cat winterm.xwd'));obs['frame_sha256']=probe.sha256(frame)
                if actual['signal']==11:
                    argv=['./fault-tracer']+(['--lookups'] if a.lookups else [])+[str(uid),str(uid),'winterm.env',*args]
                    cmd(shlex.join(argv)+' >fault.log 2>&1; trc=$?; if test "$trc" -ne 0; then cat fault.log; fi; test "$trc" -eq 0',120)
                    trace=get('cat fault.log').decode();(d/(name+'.trace')).write_text(trace)
                    stop=re.search(r'STOP phase=fault signal=(\d+) code=(\d+) address=([0-9a-f]+) pc=([0-9a-f]+)',trace)
                    if not stop or 'END exit=-1 signal=9' not in trace:raise RuntimeError('missing captured fault '+name)
                    obs['fault']=dict(signal=int(stop[1]),code=int(stop[2]),address=hex(int(stop[3],16)),pc=hex(int(stop[4],16)),stderr=get('cat trace-child.err').decode())
                result['cases'].append(obs);print(json.dumps(obs),flush=True)
        controls('after');cmd('xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"');result['native_x11_after']=True;result['status']='observed'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='observed' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
