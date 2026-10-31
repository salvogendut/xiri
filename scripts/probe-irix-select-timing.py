#!/usr/bin/env python3
"""Time the foreign select entry/return records, excluding launch and drain."""
import argparse,gzip,importlib.util,json,re,shlex,shutil,struct,tempfile
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent.parent

def module(name,filename):
    s=importlib.util.spec_from_file_location(name,ROOT/'scripts'/filename)
    m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
probe=module('probe','probe-netbsd.py')
runtime=module('runtime','probe-irix-runtime.py')

def select_interval(raw):
    # The pinned LP64 kernel's DWARF confirms the version-2 header layout.
    # o32 kdump reads the high half of the 64-bit big-endian tv_nsec as zero.
    # Decode both timestamp words explicitly; never use that displayed value.
    events=[];offset=0
    while offset<len(raw):
        if len(raw)-offset<56:raise RuntimeError('short LP64 trace header')
        length,version,kind,pid=struct.unpack_from('>iHHi',raw,offset)
        sec,nsec=struct.unpack_from('>qq',raw,offset+32)
        lwp=struct.unpack_from('>i',raw,offset+48)[0]
        if version!=2 or not 0<=length<=1048576 or not 0<=nsec<1000000000 or offset+56+length>len(raw):
            raise RuntimeError('invalid LP64 version-2 trace record')
        payload=raw[offset+56:offset+56+length];offset+=56+length
        if kind!=8:continue
        if len(payload)<20:raise RuntimeError('short user trace record')
        label=payload[:20].split(b'\0',1)[0].decode('ascii')
        if label not in ['irix_o32','irix_ret']:continue
        record=payload[20:].decode('ascii')
        fields={k:int(v,0) for k,v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)',record)}
        if fields['syscall']==1100 or (label=='irix_o32' and fields['syscall']==1000 and fields.get('a0')==1100):
            events.append({'pid':pid,'lwp':lwp,'ns':sec*1000000000+nsec,'kind':label,'record':record})
    if len(events)!=2 or [e['kind'] for e in events]!=['irix_o32','irix_ret'] or any(events[0][k]!=events[1][k] for k in ['pid','lwp']):
        raise RuntimeError('need one paired select entry/return')
    return events[1]['ns']-events[0]['ns'],events

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--seed-directory',type=Path,required=True)
    args=p.parse_args();seed=args.seed_directory.resolve();sr=json.loads((seed/'result.json').read_text())
    pin=json.loads((ROOT/'lab/irix-select/baseline.json').read_text())
    if not (sr['status']=='passed' and sr['clean_shutdown'] and sr['kernel_abi']=='lp64' and sr.get('kernel_checkpoint')=='select' and sr['pin']==pin):
        p.error('need a clean passed LP64 transport regression on the select kernel')
    probe.IRIS=ROOT/'.work/target-netbsd64/release/iris';probe.CI=ROOT/'.work/target-netbsd64/release/iris-ci'
    build=ROOT/'.work/netbsd-irix-select-build'
    for path,key in [(probe.IRIS,'emulator_sha256'),(probe.CI,'ci_client_sha256'),(build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256')]:
        if probe.sha256(path)!=pin[key]:p.error('changed input: '+str(path))
    manifest=json.loads((ROOT/'.work/irix-select/probes/manifest.json').read_text())
    oracle=json.loads((ROOT/'lab/irix-select/reference.json').read_text())
    if manifest['files']!=oracle['files']:p.error('fixture/oracle mismatch')
    for path,h in manifest['sources'].items():
        if probe.sha256(ROOT/path)!=h:p.error('stale fixture source: '+path)
    suffixes=['socket-delayed-data','socket-delayed-eof','socket-null-time','socket-timeout','timeout','read','nfds-0']
    cases=[c for c in manifest['cases'] if c['name'].split('direct-',1)[1] in suffixes]
    if len(cases)!=28:raise RuntimeError('unexpected timing matrix')
    parent=ROOT/'.work/irix-select/timing-runs';parent.mkdir(parents=True,exist_ok=True)
    directory=Path(tempfile.mkdtemp(prefix='lp64-ci-',dir=parent));print('Results: '+str(directory),flush=True)
    media=directory/'media';media.mkdir()
    for n in ['disk.raw','nvram.bin']:probe.run(['cp','--reflink=auto','--sparse=always',seed/n,directory/n],timeout=120)
    for c in cases:
        n=c['name'];src=ROOT/'.work/irix-select/probes'/n
        if probe.sha256(src)!=manifest['files'][n]['sha256']:p.error('changed fixture '+n)
        shutil.copyfile(src,media/n)
    shutil.copyfile(ROOT/'lab/irix-select/peer.c',media/'select-peer.c')
    shutil.copyfile(ROOT/'lab/irix-lp64/runner.c',media/'select-runner.c')
    (media/'SHA256').write_text(''.join(f'SHA256 ({f.name}) = {probe.sha256(f)}\n' for f in sorted(media.iterdir())))
    (media/'INHERITED').write_text(f'SHA256 (/netbsd) = {pin["native_kernel_sha256"]}\nSHA256 (/root/irix-desktop/native-o32) = {pin["native_o32_sha256"]}\n')
    probe.run(['genisoimage','-quiet','-R','-J','-o',directory/'probe.iso',media])
    config=(ROOT/'lab/indy-netbsd/iris.toml').read_text();config=re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),config,flags=re.M)
    lab=probe.Lab(SimpleNamespace(mode='ci',debugger=False,boot_timeout=300),directory,config_text=config)
    sources=['scripts/probe-irix-select-timing.py','scripts/probe-netbsd.py','scripts/probe-irix-runtime.py','lab/irix-lp64/runner.c','lab/irix-select/peer.c']
    result={'status':'error','clean_shutdown':False,'pin':pin,'seed':str(seed.relative_to(ROOT)),'seed_result_sha256':probe.sha256(seed/'result.json'),'reference_sha256':probe.sha256(ROOT/'lab/irix-select/reference.json'),'sources':{n:probe.sha256(ROOT/n) for n in sources},'observations':[],'controls':[]}
    def command(cmd,timeout=90):
        before=len(lab.serial_text());rc=lab.command(cmd,timeout);text=lab.serial_text()[before:]
        if rc:raise RuntimeError('guest command failed: '+cmd)
        return text
    def download(cmd):
        text=command('echo HEX_START; '+cmd+' 2>timing-transfer.err | gzip -c | od -An -v -tx1; echo HEX_END')
        m=re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',text,re.M)
        if not m:raise RuntimeError('missing compressed payload')
        return gzip.decompress(bytes.fromhex(m[1]))
    normal=dict(errno_bytes=0,errno=0,exit=0,signal=0,killed=0,stdout='',stderr='')
    def control():
        actual=runtime.observation(command('./select-runner ./native-o32'))
        if actual!=dict(normal,exit=37,stdout='XIRI_ABI_PROBE\n'):raise RuntimeError('native control failed')
        result['controls'].append(actual)
    try:
        lab.start()
        command('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && '
                'cd /root/irix-desktop && cp /cdrom/*direct-* /cdrom/*.c . && chmod 755 *direct-* && chmod 644 input.txt && '
                'cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=5000 -DRUNNER_TIMING select-runner.c -o select-runner && '
                'cc -O2 -Wall -Wextra -Werror select-peer.c -o select-peer && ulimit -c 0 && uname -v | grep '+shlex.quote(pin['ident']),180)
        control()
        count=sum(c['symbols']['SOCKET'] for c in cases)
        command(f'./select-peer {count} >select-peer.out 2>select-peer.err & peer=$!; sleep 1; grep RDY select-peer.out')
        expected={o['name']:o['stdout_hex'] for o in oracle['observations']}
        for c in cases:
            name=c['name'];text=command('ktrace -i -t u -f timing.ktrace ./select-runner ./'+name)
            actual=runtime.observation(text);record=re.search(r'^STDOUT bytes=512 hex=([0-9a-f]+)$',text,re.M)
            if not record or record[1]!=expected[name] or actual!=dict(normal,stdout=actual['stdout']):raise RuntimeError('guarded result failed: '+name)
            raw=download('cat timing.ktrace');(directory/(name+'.ktrace')).write_bytes(raw)
            ns,events=select_interval(raw)
            minimum=150000000 if any(s in name for s in ['delayed-data','delayed-eof','null-time']) else 90000000 if name.endswith('timeout') else 0
            passed=ns>=minimum
            result['observations'].append({'name':name,'select_duration_ns':ns,'minimum_ns':minimum,'events':events,'record_hex':record[1],'passed':passed})
            print(name+': select '+str(ns/1000000)+' ms',flush=True)
            if not passed:raise RuntimeError('select returned too early: '+name)
        command('wait "$peer" && test ! -s select-peer.err')
        peer=download('cat select-peer.out');expected_peer=b'RDY\n'+b''.join(struct.pack('>II',c['symbols']['CASE'],c['symbols']['MODE']) for c in cases if c['symbols']['SOCKET'])
        if peer!=expected_peer:raise RuntimeError('peer records differ')
        result['peer_stdout_hex']=peer.hex();control();result['status']='passed'
    except Exception as e:
        result['error']=str(e);raise
    finally:
        lab.close();result['clean_shutdown']=lab.clean_shutdown;(directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['status']=='passed' and result['clean_shutdown'] else 1
if __name__=='__main__':raise SystemExit(main())
