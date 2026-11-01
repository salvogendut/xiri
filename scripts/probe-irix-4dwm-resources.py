#!/usr/bin/env python3
"""Verify original 4Dwm with explicitly readable original resource files."""
import argparse,gzip,importlib.util,json,re,shlex,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('shell',ROOT/'scripts/probe-irix-shell.py');shell=importlib.util.module_from_spec(s);s.loader.exec_module(shell)
probe=shell.probe

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=['ci','ordinary'],default='ci')
    a=p.parse_args();a.stage='resources'
    seed=ROOT/'.work/irix-4dwm/runs/local-ci-_i17e84p';sr=json.loads((seed/'result.json').read_text())
    old=json.loads((ROOT/'lab/irix-mmap-local/baseline.json').read_text())
    assert sr['status']=='observed' and sr['clean_shutdown'] and sr['pin']==old
    checkpoint='irix-prda'
    pin=json.loads((ROOT/'lab'/checkpoint/'baseline.json').read_text());build=ROOT/('.work/netbsd-'+checkpoint+'-build')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256'),(build/'kernel-media/netbsd','native_kernel_sha256')]:assert probe.sha256(path)==pin[key]
    root=ROOT/'.work/irix-4dwm/runs';root.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix=a.stage+'-'+a.mode+'-',dir=root));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    m=d/'media';m.mkdir();manifest=json.loads((ROOT/'lab/irix-desktop/manifest.json').read_text())
    staged=sr['staged']
    fonts=json.loads((ROOT/'lab/irix-x11-fonts/manifest.json').read_text())
    for path,info in fonts['files'].items():
        if '/fonts/' not in path:continue
        source=ROOT/'.work/irix-x11-fonts/root'/path.lstrip('/');assert probe.sha256(source)==info['sha256']
        shutil.copyfile(source,m/Path(path).name)
    sources=['scripts/probe-irix-4dwm-resources.py','lab/irix-shell/guard.c','lab/irix-toolchest/session.c','lab/irix-lp64/runner.c','lab/irix-4dwm/wmcheck.c']
    for src in sources[1:]:shutil.copyfile(ROOT/src,m/Path(src).name)
    shutil.copyfile(build/'kernel-media/netbsd',m/'netbsd')
    env=['HOME=/tmp/xiri-home','USER=xiritest','LOGNAME=xiritest','SHELL=/bin/sh','DISPLAY=127.0.0.1:98','LANG=C','LC_ALL=C','PATH=/bin:/usr/bin:/usr/X11R7/bin:/emul/irix/usr/bin:/emul/irix/usr/bin/X11']
    (m/'wm.env').write_text('\n'.join(env)+'\n')
    (m/'INHERITED').write_text('SHA256 (/netbsd) = '+old['native_kernel_sha256']+'\nSHA256 (/root/irix-desktop/native-o32) = '+pin['native_o32_sha256']+'\n'+''.join(f'SHA256 ({p}) = {h}\n' for p,h in staged.items()))
    (m/'STAGED').write_text(''.join(f'SHA256 ({p}) = {h}\n' for p,h in staged.items()))
    (m/'SHA256').write_text(''.join(f'SHA256 ({p.relative_to(m)}) = {probe.sha256(p)}\n' for p in sorted(m.rglob('*')) if p.is_file()))
    for name in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',m])
    config=re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),(ROOT/'lab/indy-netbsd/iris.toml').read_text(),flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode=a.mode,debugger=False,boot_timeout=600),d,config_text=config)
    result=dict(status='error',clean_shutdown=False,stage=a.stage,mode=a.mode,pin=pin,seed=str(seed.relative_to(ROOT)),seed_result_sha256=probe.sha256(seed/'result.json'),sources={p:probe.sha256(ROOT/p) for p in sources},staged=staged,controls=[],cases=[])
    def cmd(c,t=120):
        before=len(lab.serial_text())
        if lab.command(c,t):raise RuntimeError('guest command failed: '+c)
        return lab.serial_text()[before:]
    def get(c):
        out=cmd('echo HEX_START; { '+c+'; } 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END',240)
        match=re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',out,re.M)
        if not match:raise RuntimeError('missing transfer')
        return gzip.decompress(bytes.fromhex(match[1]))
    def controls(phase):
        raw=cmd('./runner /root/irix-desktop/native-o32 0 0 0 0')
        actual=shell.r.runtime.observation(raw);assert actual==dict(errno_bytes=0,errno=0,exit=37,signal=0,killed=0,stdout='XIRI_ABI_PROBE\n',stderr=''),actual
        result['controls'].append(dict(phase=phase,actual=actual))
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd && chmod 444 /emul/irix/usr/lib/X11/app-defaults/4DWm /emul/irix/usr/lib/X11/system.4Dwmrc /emul/irix/usr/lib/X11/system.4Dwmdesks /emul/irix/usr/lib/X11/system.backgrounds && mkdir -p /tmp/xiri-wm /tmp/xiri-home && chown 1234:1234 /tmp/xiri-home && chmod 700 /tmp/xiri-home && cd /tmp/xiri-wm && cp /cdrom/*.c /cdrom/wm.env . && chmod 444 wm.env && : >input.txt && chmod 444 input.txt && ulimit -c 0',240)
        cmd('cc -O2 -Wall -Wextra -Werror guard.c -o guard && cc -O2 -Wall -Wextra -Werror session.c -o session && cc -O2 -Wall -Wextra -Werror runner.c -o runner && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include wmcheck.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o wmcheck && chmod 555 guard session runner wmcheck',240)
        cmd('uname -v | grep '+shlex.quote(pin['ident']));controls('before')
        result['resource_modes']=cmd("stat -f '%Sp %u %g %N' /emul/irix/usr/lib/X11/app-defaults/4DWm /emul/irix/usr/lib/X11/system.4Dwmrc /emul/irix/usr/lib/X11/system.4Dwmdesks /emul/irix/usr/lib/X11/system.backgrounds")
        cmd('export PATH=/usr/X11R7/bin:$PATH; install -d -m 755 /tmp/irix-screen-fonts && install -m 444 /cdrom/*.pcf* /tmp/irix-screen-fonts/ && mkfontdir /tmp/irix-screen-fonts; Xvfb :98 -screen 0 1024x768x24 -ac -noreset >xvfb.log 2>&1 & xpid=$!; sleep 3; xdpyinfo -display 127.0.0.1:98 >/dev/null && xset -display 127.0.0.1:98 +fp /tmp/irix-screen-fonts && xset -display 127.0.0.1:98 fp rehash',120)
        args=['./guard','30000','./session','wm.env','/emul/irix/usr/bin/X11/4Dwm','-display','127.0.0.1:98']
        cmd('ktrace -i -t usn -f wm.ktrace '+shlex.join(args)+' >wm.guard 2>&1 & job=$!; sleep 3; ./wmcheck 127.0.0.1:98 >wmcheck.out 2>wmcheck.err & check=$!; sleep 4; xwininfo -display 127.0.0.1:98 -root -tree >wm.tree; xprop -display 127.0.0.1:98 -root >wm.props; xwd -display 127.0.0.1:98 -root -silent >wm.xwd; wait "$check"; echo WMCHECK_STATUS=$? >wmcheck.status; wait "$job"',120)
        raw=get('cat wm.guard').decode();(d/'wm.guard').write_text(raw);actual=shell.guard(raw)
        cmd('kdump -x -f wm.ktrace >wm.dump && { head -n 6000 wm.dump; tail -n 2000 wm.dump; } >wm.capture',240)
        (d/'wm.kdump').write_bytes(get('cat wm.capture'));(d/'wm.xwd').write_bytes(get('cat wm.xwd'))
        result['cases'].append(dict(name='4Dwm',actual=actual,tree=get('cat wm.tree').decode(),properties=get('cat wm.props').decode(),frame_sha256=probe.sha256(d/'wm.xwd'),trace_info=get('sha256 wm.ktrace wm.dump').decode(),wmcheck=get('cat wmcheck.status wmcheck.out wmcheck.err').decode()))
        cmd('xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"');result['native_x11_after']=True
        controls('after');result['status']='observed'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['cases']),flush=True)
    return 0 if result['status']=='observed' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
