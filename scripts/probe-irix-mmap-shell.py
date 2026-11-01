#!/usr/bin/env python3
"""Regress the qualified winterm shell against private fixed/local mmap support."""
import argparse,gzip,hashlib,importlib.util,json,re,shlex,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('resources',ROOT/'scripts/probe-irix-winterm-resources.py')
r=importlib.util.module_from_spec(s);s.loader.exec_module(r);probe=r.probe

def guard(raw):
    m=re.search(r'^GUARD pid=(\d+) exit=(-?\d+) signal=(\d+) killed=(\d+) absent=(\d+) valid=(\d+) elapsed=(\d+)$',raw,re.M)
    if not m:raise RuntimeError('missing guard result')
    result=dict(zip(['pid','exit','signal','killed','absent','valid','elapsed_ms'],map(int,m.groups())))
    for label in ['STDOUT','STDERR']:
        m=re.search(r'^'+label+r' bytes=(\d+) hex=([0-9a-f]*)$',raw,re.M)
        if not m or len(bytes.fromhex(m[2]))!=int(m[1]):raise RuntimeError('truncated guard capture')
        result[label.lower()]=bytes.fromhex(m[2]).decode(errors='backslashreplace')
    if 'EXEC bytes=0 errno=0' not in raw or not result['absent'] or not result['valid']:raise RuntimeError('guard failed')
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed-directory',type=Path,required=True)
    p.add_argument('--mode',choices=['ci','ordinary'],default='ci')
    p.add_argument('--kernel-abi',choices=['lp64','o32'],default='lp64')
    p.add_argument('--scope',choices=['apps'],default='apps')
    p.add_argument('--smoke',action='store_true')
    a=p.parse_args();seed=a.seed_directory.resolve();sr=json.loads((seed/'result.json').read_text())
    old=json.loads((ROOT/'lab/irix-siocnread/baseline.json').read_text())
    if not(sr['status']=='observed' and sr['clean_shutdown'] and sr['native_x11_after'] and sr['pin']==old and len(sr['cases'])==8):p.error('need the stopped font/locale seed')
    pin=json.loads((ROOT/'lab/irix-mmap-local'/('o32-baseline.json' if a.kernel_abi=='o32' else 'baseline.json')).read_text())
    build=ROOT/('.work/netbsd-irix-mmap-local'+('-o32' if a.kernel_abi=='o32' else '')+'-build')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256'),(build/'kernel-media/netbsd','native_kernel_sha256')]:
        if probe.sha256(path)!=pin[key]:p.error('changed pinned input')
    fixtures=ROOT/'.work/irix-shell/probes';manifest=json.loads((fixtures/'manifest.json').read_text())
    for path,h in manifest['sources'].items():
        if probe.sha256(ROOT/path)!=h:p.error('stale fixture source')
    out=ROOT/'.work/irix-mmap-local/shell-runs';out.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix=a.kernel_abi+'-'+a.mode+'-',dir=out));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    m=d/'media';m.mkdir()
    xcomp=ROOT/'.work/netbsd-11.0/sgimips/binary/sets/xcomp.tgz'
    expected=re.search(r'^([0-9a-f]{128})  sgimips/binary/sets/xcomp.tgz$',(ROOT/'lab/netbsd-11.0/SHA512SUMS').read_text(),re.M)[1]
    if hashlib.sha512(xcomp.read_bytes()).hexdigest()!=expected:p.error('changed native X development set')
    if a.scope!='interfaces':shutil.copyfile(xcomp,m/'xcomp.tgz')
    sources=['scripts/probe-irix-mmap-shell.py','lab/irix-shell/guard.c','lab/irix-shell/ctty-control.c','lab/irix-shell/escape-control.c','lab/irix-shell/handoff.c','lab/irix-shell/type.c','lab/irix-lp64/runner.c','lab/irix-toolchest/session.c','lab/irix-pty/setup.sh','lab/irix-process/trace-window.awk']
    for src in sources[1:]:shutil.copyfile(ROOT/src,m/Path(src).name)
    shutil.copyfile(ROOT/'lab/irix-shell/setup.sh',m/'fixture-setup.sh')
    cases=[c for c in manifest['cases'] if a.kernel_abi=='lp64' or c['abi']=='o32']
    if a.smoke:cases=[c for c in cases if any(c['name'].endswith('-'+x) for x in ['descriptors','exec','path_mode-5','arg_mode-2','env_mode-2'])]
    for c in cases:
        if probe.sha256(fixtures/c['name'])!=manifest['files'][c['name']]['sha256']:p.error('changed fixture')
        shutil.copy2(fixtures/c['name'],m/c['name'])
    shutil.copyfile(build/'kernel-media/netbsd',m/'netbsd')
    inherited={'/netbsd':old['native_kernel_sha256'],'/root/irix-desktop/native-o32':pin['native_o32_sha256']}
    for path,info in json.loads((ROOT/'lab/irix-winterm/manifest.json').read_text())['files'].items():inherited['/emul/irix'+path]=info['sha256']
    for c in json.loads((ROOT/'lab/irix-reference/manifest.json').read_text())['candidates']:inherited['/root/irix-desktop/'+c['fixture_name']]=c['sha256']
    for c in pin['runtimes']:inherited['/emul/irix'+c['path']]=c['sha256']
    fonts={}
    for path,info in sr['manifest']['files'].items():
        if '/fonts/' in path:
            src=ROOT/'.work/irix-x11-fonts/root'/path.lstrip('/')
            if probe.sha256(src)!=info['sha256']:p.error('changed font')
            shutil.copyfile(src,m/Path(path).name);fonts['/tmp/irix-screen-fonts/'+Path(path).name]=info['sha256']
        else:inherited['/emul/irix'+path]=info['sha256']
    (m/'FONTS').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in fonts.items()))
    (m/'INHERITED').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in inherited.items()))
    env=['HOME=/tmp/xiri-home','USER=xiri','LOGNAME=xiri','SHELL=/bin/sh','DISPLAY=127.0.0.1:98','LANG=C','LC_ALL=C','PATH=/bin:/usr/bin:/usr/X11R7/bin:/emul/irix/usr/bin','WINTERM=/emul/irix/usr/sbin/xwsh -name winterm','PS1=xiri$ ']
    (m/'shell.env').write_text('\n'.join(env)+'\n')
    lines=['#!/bin/sh','set -eu','cd /tmp/xiri-shell','ulimit -c 0','sh /cdrom/fixture-setup.sh','ulimit -n >limit.txt']
    for c in cases:
        for i in c['identities']:
            n=c['name']+'-'+str(i);uid=manifest['identities'][i][0]
            lines+=['echo STARTCASE '+n,shlex.join(['./runner','./'+c['name'],*[str(uid)]*4]),'echo ENDCASE '+n]
    (m/'run.sh').write_text('\n'.join(lines)+'\n')
    (m/'SHA256').write_text(''.join(f'SHA256 ({path.name}) = {probe.sha256(path)}\n' for path in sorted(m.iterdir())))
    for name in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',m])
    config=re.sub(r'^tftp_dir = .*$','tftp_dir = '+json.dumps(str(build/'tftp')),(ROOT/'lab/indy-netbsd/iris.toml').read_text(),flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode=a.mode,debugger=False,boot_timeout=600),d,config_text=config)
    result=dict(status='error',clean_shutdown=False,mode=a.mode,kernel_abi=a.kernel_abi,scope=a.scope,smoke=a.smoke,pin=pin,xcomp_sha512=expected,seed=str(seed.relative_to(ROOT)),seed_result_sha256=probe.sha256(seed/'result.json'),manifest=manifest,sources={x:probe.sha256(ROOT/x) for x in sources},controls=[],observations=[],apps=[])
    def cmd(c,t=120):
        before=len(lab.serial_text())
        if lab.command(c,t):raise RuntimeError('guest command failed: '+c)
        return lab.serial_text()[before:]
    def get(c):
        x=cmd('echo HEX_START; { '+c+'; } 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END',240)
        match=re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',x,re.M)
        if not match:raise RuntimeError('missing payload')
        return gzip.decompress(bytes.fromhex(match[1]))
    def controls(phase):
        raw=cmd('./guard 2000 ./escape-control');actual=guard(raw)
        if actual['exit'] or actual['signal'] or not actual['killed'] or actual['elapsed_ms']<2000 or actual['stdout'] or actual['stderr']:raise RuntimeError('setsid cleanup control')
        result['controls'].append(dict(phase=phase,name='session-descendant-cleanup',actual=actual))
        for uid in [0,1234]:
            for exe,args,want in [('/root/irix-desktop/native-o32',[],(37,'XIRI_ABI_PROBE\n')),('/root/irix-desktop/vendor-asa',[],(0,''))]:
                # Empty input intentionally gives asa no output.
                actual=r.runtime.observation(cmd(shlex.join(['./runner',exe,*[str(uid)]*4,'--',*args])))
                if actual!=dict(errno_bytes=0,errno=0,exit=want[0],signal=0,killed=0,stdout=want[1],stderr=''):raise RuntimeError('native/vendor control '+exe)
                result['controls'].append(dict(phase=phase,name=exe,uid=uid,actual=actual))
    def ctty_controls(phase):
        for uid in [0,1234]:
            for mode in [0,2]:
                raw=cmd(shlex.join(['./runner','./ctty-control',*[str(uid)]*4,'--',str(mode)]))
                actual=r.runtime.observation(raw)
                if actual['exit'] or actual['signal'] or actual['killed'] or actual['stderr'] or ('NATIVE_CTTY mode='+str(mode)+' exit=-1 signal=1\n') not in actual['stdout']:raise RuntimeError('native controlling terminal teardown')
                result.setdefault('native_ctty_controls',[]).append(dict(phase=phase,uid=uid,mode=mode,actual=actual))
    def application(name,argv):
        work='/tmp/xiri-shell/'+name;cookie='XIRI_'+name.upper()+'_SHELL_OK'
        cmd('mkdir '+work+' && chown 1234:1234 '+work+' && chmod 700 '+work)
        args=['./guard','30000','./session','shell.env',*argv,'/usr/libexec/xiri-shell',work+'/handoff']
        cmd('ktrace -i -t usn -f '+name+'.ktrace '+shlex.join(args)+' >'+name+'.guard 2>&1 & job=$!; sleep 4; xwininfo -display 127.0.0.1:98 -root -tree >'+name+'.before')
        command="printf '"+cookie+"\\n'; uname -s; id -u; printf '"+cookie+"\\n' > "+work+'/result'
        typing=cmd("suffix=$(printf '\\n_'); ./type 127.0.0.1:98 winterm "+shlex.quote(command)+'"${suffix%_}" >'+name+'.typing 2>&1; echo TYPE_STATUS=$?; sleep 2; xwininfo -display 127.0.0.1:98 -root -tree >'+name+'.tree; xwd -display 127.0.0.1:98 -root -silent >'+name+'.xwd; wait "$job"; echo GUARD_STATUS=$?',120)
        raw=get('cat '+name+'.guard').decode();(d/(name+'.guard')).write_text(raw)
        actual=guard(raw)
        frame=d/(name+'.xwd');frame.write_bytes(get('cat '+name+'.xwd'))
        # Capture diagnostics even when input or native exec fails.
        cmd('kdump -x -f '+name+'.ktrace >'+name+'.dump && awk -f /cdrom/trace-window.awk '+name+'.dump >'+name+'.capture',240)
        (d/(name+'.kdump')).write_bytes(get('cat '+name+'.capture'))
        handoff=get('cat '+work+'/handoff').decode();output=get('cat '+work+'/result').decode()
        obs=dict(name=name,argv=argv,actual=actual,typing=typing,handoff=handoff,output=output,cookie=cookie,tree=get('cat '+name+'.tree').decode(),frame_sha256=probe.sha256(frame),trace_info=get('sha256 '+name+'.ktrace '+name+'.dump').decode())
        result['apps'].append(obs);print(json.dumps(obs),flush=True)
        if 'TYPE_STATUS=0' not in typing or output!=cookie+'\n' or not handoff.startswith('NATIVE_HANDOFF '):raise RuntimeError('shell command proof failed: '+name)
        cmd('test "$(stat -f %u '+work+'/result)" = 1234')
        obs['marker_owner']=1234
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd && mkdir -p /tmp/xiri-shell /tmp/xiri-home && chmod 755 /tmp/xiri-shell && chmod 777 /tmp/xiri-home && cd /tmp/xiri-shell && cp /cdrom/*.c /cdrom/shell.env . && cp /cdrom/*direct-* . && chmod 555 *direct-* && sh /cdrom/fixture-setup.sh && ulimit -c 0',240)
        cmd('cc -O2 -Wall -Wextra -Werror guard.c -o guard && cc -O2 -Wall -Wextra -Werror escape-control.c -o escape-control && cc -O2 -Wall -Wextra -Werror handoff.c -o /usr/libexec/xiri-shell && cc -O2 -Wall -Wextra -Werror runner.c -o runner && cc -O2 -Wall -Wextra -Werror session.c -o session && chmod 555 guard escape-control runner session /usr/libexec/xiri-shell && chmod 444 shell.env',240)
        cmd('uname -v | grep '+shlex.quote(pin['ident']));controls('before')
        if a.scope!='apps':
            cmd('sh /cdrom/run.sh >fixtures.log 2>&1',1800)
            raw=get('cat fixtures.log').decode();(d/'fixtures.log').write_text(raw)
            result['native_fd_limit']=int(get('cat limit.txt'))
            for c in cases:
                for i in c['identities']:
                    name=c['name']+'-'+str(i)
                    match=re.search(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+r'$',raw,re.M|re.S)
                    if not match:raise RuntimeError('missing '+name)
                    observation=r.runtime.observation(match[1]);h=re.search(r'^STDOUT bytes=\d+ hex=([0-9a-f]*)$',match[1],re.M)[1]
                    observation.pop('stdout');observation['stdout_hex']=h
                    result['observations'].append(dict(name=name,actual=observation))
            print(str(len(result['observations']))+' interface cases captured',flush=True)
        if a.scope!='interfaces':
            cmd('tar xzpf /cdrom/xcomp.tgz -C / && sh /cdrom/setup.sh && cc -O2 -Wall -Wextra -Werror ctty-control.c -lutil -o ctty-control && chmod 555 ctty-control && cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include type.c -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib -lX11 -lXtst -o type && install -d -m 755 /tmp/irix-screen-fonts && install -m 444 /cdrom/*.pcf* /tmp/irix-screen-fonts/ && /usr/X11R7/bin/mkfontdir /tmp/irix-screen-fonts && sha256 -c /cdrom/FONTS',240)
            cmd('export PATH=/usr/X11R7/bin:$PATH; Xvfb :98 -screen 0 1024x768x24 -ac -noreset >xvfb.log 2>&1 & xpid=$!; sleep 2; xdpyinfo -display 127.0.0.1:98 >/dev/null && xset -display 127.0.0.1:98 +fp /tmp/irix-screen-fonts && xset -display 127.0.0.1:98 fp rehash')
            ctty_controls('before')
            application('native',['/usr/X11R7/bin/xterm','-name','winterm','-title','winterm','-geometry','80x24','-fn',r.FONT,'-fb',r.FONT,'-e'])
            application('xwsh',['/emul/irix/usr/sbin/xwsh','-name','winterm','-title','winterm','-geometry','80x24','-e'])
            if not a.smoke:application('winterm',['/bin/sh','/emul/irix/usr/sbin/winterm','-name','winterm','-title','winterm','-geometry','80x24','-e'])
            ctty_controls('after')
            cmd('xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"');result['native_x11_after']=True
        controls('after');result['status']='observed-uncompared'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='observed-uncompared' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
