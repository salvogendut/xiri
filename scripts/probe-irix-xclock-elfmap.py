#!/usr/bin/env python3
"""Capture actual vendor xclock ELF map headers using native ptrace breakpoints."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed-directory', type=Path, required=True)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    args = parser.parse_args()
    seed = args.seed_directory.resolve()
    seed_result = json.loads((seed / 'result.json').read_text())
    pin = json.loads((ROOT / 'lab/irix-xstat/baseline.json').read_text())
    if not (seed_result['status'] == 'observed' and seed_result['clean_shutdown']
            and seed_result['native_x11_after'] and seed_result['pin'] == pin
            and len(seed_result['xclock']) == 4):
        parser.error('seed must be a completed xclock probe on the pinned xstat kernel')
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    build = ROOT / '.work/netbsd-irix-xstat-build'
    for path, key in [(probe.IRIS, 'emulator_sha256'), (probe.CI, 'ci_client_sha256'),
                      (build / 'tftp/netbsd-XIRI_INDY', 'boot_kernel_sha256')]:
        if probe.sha256(path) != pin[key]:
            parser.error('changed input: ' + str(path))
    output = ROOT / '.work/irix-xclock-loader/runs'
    output.mkdir(parents=True, exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=output))
    print('Results: ' + str(directory), flush=True)
    media = directory / 'media'
    media.mkdir()
    source = ROOT / 'lab/irix-xclock/elfmap-trace.c'
    shutil.copyfile(source, media / source.name)
    inputs = dict(seed_result['guest_inputs'])
    manifest = json.loads((ROOT / 'lab/irix-xclock/manifest.json').read_text())
    inputs['/root/irix-desktop/vendor-xclock'] = manifest['files']['/usr/bin/X11/xclock']['sha256']
    inputs['/emul/irix/usr/lib32/libXaw.so.2'] = manifest['files']['/usr/lib32/libXaw.so.2']['sha256']
    (media / 'GUEST_SHA256').write_text(''.join(f'SHA256 ({p}) = {h}\n' for p, h in inputs.items()))
    (media / 'SHA256').write_text(''.join(f'SHA256 ({p.name}) = {probe.sha256(p)}\n' for p in sorted(media.iterdir())))
    for name in ['disk.raw', 'nvram.bin']:
        probe.run(['cp', '--reflink=auto', '--sparse=always', seed / name, directory / name], timeout=120)
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', directory / 'probe.iso', media])
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(build / 'tftp')), config, flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode=args.mode, debugger=False, boot_timeout=600), directory, config_text=config)
    result = {'status': 'error', 'mode': args.mode, 'clean_shutdown': False, 'pin': pin,
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'seed': str(seed.relative_to(ROOT)), 'guest_inputs': inputs,
              'seed_result_sha256': probe.sha256(seed / 'result.json'),
              'seed_disk_sha256': probe.sha256(directory / 'disk.raw'),
              'sources': {str(p.relative_to(ROOT)): probe.sha256(p) for p in [source, Path(__file__), ROOT / 'scripts/probe-netbsd.py']},
              'captures': []}

    def command(cmd, timeout=90):
        before = len(lab.serial_text())
        rc = lab.command(cmd, timeout)
        text = lab.serial_text()[before:]
        if rc:
            raise RuntimeError(f'guest command failed ({rc}): {cmd}')
        return text

    try:
        lab.start()
        command('mount -t cd9660 -o ro /dev/cd0a /cdrom && '
                'cd /cdrom && sha256 -c SHA256 && sha256 -c GUEST_SHA256 && '
                'cd /root/irix-desktop && cp /cdrom/elfmap-trace.c . && '
                'cc -O2 -Wall -Wextra -Werror elfmap-trace.c -o elfmap-trace && '
                'mkdir -p /tmp/xiri-home && ulimit -c 0', 180)
        for case, program, arguments in [('native-before', 'native-o32', ''),
                                         ('vendor-analog', 'vendor-xclock', ' -analog'),
                                         ('vendor-digital', 'vendor-xclock', ' -digital'),
                                         ('native-after', 'native-o32', '')]:
            kind = 'native' if program == 'native-o32' else 'vendor'
            raw = command(f'./elfmap-trace {kind} ./{program}{arguments}', 180)
            path = directory / (case + '.txt')
            path.write_text(raw)
            expected = 'END exit=37 signal=0' if kind == 'native' else 'END exit=1 signal=0'
            if expected not in raw:
                raise RuntimeError('unexpected child outcome: ' + case)
            observed = {'name': case, 'raw_sha256': probe.sha256(path),
                        'records': re.findall(r'^(?:EXEC|NATIVE|CALL|RETURN|PHDR|RLD|END) .*$', raw, re.M)}
            result['captures'].append(observed)
            print(json.dumps(observed), flush=True)
            command(f'cp elfmap-child.out {case}.out && cp elfmap-child.err {case}.err')
        result['status'] = 'observed'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] == 'observed' and result['clean_shutdown'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
