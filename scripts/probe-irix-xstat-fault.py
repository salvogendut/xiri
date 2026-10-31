#!/usr/bin/env python3
"""Capture the later Toolchest fault after the qualified xstat/resource run."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import shutil
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


probe = module('probe', 'probe-netbsd.py')
runtime = module('runtime', 'probe-irix-runtime.py')
tcp = module('tcp', 'probe-irix-tcp.py')
RESOURCES = ['system.chestrc', 'app-defaults/Toolchest',
             'locale/locale.alias', 'locale/locale.dir']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-directory', type=Path, required=True)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    args = parser.parse_args()
    seed = args.seed_directory.resolve()
    seed_result = json.loads((seed / 'result.json').read_text())
    pin = json.loads((ROOT / 'lab/irix-xstat/baseline.json').read_text())
    if not (seed_result['status'] == 'observed' and seed_result['clean_shutdown']
            and seed_result['native_x11_after'] and seed_result['kernel_abi'] == 'lp64'
            and seed_result['pin'] == pin):
        parser.error('seed must be a clean LP64 xstat run with staged resources')
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    build = ROOT / '.work/netbsd-irix-xstat-build'
    for path, key in [(probe.IRIS, 'emulator_sha256'), (probe.CI, 'ci_client_sha256'),
                      (build / 'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256')]:
        if probe.sha256(path) != pin[key]:
            parser.error('changed input: ' + str(path))
    inventory = json.loads((ROOT / 'lab/irix-desktop/manifest.json').read_text())
    output = ROOT / '.work/irix-xstat/fault-runs'
    output.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=output))
    print('Results: ' + str(directory), flush=True)
    media = directory / 'media'
    media.mkdir()
    sources = ['lab/irix-toolchest/' + n for n in ['trace.c', 'fault.c', 'session.c']]
    sources += ['lab/irix-lp64/runner.c']
    for name in sources:
        shutil.copyfile(ROOT / name, media / Path(name).name)
    resources = {}
    for path in RESOURCES:
        full = '/usr/lib/X11/' + path
        info = inventory['resource_candidates'][full]
        source = ROOT / '.work/irix-desktop/root' / full.lstrip('/')
        if probe.sha256(source) != info['sha256']:
            parser.error('changed vendor resource: ' + full)
        shutil.copyfile(source, media / Path(path).name)
        resources[full] = info['sha256']
    # Check inherited executables/libraries before use; refresh nothing implicitly.
    guest_inputs = {'/netbsd': pin['native_kernel_sha256'],
                    '/root/irix-desktop/native-o32': pin['native_o32_sha256']}
    vendor = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    for c in vendor['candidates']:
        guest_inputs['/root/irix-desktop/' + c['fixture_name']] = c['sha256']
    for path, info in inventory['files'].items():
        if path == '/usr/bin/X11/toolchest':
            guest_inputs['/root/irix-desktop/vendor-toolchest'] = info['sha256']
        elif not path.startswith('/usr/bin/'):
            guest_inputs['/emul/irix' + path] = info['sha256']
    for path,sha in resources.items():guest_inputs['/emul/irix'+path]=sha
    for r in pin['runtimes']:
        guest_inputs['/emul/irix' + r['path']] = r['sha256']
    (media / 'GUEST_SHA256').write_text(''.join(f'SHA256 ({p}) = {h}\n' for p, h in guest_inputs.items()))
    (media / 'SHA256').write_text(''.join(f'SHA256 ({p.name}) = {probe.sha256(p)}\n' for p in sorted(media.iterdir())))
    for name in ['disk.raw', 'nvram.bin']:
        probe.run(['cp', '--reflink=auto', '--sparse=always', seed / name, directory / name], timeout=120)
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory / 'probe.iso', media])
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(build / 'tftp')), config, flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode=args.mode, debugger=False, boot_timeout=600), directory, config_text=config)
    result = {'status': 'error', 'mode': args.mode, 'clean_shutdown': False, 'pin': pin,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'seed': str(seed.relative_to(ROOT)),
              'seed_result_sha256': probe.sha256(seed / 'result.json'),
              'seed_disk_sha256': probe.sha256(directory / 'disk.raw'),
              'sources': {p: probe.sha256(ROOT / p) for p in sources + [
                  'scripts/probe-irix-xstat-fault.py', 'scripts/probe-netbsd.py',
                  'scripts/probe-irix-runtime.py', 'scripts/probe-irix-tcp.py']},
              'resources': resources, 'guest_inputs': guest_inputs, 'cases': [], 'traces': {}, 'faults': []}

    def command(cmd, timeout=90):
        before = len(lab.serial_text())
        rc = lab.command(cmd, timeout)
        text = lab.serial_text()[before:]
        if rc:
            raise RuntimeError(f'guest command failed ({rc}): {cmd}')
        return text

    def case(name, argv, uid=0, nice=False, trace=False):
        cmd = ('nice -n 20 ' if nice else '') + shlex.join([
            './runner', './session', *[str(uid)] * 4, '--', *argv])
        if trace:
            cmd = 'ktrace -i -t un -f case.ktrace ' + cmd
        text = command(cmd)
        actual = runtime.observation(text)
        result['cases'].append({'name': name, 'uid': uid, 'nice': 20 if nice else 0, 'actual': actual})
        print(name + ': ' + json.dumps(actual), flush=True)
        if trace:
            raw = command('kdump -x -f case.ktrace', 120)
            (directory / (name + '.kdump')).write_text(raw)
            result['traces'][name] = {label: tcp.trace_records(raw, label, raw=True)
                                     for label in ['irix_o32', 'irix_ret']}
            result['traces'][name]['paths'] = re.findall(r'NAMI\s+"([^"]+)"', raw)
            if not result['traces'][name]['irix_o32']:
                raise RuntimeError('missing foreign syscall trace')
        return actual

    normal = dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stdout='', stderr='')
    def controls(phase):
        for uid in [0, 1234]:
            for program, extra, expected in [
                ('native-o32', [], dict(normal, exit=37, stdout='XIRI_ABI_PROBE\n')),
                ('vendor-asa', [], dict(normal, stdout='XIRI_VENDOR_O32\n')),
                ('vendor-echo', ['XIRI_VENDOR_N32'], dict(normal, stdout='XIRI_VENDOR_N32\n'))]:
                actual = case(f'{phase}-{program}-{uid}', ['home.env', './' + program, *extra], uid)
                if actual != expected:
                    raise RuntimeError('control differs: ' + program)

    try:
        lab.start()
        command('mount -t cd9660 -o ro /dev/cd0a /cdrom && '
                'cd /cdrom && sha256 -c SHA256 && sha256 -c GUEST_SHA256 && '
                'cd /root/irix-desktop && cp /cdrom/*.c . && '
                'cc -O2 -Wall -Wextra -Werror trace.c -o tracer && '
                'cc -O0 -Wall -Wextra -Werror fault.c -o fault && '
                'cc -O2 -Wall -Wextra -Werror session.c -o session && '
                'cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=5000 runner.c -o runner && '
                ': >empty.env && printf "HOME=/tmp/xiri-home\\n" >home.env && '
                'mkdir -p /tmp/xiri-home && chmod 777 /tmp/xiri-home && ulimit -c 0', 180)
        controls('before')
        actual = case('environment', ['home.env', '/usr/bin/env'])
        if actual != dict(normal, stdout='HOME=/tmp/xiri-home\n'):
            raise RuntimeError('environment was not replaced exactly')
        native = command('./tracer 0 0 empty.env ./native-o32')
        if not re.search(r'phase=exec .*pc=0000000000400090\n', native) or 'END exit=37 signal=0' not in native:
            raise RuntimeError('native trace PC/control failed')
        fault = command('nm fault | fgrep xiri_fault_site; ./tracer 0 0 empty.env ./fault')
        site = re.search(r'^([0-9a-f]+) T xiri_fault_site$', fault, re.M)
        pc = re.search(r'phase=fault signal=11 code=1 address=00000000 pc=([0-9a-f]+)', fault)
        if not site or not pc or int(site[1], 16) != int(pc[1], 16) or 'END exit=-1 signal=9' not in fault:
            raise RuntimeError('native fault trace failed')
        result['native_trace_controls'] = {'entry_pc': '0x00400090', 'fault_pc': hex(int(pc[1], 16)), 'guard_intact': True}
        command('export PATH=/usr/X11R7/bin:$PATH; '
                '{ Xvfb :98 -screen 0 640x480x24 -ac -noreset >xvfb-session.log 2>&1 & xpid=$!; }; '
                'xwait=0; until xdpyinfo -display 127.0.0.1:98 >/dev/null 2>&1; do '
                'xwait=$((xwait+1)); test "$xwait" -lt 30 || exit 1; sleep 1; done')
        result['native_x11_before'] = True
        for uid in [0]:
            for attempt in range(2):
                name=f'fault-{uid}-{attempt}'
                raw=command(shlex.join(['./tracer',str(uid),str(uid),'home.env','./vendor-toolchest','-display','127.0.0.1:98']),90)
                path=directory/(name+'.txt');path.write_text(raw)
                stop=re.search(r'STOP phase=fault signal=(\d+) code=(\d+) address=([0-9a-f]+) pc=([0-9a-f]+)',raw)
                if not stop or 'END exit=-1 signal=9' not in raw:raise RuntimeError('no captured fault: '+name)
                fault_regs=re.findall(r'^REGS (.*)$',raw,re.M)[-1]
                regs={k:v for k,v in (word.split('=') for word in fault_regs.split())}
                observation=dict(name=name,signal=int(stop[1]),code=int(stop[2]),address='0x'+stop[3],pc='0x'+stop[4],a0='0x'+regs['4'],a1='0x'+regs['5'],a2='0x'+regs['6'],sp='0x'+regs['29'],ra='0x'+regs['31'],raw_sha256=probe.sha256(path))
                result['faults'].append(observation);print(json.dumps(observation),flush=True)
        command('xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"')
        result['native_x11_after']=True
        controls('after')
        result['status']='observed'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('Recorded boundaries; review results before claiming qualification.', flush=True)
    return 0 if result['status']=='observed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
