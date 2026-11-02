#!/usr/bin/env python3
"""Qualify the original IRIX shell and its bounded static ELF admission."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import struct
import tarfile
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
WORK = ROOT/'.work/irix-vendor-shell'
GUEST = '/tmp/xiri-vendor-shell'


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/file)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


p = module('probe', 'probe-netbsd.py')
rt = module('runtime', 'probe-irix-runtime.py')


def prepare_reference(manifest):
    lines = ['#!/bin/sh', 'set -u', 'ulimit -c 0', 'cd '+GUEST,
             'mkdir -p outputs cwd/sub cwd/denied', 'chmod 777 outputs',
             'printf TOKEN >cwd/token', 'chmod 644 cwd/token',
             'test -L cwd/link || ln -s sub cwd/link', 'chmod 000 cwd/denied',
             'cp /bin/echo vendor-echo', 'chmod 755 vendor-echo',
             'HOME=/usr/people/xiritest; PATH=/bin:/usr/bin; LANG=C;',
             'XIRI_TEST_ENV="from environment"; export HOME PATH LANG XIRI_TEST_ENV',
             ': >outputs/status.txt']
    def run(name, command):
        lines.extend([command+' >outputs/'+name+'.out 2>outputs/'+name+'.err',
                      'echo '+name+' $? >>outputs/status.txt'])
    for uid in [0, 1234]:
        lines += ['mkdir -p work-'+str(uid), 'chmod 777 work-'+str(uid),
                  "printf 'echo SCRIPT_OK\\n' >work-"+str(uid)+'/shell-script']
        for c in manifest['shell_cases']:
            av = ['../reference-exec', str(uid), '/bin/sh', '-c', c['command'], *c.get('arguments', [])]
            run('shell-'+c['name']+'-'+str(uid), '(cd work-'+str(uid)+'; '+shlex.join(av)+')')
        for c in manifest['process_cases']:
            run('process-'+c['name']+'-'+str(uid), './'+c['name']+' '+str(uid))
        run('static-n32-'+str(uid), './reference-exec '+str(uid)+' ./static-n32')
    lines += ['cd outputs', 'tar cf /tmp/xiri-vendor-shell-results.tar .']
    script = WORK/'reference.sh'; script.write_text('\n'.join(lines)+'\n')
    with tarfile.open(WORK/'reference-inputs.tar', 'w') as tar:
        tar.add(script, arcname='reference.sh')
        for name, info in manifest['files'].items():
            file = WORK/'probes'/name
            assert p.sha256(file) == info['sha256']
            tar.add(file, arcname=name)


def record(data):
    w = list(struct.unpack('>128I', data))
    assert w[0] == 0x58534850 and 8 <= w[6] <= 128
    # IDs differ between machines. Preserve their relationships, all return
    # registers, errno flags, UID/EUID, and the directory token bytes.
    if w[1]:
        sid, pgid = w[8], w[11]
        ids = {sid: 'inherited-sid', pgid: 'inherited-pgid', w[2]: 'self'}
        for i in range(8, w[6], 3):
            if w[i+2] == 0 and w[i] in ids:
                w[i] = ids[w[i]]
        # The inherited session and group may coincide on the reference.
        w[8], w[11] = 'initial-sid', 'initial-pgid'
    return dict(kind=w[1], uid=w[4], euid=w[5], values=w[8:w[6]])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--prepare-reference', action='store_true')
    ap.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    ap.add_argument('--kernel-abi', choices=['lp64', 'o32'], default='lp64')
    args = ap.parse_args()
    fixtures = WORK/'probes'; manifest = json.loads((fixtures/'manifest.json').read_text())
    assert all(p.sha256(ROOT/f) == h for f, h in manifest['sources'].items())
    if args.prepare_reference:
        prepare_reference(manifest); return 0
    with tarfile.open(WORK/'reference-results.tar') as tar:
        oracle = {m.name.removeprefix('./'): tar.extractfile(m).read()
                  for m in tar.getmembers() if m.isfile()}
    statuses = dict(line.split() for line in oracle['status.txt'].decode().splitlines())
    o32 = args.kernel_abi == 'o32'
    build = ROOT/('.work/netbsd-irix-vendor-shell'+('-o32' if o32 else '')+'-clean-build')
    assert not (build/'source-status').read_text().strip()
    assert not (build/'source.patch').read_bytes()
    seed = ROOT/'.work/xiri-image/prepared-seed-20261102-icons'
    base = json.loads((seed/'image-source.json').read_text())
    assert p.sha256(seed/'disk.raw') == base['raw_sha256']
    p.IRIS = ROOT/'.work/target-netbsd64/release/iris'
    p.CI = ROOT/'.work/target-netbsd64/release/iris-ci'
    pin = json.loads((ROOT/'lab/irix-vendor-shell'/
                      ('o32-baseline.json' if o32 else 'baseline.json')).read_text())
    assert (build/'source-revision').read_text().strip() == pin['source_revision']
    for file, key in [(p.IRIS, 'emulator_sha256'), (p.CI, 'ci_client_sha256'),
                      (build/'kernel-media/netbsd', 'native_kernel_sha256'),
                      (build/'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256')]:
        assert p.sha256(file) == pin[key], str(file)
    d = Path(tempfile.mkdtemp(prefix=args.kernel_abi+'-'+args.mode+'-', dir=WORK))
    print('Results: '+str(d), flush=True)
    shutil.copyfile(__file__, d/'harness.py')
    media = d/'media'; media.mkdir()
    for name, info in manifest['files'].items():
        assert p.sha256(fixtures/name) == info['sha256']
        shutil.copy2(fixtures/name, media/name)
    dynamic_dir = ROOT/('.work/irix-o32-runtime' if o32 else '.work/irix-exec-align/probes')
    dynamic = json.loads((dynamic_dir/'manifest.json').read_text())
    if o32:
        dynamic['cases'] = [dict(c, abi='o32') for c in dynamic['cases']]
    for name, info in dynamic['files'].items():
        assert p.sha256(dynamic_dir/name) == info['sha256']
        shutil.copy2(dynamic_dir/name, media/('dyn-'+name))
    for f in ['lab/irix-lp64/runner.c', 'lab/irix-toolchest/session.c']:
        shutil.copyfile(ROOT/f, media/Path(f).name)
    shutil.copyfile(build/'kernel-media/netbsd', media/'netbsd')
    normal = dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stdout='', stderr='')
    cases = {}
    lines = ['#!/bin/sh', 'set -eu', 'ulimit -c 0']
    def run(name, av, expected=None, process=None):
        cases[name] = dict(expected=expected, process=process)
        lines.extend(['echo STARTCASE '+name, shlex.join(av), 'echo ENDCASE '+name])
    for uid in [0, 1234]:
        ids = [str(uid)]*4
        lines += ['cd '+GUEST, 'mkdir work-'+str(uid), 'chmod 777 work-'+str(uid),
                  'cp input.txt home.env work-'+str(uid)+'/',
                  "printf 'echo SCRIPT_OK\\n' >work-"+str(uid)+'/shell-script']
        controls = [('native-o32', [], 'XIRI_ABI_PROBE\n', 37),
                    ('vendor-asa', [], 'XIRI_VENDOR_O32\n', 0)] + ([] if o32 else
                    [('vendor-echo', ['XIRI_VENDOR_N32'], 'XIRI_VENDOR_N32\n', 0)])
        for exe, av, out, status in controls:
            run('control-before-'+exe+'-'+str(uid), ['./runner', './session', *ids, '--',
                'home.env', '/root/irix-desktop/'+exe, *av], dict(normal, exit=status, stdout=out))
        for c in manifest['loader_cases']:
            reject = o32 or c['expect'] == 'reject'
            expected = dict(normal, errno_bytes=4, errno=8, exit=126) if reject else dict(normal, exit=37, stdout='XIRI_STATIC_N32\n')
            run(c['name']+'-'+str(uid), ['./runner', './'+c['name'], *ids], expected)
        for c in manifest['process_cases']:
            if o32 and c['abi'] == 'n32': continue
            name = 'process-'+c['name']+'-'+str(uid)
            assert statuses[name] == '0' and not oracle[name+'.err']
            run(name, ['./runner', './'+c['name'], *ids, '--', 'native'], process=record(oracle[name+'.out']))
        if not o32:
            lines.append('cd work-'+str(uid))
            for c in manifest['shell_cases']:
                name = 'shell-'+c['name']+'-'+str(uid)
                expected = dict(normal, exit=int(statuses[name]), stdout=oracle[name+'.out'].decode(), stderr=oracle[name+'.err'].decode())
                run(name, ['../runner', '../session', *ids, '--', 'home.env', '/emul/irix/bin/sh', '-c', c['command'], *c.get('arguments', [])], expected)
            lines.append('cd ..')
        for abi in (['o32'] if o32 else ['o32', 'n32']):
            target = '/emul/irix/usr/lib/libc.so.1' if abi == 'o32' else '/emul/irix/lib32/libc.so.1'
            lines.append('cp '+target+' saved-libc')
            for c in dynamic['cases']:
                if c['abi'] != abi: continue
                lines += ['cp dyn-'+c['interpreter']+' '+target+'.new', 'chmod 755 '+target+'.new',
                          'mv '+target+'.new '+target]
                reject = c['expect'] == 'reject' or (not o32 and c['expect'] == 'reject-lp64')
                expected = dict(normal, errno_bytes=4, errno=8, exit=126) if reject else dict(normal, exit=37, stdout='XIRI_ABI_PROBE\n')
                run('dynamic-'+c['name']+'-'+str(uid), ['./runner', './dyn-'+c['program'], *ids], expected)
            lines += ['chmod 755 saved-libc', 'mv saved-libc '+target]
        for exe, av, out, status in controls:
            run('control-after-'+exe+'-'+str(uid), ['./runner', './session', *ids, '--',
                'home.env', '/root/irix-desktop/'+exe, *av], dict(normal, exit=status, stdout=out))
    (media/'run.sh').write_text('\n'.join(lines)+'\n')
    (media/'SHA256').write_text(''.join('SHA256 ('+f.name+') = '+p.sha256(f)+'\n' for f in sorted(media.iterdir())))
    p.run(['genisoimage', '-quiet', '-R', '-J', '-o', d/'probe.iso', media])
    for name in ['disk.raw', 'nvram.bin']:
        p.run(['cp', '--reflink=auto', '--sparse=always', seed/name, d/name])
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),
                    (ROOT/'lab/indy-netbsd/iris.toml').read_text(), flags=re.M)
    lab = p.Lab(SimpleNamespace(mode=args.mode, debugger=False, boot_timeout=600), d, config_text=config)
    result = dict(status='error', clean_shutdown=False, mode=args.mode, kernel_abi=args.kernel_abi,
                  base=base, manifest=manifest, dynamic_manifest=dynamic, observations=[],
                  reference_sha256=p.sha256(WORK/'reference-results.tar'),
                  native_kernel_sha256=p.sha256(build/'kernel-media/netbsd'),
                  boot_kernel_sha256=p.sha256(build/'tftp/netbsd-XIRI_INDY'),
                  source_revision=(build/'source-revision').read_text().strip(),
                  source_patch_sha256=p.sha256(build/'source.patch'),
                  source_dirty=False,
                  vendor_shell_sha256=p.sha256(ROOT/'.work/irix-installed-desktop/root/bin/sh'),
                  device_setup_sha256=p.sha256(ROOT/'lab/irix-4dwm/setup-pty.sh'),
                  harness_sha256=p.sha256(Path(__file__)), emulator_sha256=p.sha256(p.IRIS))
    def cmd(command, timeout=180):
        before = len(lab.serial_text())
        assert lab.command(command, timeout) == 0, command
        return lab.serial_text()[before:]
    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && '
            'test "$(sha256 -q /emul/irix/bin/sh)" = '+result['vendor_shell_sha256']+' && '
            'cp netbsd /netbsd && mkdir '+GUEST+' && cp /cdrom/* '+GUEST+'/ && cd '+GUEST+' && '
            'chmod 755 . static-* native-* bad-* o32-* n32-* dyn-* && '
            'cc -O2 -Wall -Wextra -Werror runner.c -o runner && '
            'cc -O2 -Wall -Wextra -Werror session.c -o session && '
            'cp /root/irix-desktop/input.txt . && chmod 644 input.txt && '
            'mknod /emul/irix/dev/null c "$(stat -f %Hr /dev/null)" "$(stat -f %Lr /dev/null)" && '
            'chmod 666 /emul/irix/dev/null && '
            'cp /root/irix-desktop/vendor-echo vendor-echo && chmod 755 vendor-echo && '
            'mkdir -p cwd/sub cwd/denied && printf TOKEN >cwd/token && chmod 644 cwd/token && '
            'ln -s sub cwd/link && chmod 000 cwd/denied && '
            'printf "HOME=/usr/people/xiritest\\nPATH=/bin:/usr/bin\\nLANG=C\\nXIRI_TEST_ENV=from environment\\n" >home.env', 240)
        cmd('sh run.sh >fixtures.log 2>&1', 900)
        text = cmd('echo HEX_START; gzip -c fixtures.log | od -An -v -tx1; echo HEX_END', 240)
        m = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$', text, re.M); assert m
        raw = gzip.decompress(bytes.fromhex(m[1])); (d/'fixtures.log').write_bytes(raw)
        failures = []
        for name, c in cases.items():
            m = re.search(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+'$', raw.decode(), re.M|re.S)
            assert m, name
            actual = rt.observation(m[1]); entry = dict(name=name, actual=actual)
            if c['process'] is not None:
                h = re.search(r'^STDOUT bytes=512 hex=([0-9a-f]+)$', m[1], re.M)
                entry['record'] = record(bytes.fromhex(h[1])) if h else None
                good = dict(actual, stdout='') == normal and entry['record'] == c['process']
            else:
                good = actual == c['expected']
            entry['passed'] = good; result['observations'].append(entry)
            if not good: failures.append(dict(name=name, actual=entry, expected=c))
        result['failures'] = failures
        assert not failures, str(failures)[:5000]
        result['status'] = 'passed'; print(len(cases), 'checks passed', flush=True)
    except Exception as error:
        result['error'] = str(error); raise
    finally:
        lab.close(); result['clean_shutdown'] = lab.clean_shutdown
        (d/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['status'] == 'passed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
