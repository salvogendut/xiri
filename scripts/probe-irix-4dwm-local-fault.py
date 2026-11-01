#!/usr/bin/env python3
"""Capture the original 4Dwm fault after its GL mmap succeeds."""
import gzip,importlib.util,json,re,shlex,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('wm',ROOT/'scripts/probe-irix-4dwm.py');wm=importlib.util.module_from_spec(s);s.loader.exec_module(wm);probe=wm.probe

def main():
    seed=ROOT/'.work/irix-4dwm/runs/local-ci-_i17e84p';sr=json.loads((seed/'result.json').read_text())
    pin=json.loads((ROOT/'lab/irix-mmap-local/baseline.json').read_text())
    assert sr['status']=='observed' and sr['clean_shutdown'] and sr['pin']==pin
    build=ROOT/'.work/netbsd-irix-mmap-local-build'
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256')]:assert probe.sha256(path)==pin[key]
    d=Path(tempfile.mkdtemp(prefix='local-fault-ci-',dir=ROOT/'.work/irix-4dwm/runs'));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    m=d/'media';m.mkdir()
    sources=['scripts/probe-irix-4dwm-local-fault.py','lab/irix-4dwm/mmap-trace.c','lab/irix-toolchest/fault.c']
    for src in sources[1:]:shutil.copyfile(ROOT/src,m/Path(src).name)
    inherited={'/netbsd':pin['native_kernel_sha256'],'/root/irix-desktop/native-o32':pin['native_o32_sha256'],**sr['staged']}
    (m/'INHERITED').write_text(''.join(f'SHA256 ({p}) = {h}\n' for p,h in inherited.items()))
    (m/'wm.env').write_text('HOME=/tmp/xiri-home\nUSER=xiritest\nLOGNAME=xiritest\nLANG=C\nLC_ALL=C\nPATH=/bin:/usr/bin\n')
    (m/'SHA256').write_text(''.join(f'SHA256 ({p.name}) = {probe.sha256(p)}\n' for p in sorted(m.iterdir())))
    for n in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/n,d/n],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',m])
    config=re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),(ROOT/'lab/indy-netbsd/iris.toml').read_text(),flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode='ci',debugger=False,boot_timeout=600),d,config_text=config)
    result=dict(status='error',clean_shutdown=False,pin=pin,seed=str(seed.relative_to(ROOT)),seed_result_sha256=probe.sha256(seed/'result.json'),sources={p:probe.sha256(ROOT/p) for p in sources},controls=[],cases=[])
    def cmd(c,t=120):
        start=len(lab.serial_text())
        if lab.command(c,t):raise RuntimeError('guest command failed: '+c)
        return lab.serial_text()[start:]
    def get(c):
        raw=cmd('echo HEX_START; { '+c+'; } 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END',240)
        match=re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',raw,re.M)
        if not match:raise RuntimeError('missing transfer')
        return gzip.decompress(bytes.fromhex(match[1]))
    def controls(phase):
        for uid in [0,1234]:
            raw=cmd('./mmap-trace '+str(uid)+' '+str(uid)+' wm.env /root/irix-desktop/native-o32');assert 'END exit=37 signal=0' in raw
            result['controls'].append(dict(phase=phase,uid=uid,kind='native',raw=raw))
        raw=cmd('nm fault | fgrep xiri_fault_site; ./mmap-trace 0 0 wm.env ./fault')
        site=re.search(r'^([0-9a-f]+) T xiri_fault_site$',raw,re.M);pc=re.search(r'phase=fault signal=11 code=1 address=00000000 pc=([0-9a-f]+)',raw)
        assert site and pc and int(site[1],16)==int(pc[1],16) and 'END exit=-1 signal=9' in raw
        result['controls'].append(dict(phase=phase,kind='fault',site=site[1],raw=raw))
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && mkdir -p /tmp/xiri-mmap /tmp/xiri-home && chmod 777 /tmp/xiri-home && cd /tmp/xiri-mmap && cp /cdrom/*.c /cdrom/wm.env . && : >input.txt && chmod 444 input.txt wm.env && cc -O2 -Wall -Wextra -Werror mmap-trace.c -o mmap-trace && cc -O0 -Wall -Wextra -Werror fault.c -o fault && chmod 555 mmap-trace fault && ulimit -c 0',240)
        controls('before')
        for uid in [0,1234]:
            raw=cmd('./mmap-trace --lookups '+str(uid)+' '+str(uid)+' wm.env /emul/irix/usr/bin/X11/4Dwm -display 127.0.0.1:99',240)
            (d/(str(uid)+'.trace')).write_text(raw)
            assert 'LOOKUP name=mmap' in raw and 'STOP phase=fault signal=11' in raw and 'END exit=-1 signal=9' in raw
            result['cases'].append(dict(uid=uid,trace_sha256=probe.sha256(d/(str(uid)+'.trace')),records=re.findall(r'^(?:LOOKUP|LOOKUP_RETURN|STOP|REGS|END) .*$',raw,re.M),stderr=get('cat trace-child.err').decode()))
        controls('after');result['status']='observed'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['cases']),flush=True)
    return 0 if result['status']=='observed' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
