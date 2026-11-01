#!/usr/bin/env python3
"""Observe resource-limit translation and bounded executable-loader regressions."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('runtime', ROOT / 'scripts/probe-irix-runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
probe = runtime.probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci','ordinary'], default='ci')
    parser.add_argument('--kernel-abi', choices=['lp64','o32'], default='lp64')
    args = parser.parse_args()
    pin = json.loads((ROOT / 'lab/irix-rlimit' /
                     ('o32-baseline.json' if args.kernel_abi == 'o32' else 'baseline.json')).read_text())
    build = ROOT / ('.work/netbsd-irix-rlimit' + ('-o32' if args.kernel_abi == 'o32' else '') + '-build')
    seed = ROOT / '.work/irix-4dwm/runs/session-ci-xb3cj1si'
    sr = json.loads((seed / 'result.json').read_text())
    old = json.loads((ROOT / 'lab/irix-prda/baseline.json').read_text())
    assert sr['pin'] == old and sr['status'] == 'observed' and sr['clean_shutdown']
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    for path, key in [(probe.IRIS,'emulator_sha256'), (probe.CI,'ci_client_sha256'),
                      (build/'tftp/netbsd-XIRI_INDY','boot_kernel_sha256'),
                      (build/'kernel-media/netbsd','native_kernel_sha256')]:
        assert probe.sha256(path) == pin[key], path
    fixtures = ROOT / '.work/irix-rlimit/probes'
    manifest = json.loads((fixtures / 'manifest.json').read_text())
    loader_root = ROOT / '.work/irix-exec-align/probes'
    loader = json.loads((loader_root / 'manifest.json').read_text())
    for m in [manifest, loader]:
        for path, digest in m['sources'].items():
            assert probe.sha256(ROOT / path) == digest, path
    root = ROOT / '.work/irix-rlimit/runs'
    root.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.kernel_abi+'-'+args.mode+'-', dir=root))
    print('Results: '+str(directory.relative_to(ROOT)), flush=True)
    media = directory / 'media'
    media.mkdir()
    sources = ['scripts/probe-irix-rlimit.py','lab/irix-rlimit/runner.c','lab/irix-rlimit/native-limits.c']
    for source in sources[1:]:
        shutil.copyfile(ROOT / source, media / Path(source).name)
    for source, m in [(fixtures,manifest), (loader_root,loader)]:
        for name, info in m['files'].items():
            assert probe.sha256(source / name) == info['sha256'], name
            shutil.copyfile(source / name, media / name)
    shutil.copyfile(build / 'kernel-media/netbsd', media / 'netbsd')
    inherited = {'/netbsd':old['native_kernel_sha256'],
                 '/root/irix-desktop/native-o32':pin['native_o32_sha256']}
    for entry in pin['runtimes']:
        inherited['/emul/irix'+entry['path']] = entry['sha256']
        src = ROOT / '.work/irix-reference/vendor' / entry['path'].lstrip('/')
        assert probe.sha256(src) == entry['sha256']
        shutil.copyfile(src, media / entry['name'])
    vendor = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    for entry in vendor['candidates']:
        if entry['fixture_name'] in ['vendor-asa','vendor-echo']:
            inherited['/root/irix-desktop/'+entry['fixture_name']] = entry['sha256']
    (media / 'INHERITED').write_text(''.join(f'SHA256 ({p}) = {h}\n' for p,h in inherited.items()))
    cases = [c for c in manifest['cases'] if not c['reference_only'] and
             (args.kernel_abi == 'lp64' or c['abi'] == 'o32')]
    lines = ['#!/bin/sh','set -eu','cd /tmp/xiri-rlimit','ulimit -c 0']
    planned = []
    for c in cases:
        for uid in [0,1234]:
            for policy in ([0,1,2] if c['symbols']['KIND'] == 0 else [0,1]):
                name = c['name']+'-'+str(uid)+'-'+str(policy)
                command = ['./runner','./native-limits',*[str(uid)]*4,'--',str(policy),'./'+c['name']]
                lines += ['echo STARTCASE '+name, shlex.join(command), 'echo ENDCASE '+name]
                planned.append(dict(name=name,case=c['name'],uid=uid,policy=policy))
    (media / 'run.sh').write_text('\n'.join(lines)+'\n')
    loader_cases = loader['cases'] if args.kernel_abi == 'lp64' else []
    lines = ['#!/bin/sh','set -eu','cd /tmp/xiri-rlimit','ulimit -c 0']
    for c in loader_cases:
        target = '/emul/irix/lib32/libc.so.1' if c['abi'] == 'n32' else '/emul/irix/usr/lib/libc.so.1'
        for uid in [0,1234]:
            name = c['name']+'-'+str(uid)
            lines += ['cp '+shlex.quote(c['interpreter'])+' '+target+'.new',
                      'chmod 555 '+target+'.new', 'mv '+target+'.new '+target,
                      'echo STARTCASE '+name,
                      shlex.join(['./runner','./'+c['program'],*[str(uid)]*4]), 'echo ENDCASE '+name]
    for entry in pin['runtimes']:
        target = '/emul/irix'+entry['path']
        lines += ['cp /cdrom/'+entry['name']+' '+target+'.new','chmod 555 '+target+'.new',
                  'mv '+target+'.new '+target]
    (media / 'loader.sh').write_text('\n'.join(lines)+'\n')
    (media / 'SHA256').write_text(''.join(f'SHA256 ({p.name}) = {probe.sha256(p)}\n'
                                        for p in sorted(media.iterdir())))
    for name in ['disk.raw','nvram.bin']:
        probe.run(['cp','--reflink=auto','--sparse=always',seed/name,directory/name], timeout=120)
    probe.run(['genisoimage','-quiet','-R','-J','-o',directory/'probe.iso',media])
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),
                    (ROOT/'lab/indy-netbsd/iris.toml').read_text(), flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode=args.mode,debugger=False,boot_timeout=600),directory,config_text=config)
    result = dict(status='error',clean_shutdown=False,mode=args.mode,kernel_abi=args.kernel_abi,
                  pin=pin,manifest=manifest,loader_manifest=loader,seed=str(seed.relative_to(ROOT)),
                  seed_result_sha256=probe.sha256(seed/'result.json'),planned=planned,
                  sources={p:probe.sha256(ROOT/p) for p in sources},controls=[],observations=[],loader=[])

    def cmd(command, timeout=120):
        before = len(lab.serial_text())
        if lab.command(command, timeout): raise RuntimeError('guest command failed: '+command)
        return lab.serial_text()[before:]

    def get(command):
        out = cmd('echo HEX_START; { '+command+'; } 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END',240)
        match = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$',out,re.M)
        if not match: raise RuntimeError('missing transfer')
        return gzip.decompress(bytes.fromhex(match[1]))

    def decode(raw, name):
        match = re.search(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+r'$',raw,re.M|re.S)
        if not match: raise RuntimeError('missing case '+name)
        actual = runtime.observation(match[1])
        actual.pop('stdout')
        actual['stdout_hex'] = re.search(r'^STDOUT bytes=\d+ hex=([0-9a-f]*)$',match[1],re.M)[1]
        return actual

    def controls(phase):
        for uid in [0,1234]:
            for program, code, output in [('native-o32',37,'XIRI_ABI_PROBE\n'),('vendor-asa',0,'')]:
                actual = runtime.observation(cmd(shlex.join(['./runner','/root/irix-desktop/'+program,*[str(uid)]*4])))
                assert actual == dict(errno_bytes=0,errno=0,exit=code,signal=0,killed=0,stdout=output,stderr=''),actual
                result['controls'].append(dict(phase=phase,uid=uid,program=program,actual=actual))

    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd && mkdir -p /tmp/xiri-rlimit && chmod 755 /tmp/xiri-rlimit && cp /cdrom/* /tmp/xiri-rlimit/ && cd /tmp/xiri-rlimit && chmod 555 o32-* n32-* && : >input.txt && chmod 444 input.txt && ulimit -c 0',240)
        cmd('cc -O2 -Wall -Wextra -Werror runner.c -o runner && cc -O2 -Wall -Wextra -Werror native-limits.c -o native-limits && chmod 555 runner native-limits',180)
        cmd('uname -v | grep '+shlex.quote(pin['ident']))
        controls('before')
        cmd('sh run.sh >fixtures.log 2>&1',600)
        raw = get('cat fixtures.log').decode()
        (directory/'fixtures.log').write_text(raw)
        for c in planned: result['observations'].append(dict(**c,actual=decode(raw,c['name'])))
        print(str(len(planned))+' resource-limit executions captured',flush=True)
        cmd('sh loader.sh >loader.log 2>&1',600)
        raw = get('cat loader.log').decode()
        (directory/'loader.log').write_text(raw)
        for c in loader_cases:
            for uid in [0,1234]:
                result['loader'].append(dict(name=c['name']+'-'+str(uid),uid=uid,
                    expect=c['expect'],actual=decode(raw,c['name']+'-'+str(uid))))
        controls('after')
        result['processes_after'] = get('ps -axo pid,ppid,uid,comm').decode()
        result['status'] = 'observed-uncompared'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return 0 if result['clean_shutdown'] and result['status']=='observed-uncompared' else 1


if __name__ == '__main__':
    raise SystemExit(main())
