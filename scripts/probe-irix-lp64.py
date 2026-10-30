#!/usr/bin/env python3
"""Qualify bounded o32/n32 IRIX execution on the LP64 Indy kernel."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--pin', type=Path, default=ROOT/'lab/irix-lp64/baseline.json')
    parser.add_argument('--build-directory', type=Path, default=ROOT/'.work/netbsd-irix64-build')
    args = parser.parse_args()
    args.debugger, args.boot_timeout = False, 300
    pin = json.loads(args.pin.read_text())
    probe.IRIS = ROOT / '.work/target-netbsd64/release/iris'
    probe.CI = ROOT / '.work/target-netbsd64/release/iris-ci'
    for name, path in [('emulator', probe.IRIS), ('ci_client', probe.CI)]:
        if not path.is_file() or probe.sha256(path) != pin[name + '_sha256']:
            parser.error('missing or different pinned input: ' + name)
    fixtures = ROOT / '.work/netbsd64-probes'
    manifest = json.loads((fixtures / 'manifest.json').read_text())
    if manifest['page_bytes'] != pin['page_bytes'] or any(
            probe.sha256(ROOT / 'lab/netbsd64' / name) != sha
            for name, sha in manifest['sources'].items()):
        parser.error('native fixtures are stale; rebuild them first')
    vendor = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    kernel_dir = args.build_directory.resolve() / 'tftp'
    native_kernel = args.build_directory.resolve() / 'kernel-media/netbsd'
    boot_kernel = kernel_dir / 'netbsd-XIRI_INDY'
    inputs = [('native-' + n if n != 'map-input.bin' else n, fixtures / n, i['sha256']) for n, i in manifest['files'].items()]
    inputs += [('native-o32', ROOT / '.work/irix-o32-segments/native-o32', pin['native_o32_sha256'])]
    inputs += [(c['fixture_name'], ROOT / '.work/irix-reference/vendor' / c['path'].lstrip('/'), c['sha256'])
               for c in vendor['candidates'] if c['fixture_name'] in ['vendor-asa', 'vendor-echo']]
    foreign_dir = ROOT / '.work/irix-lp64-probes'
    foreign = json.loads((foreign_dir / 'manifest.json').read_text())
    if foreign['page_bytes'] != pin['page_bytes'] or any(probe.sha256(ROOT / n) != h for n,h in foreign['sources'].items()):
        parser.error('foreign fixtures are stale; rebuild them first')
    inputs += [(n, foreign_dir / n, i['sha256']) for n,i in foreign['files'].items()]
    inputs += [(r['name'], ROOT / '.work/irix-reference/vendor' / r['path'].lstrip('/'), r['sha256']) for r in pin['runtimes']]
    checkpoint = ROOT / '.work/indy-netbsd-kernel'
    for name, path, sha in [*inputs,
                             ('base disk', checkpoint / 'disk.raw', pin['base_disk_sha256']),
                             ('NVRAM', checkpoint / 'nvram.bin', pin['nvram_sha256']),
                             ('kernel config', ROOT / pin.get('config_path', 'lab/irix-lp64/XIRI_IRIX_LP64'), pin['config_sha256']), ('boot kernel', boot_kernel, pin['boot_kernel_sha256']),
                             ('native kernel', native_kernel, pin['native_kernel_sha256'])]:
        if not path.is_file() or probe.sha256(path) != sha:
            parser.error('missing or different pinned input: ' + name)
    output = ROOT / '.work/irix-lp64-runs'
    output.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=output))
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(kernel_dir)), config, flags=re.M)
    lab = probe.Lab(args, directory, config_text=config)
    result = {'status': 'error', 'mode': args.mode, 'clean_shutdown': False,
              'pin': pin, 'manifest': manifest, 'foreign_manifest': foreign, 'observations': [],
              'harness_sha256': probe.sha256(Path(__file__).resolve()),
              'runner_sha256': probe.sha256(ROOT / 'lab/irix-lp64/runner.c'),
              'native_c_source_sha256': probe.sha256(ROOT / 'lab/netbsd64/native-o32.c'),
              'emulator_sha256': probe.sha256(probe.IRIS),
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    started = time.monotonic()
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    success = {'errno_bytes': 0, 'errno': 0, 'exit': 37, 'signal': 0, 'killed': 0,
               'stdout': 'XIRI_NATIVE64_OK\n', 'stderr': ''}
    native = {**success, 'stdout': 'XIRI_ABI_PROBE\n'}
    cases = [{'name': 'native-before', 'program': 'native-o32', 'expect': native}]
    for case in manifest['cases']:
        expected = {**success, 'exit': -1, 'signal': 11, 'stdout': ''} if case['signal'] else success
        cases.append({'name': 'native-' + case['name'], 'program': 'native-' + case['name'], 'expect': expected})
    for name, ids in [('root', [0, 0, 0, 0]), ('user', [1234, 1234, 5678, 5678])]:
        cases.append({'name': 'o32-compat-' + name, 'program': 'native-compat', 'ids': ids,
                      'expect': {**success, 'exit': 0, 'stdout': 'XIRI_O32_COMPAT_OK\n'}})
    rejected = {**success, 'errno_bytes':4, 'errno':8, 'exit':126, 'stdout':''}
    for c in foreign['cases'] + foreign['heap_cases']:
        cases.append({'name':c['name'], 'program':c['name'], 'dispatch':c,
                      'expect':{**success,'exit':c['netbsd']['exit'],'stdout':'dispatch record'}})
        if c.get('signal'):
            cases[-1].pop('dispatch')
            cases[-1]['expect'] = {**success,'exit':-1,'signal':c['signal'],'stdout':''}
    for c in foreign['loader_cases']:
        cases.append({**c,'expect':{**success,'stdout':'XIRI_ABI_PROBE\n'} if c['expect']=='output' else rejected})
    cases.append({'name':'n32-fp','program':'n32-fp','expect':{**success,'stdout':'XIRI_N32_FP_OK\n'}})
    for name,ids in [('root',[0,0,0,0]),('user',[1234,1234,5678,5678])]:
        for abi in ['o32','n32']:
            for kind,index in [('uid',0),('gid',2)]:
                c = next(c for c in foreign['cases'] if c['name']==abi+'-'+kind)
                c = {**c,'netbsd':{**c['netbsd'],'v0':ids[index],'v1':ids[index+1]}}
                cases.append({'name':abi+'-'+kind+'-'+name,'program':c['name'],'ids':ids,'dispatch':c,
                              'expect':{**success,'exit':0,'stdout':'dispatch record'}})
        for c in [{'name':'asa-line','input':None,'stdout':'XIRI_VENDOR_O32\n'},*foreign['asa_cases']]:
            cases.append({'name':c['name']+'-'+name,'program':'vendor-asa','ids':ids,'abi':'o32','interpreter':'vendor-o32-libc',
                          'input':c['input'],'trace':c['name']=='asa-line' and name=='root',
                          'expect':{**success,'exit':0,'stdout':c['stdout']}})
        for i,argv in enumerate([[],['XIRI_VENDOR_N32'],['one','two'],['two words'],[''],['one','','three']]):
            cases.append({'name':'echo-'+str(i)+'-'+name,'program':'vendor-echo','ids':ids,'argv':argv,'abi':'n32',
                          'interpreter':'vendor-n32-libc','trace':i==1 and name=='root',
                          'expect':{**success,'exit':0,'stdout':' '.join(argv)+'\n'}})
    for i in range(3):
        for name in ['native-n32-registers', 'native-n64-registers', 'native-o32']:
            cases.append({'name': name + '-repeat-' + str(i), 'program': name,
                          'expect': native if name == 'native-o32' else success})
    cases.append({'name': 'native-after', 'program': 'native-o32', 'expect': native})
    try:
        checkpoint = ROOT / '.work/indy-netbsd-kernel'
        result['base_disk_sha256'] = probe.sha256(checkpoint / 'disk.raw')
        result['nvram_sha256'] = probe.sha256(checkpoint / 'nvram.bin')
        for name in ['disk.raw', 'nvram.bin']:
            probe.run(['cp', '--reflink=auto', '--sparse=always', checkpoint / name, directory / name], timeout=120)
        media = directory / 'media'
        media.mkdir()
        for name, source, sha in inputs:
            probe.run(['cp', source, media / name])
            if probe.sha256(media / name) != sha:
                raise RuntimeError('input changed: ' + name)
        (media / 'SHA256').write_text(''.join(f'SHA256 ({n}) = {s}\n' for n, _, s in inputs))
        for source, name in [(native_kernel, 'netbsd'), (ROOT / 'lab/indy-netbsd/probe.sh', 'probe.sh'),
                             (ROOT / 'lab/irix-lp64/runner.c', 'runner.c'),
                             (ROOT / 'lab/netbsd64/native-o32.c', 'native-o32.c')]:
            probe.run(['cp', source, media / name])
        (media / 'input.txt').write_text(' XIRI_VENDOR_O32\n')
        (media / 'payload.bin').write_bytes(bytes(range(256)) * 512)
        lines = ['#!/bin/sh', 'set -eu', 'cd /root/irix-lp64', 'ulimit -c 0']
        for case in cases:
            assert all(re.fullmatch(r'[A-Za-z0-9-]+', case[k]) for k in ['name', 'program'])
            if 'input' in case:
                lines += ['cp ' + shlex.quote(case['input']) + ' input.txt' if case['input'] else "printf ' XIRI_VENDOR_O32\\n' > input.txt"]
            if 'interpreter' in case:
                target = '/emul/irix/lib32/libc.so.1' if case['abi']=='n32' else '/emul/irix/usr/lib/libc.so.1'
                lines += ['cp '+shlex.quote(case['interpreter'])+' '+target+'.new', 'chmod 755 '+target+'.new', 'mv '+target+'.new '+target]
            command = './runner ./' + case['program']
            if 'ids' in case:
                command += ' ' + ' '.join(map(str,case['ids']))
            if 'argv' in case:
                command += ' --' + ((' ' + shlex.join(case['argv'])) if case['argv'] else '')
            if '-heap-' in case['name']:
                command = '(ulimit -d 16384; ' + command + ')'
            if case.get('trace'):
                command = 'ktrace -i -t u -f '+case['name']+'.ktrace '+command
            lines += ['echo STARTCASE ' + case['name'], command, 'echo ENDCASE ' + case['name']]
        for case in cases:
            if case.get('trace'):
                lines += ['echo STARTTRACE '+case['name'], 'kdump -f '+case['name']+'.ktrace -t u', 'echo ENDTRACE '+case['name']]
        lines += ['sha256 -c SHA256', 'echo IRIX_LP64_DONE']
        (media / 'run.sh').write_text('\n'.join(lines) + '\n')
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-V', 'XIRI_IRIX_LP64', '-o', directory / 'probe.iso', media])
        lab.start()
        before = len(lab.serial_text())
        rc = lab.command('uname -a && sysctl kern.configname hw.machine hw.machine_arch && getconf PAGESIZE', 30)
        result['identity'] = lab.serial_text()[before:]
        if rc:
            raise RuntimeError('native identity query failed')
        if lab.command('mkdir -p /cdrom /root/irix-lp64 /emul/irix/usr/lib /emul/irix/lib /emul/irix/lib32 && mount -t cd9660 -o ro /dev/cd0a /cdrom && '
                       'cp /cdrom/* /root/irix-lp64/ && cp /cdrom/netbsd /netbsd && cd /root/irix-lp64 && '
                       'sha256 -c SHA256 && chmod 755 o32-* n32-* native-* vendor-* && '
                       'chmod 644 map-input.bin dispatch-input && '
                       'cp vendor-o32-rld /emul/irix/lib/rld && cp vendor-n32-rld /emul/irix/lib32/rld && '
                       'chmod 755 /emul/irix/lib/rld /emul/irix/lib32/rld && '
                       'cc -O2 -Wall -Wextra -Werror runner.c -o runner && '
                       'cc -O2 -Wall -Wextra -Werror native-o32.c -o native-compat', 180):
            raise RuntimeError('native import or o32 compilation failed')
        if lab.command(shlex.join(['sh', '/cdrom/probe.sh', pin['ident'], pin['native_kernel_sha256'],
                                  probe.sha256(media / 'payload.bin')]), 60):
            raise RuntimeError('native kernel/file/swap controls failed')
        before = len(lab.serial_text())
        rc = lab.command('sh /root/irix-lp64/run.sh', 180)
        output = lab.serial_text()[before:]
        (directory / 'compat-serial.txt').write_text(output)
        result['guest_exit_status'] = rc
        result['traces'] = {c['name']: re.search(r'^STARTTRACE '+c['name']+r'\n(.*?)^ENDTRACE '+c['name']+r'$',output,re.M|re.S)[1] for c in cases if c.get('trace')}
        failures = []
        for case in cases:
            match = re.search(r'^STARTCASE ' + case['name'] + r'\n(.*?)^ENDCASE ' + case['name'] + r'$', output, re.M | re.S)
            if not match:
                raise RuntimeError('missing case ' + case['name'])
            actual = runtime.observation(match[1])
            record = None
            if 'dispatch' in case:
                encoded = re.search(r'^STDOUT bytes=32 hex=([0-9a-f]+)$', match[1], re.M)
                record = runtime.dispatch_record(bytes.fromhex(encoded[1])) if encoded else None
                if encoded or actual['stdout']=='' and case['dispatch']['netbsd']['exit']==37:
                    actual['stdout']='dispatch record'
            passed = actual == case['expect'] and ('dispatch' not in case or runtime.dispatch_passed(record,case['dispatch']))
            if case.get('dispatch',{}).get('mapping') and record:
                passed = passed and record['v0'] % 8192 == 0
            result['observations'].append({'name': case['name'], 'actual': actual, 'expected': case['expect'], 'passed': passed})
            if 'dispatch' in case:
                result['observations'][-1]['record'] = record
            if 'ids' in case:
                result['observations'][-1]['ids'] = case['ids']
            if not passed:
                failures.append(case['name'])
                print(case['name'] + ': ' + repr(actual), flush=True)
        if rc or '\nIRIX_LP64_DONE\n' not in output or failures:
            raise RuntimeError('LP64 qualification failed: ' + ', '.join(failures))
        if lab.command('test "$(cksum /root/xiri-probe)" = "3540535338 33 /root/xiri-probe"', 30):
            raise RuntimeError('native post-run file control failed')
        result['status'] = 'passed'
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
        result['seconds'] = round(time.monotonic() - started, 3)
        (directory / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
