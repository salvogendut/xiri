#!/usr/bin/env python3
"""Check high library mappings and lower-window regressions in a disposable guest."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import struct
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent


def module(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT/'scripts'/file)
    m = importlib.util.module_from_spec(s); s.loader.exec_module(m)
    return m


p = module('probe', 'probe-netbsd.py')
rt = module('runtime', 'probe-irix-runtime.py')
qualify = module('qualify', 'qualify-irix-elfmap-relocation.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--kernel-abi', choices=['lp64', 'o32'], default='lp64')
    args = parser.parse_args()
    o32 = args.kernel_abi == 'o32'
    seed = ROOT/'.work/xiri-image/prepared-seed-20261102-icons'
    provenance = json.loads((seed/'image-source.json').read_text())
    assert p.sha256(seed/'disk.raw') == provenance['raw_sha256']
    build = ROOT/('.work/netbsd-irix-elfmap-high'+('-o32' if o32 else '')+'-build')
    pin = json.loads((ROOT/'lab/irix-elfmap-high'/('o32-baseline.json' if o32 else 'baseline.json')).read_text())
    p.IRIS = ROOT/'.work/target-netbsd64/release/iris'
    p.CI = ROOT/'.work/target-netbsd64/release/iris-ci'
    for file, key in [(p.IRIS, 'emulator_sha256'), (p.CI, 'ci_client_sha256'),
                      (build/'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256'),
                      (build/'kernel-media/netbsd', 'native_kernel_sha256')]:
        assert p.sha256(file) == pin[key], str(file)
    fixtures = ROOT/'.work/irix-elfmap-high/probes'
    manifest = json.loads((fixtures/'manifest.json').read_text())
    assert all(p.sha256(ROOT/f)==h for f,h in manifest['sources'].items())
    runs = ROOT/'.work/irix-elfmap-high/runs'; runs.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix=args.kernel_abi+'-'+args.mode+'-', dir=runs))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    media = d/'media'; media.mkdir()
    sources = ['lab/irix-lp64/runner.c', 'lab/irix-toolchest/session.c',
               'scripts/probe-irix-elfmap-high.py', 'scripts/qualify-irix-elfmap-relocation.py',
               'scripts/probe-irix-runtime.py']
    for f in sources[:2]:
        shutil.copyfile(ROOT/f, media/Path(f).name)
    for f, info in manifest['files'].items():
        assert p.sha256(fixtures/f) == info['sha256']
        shutil.copy2(fixtures/f, media/f)
    shutil.copyfile(build/'kernel-media/netbsd', media/'netbsd')
    abis = ['o32'] if o32 else ['o32', 'n32']
    lines = ['#!/bin/sh', 'set -eu', 'ulimit -c 0']
    cases = {}
    for uid in [0, 1234]:
        for abi in abis:
            for c in manifest['cases']:
                name = abi+'-'+c['name']+'-'+str(uid); cases[name] = c
                lines += ['cp '+c['input']+' elfmap-input.new',
                          'chmod '+('666' if c['mode']==0o644 else '777')+' elfmap-input.new',
                          'mv elfmap-input.new elfmap-input', 'echo STARTCASE '+name,
                          shlex.join(['./runner', './elfmap-'+abi, *[str(uid)]*4]),
                          'echo ENDCASE '+name]
    (media/'run.sh').write_text('\n'.join(lines)+'\n')
    (media/'SHA256').write_text(''.join('SHA256 ('+f.name+') = '+p.sha256(f)+'\n'
                                       for f in sorted(media.iterdir())))
    p.run(['genisoimage', '-quiet', '-R', '-J', '-o', d/'probe.iso', media])
    for name in ['disk.raw', 'nvram.bin']:
        p.run(['cp', '--reflink=auto', '--sparse=always', seed/name, d/name])
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),
                    (ROOT/'lab/indy-netbsd/iris.toml').read_text(), flags=re.M)
    lab = p.Lab(SimpleNamespace(mode=args.mode, debugger=False, boot_timeout=600), d, config_text=config)
    result = dict(status='error', clean_shutdown=False, mode=args.mode, kernel_abi=args.kernel_abi,
                  pin=pin, seed=provenance, manifest=manifest, controls=[], observations=[],
                  sources={f:p.sha256(ROOT/f) for f in sources})

    def cmd(text, timeout=180):
        before = len(lab.serial_text())
        assert lab.command(text, timeout)==0, text
        return lab.serial_text()[before:]

    def controls(phase):
        normal = dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stdout='', stderr='')
        for uid in [0, 1234]:
            checks = [('native-o32', [], dict(normal, exit=37, stdout='XIRI_ABI_PROBE\n')),
                      ('vendor-asa', [], dict(normal, stdout='XIRI_VENDOR_O32\n'))]
            if not o32:
                checks.append(('vendor-echo', ['XIRI_VENDOR_N32'], dict(normal, stdout='XIRI_VENDOR_N32\n')))
            for exe, av, expected in checks:
                actual = rt.observation(cmd(shlex.join(['./runner', './session', *[str(uid)]*4,
                    '--', 'home.env', '/root/irix-desktop/'+exe, *av])))
                assert actual == expected, (exe, actual)
                result['controls'].append(dict(phase=phase, uid=uid, name=exe, actual=actual))

    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && '
            'cp netbsd /netbsd && mkdir /var/tmp/xiri-elfmap-high && '
            'cp /cdrom/* /var/tmp/xiri-elfmap-high/ && cd /var/tmp/xiri-elfmap-high && '
            'chmod 755 . elfmap-* && cc -O2 -Wall -Wextra -Werror runner.c -o runner && '
            'cc -O2 -Wall -Wextra -Werror session.c -o session && '
            'cp /root/irix-desktop/input.txt . && chmod 644 input.txt && '
            'printf "HOME=/usr/people/xiritest\\n" >home.env && '
            'uname -v | grep '+shlex.quote(pin['ident']), 240)
        controls('before')
        cmd('sh run.sh >fixtures.log 2>&1', 900)
        text = cmd('echo HEX_START; gzip -c fixtures.log | od -An -v -tx1; echo HEX_END', 240)
        m = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$', text, re.M); assert m
        raw = gzip.decompress(bytes.fromhex(m[1])); (d/'fixtures.log').write_bytes(raw)
        for name, c in cases.items():
            m = re.search(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+'$', raw.decode(), re.M|re.S)
            assert m, name
            actual = rt.observation(m[1]); sig = c['netbsd']['signal']
            assert actual['errno_bytes']==0 and actual['errno']==0 and actual['exit']==(-1 if sig else 0) and actual['signal']==sig and not actual['killed'] and not actual['stderr'], (name, actual)
            rec = re.search(r'^STDOUT bytes=48 hex=([0-9a-f]+)$', m[1], re.M); assert rec, name
            record = rt.elfmap_record(bytes.fromhex(rec[1]))
            data = (fixtures/c['input']).read_bytes()
            layout = [struct.unpack_from('>8I', data, 52+i*32) for i in range(2)]
            # Reuse the relocation assertions for a pre-existing stack
            # reservation, without asking the fixture to overwrite it.
            expected_case = dict(c, block=layout[0][2]) if c.get('native_collision') else c
            qualify.expected(expected_case, record, layout)
            result['observations'].append(dict(name=name, actual=actual, record=record, record_hex=rec[1]))
        controls('after')
        result['status'] = 'passed'
        print(len(cases), 'mapping checks passed', flush=True)
    except Exception as e:
        result['error'] = str(e)
        raise
    finally:
        lab.close(); result['clean_shutdown'] = lab.clean_shutdown
        (d/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['status']=='passed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
