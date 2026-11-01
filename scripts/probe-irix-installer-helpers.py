#!/usr/bin/env python3
"""Observe installer helper arguments, native I/O and child completion."""
import argparse
import gzip
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import tarfile
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


probe = module('probe', 'probe-netbsd.py')
runtime = module('runtime', 'probe-irix-runtime.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--native-paths', action='store_true')
    args = parser.parse_args()
    mode = args.mode
    native_paths = args.native_paths
    seed = ROOT / '.work/irix-desktop-pipe/runs/ordinary-cg_e3vdl'
    sr = json.loads((seed / 'result.json').read_text())
    old = json.loads((ROOT / 'lab/irix-pipe/baseline.json').read_text())
    pin = json.loads((ROOT / 'lab/irix-time/baseline.json').read_text())
    assert sr['status'] == 'observed' and sr['clean_shutdown'] and sr['pin'] == old
    manifest_path = ROOT / 'lab/irix-installer/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    inputs_path = ROOT / 'lab/irix-installer/inputs.json'
    inputs = json.loads(inputs_path.read_text())
    build = ROOT / '.work/netbsd-irix-time-build'
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    for path, key in [(probe.IRIS, 'emulator_sha256'), (probe.CI, 'ci_client_sha256'),
                      (build / 'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256'),
                      (build / 'kernel-media/netbsd', 'native_kernel_sha256')]:
        assert probe.sha256(path) == pin[key]
    out = ROOT / '.work/irix-installer-helpers/runs'
    out.mkdir(parents=True, exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix=mode+('-native-' if native_paths else '-baseline-'), dir=out))
    print('Results: ' + str(d.relative_to(ROOT)), flush=True)
    media = d / 'media'
    media.mkdir()
    shutil.copyfile(build / 'kernel-media/netbsd', media / 'netbsd')
    sources = ['scripts/probe-irix-installer-helpers.py', 'scripts/setup-xiri-user.sh',
               'lab/irix-process/runner.c', 'lab/irix-toolchest/session.c',
               'lab/irix-installer-helpers/setup-native-paths.sh']
    for path in sources[1:]:
        shutil.copyfile(ROOT / path, media / Path(path).name)
    selected, queue = set(), ['/usr/sbin/inst', '/usr/sbin/iconcatalogedit']
    while queue:
        path = queue.pop()
        if path in selected:
            continue
        selected.add(path)
        queue.extend(manifest['files'][path]['interpreter'])
        queue.extend(e['selected'] for e in manifest['edges'] if e['source'] == path)
    staged = dict(sr['staged'])
    install = ['#!/bin/sh', 'set -eu', 'cd /', 'tar xzf /cdrom/installer.tgz']
    with tarfile.open(media / 'installer.tgz', 'w:gz') as tar:
        for path in sorted(selected | {'/var/inst/machfile'}):
            info = manifest['files'][path] if path in selected else inputs[path]
            source = ROOT / '.work/irix-freeware/installed' / path.lstrip('/')
            assert probe.sha256(source) == info['sha256']
            target = '/emul/irix' + path
            if target in staged:
                assert staged[target] == info['sha256']
            staged[target] = info['sha256']
            tar.add(source, arcname=target.lstrip('/'), recursive=False)
            install.append('chmod 555 ' + shlex.quote(target))
    (media / 'install.sh').write_text('\n'.join(install) + '\n')
    (media / 'dist').mkdir()
    for path, info in inputs.items():
        if info['source'] != 'media':
            continue
        source = ROOT / '.work/irix-freeware/package' / path.lstrip('/')
        assert probe.sha256(source) == info['sha256']
        shutil.copyfile(source, media / 'dist' / Path(path).name)
    (media / 'commands').write_text('list fw_xmahjongg*\nquit\n')
    (media / 'root.env').write_text('HOME=/\nUSER=root\nLOGNAME=root\nSHELL=/bin/ksh\nLANG=C\nLC_ALL=C\nTERM=dumb\nPATH=/bin:/usr/bin:/emul/irix/usr/sbin\n')
    (media / 'user.env').write_text('HOME=/usr/people/xiritest\nUSER=xiritest\nLOGNAME=xiritest\nSHELL=/bin/ksh\nLANG=C\nLC_ALL=C\nPATH=/bin:/usr/bin\n')
    inherited = {'/netbsd': old['native_kernel_sha256'],
                 '/root/irix-desktop/native-o32': pin['native_o32_sha256'], **sr['staged']}
    for label, files in [('INHERITED', inherited), ('STAGED', staged)]:
        (media / label).write_text(''.join(f'SHA256 ({p}) = {h}\n' for p, h in files.items()))
    (media / 'SHA256').write_text(''.join(f'SHA256 ({p.relative_to(media)}) = {probe.sha256(p)}\n'
        for p in sorted(media.rglob('*')) if p.is_file()))
    for name in ['disk.raw', 'nvram.bin']:
        probe.run(['cp', '--reflink=auto', '--sparse=always', seed / name, d / name], timeout=120)
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', d / 'probe.iso', media])
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(build / 'tftp')),
                    (ROOT / 'lab/indy-netbsd/iris.toml').read_text(), flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode=mode, debugger=False, boot_timeout=600), d, config_text=config)
    result = dict(status='error', mode=mode, native_paths=native_paths, clean_shutdown=False, pin=pin, seed=str(seed.relative_to(ROOT)),
        seed_result_sha256=probe.sha256(seed / 'result.json'), manifest_sha256=probe.sha256(manifest_path),
        inputs_sha256=probe.sha256(inputs_path), staged=staged, sources={p: probe.sha256(ROOT / p) for p in sources},
        controls=[], cases=[])

    def cmd(command, timeout=180):
        start = len(lab.serial_text())
        if lab.command(command, timeout):
            raise RuntimeError('guest command failed: ' + command)
        return lab.serial_text()[start:]

    def get(command):
        raw = cmd('echo HEX_START; { ' + command + '; } 2>transfer.err | gzip -c | od -An -v -tx1; echo HEX_END', 240)
        match = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$', raw, re.M)
        assert match
        return gzip.decompress(bytes.fromhex(match[1]))

    def controls(phase):
        for uid in [0, 1234]:
            raw = cmd('./runner ./native-control-o32 ' + ' '.join([str(uid)] * 4))
            actual = runtime.observation(raw)
            assert actual == dict(errno_bytes=0, errno=0, exit=37, signal=0, killed=0,
                                  stdout='XIRI_ABI_PROBE\n', stderr='')
            assert 'GROUP absent=1' in raw
            result['controls'].append(dict(phase=phase, uid=uid, actual=actual, group_absent=True))

    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && cd /cdrom && sha256 -c SHA256 && sha256 -c INHERITED && cp netbsd /netbsd && sh install.sh && sha256 -c STAGED && mkdir -p /tmp/xiri-installer && cd /tmp/xiri-installer && cp /cdrom/*.c /cdrom/*.env . && : >input.txt && chmod 444 input.txt *.env && cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=30000 runner.c -o runner && cc -O2 -Wall -Wextra -Werror session.c -o session && chmod 555 runner session && install -m 555 /root/irix-desktop/native-o32 native-control-o32 && ulimit -c 0', 300)
        cmd('uname -v | grep '+shlex.quote(pin['ident']))
        controls('before')
        result['home_setup'] = cmd('sh /cdrom/setup-xiri-user.sh xiritest 1234 && sh /cdrom/setup-xiri-user.sh xiritest 1234 && getent passwd xiritest | cut -d: -f1,3,4,6,7 && stat -f "%u %Lp" /usr/people/xiritest')
        assert 'XIRI_USER created name=xiritest home=/usr/people/xiritest shell=/bin/ksh' in result['home_setup']
        assert 'XIRI_USER existing name=xiritest home=/usr/people/xiritest' in result['home_setup']
        assert '\n1234 700\n' in result['home_setup']
        native = cmd('./runner ./session 1234 1234 1234 1234 -- user.env /bin/ksh -c ' + shlex.quote('cd "$HOME" && printf " XIRI_SHARED_HOME\\n" > shared.txt && printf "XIRI_HOME_NATIVE\\n"'))
        assert runtime.observation(native) == dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stdout='XIRI_HOME_NATIVE\n', stderr='')
        cmd('install -m 555 /root/irix-desktop/vendor-asa vendor-asa')
        foreign = cmd('./runner ./session 1234 1234 1234 1234 -- user.env ./vendor-asa /usr/people/xiritest/shared.txt')
        assert runtime.observation(foreign) == dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stdout='XIRI_SHARED_HOME\n', stderr='')
        assert 'GROUP absent=1' in native and 'GROUP absent=1' in foreign
        result['shared_home'] = dict(native=native, foreign=foreign, owner=cmd('stat -f %u /usr/people/xiritest/shared.txt'))
        result['helper_paths_before'] = cmd('sha256 /bin/sh /bin/ls /bin/mkdir /bin/mv /bin/ln /usr/bin/stat; for name in ls mkdir mv ln; do if test -e /usr/bin/$name || test -L /usr/bin/$name; then echo PRESENT-$name; else echo ABSENT-$name; fi; done')
        assert all('ABSENT-'+name in result['helper_paths_before'] for name in ['ls', 'mkdir', 'mv', 'ln'])
        if native_paths:
            result['helper_setup'] = cmd('sh /cdrom/setup-native-paths.sh && sh /cdrom/setup-native-paths.sh && mkdir -p /tmp/xiri-helper-check && /usr/bin/mkdir /tmp/xiri-helper-check/created && /usr/bin/ls -d /tmp/xiri-helper-check/created && /usr/bin/mv /tmp/xiri-helper-check/created /tmp/xiri-helper-check/moved && /usr/bin/ln -s moved /tmp/xiri-helper-check/link && test "$(readlink /tmp/xiri-helper-check/link)" = moved && /usr/bin/ls -ld /tmp/xiri-helper-check/moved >&- 2>&- && rm /tmp/xiri-helper-check/link && rmdir /tmp/xiri-helper-check/moved /tmp/xiri-helper-check && echo XIRI_HELPER_CONTROLS_OK && ls -l /usr/bin/ls /usr/bin/mkdir /usr/bin/mv /usr/bin/ln')
            assert '\nXIRI_HELPER_CONTROLS_OK\n' in result['helper_setup']
        result['layout_before'] = cmd('for path in /emul/irix/usr /emul/irix/var /emul/irix/var/inst /emul/irix/tmp /emul/irix/var/tmp /emul/irix/usr/tmp; do ls -ld "$path"; done; :')
        for name, args in [('distribution', ['-n', '-M', '-r', '/emul/irix', '-f', '/cdrom/dist', '-c', '/cdrom/commands'])]:
            launch = ['./runner', './session', '0', '0', '0', '0', '--', 'root.env', '/usr/bin/ktrace', '-i', '-t', 'acefinsuv', '-f', name+'.ktrace', '/emul/irix/usr/sbin/inst', *args]
            rc = lab.command(shlex.join(launch) + ' >' + name + '.log 2>&1 & job=$!; sleep 4; ps -ax -o pid,ppid,pgid,sess,stat,args >' + name + '.processes; wait "$job"', 120)
            raw = get('cat ' + name + '.log').decode()
            (d / (name + '.log')).write_text(raw)
            actual = runtime.observation(raw)
            assert 'GROUP absent=1' in raw
            (d / (name + '.processes')).write_bytes(get('cat ' + name + '.processes'))
            cmd('kdump -x -n -m 4096 -f ' + name + '.ktrace >' + name + '.dump 2>' + name + '.decode.err')
            (d / (name + '.kdump')).write_bytes(get('cat ' + name + '.dump'))
            result['decoder_stderr'] = get('cat ' + name + '.decode.err').decode()
            # Retain the original binary trace, not only the text rendering.
            (d / (name + '.ktrace.gz')).write_bytes(get('gzip -c ' + name + '.ktrace'))
            trace = (d / (name + '.kdump')).read_text()
            traced_pids = sorted({int(x) for x in re.findall(r'^\s*(\d+)\s+\d+\s+\S+\s+(?:CALL|MISC|ARG|GENIO|PSIG)', trace, re.M)})
            result['traced_pids'] = traced_pids
            result['post_processes'] = cmd('live=0; for pid in ' + ' '.join(map(str, traced_pids)) + '; do if kill -0 "$pid" 2>/dev/null; then ps -p "$pid" -o pid,ppid,pgid,sess,stat,args; live=1; fi; done; test "$live" = 0 && echo XIRI_TRACED_PIDS_ABSENT')
            assert '\nXIRI_TRACED_PIDS_ABSENT\n' in result['post_processes']
            result['layout_after'] = cmd('for path in /emul/irix/usr /emul/irix/var /emul/irix/var/inst /emul/irix/tmp /emul/irix/var/tmp /emul/irix/usr/tmp; do ls -ld "$path"; done; :')
            result['cases'].append(dict(name=name, argv=launch, runner_rc=rc, actual=actual, group_absent=True,
                log_sha256=probe.sha256(d / (name + '.log')), trace_sha256=probe.sha256(d / (name + '.kdump')),
                raw_trace_sha256=probe.sha256(d / (name + '.ktrace.gz')),
                process_snapshot_sha256=probe.sha256(d / (name + '.processes'))))
            print(json.dumps(result['cases'][-1]), flush=True)
        controls('after')
        result['status'] = 'observed'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        (d / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] == 'observed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
