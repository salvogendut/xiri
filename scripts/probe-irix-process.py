#!/usr/bin/env python3
"""Observe fork/mask/child-exit fixtures with independent native process snapshots."""
import argparse,gzip,importlib.util,json,re,shlex,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent

def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
probe=module('probe','probe-netbsd.py');runtime=module('runtime','probe-irix-runtime.py')

def observation(text):
    m=re.search(r'^OBS pid=(\d+) exit=(-?\d+) signal=(\d+) timeout=(\d+) valid=(\d+) released=(\d+) group_absent=(\d+)$',text,re.M)
    if not m:raise RuntimeError('missing supervisor outcome')
    result=dict(zip(['pid','exit','signal','timeout','valid','released','group_absent'],map(int,m.groups())))
    for label in ['STDOUT','STDERR']:
        q=re.search(r'^'+label+r' bytes=(\d+) hex=([0-9a-f]*)$',text,re.M)
        if not q or len(bytes.fromhex(q[2]))!=int(q[1]):raise RuntimeError('missing supervisor data')
        result[label.lower()+'_hex']=q[2]
    result['snapshots']=[]
    for q in re.finditer(r'^SNAP role=(\d+) pid=(\d+) ppid=(\d+) pgid=(\d+) ids=([0-9,]+) groups=(\d+) mask=([0-9a-f,]+)$',text,re.M):
        result['snapshots'].append(dict(role=int(q[1]),pid=int(q[2]),ppid=int(q[3]),pgid=int(q[4]),ids=list(map(int,q[5].split(','))),groups=int(q[6]),mask=[int(v,16) for v in q[7].split(',')]))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed-directory',type=Path,required=True)
    p.add_argument('--mode',choices=['ci','ordinary'],default='ci')
    p.add_argument('--kernel-abi',choices=['lp64','o32'],default='lp64')
    p.add_argument('--smoke',action='store_true')
    a=p.parse_args();seed=a.seed_directory.resolve();sr=json.loads((seed/'result.json').read_text())
    old=json.loads((ROOT/'lab/irix-siocnread/baseline.json').read_text())
    if not(sr['status']=='observed' and sr['clean_shutdown'] and sr['native_x11_after'] and sr['pin']==old and len(sr['cases'])==8):p.error('need the stopped font/locale seed')
    pin=json.loads((ROOT/'lab/irix-process'/('o32-baseline.json' if a.kernel_abi=='o32' else 'baseline.json')).read_text())
    build=ROOT/('.work/netbsd-irix-process'+('-o32' if a.kernel_abi=='o32' else '')+'-build')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256'),(build/'kernel-media/netbsd','native_kernel_sha256')]:
        if probe.sha256(path)!=pin[key]:p.error('changed pinned input '+str(path))
    fixtures=ROOT/'.work/irix-process/probes';manifest=json.loads((fixtures/'manifest.json').read_text())
    for path,h in manifest['sources'].items():
        if probe.sha256(ROOT/path)!=h:p.error('stale fixture source')
    out=ROOT/'.work/irix-process/runs';out.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix=a.kernel_abi+'-'+a.mode+'-',dir=out));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    m=d/'media';m.mkdir()
    sources=['lab/irix-process/inspect.c','lab/irix-process/native.c','lab/irix-lp64/runner.c','lab/irix-toolchest/session.c','scripts/probe-irix-process.py']
    for src in sources[:4]:shutil.copyfile(ROOT/src,m/Path(src).name)
    cases=[c for c in manifest['cases'] if a.kernel_abi=='lp64' or c['abi']=='o32']
    if a.smoke:cases=[c for c in cases if any(c['name'].endswith('-'+x) for x in ['mask-bit-16','mask-bit-33','mask-all','set-pointer-5','old-pointer-5','fork-exit-37','fork-nohang','fork-nowait','fork-options-0'])]
    for name in ['setup.sh']+[c['name'] for c in cases]:
        if probe.sha256(fixtures/name)!=manifest['files'][name]['sha256']:p.error('changed fixture')
        shutil.copy2(fixtures/name,m/name)
    shutil.copyfile(build/'kernel-media/netbsd',m/'netbsd')
    inherited={'/netbsd':old['native_kernel_sha256'],'/root/irix-desktop/native-o32':pin['native_o32_sha256']}
    vendor=json.loads((ROOT/'lab/irix-reference/manifest.json').read_text())
    for c in vendor['candidates']:inherited['/root/irix-desktop/'+c['fixture_name']]=c['sha256']
    for c in pin['runtimes']:inherited['/emul/irix'+c['path']]=c['sha256']
    (m/'INHERITED').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in inherited.items()))
    # Fixtures only read shared; every process reopens it at offset zero.
    # The FIFO empties when its last descriptor closes. The supervisor proves
    # the complete group is gone before the next case, so reuse is isolated.
    lines=['#!/bin/sh','set -eu','cd /tmp/xiri-process-records','ulimit -c 0','sh /cdrom/setup.sh']
    for c in cases:
        for i in c['identities']:
            name=c['name']+'-'+str(i)
            lines+=['echo STARTCASE '+name,shlex.join(['./inspect',str(manifest['identities'][i][0]),str(c['symbols']['KIND']),'./'+c['name']])+' || true','echo ENDCASE '+name]
    (m/'run.sh').write_text('\n'.join(lines)+'\n')
    (m/'SHA256').write_text(''.join(f'SHA256 ({path.name}) = {probe.sha256(path)}\n' for path in sorted(m.iterdir())))
    for name in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',m])
    config=re.sub(r'^tftp_dir = .*$','tftp_dir = '+json.dumps(str(build/'tftp')),(ROOT/'lab/indy-netbsd/iris.toml').read_text(),flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode=a.mode,debugger=False,boot_timeout=600),d,config_text=config)
    result=dict(status='error',scope='smoke' if a.smoke else 'full',clean_shutdown=False,mode=a.mode,kernel_abi=a.kernel_abi,pin=pin,seed=str(seed.relative_to(ROOT)),seed_result_sha256=probe.sha256(seed/'result.json'),manifest=manifest,sources={x:probe.sha256(ROOT/x) for x in sources},controls=[],native_process_controls=[],observations=[])
    def cmd(c,t=120):
        before=len(lab.serial_text())
        if lab.command(c,t):raise RuntimeError('guest command failed: '+c)
        return lab.serial_text()[before:]
    def get(c):
        x=cmd('echo HEX_START; '+c+' 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END',240)
        match=re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',x,re.M)
        if not match:raise RuntimeError('missing payload')
        return gzip.decompress(bytes.fromhex(match[1]))
    def controls(phase):
        for uid in [0,1234]:
            for kind in [0,1]:
                raw=cmd('cd /tmp/xiri-process-records && sh /cdrom/setup.sh && ./inspect '+str(uid)+' '+str(kind)+' ./native-'+str(kind))
                actual=observation(raw)
                if actual['exit'] or actual['signal'] or actual['stderr_hex'] or not actual['valid'] or not actual['group_absent']:raise RuntimeError('native supervisor control failed')
                result['native_process_controls'].append(dict(phase=phase,uid=uid,kind=kind,actual=actual))
            cmd('cd /root/irix-desktop')
            for exe,args,want in [('native-o32',[],(37,'XIRI_ABI_PROBE\n')),('vendor-asa',[],(0,'XIRI_VENDOR_O32\n'))]+([('vendor-echo',['XIRI_VENDOR_N32'],(0,'XIRI_VENDOR_N32\n'))] if a.kernel_abi=='lp64' else []):
                actual=runtime.observation(cmd(shlex.join(['./runner','./session',*[str(uid)]*4,'--','home.env','./'+exe,*args])))
                if actual!=dict(errno_bytes=0,errno=0,exit=want[0],signal=0,killed=0,stdout=want[1],stderr=''):raise RuntimeError('control failed '+exe)
                result['controls'].append(dict(phase=phase,uid=uid,name=exe,actual=actual))
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd',240)
        cmd('mkdir -p /tmp/xiri-process-records /tmp/xiri-home && chmod 755 /tmp/xiri-process-records && chmod 777 /tmp/xiri-home && cd /tmp/xiri-process-records && cp /cdrom/*.c . && cc -O2 -Wall -Wextra -Werror inspect.c -o inspect && cc -O2 -Wall -Wextra -Werror -DFORK_CONTROL=0 native.c -o native-0 && cc -O2 -Wall -Wextra -Werror -DFORK_CONTROL=1 native.c -o native-1 && cp /cdrom/*direct-* . && chmod 555 inspect native-* *direct-*',240)
        cmd('cd /root/irix-desktop && cp /cdrom/runner.c /cdrom/session.c . && cc -O2 -Wall -Wextra -Werror runner.c -o runner && cc -O2 -Wall -Wextra -Werror session.c -o session && chmod 555 runner session && printf "HOME=/tmp/xiri-home\\n" >home.env && chmod 444 home.env input.txt && ulimit -c 0',240)
        cmd('uname -v | grep '+shlex.quote(pin['ident']));controls('before')
        cmd('sh /cdrom/run.sh > /tmp/xiri-process-records/process.log 2>&1',1800)
        raw=get('cat /tmp/xiri-process-records/process.log').decode();(d/'fixtures.log').write_text(raw)
        for c in cases:
            for i in c['identities']:
                name=c['name']+'-'+str(i)
                match=re.search(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+r'$',raw,re.M|re.S)
                if not match:raise RuntimeError('missing '+name)
                result['observations'].append(dict(name=name,actual=observation(match[1])))
        print(str(len(result['observations']))+' process cases captured',flush=True)
        controls('after');result['status']='observed-uncompared'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='observed-uncompared' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
