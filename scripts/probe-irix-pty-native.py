#!/usr/bin/env python3
"""Measure native PTY allocation and data flow on the pinned access kernel."""
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
    out=ROOT/'.work/irix-pty/native-runs';out.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix=a.mode+'-',dir=out));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    m=d/'media';m.mkdir()
    sources=['lab/irix-pty/native.c','lab/irix-lp64/runner.c','scripts/probe-irix-pty-native.py']
    for src in sources[:2]:shutil.copyfile(ROOT/src,m/Path(src).name)
    shutil.copyfile(build/'kernel-media/netbsd',m/'netbsd')
    inherited={'/netbsd':old['native_kernel_sha256'],'/root/irix-desktop/native-o32':pin['native_o32_sha256']}
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
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd && mkdir -p /root/irix-pty && cd /root/irix-pty && cp /cdrom/*.c . && cc -O2 -Wall -Wextra -Werror native.c -o native-pty && cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=5000 runner.c -o runner && chmod 555 native-pty runner && : >input.txt && chmod 444 input.txt && ulimit -c 0',240)
        cmd('uname -v | grep '+shlex.quote(pin['ident']))
        result['devices']=cmd('ls -l /dev/ptm* /dev/ptyp0 /dev/ttyp0; mount; sysctl kern.tty')
        for uid in [0,1234]:
            output=cmd('./runner ./native-pty '+' '.join([str(uid)]*4))
            actual=r.runtime.observation(output)
            result['cases'].append(dict(uid=uid,actual=actual))
            print(json.dumps(result['cases'][-1]),flush=True)
            if actual['exit'] or actual['signal'] or actual['killed'] or actual['stderr'] or 'NATIVE_PTY_PASS' not in actual['stdout']:raise RuntimeError('native PTY failed')
        result['status']='observed'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='observed' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
