#!/usr/bin/env python3
"""Observe original Xsgi startup in a disposable NetBSD guest, preserving Xorg."""
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


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


probe = module('netbsd_probe', 'probe-netbsd.py')
trace = module('lp64_trace', 'irix-lp64-ktrace.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=Path,
        default=ROOT/'.work/xiri-image/prepared-seed-20261102')
    args = parser.parse_args()
    seed = args.seed.resolve()
    provenance = json.loads((seed/'image-source.json').read_text())
    previous = json.loads((seed/'result.json').read_text())
    pin = json.loads((ROOT/'lab/irix-signal/baseline.json').read_text())
    assert previous['status'] == 'observed' and previous['clean_shutdown']
    assert previous['pin'] == pin
    assert probe.sha256(seed/'disk.raw') == provenance['raw_sha256']
    vendor = ROOT/'.work/irix-desktop/root/usr/bin/X11/Xsgi'
    vendor_pin = json.loads((ROOT/'lab/irix-desktop/manifest.json').read_text())[
        'resource_candidates']['/usr/bin/X11/Xsgi']
    assert probe.sha256(vendor) == vendor_pin['sha256']
    probe.IRIS = ROOT/'.work/target-netbsd64/release/iris'
    probe.CI = ROOT/'.work/target-netbsd64/release/iris-ci'
    assert probe.sha256(probe.IRIS) == pin['emulator_sha256']
    runs = ROOT/'.work/xsgi-probe'
    runs.mkdir(exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix='startup-', dir=runs))
    print('Results: '+str(run.relative_to(ROOT)), flush=True)
    media = run/'media'
    media.mkdir()
    shutil.copyfile(vendor, media/'Xsgi')
    shutil.copyfile(__file__, run/'probe-as-run.py')
    probe.run(['genisoimage', '-quiet', '-R', '-J', '-o', run/'probe.iso', media])
    for name in ['disk.raw', 'nvram.bin']:
        probe.run(['cp', '--reflink=auto', '--sparse=always', seed/name, run/name])
    config = (ROOT/'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = '+json.dumps(
        str(ROOT/'.work/netbsd-irix-signal-build/tftp')), config, flags=re.M)
    lab = probe.Lab(SimpleNamespace(mode='ordinary', debugger=False,
        boot_timeout=600), run, config_text=config)
    result = dict(schema=1, status='error', clean_shutdown=False,
        directory=str(run.relative_to(ROOT)), pin=pin, base_image=provenance,
        vendor=vendor_pin, cases={}, sources={str(p.relative_to(ROOT)):probe.sha256(p)
            for p in [Path(__file__).resolve(), ROOT/'scripts/probe-netbsd.py',
                      ROOT/'scripts/irix-lp64-ktrace.py']})

    def cmd(command, timeout=120):
        start = len(lab.serial_text())
        if lab.command(command, timeout):
            raise RuntimeError('guest command failed: '+command)
        return lab.serial_text()[start:]

    def get(command):
        text = cmd('echo HEX_START; { '+command+
            '; } | gzip -c | od -An -v -tx1; echo HEX_END', 240)
        match = re.search(r'^HEX_START\n([0-9a-f \n]+)^HEX_END$', text, re.M)
        if not match:
            raise RuntimeError('missing compressed payload')
        return gzip.decompress(bytes.fromhex(match[1]))

    try:
        lab.start()
        cmd('mount -t cd9660 -o ro /dev/cd0a /cdrom && '
            'mkdir -p /root/xsgi-probe && cd /root/xsgi-probe && '
            'install -m 555 /cdrom/Xsgi /emul/irix/usr/bin/X11/Xsgi && '
            'test "$(sha256 -q /emul/irix/usr/bin/X11/Xsgi)" = '+vendor_pin['sha256'])
        result['native_before'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        # Xsgi does not accept Xorg's -noreset. Use only its own documented
        # switches, without patching its binary or suppressing syscall failures.
        for name, options in [('help', ['-help']), ('startup', [':96', '-ac'])]:
            command = '/emul/irix/usr/bin/X11/Xsgi '+shlex.join(options)
            out = cmd('ulimit -c 0; ktrace -i -t cnisu -f '+name+'.ktrace '+command+
                ' >'+name+'.out 2>'+name+'.err & xp=$!; n=0; '
                'while kill -0 "$xp" 2>/dev/null && test "$n" -lt 20; do '
                'sleep 1; n=$((n+1)); done; '
                'if kill -0 "$xp" 2>/dev/null; then echo XSGI_TIMED_OUT; '
                'kill -TERM "$xp"; sleep 1; '
                'kill -0 "$xp" 2>/dev/null && kill -KILL "$xp"; fi; '
                'wait "$xp"; status=$?; printf "XSGI_STATUS=%s\\n" "$status"; true', 120)
            match = re.search(r'^XSGI_STATUS=(\d+)$', out, re.M)
            assert match
            raw = get('cat '+name+'.ktrace')
            (run/(name+'.ktrace')).write_bytes(raw)
            events = list(trace.records(raw))
            pairs = list(trace.foreign_pairs(events))
            result['cases'][name] = dict(command=command, exit=int(match[1]),
                timed_out='\nXSGI_TIMED_OUT\n' in out, transcript=out,
                stdout=get('cat '+name+'.out').decode(errors='backslashreplace'),
                stderr=get('cat '+name+'.err').decode(errors='backslashreplace'),
                trace_sha256=probe.sha256(run/(name+'.ktrace')),
                paths=list(dict.fromkeys(e['text'] for e in events if e['kind']==3)),
                calls=pairs)
            print(name+': exit '+match[1], flush=True)
        result['native_after'] = cmd('/root/irix-desktop/native-o32; test "$?" = 37')
        result['native_x_after'] = cmd('export PATH=/usr/X11R7/bin:$PATH; '
            'Xvfb :98 -screen 0 1280x1024x24 -ac -noreset >xvfb.log 2>&1 & xvfb=$!; '
            'n=0; until xdpyinfo -display 127.0.0.1:98 >native-display 2>&1; do '
            'n=$((n+1)); test "$n" -lt 30 || break; sleep 1; done; '
            'grep "dimensions:    1280x1024 pixels" native-display; status=$?; '
            'kill "$xvfb"; wait "$xvfb"; test "$status" = 0', 90)
        result['status'] = 'observed'
    except Exception as error:
        result['error'] = str(error)
        raise
    finally:
        if lab.logged_in:
            try:
                lab.command('test -z "$xvfb" || kill "$xvfb" 2>/dev/null; true', 15)
            except Exception:
                pass
        lab.close()
        result['clean_shutdown'] = lab.clean_shutdown
        result['base_raw_unchanged'] = probe.sha256(seed/'disk.raw') == provenance['raw_sha256']
        (run/'result.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
