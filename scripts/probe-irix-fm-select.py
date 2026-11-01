#!/usr/bin/env python3
"""Capture the first file-manager select EINVAL and its actual timeval."""
import argparse,gzip,importlib.util,json,re,shlex,shutil,tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent
s=importlib.util.spec_from_file_location('wm',ROOT/'scripts/probe-irix-4dwm.py');wm=importlib.util.module_from_spec(s);s.loader.exec_module(wm);probe=wm.probe

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--seed-directory',type=Path,required=True);a=p.parse_args()
    seed=a.seed_directory.resolve();sr=json.loads((seed/'result.json').read_text())
    pin=json.loads((ROOT/'lab/irix-pipe/baseline.json').read_text())
    assert sr['status']=='observed' and sr['clean_shutdown'] and sr['pin']==pin
    build=ROOT/'.work/netbsd-irix-pipe-build'
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256')]:assert probe.sha256(path)==pin[key]
    d=Path(tempfile.mkdtemp(prefix='select-ci-',dir=ROOT/'.work/irix-desktop-pipe/runs'));print('Results: '+str(d.relative_to(ROOT)),flush=True)
    m=d/'media';m.mkdir()
    sources=['scripts/probe-irix-fm-select.py','lab/irix-pipe/select-trace.c','lab/irix-toolchest/fault.c']
    for src in sources[1:]:shutil.copyfile(ROOT/src,m/Path(src).name)
    inherited={'/netbsd':pin['native_kernel_sha256'],'/root/irix-desktop/native-o32':pin['native_o32_sha256'],**sr['staged']}
    fonts=json.loads((ROOT/'lab/irix-x11-fonts/manifest.json').read_text())
    staged_fonts={}
    for path,info in fonts['files'].items():
        if '/fonts/' in path:
            src=ROOT/'.work/irix-x11-fonts/root'/path.lstrip('/')
            assert probe.sha256(src)==info['sha256']
            shutil.copyfile(src,m/Path(path).name)
            staged_fonts['/tmp/irix-screen-fonts/'+Path(path).name]=info['sha256']
    (m/'FONTS').write_text(''.join(f'SHA256 ({p}) = {h}\n' for p,h in staged_fonts.items()))
    (m/'INHERITED').write_text(''.join(f'SHA256 ({p}) = {h}\n' for p,h in inherited.items()))
    (m/'wm.env').write_text('HOME=/tmp/xiri-home\nUSER=xiritest\nLOGNAME=xiritest\nLANG=C\nLC_ALL=C\nPATH=/bin:/usr/bin:/usr/X11R7/bin:/emul/irix/usr/sbin\nDISPLAY=127.0.0.1:98\n')
    (m/'SHA256').write_text(''.join(f'SHA256 ({p.name}) = {probe.sha256(p)}\n' for p in sorted(m.iterdir())))
    for n in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/n,d/n],timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',d/'probe.iso',m])
    config=re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),(ROOT/'lab/indy-netbsd/iris.toml').read_text(),flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode='ci',debugger=False,boot_timeout=600),d,config_text=config)
    result=dict(status='error',clean_shutdown=False,pin=pin,seed=str(seed.relative_to(ROOT)),seed_result_sha256=probe.sha256(seed/'result.json'),sources={p:probe.sha256(ROOT/p) for p in sources},fonts=staged_fonts,controls=[],cases=[])
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
            raw=cmd('./fault-tracer '+str(uid)+' '+str(uid)+' wm.env ./native-control-o32');assert 'END exit=37 signal=0' in raw
            result['controls'].append(dict(phase=phase,uid=uid,kind='native',raw=raw))
        raw=cmd('nm fault | fgrep xiri_fault_site; ./fault-tracer 0 0 wm.env ./fault')
        site=re.search(r'^([0-9a-f]+) T xiri_fault_site$',raw,re.M);pc=re.search(r'phase=fault signal=11 code=1 address=00000000 pc=([0-9a-f]+)',raw)
        assert site and pc and int(site[1],16)==int(pc[1],16) and 'END exit=-1 signal=9' in raw
        result['controls'].append(dict(phase=phase,kind='fault',site=site[1],raw=raw))
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && mkdir -p /tmp/xiri-mmap /tmp/xiri-home && chmod 700 /tmp/xiri-home && chown 1234:1234 /tmp/xiri-home && cd /tmp/xiri-mmap && cp /cdrom/*.c /cdrom/wm.env . && : >input.txt && chmod 444 input.txt wm.env && cc -O2 -Wall -Wextra -Werror select-trace.c -o fault-tracer && cc -O0 -Wall -Wextra -Werror fault.c -o fault && chmod 555 fault-tracer fault && install -m 555 /root/irix-desktop/native-o32 native-control-o32 && install -d -m 755 /tmp/irix-screen-fonts && install -m 444 /cdrom/*.pcf* /tmp/irix-screen-fonts/ && /usr/X11R7/bin/mkfontdir /tmp/irix-screen-fonts && sha256 -c /cdrom/FONTS && ulimit -c 0',240)
        cmd('export PATH=/usr/X11R7/bin:$PATH; Xvfb :98 -screen 0 1024x768x24 -ac -noreset >xvfb.log 2>&1 & xpid=$!; sleep 3; xdpyinfo -display 127.0.0.1:98 >/dev/null && xset -display 127.0.0.1:98 +fp /tmp/irix-screen-fonts && xset -display 127.0.0.1:98 fp rehash')
        controls('before')
        for uid in [1234]:
            for component,arg in [('fm-background','-b')]:
                name=str(uid)+'-'+component
                result['tracer_rc'] = lab.command('ktrace -i -t usn -f fault.ktrace ./fault-tracer --lookups '+str(uid)+' '+str(uid)+' wm.env /emul/irix/usr/sbin/fm '+arg+' >fault.log 2>&1',180)
                raw=get('cat fault.log').decode();(d/(name+'.trace')).write_text(raw)
                cmd('kdump -x -f fault.ktrace >fault.dump; { head -n 4000 fault.dump; tail -n 4000 fault.dump; } >fault.capture',240)
                (d/(name+'.kdump')).write_bytes(get('cat fault.capture'))
                stop=re.search(r'STOP phase=target signal=(\d+) code=(\d+) address=([0-9a-f]+) pc=([0-9a-f]+)',raw)
                assert stop and 'TARGET select-einval' in raw and 'END exit=-1 signal=9' in raw
                result['cases'].append(dict(name=name,uid=uid,component=component,signal=int(stop[1]),code=int(stop[2]),address=hex(int(stop[3],16)),pc=hex(int(stop[4],16)),trace_sha256=probe.sha256(d/(name+'.trace')),ktrace_sha256=probe.sha256(d/(name+'.kdump')),stderr=get('cat trace-child.err').decode()))
                cmd("pkill -KILL -U 1234 || true; sleep 1; test $(ps -axo uid | awk '$1 == 1234 { n++ } END { print n+0 }') -eq 0")
                result['cases'][-1]['reserved_uid_absent'] = True
                print(json.dumps(result['cases'][-1]),flush=True)
        controls('after');cmd('xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"');result['native_x11_after']=True;result['status']='observed'
    except Exception as e:result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['cases']),flush=True)
    return 0 if result['status']=='observed' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
