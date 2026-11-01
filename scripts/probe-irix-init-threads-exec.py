#!/usr/bin/env python3
"""Check initialized foreign-to-native exec using stopped qualification seeds."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import struct
import tempfile
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parent.parent
spec=importlib.util.spec_from_file_location('suite',ROOT/'scripts/probe-irix-init-threads.py')
suite=importlib.util.module_from_spec(spec);spec.loader.exec_module(suite)
probe=suite.probe

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed-directory',type=Path,required=True)
    a=p.parse_args();seed=a.seed_directory.resolve()
    sr=json.loads((seed/'result.json').read_text())
    assert sr['status']=='observed-uncompared' and sr['clean_shutdown'] and not sr['smoke']
    abi=sr['kernel_abi'];pin=sr['pin']
    assert pin==json.loads((ROOT/'lab/irix-init-threads'/('o32-baseline.json' if abi=='o32' else 'baseline.json')).read_text())
    build=ROOT/('.work/netbsd-irix-init-threads'+('-o32' if abi=='o32' else '')+'-build')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    assert probe.sha256(probe.IRIS)==pin['emulator_sha256'] and probe.sha256(build/'tftp/netbsd-XIRI_INDY')==pin['boot_kernel_sha256']
    out=ROOT/'.work/irix-init-threads/exec-runs';out.mkdir(parents=True,exist_ok=True)
    d=Path(tempfile.mkdtemp(prefix=abi+'-',dir=out));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    media=d/'media';media.mkdir()
    sources=['scripts/probe-irix-init-threads-exec.py','lab/irix-init-threads/exec-launch.c','lab/irix-init-threads/after-init.c','lab/irix-lp64/runner.c']
    for source in sources[1:]:shutil.copyfile(ROOT/source,media/Path(source).name)
    cases=[c for c in sr['manifest']['cases'] if c['symbols']['KIND']==4 and (abi=='lp64' or c['abi']=='o32')]
    for c in cases:
        fixture=seed/'media'/c['name']
        assert probe.sha256(fixture)==sr['manifest']['files'][c['name']]['sha256']
        shutil.copyfile(fixture,media/c['name'])
    (media/'SHA256').write_text(''.join(f'SHA256 ({p.name}) = {probe.sha256(p)}\n' for p in media.iterdir()))
    (media/'INHERITED').write_text(f"SHA256 (/netbsd) = {pin['native_kernel_sha256']}\n")
    for name in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/name,d/name],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',media])
    config=re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),(ROOT/'lab/indy-netbsd/iris.toml').read_text(),flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode='ci',debugger=False,boot_timeout=600),d,config_text=config)
    result=dict(status='error',clean_shutdown=False,pin=pin,kernel_abi=abi,seed=str(seed.relative_to(ROOT)),
        seed_result_sha256=probe.sha256(seed/'result.json'),sources={s:probe.sha256(ROOT/s) for s in sources},cases=[])
    def cmd(command,timeout=120):
        before=len(lab.serial_text())
        if lab.command(command,timeout):raise RuntimeError('guest command failed: '+command)
        return lab.serial_text()[before:]
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && mkdir -p /tmp/xiri-shell && cd /tmp/xiri-shell && cp /cdrom/*.c /cdrom/*direct-exec . && chmod 555 *direct-exec && : >input.txt && chmod 444 input.txt && ulimit -c 0',240)
        cmd('cc -O2 -Wall -Wextra -Werror runner.c -o runner && chmod 555 runner && cc -O2 -Wall -Wextra -Werror exec-launch.c -o exec-launch && cc -O2 -Wall -Wextra -Werror after-init.c -o after-init && chmod 555 exec-launch after-init',240)
        for case in cases:
            for uid in [0,1234]:
                raw=cmd(shlex.join(['./runner','./exec-launch',*[str(uid)]*4,'--','./'+case['name']]))
                observed=suite.r.runtime.observation(raw)
                data=bytes.fromhex(re.search(r'^STDOUT bytes=\d+ hex=([0-9a-f]*)$',raw,re.M)[1])
                assert observed['errno_bytes']==observed['errno']==observed['exit']==observed['signal']==observed['killed']==0 and not observed['stderr'],observed
                assert len(data)>768
                rows=[struct.unpack_from('>96I',data,i*384) for i in range(2)]
                for i,w in enumerate(rows):
                    assert w[:3]==(0x58505449,4,i) and w[5:9]==(uid,)*4
                    assert w[18:22]==(0x8000,0,0,0) and w[32]==w[3]
                    assert w[59:62]==((1,0,0x8000) if i else (0,0,0))
                assert rows[1][9:12]==(0,0xfeedface,0)
                text=data[768:].decode()
                assert text==f'NATIVE_AFTER_INIT uid={uid} mask=30000000,00000001,00000000,00000000 prda_absent=1 fork=37\n',text
                observed.pop('stdout');observed['stdout_hex']=data.hex()
                result['cases'].append(dict(name=case['name'],uid=uid,actual=observed,native=text))
        result['status']='passed'
    except Exception as error:
        result['error']=str(error);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown
        (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(str(len(result['cases']))+' initialized native-exec controls passed',flush=True)
    return 0 if result['status']=='passed' and result['clean_shutdown'] else 1

if __name__=='__main__':raise SystemExit(main())
