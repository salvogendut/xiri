#!/usr/bin/env python3
"""Measure bounded ELF-map relocation and original xclock on a pinned kernel."""
import argparse,gzip,importlib.util,json,re,shlex,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent

def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
probe=module('probe','probe-netbsd.py');runtime=module('runtime','probe-irix-runtime.py');tcp=module('tcp','probe-irix-tcp.py')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed-directory',type=Path,required=True)
    p.add_argument('--limits-only',action='store_true')
    p.add_argument('--mode',choices=['ci','ordinary'],default='ci')
    p.add_argument('--kernel-abi',choices=['lp64','o32'],default='lp64')
    a=p.parse_args();seed=a.seed_directory.resolve();sr=json.loads((seed/'result.json').read_text())
    old=json.loads((ROOT/'lab/irix-siocnread/baseline.json').read_text())
    if not(sr['status']=='observed' and sr['clean_shutdown'] and sr['native_x11_after'] and sr['pin']==old and len(sr['xclock'])==4):p.error('need a stopped siocnread xclock seed')
    pin=json.loads((ROOT/'lab/irix-elfmap-relocation'/('o32-baseline.json' if a.kernel_abi=='o32' else 'baseline.json')).read_text())
    build=ROOT/('.work/netbsd-irix-elfmap-relocation'+('-o32' if a.kernel_abi=='o32' else '')+'-build')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256'),(build/'kernel-media/netbsd','native_kernel_sha256')]:
        if probe.sha256(path)!=pin[key]:p.error('changed pinned input')
    fixtures=ROOT/'.work/irix-elfmap-relocation/probes';manifest=json.loads((fixtures/'manifest.json').read_text())
    for path,h in manifest['sources'].items():
        if probe.sha256(ROOT/path)!=h:p.error('stale fixture source')
    out=ROOT/'.work/irix-elfmap-relocation/runs';out.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix=a.kernel_abi+'-'+a.mode+'-',dir=out));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    m=d/'media';m.mkdir()
    sources=['lab/irix-lp64/runner.c','lab/irix-toolchest/session.c','lab/irix-elfmap-relocation/limit.c','scripts/probe-irix-elfmap-relocation.py']
    for src in sources[:3]:shutil.copyfile(ROOT/src,m/Path(src).name)
    for name,info in manifest['files'].items():
        if probe.sha256(fixtures/name)!=info['sha256']:p.error('changed fixture')
        shutil.copy2(fixtures/name,m/name)
    shutil.copyfile(build/'kernel-media/netbsd',m/'netbsd')
    inherited={'/netbsd':old['native_kernel_sha256'],**sr['guest_inputs']}
    (m/'INHERITED').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in inherited.items()))
    abis=['o32'] if a.kernel_abi=='o32' else ['o32','n32']
    run_cases=[] if a.limits_only else manifest['cases']
    lines=['#!/bin/sh','set -eu','cd /root/irix-desktop','ulimit -c 0']
    for uid in [0,1234]:
        for abi in abis:
            for c in run_cases:
                name=abi+'-'+c['name']+'-'+str(uid)
                lines += ['cp '+c['input']+' elfmap-input.new','chmod '+('666' if c['mode']==0o644 else '777')+' elfmap-input.new','mv elfmap-input.new elfmap-input','echo STARTCASE '+name,
                          shlex.join(['./relocation-runner','./session',*[str(uid)]*4,'--','home.env','./elfmap-'+abi]),'echo ENDCASE '+name]
            name=abi+'-as-limit-'+str(uid)
            lines += ['cp elfmap-as-limit-payload elfmap-input.new','chmod 777 elfmap-input.new','mv elfmap-input.new elfmap-input','echo STARTCASE '+name,
                      shlex.join(['./relocation-runner','./session',*[str(uid)]*4,'--','home.env','./limit','40' if a.kernel_abi=='o32' else '128','./elfmap-'+abi]),'echo ENDCASE '+name]
    (m/'run.sh').write_text('\n'.join(lines)+'\n')
    (m/'SHA256').write_text(''.join(f'SHA256 ({path.name}) = {probe.sha256(path)}\n' for path in sorted(m.iterdir())))
    for name in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',m])
    config=re.sub(r'^tftp_dir = .*$','tftp_dir = '+json.dumps(str(build/'tftp')),(ROOT/'lab/indy-netbsd/iris.toml').read_text(),flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode=a.mode,debugger=False,boot_timeout=600),d,config_text=config)
    result=dict(status='error',clean_shutdown=False,mode=a.mode,limits_only=a.limits_only,kernel_abi=a.kernel_abi,pin=pin,seed=str(seed.relative_to(ROOT)),seed_result_sha256=probe.sha256(seed/'result.json'),manifest=manifest,sources={x:probe.sha256(ROOT/x) for x in sources},controls=[],observations=[],xclock=[])
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
        normal=dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout='',stderr='')
        for uid in [0,1234]:
            for exe,args,want in [('native-o32',[],dict(normal,exit=37,stdout='XIRI_ABI_PROBE\n')),('vendor-asa',[],dict(normal,stdout='XIRI_VENDOR_O32\n'))]+([('vendor-echo',['XIRI_VENDOR_N32'],dict(normal,stdout='XIRI_VENDOR_N32\n'))] if a.kernel_abi=='lp64' else []):
                actual=runtime.observation(cmd(shlex.join(['./relocation-runner','./session',*[str(uid)]*4,'--','home.env','./'+exe,*args])))
                if actual!=want:raise RuntimeError('control failed '+exe)
                result['controls'].append(dict(phase=phase,uid=uid,name=exe,actual=actual))
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd',240)
        cmd('cd /root/irix-desktop && cp /cdrom/*.c /cdrom/elfmap-* . && chmod 555 elfmap-* && cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=10000 runner.c -o relocation-runner && cc -O2 -Wall -Wextra -Werror session.c -o session && cc -O2 -Wall -Wextra -Werror limit.c -o limit && chmod 555 session relocation-runner limit && mkdir -p /tmp/xiri-home && chmod 777 /tmp/xiri-home && ulimit -c 0',240)
        cmd('uname -v | grep '+shlex.quote(pin['ident']))
        controls('before')
        cmd('sh /cdrom/run.sh >relocation.log 2>&1',600)
        raw=get('cat relocation.log').decode();(d/'fixtures.log').write_text(raw)
        for uid in [0,1234]:
            for abi in abis:
                for c in run_cases:
                    name=abi+'-'+c['name']+'-'+str(uid)
                    match=re.search(r'^STARTCASE '+name+r'\n(.*?)^ENDCASE '+name+r'$',raw,re.M|re.S)
                    if not match:raise RuntimeError('missing '+name)
                    actual=runtime.observation(match[1]);record=re.search(r'^STDOUT bytes=48 hex=([0-9a-f]+)$',match[1],re.M)
                    result['observations'].append(dict(name=name,actual=actual,record=runtime.elfmap_record(bytes.fromhex(record[1])) if record else None,record_hex=record[1] if record else None))
                name=abi+'-as-limit-'+str(uid)
                match=re.search(r'^STARTCASE '+name+r'\n(.*?)^ENDCASE '+name+r'$',raw,re.M|re.S)
                if not match:raise RuntimeError('missing '+name)
                actual=runtime.observation(match[1]);record=re.search(r'^STDOUT bytes=48 hex=([0-9a-f]+)$',match[1],re.M)
                result.setdefault('limits',[]).append(dict(name=name,actual=actual,record=runtime.elfmap_record(bytes.fromhex(record[1])) if record else None))
        print(str(len(result['observations']))+' mapping attempts observed',flush=True)
        if a.kernel_abi=='lp64' and not a.limits_only:
            cmd('export PATH=/usr/X11R7/bin:$PATH; Xvfb :98 -screen 0 640x480x24 -ac -noreset >relocation-xvfb.log 2>&1 & xpid=$!; sleep 2; xdpyinfo -display 127.0.0.1:98 >/dev/null')
            for phase in ['before','after']:
                cmd('xclock -display 127.0.0.1:98 -name NativeClock -title NativeClock >native-clock.err 2>&1 & npid=$!; sleep 2; xwininfo -display 127.0.0.1:98 -name NativeClock >native-window; kill "$npid"; wait "$npid" || true')
                window=get('cat native-window').decode()
                if 'Map State: IsViewable' not in window:raise RuntimeError('native clock failed')
                result['native_x11_'+phase]=True
                if phase=='after':break
                for uid in [0,1234]:
                    for style in ['analog','digital']:
                        name='clock-'+style+'-'+str(uid)
                        argv=['./relocation-runner','./session',*[str(uid)]*4,'--','home.env','./vendor-xclock','-display','127.0.0.1:98','-'+style,'-update','1','-title','Xiri_IRIX_clock']
                        cmd('ktrace -i -t un -f clock.ktrace '+shlex.join(argv)+' >clock-parent.log 2>&1 & cpid=$!; sleep 2; xwininfo -display 127.0.0.1:98 -root -tree >clock.tree; xwininfo -display 127.0.0.1:98 -name Xiri_IRIX_clock >clock.window 2>&1 || true; xwd -display 127.0.0.1:98 -root -silent >clock-before.xwd; sleep 2; xwd -display 127.0.0.1:98 -root -silent >clock-after.xwd; wait "$cpid"',90)
                        actual=runtime.observation(get('cat clock-parent.log').decode());trace=get('kdump -x -f clock.ktrace').decode();(d/(name+'.kdump')).write_text(trace)
                        frames={}
                        for ph in ['before','after']:
                            f=d/(name+'-'+ph+'.xwd');f.write_bytes(get('cat clock-'+ph+'.xwd'));frames[ph]=probe.sha256(f)
                        obs=dict(name=name,uid=uid,style=style,actual=actual,window=get('cat clock.window').decode(),tree=get('cat clock.tree').decode(),calls=tcp.trace_records(trace,'irix_o32',True),returns=tcp.trace_records(trace,'irix_ret',True),frames=frames)
                        result['xclock'].append(obs);print(name+': '+json.dumps(actual),flush=True)
            cmd('xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"')
        controls('after');result['status']='observed'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='observed' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
