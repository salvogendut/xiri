#!/usr/bin/env python3
"""Qualify the bounded o32/n32 TCP client path and Toolchest connection refusal."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


probe = module('probe', 'probe-netbsd.py')
runtime = module('runtime', 'probe-irix-runtime.py')


def trace_signature(trace):
    calls = []
    for line in trace['calls']:
        fields = {k: int(v, 0) for k, v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)', line)}
        number = fields['syscall']
        item = {'syscall': number}
        if number in [1000, 1040, 1056, 1107, 1082]:
            item['a0'] = fields['a0']
        if number == 1107:
            item.update(a1=fields['a1'], a2=fields['a2'])
        calls.append(item)
    return {'calls': calls, 'returns': [v for v in trace.get('returns',[]) if int(re.search(r'syscall=(\d+)',v)[1]) in [1082,1091,1094,1105,1107]], 'paths': [p for p in trace['paths'] if p.startswith(('/emul/irix/', '/usr/lib32/', '/lib32/', '/dev/'))]}


def expected_record(case):
    """Fixed client subset contract; broader original behavior is pinned separately."""
    s = case['symbols']
    kind, error, value = s['KIND'], 0, 0
    if kind == 0:
        value = 3
        if s['DOMAIN'] != 2:
            error = 124  # EAFNOSUPPORT
        elif s['TYPE'] != 2:
            error = 121 if s['TYPE'] == 1 else 120
        elif s['PROTOCOL'] not in [0, 6]:
            error = 98  # EPROTOTYPE
    elif kind in [1, 4]:
        if s['LENGTH'] != 16:
            error = 22
        elif 'POINTER' in s:
            error = 14
        elif s['FAMILY'] != 2:
            error = 124
        elif s.get('FD') in [-1, 1]:
            error = 9 if s['FD'] == -1 else 95
        elif kind == 1:
            error = 146  # ECONNREFUSED
    elif kind == 2:
        if s['LENGTH'] != 4 or (s['LEVEL'], s['OPTION']) not in [(6, 1), (0xffff, 8)]:
            error = 22
        elif s.get('POINTER') == 0:
            error = 22
        elif s.get('FD') in [-1, 1]:
            error = 9 if s['FD'] == -1 else 95
        elif 'POINTER' in s:
            error = 14
        if case['abi'] == 'o32' and 'BAD_STACK' in s:
            error = 14
    elif kind == 3:
        error = 22 if s['TICKS'] < 0 else 0
    elif kind == 5:
        value = 100
    return {'magic': 0x58494431, 'case': case['number'], 'v0': error or value,
            'v1': 0xfeedface, 'a3': int(bool(error)), 'checks': int(kind == 4 and not error),
            'preserved': 0, 'reserved': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--x11', action='store_true', help='Also observe Toolchest against a controlled native Xvfb server')
    parser.add_argument('--kernel-abi',choices=['lp64','o32'],default='lp64')
    args = parser.parse_args()
    if args.x11 and args.kernel_abi=='o32': parser.error('X11 is qualified on the LP64 route')
    args.debugger, args.boot_timeout = False, 300
    pin = json.loads((ROOT / ('lab/irix-tcp/o32-baseline.json' if args.kernel_abi=='o32' else 'lab/irix-tcp/baseline.json')).read_text())
    inventory = json.loads((ROOT / 'lab/irix-desktop/manifest.json').read_text())
    expectations_path = ROOT / ('lab/irix-tcp/desktop-x11.json' if args.x11 else 'lab/irix-tcp/desktop.json')
    expectations = json.loads(expectations_path.read_text()) if expectations_path.exists() else None
    if args.kernel_abi=='o32': expectations={'cases':{}}
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    seed = ROOT / '.work/indy-netbsd-kernel'
    build=ROOT/('.work/netbsd-irix-tcp-o32-build' if args.kernel_abi=='o32' else '.work/netbsd-irix-tcp-build')
    kernel_dir=build/'tftp'
    native_kernel=build/'kernel-media/netbsd'
    inputs = [('native-o32', ROOT / '.work/irix-o32-segments/native-o32', pin['native_o32_sha256'])]
    vendor = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    for c in vendor['candidates']:
        inputs.append((c['fixture_name'], ROOT / '.work/irix-reference/vendor' / c['path'].lstrip('/'), c['sha256']))
    for r in pin['runtimes']:
        inputs.append((r['name'], ROOT / '.work/irix-reference/vendor' / r['path'].lstrip('/'), r['sha256']))
    fixtures = ROOT/'.work/irix-tcp/probes'
    manifest = json.loads((fixtures/'manifest.json').read_text())
    if any(probe.sha256(ROOT/p) != h for p,h in manifest['sources'].items()):
        parser.error('stale TCP fixtures')
    inputs += [(n,fixtures/n,i['sha256']) for n,i in manifest['files'].items() if n != 'reference-server']
    library_inputs = {}
    for i, (path, info) in enumerate(inventory['files'].items()):
        if path.startswith('/usr/bin/'):
            continue
        name = f'library-{i:02d}'
        inputs.append((name, ROOT / '.work/irix-desktop/root' / path.lstrip('/'), info['sha256']))
        library_inputs[path] = name
    checked = [*inputs, ('emulator', probe.IRIS, pin['emulator_sha256']),
               ('ci client', probe.CI, pin['ci_client_sha256']),
               ('disk', seed / 'disk.raw', pin['base_disk_sha256']),
               ('nvram', seed / 'nvram.bin', pin['nvram_sha256']),
               ('boot kernel', kernel_dir / 'netbsd-XIRI_INDY', pin['boot_kernel_sha256']),
               ('native kernel', native_kernel, pin['native_kernel_sha256']),
               ('kernel config', ROOT/pin['config_path'], pin['config_sha256'])]
    for name, path, sha in checked:
        if probe.sha256(path) != sha:
            parser.error('input differs: ' + name)
    output = ROOT / '.work/irix-tcp/runs'
    output.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.kernel_abi+'-'+args.mode + '-', dir=output))
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(kernel_dir)), config, flags=re.M)
    lab = probe.Lab(args, directory, config_text=config)
    result = {'status': 'error', 'mode': args.mode, 'clean_shutdown': False,
              'pin': pin, 'inventory_sha256': probe.sha256(ROOT / 'lab/irix-desktop/manifest.json'),
              'harness_sha256': probe.sha256(Path(__file__).resolve()),
              'runner_sha256': probe.sha256(ROOT / 'lab/irix-lp64/runner.c'),
              'decoder_sha256': probe.sha256(ROOT/'scripts/probe-irix-runtime.py'),
              'lab_harness_sha256': probe.sha256(ROOT/'scripts/probe-netbsd.py'),
              'helper_sources': {n:probe.sha256(ROOT/'lab/irix-tcp'/n) for n in ['server.c','optioncheck.c']},
              'x11': args.x11, 'kernel_abi':args.kernel_abi,
              'manifest': manifest, 'observations': [], 'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    started = time.monotonic()
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    normal = {'errno_bytes': 0, 'errno': 0, 'exit': 0, 'signal': 0, 'killed': 0, 'stdout': '', 'stderr': ''}
    native = {**normal, 'exit': 37, 'stdout': 'XIRI_ABI_PROBE\n'}
    cases = [{'name':'native-before','program':'native-o32','expect':native}]
    for label,ids in [('root',[0,0,0,0]),('user',[1234,1234,5678,5678])]:
        for c in manifest['cases']:
            if args.kernel_abi=='o32' and c['abi']!='o32': continue
            suffix=c['name'].split('-',2)[2]
            if label=='user' and suffix not in ['socket-default','connect-refused','setopt-nodelay','setopt-keepalive','nap-one','echo','borrow-nodelay','borrow-nodelay-off','borrow-keepalive','clock-rate']:
                continue
            cases.append({'name':c['name']+'-'+label,'program':c['name'],'ids':ids,'fixture':c})
        for case in cases:
            if 'fixture' in case and 'BORROW' in case['fixture']['symbols'] and case.get('program')!='optioncheck':
                fs=case['fixture']['symbols']
                case['argv']=['./'+case['program'],str(int(fs['LEVEL']==0xffff)),str(fs['VALUE'])]
                case['program']='optioncheck'
        for program,stdout,argv in [('asa','XIRI_VENDOR_O32\n',None),('echo','XIRI_VENDOR_N32\n',['XIRI_VENDOR_N32'])]:
            if args.kernel_abi=='o32' and program=='echo':continue
            cases.append({'name':program+'-'+label,'program':'vendor-'+program,'ids':ids,'expect':{**normal,'stdout':stdout}})
            if argv: cases[-1]['argv']=argv
        for program in ([] if args.kernel_abi=='o32' else ['4Dwm','toolchest']):
            cases.append({'name':'closure-'+program+'-'+label,'program':'vendor-'+program,'ids':ids,
                          'argv':['-display','127.0.0.1:99'],'trace':True,'stage':'closure'})
    cases += [{'name':'asa-after','program':'vendor-asa','expect':{**normal,'stdout':'XIRI_VENDOR_O32\n'}},
              {'name':'echo-after','program':'vendor-echo','ids':[0,0,0,0],'argv':['XIRI_VENDOR_N32'],
               'expect':{**normal,'stdout':'XIRI_VENDOR_N32\n'}},
              {'name':'native-after','program':'native-o32','expect':native}]
    if args.kernel_abi=='o32': cases=[c for c in cases if c['name']!='echo-after']
    if args.x11:
        for label,ids in [('root',[0,0,0,0]),('user',[1234,1234,5678,5678])]:
            cases.append({'name':'x11-toolchest-'+label,'program':'vendor-toolchest','ids':ids,
                          'argv':['-display','127.0.0.1:98'],'trace':True,'stage':'x11'})
    try:
        for name in ['disk.raw', 'nvram.bin']:
            probe.run(['cp', '--reflink=auto', '--sparse=always', seed/name, directory/name], timeout=120)
        media = directory / 'media'
        media.mkdir()
        for name, source, sha in inputs:
            probe.run(['cp', source, media/name])
            if probe.sha256(media/name) != sha:
                raise RuntimeError('input changed: ' + name)
        (media/'SHA256').write_text(''.join(f'SHA256 ({n}) = {s}\n' for n, _, s in inputs))
        for source, name in [(native_kernel, 'netbsd'), (ROOT/'lab/indy-netbsd/probe.sh', 'probe.sh'),
                             (ROOT/'lab/irix-lp64/runner.c', 'runner.c')]:
            probe.run(['cp', source, media/name])
        for n in ['server.c','optioncheck.c']:
            probe.run(['cp',ROOT/'lab/irix-tcp'/n,media/n])
        if args.x11:
            sets=['xbase','xetc','xfont','xserver']
            selected=[line for line in (ROOT/'lab/netbsd-11.0/SHA512SUMS').read_text().splitlines()
                      if line.split()[1] in [f'sgimips/binary/sets/{n}.tgz' for n in sets]]
            if len(selected)!=len(sets): raise RuntimeError('missing X set hashes')
            subprocess.run(['sha512sum','-c','-'], cwd=ROOT/'.work/netbsd-11.0',
                           input='\n'.join(selected)+'\n',text=True,check=True,capture_output=True)
            result['x11_sets']=selected
            for n in sets: (media/(n+'.tgz')).symlink_to(ROOT/'.work/netbsd-11.0/sgimips/binary/sets'/(n+'.tgz'))
        (media/'input.txt').write_text(' XIRI_VENDOR_O32\n')
        (media/'payload.bin').write_bytes(bytes(range(256))*512)
        lines = ['#!/bin/sh', 'set -eu', 'cd /root/irix-desktop', 'ulimit -c 0',
                 './server '+('4' if args.kernel_abi=='o32' else '8')+' >server.log 2>&1 & server=$!', 'sleep 1', 'grep RDY server.log']
        for path,name in library_inputs.items():
            target='/emul/irix'+path
            lines += ['mkdir -p '+shlex.quote(str(Path(target).parent)),
                      'cp '+name+' '+shlex.quote(target), 'chmod 755 '+shlex.quote(target)]
        for case in cases:
            command = './runner ./' + case['program']
            if 'ids' in case:
                command += ' ' + ' '.join(map(str, case['ids']))
            if 'argv' in case:
                command += ' -- ' + shlex.join(case['argv'])
            if case.get('trace'):
                command = 'ktrace -i -t un -f ' + case['name'] + '.ktrace ' + command
            lines += ['echo STARTCASE '+case['name'], command, 'echo ENDCASE '+case['name']]
        for case in cases:
            if case.get('trace'):
                lines += ['echo STARTTRACE '+case['name'], 'kdump -f '+case['name']+'.ktrace -t un',
                          'echo ENDTRACE '+case['name']]
        lines += ['wait "$server"', 'echo SERVER_OK', 'sha256 -c SHA256', 'echo DESKTOP_DONE']
        (media/'run.sh').write_text('\n'.join(lines)+'\n')
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-follow-links', '-V', 'XIRI_TCP', '-o', directory/'probe.iso', media])
        lab.start()
        if lab.command('mkdir -p /cdrom /root/irix-desktop /emul/irix/usr/lib /emul/irix/lib /emul/irix/lib32 /emul/irix/usr/lib32 && '
                       'mount -t cd9660 -o ro /dev/cd0a /cdrom && '
                       '(set -e; for f in /cdrom/*; do case "$f" in *.tgz) ;; *) cp "$f" /root/irix-desktop/ ;; esac; done) && '
                       'cp /cdrom/netbsd /netbsd && cd /root/irix-desktop && sha256 -c SHA256 && '
                       'chmod 755 native-o32 vendor-* library-* o32-* n32-* && '
                       'cp vendor-o32-libc /emul/irix/usr/lib/libc.so.1 && cp vendor-o32-rld /emul/irix/lib/rld && '
                       'cp vendor-n32-libc /emul/irix/lib32/libc.so.1 && cp vendor-n32-libc /emul/irix/usr/lib32/libc.so.1 && '
                       'cp vendor-n32-rld /emul/irix/lib32/rld && chmod 755 /emul/irix/*/rld /emul/irix/*/libc.so.1 /emul/irix/usr/*/libc.so.1 && '
                       'cc -O2 -Wall -Wextra -Werror -DRUNNER_TIMEOUT_MS=30000 -DRUNNER_TIMING runner.c -o runner && '
                       'cc -O2 -Wall -Wextra -Werror server.c -o server && '
                       'cc -O2 -Wall -Wextra -Werror optioncheck.c -o optioncheck', 180):
            raise RuntimeError('desktop inputs or native runner failed')
        if lab.command(shlex.join(['sh', '/cdrom/probe.sh', pin['ident'], pin['native_kernel_sha256'],
                                  probe.sha256(media/'payload.bin')]), 60):
            raise RuntimeError('native kernel/file/swap controls failed')
        if args.x11:
            if lab.command('for s in xbase xetc xfont xserver; do tar -xzpf /cdrom/$s.tgz -C / || exit; done',1200):
                raise RuntimeError('X sets failed')
            if lab.command('export PATH=/usr/X11R7/bin:$PATH; '
                           '{ Xvfb :98 -screen 0 640x480x24 -ac -noreset >/root/irix-desktop/xvfb.log 2>&1 & xpid=$!; }; '
                           'xwait=0; until xdpyinfo -display 127.0.0.1:98 >/root/irix-desktop/xdpyinfo.txt 2>/dev/null; do '
                           'kill -0 "$xpid" || break; xwait=$((xwait+1)); test "$xwait" -lt 30 || break; sleep 1; done; '
                           'xdpyinfo -display 127.0.0.1:98 >/root/irix-desktop/xdpyinfo.txt',60):
                lab.command('cat /root/irix-desktop/xvfb.log; cat /root/irix-desktop/xdpyinfo.txt',30)
                raise RuntimeError('native TCP X connection failed')
            result['native_x11_before']=True
        before = len(lab.serial_text())
        rc = lab.command('sh /root/irix-desktop/run.sh', 300)
        output = lab.serial_text()[before:]
        (directory/'desktop-serial.txt').write_text(output)
        result['traces'] = {}
        failures = []
        for case in cases:
            name = case['name']
            match = re.search(r'^STARTCASE '+name+r'\n(.*?)^ENDCASE '+name+r'$', output, re.M|re.S)
            if not match:
                raise RuntimeError('missing case '+name)
            actual = runtime.observation(match[1])
            expected = case.get('expect')
            record = None
            if 'fixture' in case:
                record_match=re.search(r'^STDOUT bytes=32 hex=([0-9a-f]+)$',match[1],re.M)
                if not record_match:
                    raise RuntimeError('missing TCP record: '+name)
                data=bytes.fromhex(record_match[1])
                record=runtime.dispatch_record(data)
                expected={**normal,'stdout':actual['stdout']}
            if expectations and case.get('stage'):
                expected = expectations['cases'][name]['actual']
            passed = actual == expected if expected is not None else None
            if record is not None:
                passed = passed and record == expected_record(case['fixture'])
                elapsed=int(re.search(r'^ELAPSED_MS (\d+)$',match[1],re.M)[1])
                ticks=case['fixture']['symbols']['TICKS']
                if case['fixture']['symbols']['KIND']==3 and ticks>0:
                    passed = passed and elapsed >= ticks*10-5
            console = '\n'.join(line for line in match[1].splitlines() if line and not line.startswith(('OBS ', 'STDOUT ', 'STDERR ', 'ELAPSED_MS ')))
            result['observations'].append({'name': name, 'actual': actual, 'console': console, 'record': record, 'elapsed_ms':int(re.search(r'^ELAPSED_MS (\d+)$',match[1],re.M)[1]), 'passed': passed})
            if passed is False:
                failures.append(name)
            if case.get('trace'):
                trace = re.search(r'^STARTTRACE '+name+r'\n(.*?)^ENDTRACE '+name+r'$', output, re.M|re.S)
                if not trace:
                    raise RuntimeError('missing trace '+name)
                result['traces'][name] = {
                    'calls': [bytes.fromhex(x).decode() for x in re.findall(r'irix_o32: \d+, ([0-9a-f]+)', trace[1])],
                    'returns': [bytes.fromhex(x).decode() for x in re.findall(r'irix_ret: \d+, ([0-9a-f]+)',trace[1])],
                    'paths': re.findall(r'NAMI\s+"([^"]+)"', trace[1])}
                signature = trace_signature(result['traces'][name])
                result['traces'][name]['signature'] = signature
                if expectations:
                    trace_ok = signature == expectations['cases'][name]['trace_signature']
                    console_ok = console == expectations['cases'][name]['console']
                    result['observations'][-1]['passed'] = passed and trace_ok and console_ok
                    if not trace_ok or not console_ok:
                        failures.append(name + '-trace-or-console')
                if not result['traces'][name]['calls']:
                    raise RuntimeError('desktop never entered foreign dispatcher: '+name)
        if args.x11:
            if lab.command('/usr/X11R7/bin/xdpyinfo -display 127.0.0.1:98 >/dev/null && kill "$xpid"',30):
                raise RuntimeError('native X server control failed after foreign clients')
            result['native_x11_after']=True
        if '\nSERVER_OK\n' not in output: raise RuntimeError('native echo peer failed')
        if rc or '\nDESKTOP_DONE\n' not in output or failures:
            raise RuntimeError('TCP qualification failed: '+', '.join(failures))
        if lab.command('test "$(cksum /root/xiri-probe)" = "3540535338 33 /root/xiri-probe"', 30):
            raise RuntimeError('native post-run file control failed')
        result['status'] = 'passed' if expectations else 'observed'
        if expectations and args.kernel_abi!='o32':
            result['expectations_sha256'] = probe.sha256(expectations_path)
        print(f'{len(cases)} TCP/desktop/control cases {result["status"]}', flush=True)
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'
        print(result['error'], flush=True)
    finally:
        try:
            lab.close()
        except Exception as error:
            result.update(status='error', cleanup_error=str(error))
        result['clean_shutdown'] = lab.clean_shutdown
        if not lab.clean_shutdown:
            result['status'] = 'error'
        result['seconds'] = round(time.monotonic()-started, 3)
        (directory/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    return 0 if result['status'] in ['observed', 'passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
