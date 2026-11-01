#!/usr/bin/env python3
"""Capture shared mmap ABI and lifecycle records on a pinned NetBSD kernel."""
import argparse,gzip,importlib.util,json,re,shlex,shutil,struct,tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent

def module(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
probe=module('probe','probe-netbsd.py');runtime=module('runtime','probe-irix-runtime.py')

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed-directory',type=Path,required=True)
    p.add_argument('--mode',choices=['ci','ordinary'],default='ci')
    p.add_argument('--kernel-abi',choices=['lp64','o32'],default='lp64')
    a=p.parse_args();seed=a.seed_directory.resolve();sr=json.loads((seed/'result.json').read_text())
    old=json.loads((ROOT/'lab/irix-siocnread/baseline.json').read_text())
    if not(sr['status']=='observed' and sr['clean_shutdown'] and sr['native_x11_after'] and sr['pin']==old and len(sr['cases'])==8):p.error('need a stopped font/locale winterm seed')
    pin=json.loads((ROOT/'lab/irix-mmap-shared'/('o32-baseline.json' if a.kernel_abi=='o32' else 'baseline.json')).read_text())
    build=ROOT/('.work/netbsd-irix-mmap-shared'+('-o32' if a.kernel_abi=='o32' else '')+'-build')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256'),(build/'kernel-media/netbsd','native_kernel_sha256')]:
        if probe.sha256(path)!=pin[key]:p.error('changed pinned input '+str(path))
    fixtures=ROOT/'.work/irix-mmap-shared/probes';manifest=json.loads((fixtures/'manifest.json').read_text())
    for path,h in manifest['sources'].items():
        if probe.sha256(ROOT/path)!=h:p.error('stale fixture source')
    out=ROOT/'.work/irix-mmap-shared/runs';out.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix=a.kernel_abi+'-'+a.mode+'-',dir=out));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    m=d/'media';m.mkdir()
    sources=['lab/irix-process/runner.c','lab/irix-toolchest/session.c','scripts/probe-irix-mmap-shared.py','lab/irix-mmap-shared/native-control.c']
    for src in [sources[0],sources[1],sources[3]]:shutil.copyfile(ROOT/src,m/Path(src).name)
    cases=[c for c in manifest['cases'] if a.kernel_abi=='lp64' or c['abi']=='o32']
    for name in ['setup.sh','mapping']+[c['name'] for c in cases]:
        if probe.sha256(fixtures/name)!=manifest['files'][name]['sha256']:p.error('changed fixture')
        shutil.copy2(fixtures/name,m/name)
    shutil.copyfile(build/'kernel-media/netbsd',m/'netbsd')
    inherited={'/netbsd':old['native_kernel_sha256'],'/root/irix-desktop/native-o32':pin['native_o32_sha256']}
    vendor=json.loads((ROOT/'lab/irix-reference/manifest.json').read_text())
    for c in vendor['candidates']:inherited['/root/irix-desktop/'+c['fixture_name']]=c['sha256']
    for c in pin['runtimes']:inherited['/emul/irix'+c['path']]=c['sha256']
    (m/'INHERITED').write_text(''.join(f'SHA256 ({path}) = {h}\n' for path,h in inherited.items()))
    lines=['#!/bin/sh','set -eu','cd /tmp/xiri-mmap-shared','ulimit -c 0']
    for c in cases:
        for i in c['identities']:
            name=c['name']+'-'+str(i)
            lines += ['sh setup.sh '+str(c['symbols']['FILE_SIZE']), 'echo STARTCASE '+name,
                shlex.join(['./mmap-runner','./'+c['name'],*map(str,manifest['identities'][i])]),
                'cp '+('zero' if c['symbols']['FILE_KIND']==4 else 'data')+' '+name+'.data',
                'echo ENDCASE '+name]
    (m/'run.sh').write_text('\n'.join(lines)+'\n')
    (m/'SHA256').write_text(''.join(f'SHA256 ({path.name}) = {probe.sha256(path)}\n' for path in sorted(m.iterdir())))
    for name in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',m])
    config=re.sub(r'^tftp_dir = .*$','tftp_dir = '+json.dumps(str(build/'tftp')),(ROOT/'lab/indy-netbsd/iris.toml').read_text(),flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode=a.mode,debugger=False,boot_timeout=600),d,config_text=config)
    result=dict(status='error',clean_shutdown=False,mode=a.mode,kernel_abi=a.kernel_abi,pin=pin,seed=str(seed.relative_to(ROOT)),seed_result_sha256=probe.sha256(seed/'result.json'),manifest=manifest,sources={x:probe.sha256(ROOT/x) for x in sources},controls=[],observations=[])
    def cmd(c,t=120):
        before=len(lab.serial_text())
        if lab.command(c,t):raise RuntimeError('guest command failed: '+c)
        return lab.serial_text()[before:]
    def get(c):
        x=cmd('echo HEX_START; '+c+' 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END',240)
        match=re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',x,re.M)
        if not match:raise RuntimeError('missing payload')
        return gzip.decompress(bytes.fromhex(match[1]))
    normal=dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout='',stderr='')
    def controls(phase):
        for uid in [0,1234]:
            for exe,args,want in [('native-o32',[],dict(normal,exit=37,stdout='XIRI_ABI_PROBE\n')),('vendor-asa',[],dict(normal,stdout='XIRI_VENDOR_O32\n'))]+([('vendor-echo',['XIRI_VENDOR_N32'],dict(normal,stdout='XIRI_VENDOR_N32\n'))] if a.kernel_abi=='lp64' else []):
                actual=runtime.observation(cmd(shlex.join(['./mmap-runner','./session',*[str(uid)]*4,'--','home.env','./'+exe,*args])))
                if actual!=want:raise RuntimeError('control failed '+exe)
                result['controls'].append(dict(phase=phase,uid=uid,name=exe,actual=actual))
        for uid in [0,1234]:
            raw=cmd(shlex.join(['./mmap-runner','./native-control',*[str(uid)]*4]))
            actual=runtime.observation(raw)
            assert actual==dict(normal,stdout=f'NATIVE_MMAP uid={uid} zero=1 shared=1 private=1 close=1 file=1 eof=1\n'),actual
            assert 'GROUP absent=1' in raw
            result['controls'].append(dict(phase=phase,uid=uid,name='native-mmap',actual=actual,group_absent=True))
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd',240)
        cmd('cd /root/irix-desktop && cp /cdrom/*.c . && cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=5000 runner.c -o mmap-runner && cc -O2 -Wall -Wextra -Werror session.c -o session && cc -O2 -Wall -Wextra -Werror native-control.c -o native-control && chmod 555 native-control && chmod 555 session mmap-runner && mkdir -p /tmp/xiri-home /tmp/xiri-mmap-shared && chmod 777 /tmp/xiri-home && chmod 755 /tmp/xiri-mmap-shared && printf "HOME=/tmp/xiri-home\\n" >home.env && chmod 444 home.env input.txt && cp /cdrom/*direct-* /cdrom/setup.sh /cdrom/mapping mmap-runner input.txt /tmp/xiri-mmap-shared/ && chmod 555 /tmp/xiri-mmap-shared/*direct-* /tmp/xiri-mmap-shared/mmap-runner && ulimit -c 0',240)
        cmd('uname -v | grep '+shlex.quote(pin['ident']));controls('before')
        cmd('sh /cdrom/run.sh >mmap.log 2>&1',900)
        raw=get('cat mmap.log').decode();(d/'fixtures.log').write_text(raw)
        backing_data=get('(cd /tmp/xiri-mmap-shared && tar cf - *.data)');(d/'backings.tar').write_bytes(backing_data)
        import io,tarfile
        with tarfile.open(fileobj=io.BytesIO(backing_data)) as archive:
            backings={m.name:archive.extractfile(m).read() for m in archive.getmembers()}
        for c in cases:
            for i in c['identities']:
                name=c['name']+'-'+str(i)
                match=re.search(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+r'$',raw,re.M|re.S)
                if not match:raise RuntimeError('missing '+name)
                actual=runtime.observation(match[1])
                record=re.search(r'^STDOUT bytes=256 hex=([0-9a-f]+)$',match[1],re.M)
                data=bytes.fromhex(record[1]) if record else b''
                assert len(data)==256 and actual==dict(normal,stdout=actual['stdout']), (name,actual)
                actual.pop('stdout');actual['stdout_hex']=data.hex()
                assert 'GROUP absent=1' in match[1]
                result['observations'].append(dict(name=name,actual=actual,group_absent=True,backing_hex=backings[name+'.data'].hex()))
        print(str(len(result['observations']))+' mmap executions captured',flush=True)
        cmd('cd /root/irix-desktop');controls('after')
        result['status']='observed-uncompared'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status'] in ['observed','observed-uncompared'] and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
