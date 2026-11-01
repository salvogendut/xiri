#!/usr/bin/env python3
"""Observe measured pthread initialization with native exec isolation controls."""
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
    p.add_argument('--smoke',action='store_true')
    a=p.parse_args();seed=a.seed_directory.resolve();sr=json.loads((seed/'result.json').read_text())
    old=json.loads((ROOT/'lab/irix-siocnread/baseline.json').read_text())
    if not(sr['status']=='observed' and sr['clean_shutdown'] and sr['native_x11_after'] and sr['pin']==old and len(sr['cases'])==8):p.error('need the stopped font/locale seed')
    pin=json.loads((ROOT/'lab/irix-init-threads'/('o32-baseline.json' if a.kernel_abi=='o32' else 'baseline.json')).read_text())
    build=ROOT/('.work/netbsd-irix-init-threads'+('-o32' if a.kernel_abi=='o32' else '')+'-build')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256'),(build/'kernel-media/netbsd','native_kernel_sha256')]:
        if probe.sha256(path)!=pin[key]:p.error('changed pinned input')
    fixtures=ROOT/'.work/irix-init-threads/probes';manifest=json.loads((fixtures/'manifest.json').read_text())
    for path,h in manifest['sources'].items():
        if probe.sha256(ROOT/path)!=h:p.error('stale fixture source')
    out=ROOT/'.work/irix-init-threads/runs';out.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix=a.kernel_abi+'-'+a.mode+'-',dir=out));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    m=d/'media';m.mkdir()
    sources=['scripts/probe-irix-init-threads.py','lab/irix-shell/guard.c','lab/irix-shell/escape-control.c','lab/irix-lp64/runner.c','lab/irix-mmap-local/zero-control.c','lab/irix-prda/prda-control.c','lab/irix-init-threads/signal-inspect.c','lab/irix-init-threads/signal-native.c']
    for src in sources[1:]:shutil.copyfile(ROOT/src,m/Path(src).name)
    execdir=ROOT/'.work/irix-mmap-local/exec-controls';exec_manifest=json.loads((execdir/'manifest.json').read_text())
    for path,h in exec_manifest['sources'].items():assert probe.sha256(ROOT/path)==h
    for name,info in exec_manifest['files'].items():
        assert probe.sha256(execdir/name)==info['sha256']
        shutil.copyfile(execdir/name,m/name)
    forkdir=ROOT/'.work/irix-prda/fork-controls';fork_manifest=json.loads((forkdir/'manifest.json').read_text())
    for path,h in fork_manifest['sources'].items():assert probe.sha256(ROOT/path)==h
    for name,info in fork_manifest['files'].items():
        assert probe.sha256(forkdir/name)==info['sha256']
        shutil.copyfile(forkdir/name,m/name)
    signal_dir=ROOT/'.work/irix-init-threads/signal-controls'
    signal_manifest=json.loads((signal_dir/'manifest.json').read_text())
    for path,h in signal_manifest['sources'].items():assert probe.sha256(ROOT/path)==h
    for name,info in signal_manifest['files'].items():
        assert probe.sha256(signal_dir/name)==info['sha256']
        shutil.copyfile(signal_dir/name,m/name)
    cases=[c for c in manifest['cases'] if a.kernel_abi=='lp64' or c['abi']=='o32']
    if a.smoke:cases=[c for c in cases if any(c['name'].endswith('-'+x) for x in ['initial','fork','exec','mask'])]
    for c in cases:
        if probe.sha256(fixtures/c['name'])!=manifest['files'][c['name']]['sha256']:p.error('changed fixture')
        shutil.copy2(fixtures/c['name'],m/c['name'])
    shutil.copyfile(build/'kernel-media/netbsd',m/'netbsd')
    inherited={'/netbsd':old['native_kernel_sha256'],'/root/irix-desktop/native-o32':pin['native_o32_sha256']}
    for path,info in json.loads((ROOT/'lab/irix-winterm/manifest.json').read_text())['files'].items():inherited['/emul/irix'+path]=info['sha256']
    for c in json.loads((ROOT/'lab/irix-reference/manifest.json').read_text())['candidates']:inherited['/root/irix-desktop/'+c['fixture_name']]=c['sha256']
    for c in pin['runtimes']:inherited['/emul/irix'+c['path']]=c['sha256']
    (m/'INHERITED').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in inherited.items()))
    lines=['#!/bin/sh','set -eu','cd /tmp/xiri-shell','ulimit -c 0']
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
    result=dict(status='error',clean_shutdown=False,mode=a.mode,kernel_abi=a.kernel_abi,smoke=a.smoke,pin=pin,seed=str(seed.relative_to(ROOT)),seed_result_sha256=probe.sha256(seed/'result.json'),manifest=manifest,exec_manifest=exec_manifest,fork_manifest=fork_manifest,sources={x:probe.sha256(ROOT/x) for x in sources},controls=[],native_zero_controls=[],native_prda_controls=[],fork_errors=[],signal_manifest=signal_manifest,signal_controls=[],observations=[])
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
        for uid in [0,1234]:
            for abi in ['native','o32']+(['n32'] if a.kernel_abi=='lp64' else []):
                argv=['./zero-control'] if abi=='native' else ['./'+abi+'-native-exec']
                argv=[argv[0],*[str(uid)]*4]+(['--','/tmp/xiri-shell/zero-control'] if abi!='native' else [])
                actual=r.runtime.observation(cmd(shlex.join(['./runner',*argv])))
                assert actual==dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout='NATIVE_ZERO page='+str(pin['page_bytes'])+' guard=1 errno=22\n',stderr=''),(abi,actual)
                result['native_zero_controls'].append(dict(phase=phase,abi=abi,uid=uid,actual=actual))
                argv=['./prda-control',*[str(uid)]*4] if abi=='native' else ['./'+abi+'-native-exec',*[str(uid)]*4,'--','/tmp/xiri-shell/prda-control']
                actual=r.runtime.observation(cmd(shlex.join(['./runner',*argv])))
                assert actual==dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout='NATIVE_PRDA absent=1 errno=12 page='+str(pin['page_bytes'])+'\n',stderr=''),(abi,actual)
                result['native_prda_controls'].append(dict(phase=phase,abi=abi,uid=uid,actual=actual))
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd && mkdir -p /tmp/xiri-shell /tmp/xiri-home && chmod 755 /tmp/xiri-shell && chmod 777 /tmp/xiri-home && cd /tmp/xiri-shell && cp /cdrom/*.c . && cp /cdrom/*direct-* /cdrom/*-native-exec /cdrom/*-fork-error-* /cdrom/*-signal-spin-* . && chmod 555 *direct-* *-native-exec *-fork-error-* *-signal-spin-* && : >input.txt && chmod 444 input.txt && ulimit -c 0',240)
        cmd('cc -O2 -Wall -Wextra -Werror guard.c -o guard && cc -O2 -Wall -Wextra -Werror escape-control.c -o escape-control && cc -O2 -Wall -Wextra -Werror runner.c -o runner && cc -O2 -Wall -Wextra -Werror zero-control.c -o zero-control && cc -O2 -Wall -Wextra -Werror prda-control.c -o prda-control && chmod 555 guard escape-control runner zero-control prda-control',240)
        cmd('cc -O2 -Wall -Wextra -Werror signal-inspect.c -o signal-inspect && cc -O2 -Wall -Wextra -Werror -DMODE=0 signal-native.c -o native-signal-0 && cc -O2 -Wall -Wextra -Werror -DMODE=1 signal-native.c -o native-signal-1 && chmod 555 signal-inspect native-signal-*',240)
        cmd('uname -v | grep '+shlex.quote(pin['ident']));controls('before')
        cmd('sh /cdrom/run.sh >fixtures.log 2>&1',1800)
        raw=get('cat fixtures.log').decode();(d/'fixtures.log').write_text(raw)
        for c in cases:
            for i in c['identities']:
                name=c['name']+'-'+str(i)
                match=re.search(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+r'$',raw,re.M|re.S)
                if not match:raise RuntimeError('missing '+name)
                observation=r.runtime.observation(match[1]);h=re.search(r'^STDOUT bytes=\d+ hex=([0-9a-f]*)$',match[1],re.M)[1]
                observation.pop('stdout');observation['stdout_hex']=h
                result['observations'].append(dict(name=name,actual=observation))
        print(str(len(result['observations']))+' interface cases captured',flush=True)

        for abi in ['o32']+(['n32'] if a.kernel_abi=='lp64' else []):
            for mode in [0,1]:
                for uid in [0,1234]:
                    raw=cmd(shlex.join(['./runner','./'+abi+'-fork-error-'+str(mode),*[str(uid)]*4]))
                    actual=r.runtime.observation(raw);actual.pop('stdout');actual['stdout_hex']=re.search(r'^STDOUT bytes=\d+ hex=([0-9a-f]*)$',raw,re.M)[1]
                    result['fork_errors'].append(dict(abi=abi,mode=mode,uid=uid,actual=actual))
        for abi in ['native','o32']+(['n32'] if a.kernel_abi=='lp64' else []):
            for mode in [0,1]:
                for uid in [0,1234]:
                    exe=('./native-signal-' if abi=='native' else './'+abi+'-signal-spin-')+str(mode)
                    raw=cmd(shlex.join(['./signal-inspect',str(uid),str(mode),exe]),60)
                    result['signal_controls'].append(dict(abi=abi,mode=mode,uid=uid,output=raw))
        controls('after');result['status']='observed-uncompared'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='observed-uncompared' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
