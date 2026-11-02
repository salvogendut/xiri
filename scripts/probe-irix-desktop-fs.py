#!/usr/bin/env python3
"""Qualify desktop link, poll and directory adapters with xstat regression in a disposable guest."""
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


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


probe = module('probe', 'probe-netbsd.py')
runtime = module('runtime', 'probe-irix-runtime.py')
stat_records = module('stat_records', 'irix-xstat-records.py')
link_records = module('link_records', 'irix-lxstat-records.py')
queries = module('queries', 'irix-desktop-query-records.py')
poll_records = module('poll_records', 'irix-poll-records.py')
dirent_records = module('dirent_records', 'irix-dirent-records.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--kernel-abi', choices=['lp64', 'o32'], default='lp64')
    args = parser.parse_args()
    seed = ROOT/'.work/xiri-image/prepared-seed-20261102'
    sr = json.loads((seed/'result.json').read_text())
    provenance = json.loads((seed/'image-source.json').read_text())
    assert sr['status']=='observed' and sr['clean_shutdown']
    assert probe.sha256(seed/'disk.raw') == provenance['raw_sha256']
    o32 = args.kernel_abi == 'o32'
    pin = json.loads((ROOT/'lab/irix-lxstat'/('o32-baseline.json' if o32 else 'baseline.json')).read_text())
    build = ROOT/('.work/netbsd-irix-desktop'+('-o32' if o32 else '')+'-build')
    probe.IRIS = ROOT/'.work/target-netbsd64/release/iris'
    probe.CI = ROOT/'.work/target-netbsd64/release/iris-ci'
    for file, key in [(probe.IRIS, 'emulator_sha256'), (probe.CI, 'ci_client_sha256'),
                      (build/'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256'),
                      (build/'kernel-media/netbsd', 'native_kernel_sha256')]:
        assert probe.sha256(file) == pin[key], str(file)
    runs = ROOT/'.work/irix-desktop-fs/runs'
    runs.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix=args.kernel_abi+'-'+args.mode+'-', dir=runs))
    print('Results: '+str(run.relative_to(ROOT)), flush=True)
    media = run/'media'; media.mkdir()
    for filename, source in [('runner.c', 'lab/irix-lp64/runner.c'),
                             ('session.c', 'lab/irix-toolchest/session.c')]:
        shutil.copyfile(ROOT/source, media/filename)
    shutil.copyfile(build/'kernel-media/netbsd', media/'netbsd')
    suites = {}
    commands = ['#!/bin/sh', 'set -eu', 'umask 022', 'ulimit -c 0']
    for kind in ['lxstat', 'desktop-queries', 'poll', 'dirent', 'xstat']:
        fixtures = ROOT/('.work/irix-'+kind+'/probes')
        manifest = json.loads((fixtures/'manifest.json').read_text())
        oracle = json.loads((ROOT/('lab/irix-'+kind+'/reference.json')).read_text())
        assert manifest['files'] == oracle['files'], kind
        for p, digest in manifest['sources'].items():
            assert probe.sha256(ROOT/p) == digest, p
        checker = {'lxstat':link_records, 'xstat':stat_records, 'desktop-queries':queries,
                   'poll':poll_records, 'dirent':dirent_records}[kind]
        checker.validate_reference(manifest['cases'], oracle['observations'])
        cases = [c for c in manifest['cases'] if not o32 or c['abi']=='o32']
        path = media/kind; path.mkdir()
        for c in cases:
            name = c['name']
            assert probe.sha256(fixtures/name) == manifest['files'][name]['sha256']
            shutil.copyfile(fixtures/name, path/name)
        shutil.copyfile(fixtures/'setup.sh', path/'setup.sh')
        paths = list(dict.fromkeys(c['path'] for c in cases)) if kind in ['lxstat', 'xstat', 'dirent'] else []
        if paths:
            shutil.copyfile(ROOT/('lab/irix-'+kind+'/native-'+('dirent' if kind=='dirent' else 'stat')+'.c'), path/'native-stat.c')
        commands += ['cd /var/tmp/xiri-desktop-fs/'+kind, 'sh setup.sh']
        if paths and kind!='dirent':
            namespace = '/tmp/xiri-'+kind+'-namespace'
            commands += ['mkdir -p /emul/irix'+namespace,
                         'printf "emulation shadow with different metadata\\n" >/emul/irix'+namespace+'/shadow',
                         'chmod 0604 /emul/irix'+namespace+'/shadow',
                         'cc -O2 -Wall -Wextra -Werror native-stat.c -o native-stat']
        if kind=='dirent':
            commands += ['cc -O2 -Wall -Wextra -Werror native-stat.c -o native-stat']
        for uid in [0, 1234]:
            for i, path in enumerate(paths):
                native_path = path.rstrip('/') or path
                if path == '/tmp/xiri-'+kind+'-namespace/shadow':
                    native_path = '/emul/irix'+path
                name = kind+'-'+str(i)+'-'+str(uid)
                commands += ['echo STARTNATIVE '+name,
                             shlex.join(['../runner', './native-stat', *[str(uid)]*4, '--', native_path]),
                             'echo ENDNATIVE '+name]
            for c in cases:
                name = kind+'-'+c['name']+'-'+str(uid)
                commands += ['echo STARTCASE '+name,
                             shlex.join(['../runner', './'+c['name'], *[str(uid)]*4]),
                             'echo ENDCASE '+name]
        suites[kind] = dict(manifest=manifest, oracle=oracle, cases=cases, paths=paths,
                           checker=checker)
    (media/'run.sh').write_text('\n'.join(commands)+'\n')
    (media/'SHA256').write_text(''.join('SHA256 ('+str(p.relative_to(media))+') = '+probe.sha256(p)+'\n'
        for p in sorted(media.rglob('*')) if p.is_file()))
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', run/'probe.iso', media])
    for name in ['disk.raw', 'nvram.bin']:
        probe.run(['cp', '--reflink=auto', '--sparse=always', seed/name, run/name])
    config = (ROOT/'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')), config, flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode=args.mode, debugger=False, boot_timeout=600), run, config_text=config)
    result = dict(status='error', clean_shutdown=False, mode=args.mode, kernel_abi=args.kernel_abi,
                  pin=pin, seed=provenance, suites={}, controls=[], failures=[],
                  sources={str(p.relative_to(ROOT)):probe.sha256(p) for p in [Path(__file__).resolve(),
                      ROOT/'scripts/irix-desktop-query-records.py', ROOT/'scripts/irix-lxstat-records.py',
                      ROOT/'scripts/irix-xstat-records.py', ROOT/'scripts/probe-netbsd.py',
                      ROOT/'scripts/irix-poll-records.py', ROOT/'scripts/irix-dirent-records.py',
                      ROOT/'lab/irix-dirent/native-dirent.c',
                      ROOT/'lab/irix-lp64/runner.c']})

    def command(text, timeout=120):
        before = len(lab.serial_text())
        assert lab.command(text, timeout) == 0, text
        return lab.serial_text()[before:]

    normal = dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stdout='', stderr='')

    def controls(phase):
        command('cd /var/tmp/xiri-desktop-fs')
        for uid in [0, 1234]:
            cases = [('native-o32', [], dict(normal, exit=37, stdout='XIRI_ABI_PROBE\n')),
                     ('vendor-asa', [], dict(normal, stdout='XIRI_VENDOR_O32\n'))]
            if not o32:
                cases.append(('vendor-echo', ['XIRI_VENDOR_N32'], dict(normal, stdout='XIRI_VENDOR_N32\n')))
            for exe, argv, expected in cases:
                text = command(shlex.join(['./runner', './session', *[str(uid)]*4, '--',
                    'home.env', '/root/irix-desktop/'+exe, *argv]))
                actual = runtime.observation(text)
                assert actual == expected, exe
                result['controls'].append(dict(name=phase+'-'+str(uid)+'-'+exe, actual=actual))

    def block(text, kind, name):
        match = re.search('^START'+kind+' '+re.escape(name)+r'\n(.*?)^END'+kind+' '+re.escape(name)+'$', text, re.M|re.S)
        assert match, name
        actual = runtime.observation(match[1])
        assert actual == dict(normal, stdout=actual['stdout']), (name, actual)
        return match[1], actual

    try:
        lab.start()
        command('umask 022; mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && '
            'test "$(sha256 -q /netbsd)" = '+sr['pin']['native_kernel_sha256']+' && '
            'cp netbsd /netbsd && mkdir /var/tmp/xiri-desktop-fs && '
            'cp -R /cdrom/* /var/tmp/xiri-desktop-fs/ && cd /var/tmp/xiri-desktop-fs && '
            'chmod 755 . lxstat desktop-queries poll dirent xstat && '
            'cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=5000 -DRUNNER_TIMING runner.c -o runner && '
            'cc -O2 -Wall -Wextra -Werror session.c -o session && '
            'cp /root/irix-desktop/input.txt . && chmod 644 input.txt && '
            'printf "HOME=/usr/people/xiritest\\n" >home.env && '
            'for d in lxstat desktop-queries poll dirent xstat; do cp input.txt "$d/"; chmod 755 "$d"/*direct-*; done && '
            'uname -v | grep '+shlex.quote(pin['ident']), 240)
        controls('before')
        command('sh run.sh >fixtures.log 2>&1', 1200)
        text = command('echo HEX_START; gzip -c fixtures.log | od -An -v -tx1; echo HEX_END', 240)
        match = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$', text, re.M)
        assert match
        raw = gzip.decompress(bytes.fromhex(match[1]))
        (run/'fixtures.txt').write_bytes(raw); text = raw.decode()
        for kind, suite in suites.items():
            observations, metadata = [], {}
            reference = {o['name']:bytes.fromhex(o['stdout_hex']) for o in suite['oracle']['observations']}
            for uid in [0, 1234]:
                for i, path in enumerate(suite['paths']):
                    name = str(i)+'-'+str(uid)
                    _, actual = block(text, 'NATIVE', kind+'-'+name)
                    metadata[name] = json.loads(actual['stdout'])
                for c in suite['cases']:
                    name = c['name']+'-'+str(uid)
                    body, actual = block(text, 'CASE', kind+'-'+name)
                    match = re.search(r'^STDOUT bytes='+str(c.get('record_bytes',576))+r' hex=([0-9a-f]+)$', body, re.M)
                    assert match, name
                    record = bytes.fromhex(match[1])
                    if kind=='desktop-queries':
                        expected = queries.expected(c, uid, native=True, page_bytes=pin['page_bytes'])
                        comparison = dict(passed=record==expected, expected_hex=expected.hex())
                    elif kind=='poll':
                        expected = poll_records.expected(c, uid, native=True)
                        comparison = dict(passed=record==expected, expected_hex=expected.hex(),
                            original_irix_equal=record==poll_records.expected(c,uid))
                    else:
                        native = metadata[str(suite['paths'].index(c['path']))+'-'+str(uid)]
                        comparison = suite['checker'].compare(c, uid, record, reference[name], native)
                    observations.append(dict(name=name, actual=actual, record_hex=record.hex(), comparison=comparison))
                    if not comparison['passed']:
                        result['failures'].append(kind+'-'+name)
            result['suites'][kind] = dict(observations=observations, native_metadata=metadata,
                reference_sha256=probe.sha256(ROOT/('lab/irix-'+kind+'/reference.json')))
            print(kind+': '+str(len(observations))+' observations', flush=True)
        controls('after')
        result['status'] = 'passed' if not result['failures'] else 'different'
        print(result['status']+': '+str(result['failures']), flush=True)
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        (run/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['status']=='passed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
