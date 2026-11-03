#!/usr/bin/env python3
"""Replay measured signal and sproc cases with the boot-loaded IRIX module."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import tempfile
from types import SimpleNamespace

from xiri_lab import Guest, ROOT, load_probe, sha256, source_hashes


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path, required=True)
    parser.add_argument('--build', type=Path, default=ROOT/'.work/netbsd-module-build')
    args = parser.parse_args()
    seed, build = args.seed.resolve(), args.build.resolve()
    previous = json.loads((seed/'result.json').read_text())
    assert previous['status'] == 'passed' and previous['clean_shutdown']
    manifest = json.loads((build/'module.json').read_text())
    assert manifest['artifacts'] == previous['build']['artifacts']
    p = load_probe()
    image = json.loads((ROOT/'lab/irix-installed-desktop/image.json').read_text())
    p.IRIS, p.CI = (ROOT/image['bundle']/'emulator'/name for name in ('iris', 'iris-ci'))
    for name, path in [('iris', p.IRIS), ('iris-ci', p.CI)]:
        assert sha256(path) == image['emulator_files']['emulator/'+name]
    runtime = module('runtime', 'probe-irix-runtime.py')
    signal = module('signal_check', 'qualify-irix-signal.py')
    sproc = module('sproc_check', 'qualify-irix-sproc-kernel.py')
    recvmsg = module('recvmsg_check', 'irix-recvmsg-records.py')
    d = Path(tempfile.mkdtemp(prefix='regressions-', dir=ROOT/'.work/irix-module/runs'))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    media = d/'media'; media.mkdir()
    suites = {}
    variants = {
        'signal': {'action', 'deliver-legacy', 'deliver-siginfo', 'child-reap', 'fpu-legacy', 'fpu-siginfo'},
        'sproc': {'unblock', 'exec-release', 'new-mapping', 'local', 'short-stack', 'bad-entry'},
        'recvmsg': {'recvmsg-length-0', 'recvmsg-length-1', 'recvmsg-length-3', 'recvmsg-length-16',
                    'recvmsg-two', 'recvmsg-partial-fault', 'recvmsg-eof', 'recvmsg-peek-short',
                    'recvmsg-nonblock-empty'},
    }
    lines = ['#!/bin/sh', 'set -eu', 'ulimit -c 0']
    for suite, names in variants.items():
        fixtures = ROOT/('.work/irix-signal-v2/probes' if suite == 'signal' else '.work/irix-'+suite+'/probes')
        record = json.loads((fixtures/'manifest.json').read_text())
        for path, digest in record['sources'].items():
            assert sha256(ROOT/path) == digest, path
        cases = [c for c in record['cases'] if c['name'].split('-', 2)[2] in names]
        assert len(cases) == (36 if suite == 'recvmsg' else 24)
        if suite == 'recvmsg':
            record['identities'] = [[0]*4, [1234]*4]
        dest = media/suite; dest.mkdir()
        for case in cases:
            name = case['name']
            assert sha256(fixtures/name) == record['files'][name]['sha256']
            shutil.copyfile(fixtures/name, dest/name)
        suites[suite] = dict(manifest=record, cases=cases)
        lines += ['cd /tmp/xiri-module-'+suite]
        if suite == 'recvmsg':
            lines += ['./receive '+str(len(cases)*2)+' >receive.log 2>receive.err & peer=$!',
                      'sleep 1', 'grep RDY receive.log']
        for case in cases:
            for ids in record['identities']:
                name = suite+'-'+case['name']+'-'+str(ids[0])
                lines += ['echo STARTCASE '+name,
                          '(ulimit -n 32; '+shlex.join(['./runner', './'+case['name'], *map(str, ids)])+')',
                          'echo ENDCASE '+name]
        if suite == 'recvmsg':
            lines += ['wait "$peer"', 'test ! -s receive.err', 'echo RECEIVE_OK']
    lines += ['echo MODULE_REGRESSIONS_DONE']
    (media/'run.sh').write_text('\n'.join(lines)+'\n')
    shutil.copyfile(ROOT/'lab/irix-process/runner.c', media/'runner.c')
    shutil.copyfile(ROOT/'lab/irix-signal/native-signals.c', media/'native-signals.c')
    shutil.copyfile(ROOT/'lab/irix-time/native-control.c', media/'native-control.c')
    shutil.copyfile(ROOT/'lab/irix-recvmsg/receive.c', media/'receive.c')
    (media/'SHA256').write_text(''.join(f'SHA256 ({f.relative_to(media)}) = {sha256(f)}\n'
                                      for f in sorted(media.rglob('*')) if f.is_file()))
    p.run(['genisoimage', '-quiet', '-R', '-J', '-o', d/'probe.iso', media])
    before = sha256(seed/'disk.raw')
    for name in ('disk.raw', 'nvram.bin'):
        p.run(['cp', '--reflink=auto', '--sparse=always', seed/name, d/name])
    assert sha256(d/'disk.raw') == before
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(str(build/'tftp')),
                    (ROOT/'lab/indy-netbsd/iris.toml').read_text(), flags=re.M)
    lab = p.Lab(SimpleNamespace(mode='ordinary', debugger=False, boot_timeout=600), d, config_text=config)
    guest = Guest(lab)
    cmd, get = guest.command, guest.read_text
    r = dict(status='error', clean_shutdown=False, build=manifest, suites=suites,
             seed=str(seed.relative_to(ROOT)), seed_sha256=before,
             seed_result_sha256=sha256(seed/'result.json'), observations=[], controls=[],
             sources={**source_hashes(), **{name:sha256(ROOT/name) for name in [
                 'scripts/probe-irix-module-regressions.py', 'scripts/qualify-irix-signal.py',
                 'scripts/qualify-irix-signal-reference-v2.py', 'scripts/qualify-irix-sproc-kernel.py',
                 'scripts/qualify-irix-sproc.py', 'scripts/probe-irix-runtime.py',
                 'scripts/irix-recvmsg-records.py', 'lab/irix-recvmsg/reference.json', 'lab/irix-recvmsg/receive.c',
                 'lab/irix-process/runner.c', 'lab/irix-signal/native-signals.c',
                 'lab/irix-time/native-control.c']}})
    try:
        lab.start()
        cmd("modstat | grep -E '^compat_irix_o32[[:space:]]+exec[[:space:]]+filesys[[:space:]]'")
        cmd('test "$(sysctl -n kern.securelevel)" = 1 && mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 >/root/module-regressions-media.log')
        cmd('mkdir -p /root/module-regressions && cp *.c /root/module-regressions/ && cd /root/module-regressions && cc -O2 -Wall -Wextra -Werror runner.c -o runner && cc -O2 -Wall -Wextra -Werror native-signals.c -o native-signals && cc -O2 -Wall -Wextra -Werror native-control.c -o native-control', 240)
        cmd('cc -O2 -Wall -Wextra -Werror receive.c -o receive', 120)
        for suite in suites:
            cmd('mkdir -p /tmp/xiri-module-'+suite+' && cp /cdrom/'+suite+'/* runner native-signals native-control /tmp/xiri-module-'+suite+'/ && chmod 555 /tmp/xiri-module-'+suite+'/* && touch /tmp/xiri-module-'+suite+'/input.txt && chmod 444 /tmp/xiri-module-'+suite+'/input.txt')
        cmd('cp receive /tmp/xiri-module-recvmsg/ && chmod 555 /tmp/xiri-module-recvmsg/receive')
        cmd('sh /cdrom/run.sh >fixtures.log 2>&1', 900)
        log = get('cat fixtures.log')
        (d/'fixtures.log').write_text(log)
        assert 'MODULE_REGRESSIONS_DONE' in log
        for suite, record in suites.items():
            for case in record['cases']:
                for ids in record['manifest']['identities']:
                    name = suite+'-'+case['name']+'-'+str(ids[0])
                    raw, = re.findall(r'^STARTCASE '+name+r'\n(.*?)^ENDCASE '+name+r'$', log, re.M|re.S)
                    seen = runtime.observation(raw)
                    seen.pop('stdout')
                    assert seen == dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stderr=''), (name, seen)
                    assert 'GROUP absent=1' in raw
                    data = bytes.fromhex(re.search(r'^STDOUT bytes=\d+ hex=([0-9a-f]+)$', raw, re.M)[1])
                    if suite == 'signal':
                        signal.decode(data, case, ids[0], (media/suite/case['name']).read_bytes(), 8192)
                    elif suite == 'recvmsg':
                        actual = dict(runtime.dispatch_record(data[:32]), memory_hex=data[32:].hex())
                        assert actual == recvmsg.expected_record(case), (name, actual)
                    elif case['name'].endswith('-bad-entry'):
                        sproc.bad_entry(case, ids, data)
                    else:
                        sproc.reference.qualify_case(case, ids, data, 0, '0', b'', 'clear')
                    r['observations'].append(dict(name=name, passed=True, bytes=len(data)))
        assert 'RECEIVE_OK' in log
        received = guest.read('cat /tmp/xiri-module-recvmsg/receive.log')
        (d/'receive.log').write_bytes(received)
        r['receive_records'] = recvmsg.receive_records(received)
        assert r['receive_records'] == [recvmsg.expected_receive(c) for c in suites['recvmsg']['cases'] for _ in range(2)]
        cmd('cd /tmp/xiri-module-signal')
        for uid in (0, 1234):
            for exe, expected in [('native-signals', 'NATIVE_SIGNALS handler=1 mask=1 return=1 child=1\n'),
                                  ('native-control', f'NATIVE_TIME uid={uid} seconds=1 microseconds=1 progression=1 select=1\n')]:
                raw = cmd('./runner ./'+exe+' '+(' '.join([str(uid)]*4)))
                seen = runtime.observation(raw)
                assert seen == dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stderr='', stdout=expected)
                assert 'GROUP absent=1' in raw
                r['controls'].append(dict(name=exe, uid=uid, observed=seen))
        r['status'] = 'passed'
    except BaseException as error:
        r['error'] = repr(error)
        raise
    finally:
        lab.close()
        r['clean_shutdown'] = lab.clean_shutdown
        (d/'result.json').write_text(json.dumps(r, indent=2)+'\n')
    assert r['clean_shutdown']
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
