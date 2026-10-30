#!/usr/bin/env python3
"""Qualify the bounded o32 loader and record the first vendor startup boundary."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shlex
import struct
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('probe', ROOT / 'scripts/probe-netbsd.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def observation(output):
    match = re.search(r'^OBS path=\S+ errno_bytes=(\d+) errno=(\d+) exit=(-?\d+) signal=(\d+) killed=(\d+)$', output, re.M)
    if not match:
        raise RuntimeError('missing direct-exec observation')
    result = dict(zip(['errno_bytes', 'errno', 'exit', 'signal', 'killed'], map(int, match.groups())))
    for stream in ['stdout', 'stderr']:
        match = re.search(r'^' + stream.upper() + r' bytes=(\d+) hex=([0-9a-f]*)$', output, re.M)
        if not match:
            raise RuntimeError('missing captured ' + stream)
        data = bytes.fromhex(match[2])
        if len(data) != int(match[1]):
            raise RuntimeError('truncated ' + stream)
        result[stream] = data.decode('utf-8', errors='backslashreplace')
    return result


def query_records(output, ids, *, cap_mode=0, unknown_syssgi=89):
    match = re.search(r'^STDOUT bytes=(\d+) hex=([0-9a-f]*)$', output, re.M)
    data = bytes.fromhex(match[2]) if match else b''
    if len(data) != 16 * 64 or int(match[1]) != len(data):
        raise RuntimeError('missing or truncated query records')
    # v0 and a3 for each case. Other syssgi requests retain the personality's
    # explicit ENOSYS policy, distinct from the reference's EINVAL.
    expected = [(cap_mode, 0), (4096, 0), (22, 1), (0, 0), (1009, 1), (22, 1), (22, 1),
                (ids[0], 0), (ids[2], 0), (unknown_syssgi, 1), (14, 1), (14, 1), (14, 1),
                (78, 1), (1009, 1), (78, 1)]
    result = []
    for i, words in enumerate(struct.iter_unpack('>16I', data)):
        want_v1 = ids[1] if i == 7 else ids[3] if i == 8 else 0xfeedface
        want_caps = [0] * 6 if i == 3 else [0xa5a5a5a5] * 6
        passed = words[:2] == (0x58495131, i + 1) and (words[2], words[4]) == expected[i] and \
            words[3] == want_v1 and list(words[6:12]) == want_caps and \
            all(words[j] == 0xa5a5a5a5 for j in [5, 12, 13, 14, 15])
        result.append({'case': i + 1, 'v0': words[2], 'v1': words[3], 'a3': words[4],
                       'cap_words': list(words[6:12]), 'guards': [words[j] for j in [5, 12, 13, 14, 15]],
                       'passed': passed})
    return result


def elfmap_record(data):
    if len(data) != 48:
        raise RuntimeError('missing or truncated ELF-map record')
    fields = ['magic', 'case', 'v0', 'v1', 'a3', 'checks', 'second_v0', 'second_a3',
              'third_v0', 'third_a3', 'preserved_word', 'reserved']
    return dict(zip(fields, struct.unpack('>12I', data)))


def elfmap_passed(record, case):
    expected = {'magic': 0x58494531, 'case': case['number'], 'v1': 0xfeedface,
                'second_v0': 0, 'second_a3': 0, 'third_v0': 0, 'third_a3': 0,
                'preserved_word': 0, 'reserved': 0}
    expected.update({k: case['netbsd'][k] for k in ['v0', 'a3', 'checks']})
    if case['action'] == 2:
        expected['second_v0'] = 0x0e000000
    if case['action'] in [5, 6]:
        expected.update(second_v0=12, second_a3=1, third_v0=0x0e010000,
                        preserved_word=0x12345678)
    return record == expected


def dispatch_record(data):
    if len(data) != 32:
        raise RuntimeError('missing or truncated dispatch record')
    return dict(zip(['magic', 'case', 'v0', 'v1', 'a3', 'checks', 'preserved', 'reserved'],
                    struct.unpack('>8I', data)))


def dispatch_passed(record, case):
    if case['netbsd']['exit'] == 37:
        return record is None
    if record is None:
        return False
    expected = {k: case['netbsd'][k] for k in ['v0', 'v1', 'a3', 'checks']}
    expected.update(magic=0x58494431, case=case['number'], preserved=0, reserved=0)
    if case['mapping']:
        if not 4096 <= record['v0'] < 0x80000000 or record['v0'] % 4096:
            return False
        expected['v0'] = record['v0']
    if 'OCCUPIED' in case['symbols']:
        if not 4096 <= record['preserved'] < 0x80000000 or record['preserved'] % 4096 or \
                record['preserved'] == record['v0']:
            return False
        expected['preserved'] = record['preserved']
    if 'TEXT_HINT' in case['symbols']:
        expected['preserved'] = 0x27bdff00
    return record == expected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['ci', 'ordinary'], default='ci')
    parser.add_argument('--suite', choices=['runtime', 'queries', 'elfmap', 'dispatch'], default='runtime')
    args = parser.parse_args()
    args.debugger, args.boot_timeout = False, 300
    fixtures = ROOT / '.work/irix-o32-runtime'
    synthetic = json.loads((fixtures / 'manifest.json').read_text())
    pin = json.loads((ROOT / f'lab/irix-o32/{args.suite}.json').read_text())
    vendor = json.loads((ROOT / 'lab/irix-reference/manifest.json').read_text())
    kernel_dir = ROOT / f'.work/netbsd-irix-build/{args.suite}-tftp'
    kernel = kernel_dir / 'netbsd-XIRI_INDY'
    inputs = [(name, fixtures / name, info['sha256']) for name, info in synthetic['files'].items()]
    queries = None
    if args.suite in ['queries', 'elfmap', 'dispatch']:
        query_dir = ROOT / '.work/irix-o32-queries'
        queries = json.loads((query_dir / 'manifest.json').read_text())
        inputs += [(name, query_dir / name, info['sha256']) for name, info in queries['files'].items()]
    elfmap = None
    if args.suite in ['elfmap', 'dispatch']:
        elfmap_dir = ROOT / '.work/irix-o32-elfmap'
        elfmap = json.loads((elfmap_dir / 'manifest.json').read_text())
        inputs += [(name, elfmap_dir / name, info['sha256']) for name, info in elfmap['files'].items()]
    dispatch = None
    if args.suite == 'dispatch':
        dispatch_dir = ROOT / '.work/irix-o32-dispatch'
        dispatch = json.loads((dispatch_dir / 'manifest.json').read_text())
        inputs += [(name, dispatch_dir / name, info['sha256']) for name, info in dispatch['files'].items()]
    inputs += [('native-o32', ROOT / '.work/irix-o32-segments/native-o32', pin['native_control_sha256'])]
    inputs += [(c['fixture_name'], ROOT / '.work/irix-reference/vendor' / c['path'].lstrip('/'), c['sha256'])
               for c in vendor['candidates']]
    inputs += [(f'vendor-runtime-{i}', ROOT / '.work/irix-reference/vendor' / r['path'].lstrip('/'), r['sha256'])
               for i, r in enumerate(pin['runtimes'])]
    for name, path, sha in [*inputs, ('kernel', kernel, pin['kernel']['sha256'])]:
        if not path.is_file() or probe.sha256(path) != sha:
            parser.error(f'{name}: missing or different pinned input: {path}')
    output_root = ROOT / f'.work/irix-{args.suite}-runs'
    output_root.mkdir(exist_ok=True)
    directory = Path(tempfile.mkdtemp(prefix=args.mode + '-', dir=output_root))
    config = (ROOT / 'lab/indy-netbsd/iris.toml').read_text()
    config = re.sub(r'^tftp_dir = .*$', 'tftp_dir = ' + json.dumps(str(kernel_dir)), config, flags=re.M)
    lab = probe.Lab(args, directory, config_text=config)
    result = {'status': 'error', 'mode': args.mode, 'clean_shutdown': False, 'pin': pin,
              'synthetic_manifest': synthetic, 'query_manifest': queries,
              'elfmap_manifest': elfmap, 'dispatch_manifest': dispatch, 'observations': [],
              'started_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
    started = time.monotonic()
    print(f'Results: {directory.relative_to(ROOT)}', flush=True)
    success = {'errno_bytes': 0, 'errno': 0, 'exit': 37, 'signal': 0, 'killed': 0,
               'stdout': 'XIRI_ABI_PROBE\n', 'stderr': ''}
    rejected = {**success, 'errno_bytes': 4, 'errno': 8, 'exit': 126, 'stdout': ''}
    cases = [{'name': 'native-before', 'program': 'native-o32', 'interpreter': 'interpreter', 'expect': success}]
    cases += [{**c, 'expect': success if c['expect'] == 'output' else rejected} for c in synthetic['cases']]
    cases += [{'name': 'missing-interpreter', 'program': 'dynamic', 'interpreter': None,
               'expect': {**rejected, 'errno': 2}}]
    cases += [{'name': c['fixture_name'], 'program': c['fixture_name'], 'interpreter': 'vendor-runtime-0',
               'expect': pin['asa_expected'] if c['fixture_name'] == 'vendor-asa' else rejected}
              for c in vendor['candidates']]
    if queries:
        cases.append({'name': 'vendor-asa-user', 'program': 'vendor-asa', 'interpreter': 'vendor-runtime-0',
                      'ids': [1234, 1234, 5678, 5678], 'expect': pin['asa_expected']})
        for name, ids in [('root', [0, 0, 0, 0]), ('user', [1234, 1234, 5678, 5678]),
                          ('effective-root', [1234, 0, 5678, 0]), ('real-root', [0, 1234, 0, 5678])]:
            cases.append({'name': 'queries-' + name, 'program': 'queries', 'interpreter': 'interpreter',
                          'ids': ids, 'query': True,
                          'expect': {**success, 'exit': 0, 'stdout': '16 query records'}})
    if elfmap:
        for case in elfmap['cases']:
            signal = case['netbsd']['signal']
            cases.append({'name': case['name'], 'program': 'elfmap', 'interpreter': 'interpreter',
                          'elfmap': case, 'expect': {**success, 'exit': -1 if signal else 0,
                                                   'signal': signal, 'stdout': 'ELF-map record'}})
        cases.append({'name': 'elfmap-user', 'program': 'elfmap', 'interpreter': 'interpreter',
                      'elfmap': elfmap['cases'][0], 'ids': [1234, 1234, 5678, 5678],
                      'expect': {**success, 'exit': 0, 'stdout': 'ELF-map record'}})
        cases.append({'name': 'elfmap-noexec-mount', 'program': 'elfmap', 'interpreter': 'interpreter',
                      'elfmap': {**elfmap['cases'][0], 'noexec_mount': True,
                                 'netbsd': {'v0': 13, 'a3': 1, 'checks': 0, 'signal': 0}},
                      'expect': {**success, 'exit': 0, 'stdout': 'ELF-map record'}})
    if dispatch:
        for case in dispatch['cases']:
            cases.append({'name': case['name'], 'program': case['name'], 'interpreter': 'interpreter',
                          'dispatch': case, 'expect': {**success, 'exit': case['netbsd']['exit'],
                                                       'stdout': 'dispatch record'}})
        for ids_name, ids in [('user', [1234, 1234, 5678, 5678]),
                              ('effective-root', [1234, 0, 5678, 0]),
                              ('real-root', [0, 1234, 0, 5678])]:
            for kind, start in [('uid', 0), ('gid', 2)]:
                case = next(c for c in dispatch['cases'] if c['name'] == 'dispatch-' + kind)
                expected = {**case, 'netbsd': {**case['netbsd'], 'v0': ids[start], 'v1': ids[start + 1]}}
                cases.append({'name': case['name'] + '-' + ids_name, 'program': case['name'],
                              'interpreter': 'interpreter', 'ids': ids, 'dispatch': expected,
                              'expect': {**success, 'exit': 0, 'stdout': 'dispatch record'}})
        for case in dispatch['asa_cases']:
            for suffix, ids in [('', [0, 0, 0, 0]), ('-user', [1234, 1234, 5678, 5678])]:
                cases.append({'name': case['name'] + suffix, 'program': 'vendor-asa',
                              'interpreter': 'vendor-runtime-0', 'asa_input': case['input'], 'ids': ids,
                              'expect': {**success, 'exit': 0, 'stdout': case['stdout']}})
    cases += [{'name': 'native-after', 'program': 'native-o32', 'interpreter': 'interpreter', 'expect': success}]
    try:
        checkpoint = ROOT / '.work/indy-netbsd-kernel'
        result['base_disk_sha256'] = probe.sha256(checkpoint / 'disk.raw')
        for name in ['disk.raw', 'nvram.bin']:
            probe.run(['cp', '--reflink=auto', '--sparse=always', checkpoint / name, directory / name], timeout=120)
        result['nvram_sha256'] = probe.sha256(directory / 'nvram.bin')
        result['kernel_sha256'] = probe.sha256(kernel)
        result['emulator_sha256'] = probe.sha256(probe.IRIS)
        result['harness_sha256'] = probe.sha256(Path(__file__).resolve())
        media = directory / 'media'
        media.mkdir()
        sums = []
        for name, source, sha in inputs:
            probe.run(['cp', source, media / name])
            sums.append(f'SHA256 ({name}) = {sha}')
        (media / 'SHA256').write_text('\n'.join(sums) + '\n')
        (media / 'input.txt').write_text(' XIRI_VENDOR_O32\n')
        (media / 'payload.bin').write_bytes(bytes(range(256)) * 512)
        payload_sha = probe.sha256(media / 'payload.bin')
        for source, name in [(ROOT / 'lab/irix-o32/runtime-runner.c', 'runner.c'),
                             (ROOT / 'lab/indy-netbsd/probe.sh', 'probe.sh'), (kernel, 'netbsd')]:
            probe.run(['cp', source, media / name])
        result['runner_sha256'] = probe.sha256(media / 'runner.c')
        lines = ['#!/bin/sh', 'set -eu', 'cd /root/irix-runtime', 'ulimit -c 0']
        for case in cases:
            for name in [case['name'], case['program'], case['interpreter']]:
                if name is not None and not re.fullmatch(r'[A-Za-z0-9-]+', name):
                    raise RuntimeError('unsafe case name')
            lines += [f'echo STARTCASE {case["name"]}']
            if 'asa_input' in case:
                if not re.fullmatch(r'[A-Za-z0-9-]+', case['asa_input']):
                    raise RuntimeError('unsafe asa input name')
                lines += [f'cp {case["asa_input"]} input.txt']
            if 'elfmap' in case:
                e = case['elfmap']
                if not re.fullmatch(r'[A-Za-z0-9-]+', e['input']):
                    raise RuntimeError('unsafe ELF-map input')
                if e.get('noexec_mount'):
                    lines += ['mount -u -o noexec /cdrom', 'rm -f elfmap-input',
                              f'ln -s /cdrom/{e["input"]} elfmap-input']
                else:
                    lines += [f'cp {e["input"]} elfmap-input.new',
                              f'chmod {e["mode"]:o} elfmap-input.new',
                              'mv elfmap-input.new elfmap-input']
            if case['interpreter'] is None:
                lines += ['rm /emul/irix/usr/lib/libc.so.1']
            else:
                lines += [f'cp {case["interpreter"]} /emul/irix/usr/lib/libc.new',
                          'chmod 755 /emul/irix/usr/lib/libc.new',
                          'mv /emul/irix/usr/lib/libc.new /emul/irix/usr/lib/libc.so.1']
            command = './runner ./' + case['program']
            if 'ids' in case:
                command += ' ' + ' '.join(map(str, case['ids']))
            if case['name'] == 'vendor-asa':
                command = 'ktrace -i -t u -f runtime.ktrace ' + command
            lines += [command, f'echo ENDCASE {case["name"]}']
            if case.get('elfmap', {}).get('noexec_mount'):
                lines += ['mount -u -o exec /cdrom']
        lines += ['echo STARTTRACE', 'kdump -f runtime.ktrace -t u', 'echo ENDTRACE',
                  'sha256 -c SHA256', 'echo RUNTIME_DONE']
        (media / 'run.sh').write_text('\n'.join(lines) + '\n')
        probe.run(['genisoimage', '-quiet', '-R', '-J', '-V', 'XIRI_RUNTIME', '-o', directory / 'probe.iso', media])
        lab.start()
        if lab.command('mkdir -p /cdrom /root/irix-runtime /emul/irix/usr/lib /emul/irix/lib && '
                       'mount -t cd9660 -o ro /dev/cd0a /cdrom && cp /cdrom/* /root/irix-runtime/ && '
                       'cp /cdrom/netbsd /netbsd && cd /root/irix-runtime && sha256 -c SHA256 && '
                       'chmod 755 dynamic native-o32 vendor-* bad-* ' + ('queries ' if queries else '') +
                       ('elfmap ' if elfmap else '') + ('dispatch-* ' if dispatch else '') + '&& '
                       'cp vendor-runtime-1 /emul/irix/lib/rld && chmod 755 /emul/irix/lib/rld && '
                       'cc -O2 -Wall -Wextra -Werror runner.c -o runner', 180):
            raise RuntimeError('runtime import or native runner build failed')
        if lab.command(shlex.join(['sh', '/cdrom/probe.sh', pin['kernel']['ident'], result['kernel_sha256'], payload_sha]), 60):
            raise RuntimeError('native kernel/file/swap smoke failed')
        before = len(lab.serial_text())
        rc = lab.command('sh /root/irix-runtime/run.sh', 180)
        output = lab.serial_text()[before:]
        (directory / 'runtime-serial.txt').write_text(output)
        result['guest_exit_status'] = rc
        failures = []
        for case in cases:
            match = re.search(r'^STARTCASE ' + case['name'] + r'\n(.*?)^ENDCASE ' + case['name'] + r'$', output, re.M | re.S)
            if not match:
                raise RuntimeError('missing case ' + case['name'])
            actual = observation(match[1])
            records = query_records(match[1], case['ids']) if case.get('query') else None
            if records is not None:
                actual['stdout'] = '16 query records'
            mapping = None
            if 'elfmap' in case:
                encoded = re.search(r'^STDOUT bytes=48 hex=([0-9a-f]+)$', match[1], re.M)
                mapping = elfmap_record(bytes.fromhex(encoded[1])) if encoded else None
                actual['stdout'] = 'ELF-map record'
            dispatch_data = None
            if 'dispatch' in case:
                encoded = re.search(r'^STDOUT bytes=32 hex=([0-9a-f]+)$', match[1], re.M)
                dispatch_data = dispatch_record(bytes.fromhex(encoded[1])) if encoded else None
                # Only indirect exit may produce no record, and it must be empty.
                if encoded or actual['stdout'] == '' and case['dispatch']['netbsd']['exit'] == 37:
                    actual['stdout'] = 'dispatch record'
            passed = actual == case['expect'] and (records is None or all(r['passed'] for r in records)) and \
                ('elfmap' not in case or mapping is not None and elfmap_passed(mapping, case['elfmap'])) and \
                ('dispatch' not in case or dispatch_passed(dispatch_data, case['dispatch']))
            result['observations'].append({'name': case['name'], 'passed': passed, 'actual': actual, 'expected': case['expect']})
            if 'ids' in case:
                result['observations'][-1]['ids'] = case['ids']
            if records is not None:
                result['observations'][-1]['query_records'] = records
            if 'elfmap' in case:
                result['observations'][-1]['elfmap_record'] = mapping
            if 'dispatch' in case:
                result['observations'][-1]['dispatch_record'] = dispatch_data
            if not passed:
                failures.append(case['name'])
                print(f'{case["name"]}: {actual}', flush=True)
        result['trace'] = [bytes.fromhex(s).decode() for s in
                           re.findall(r'irix_o32: \d+, ([0-9a-f]+)', output)]
        print('Vendor trace: ' + json.dumps(result['trace']), flush=True)
        parsed_trace = [dict((k, int(v, 0)) for k, v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)', line))
                        for line in result['trace']]
        expected_trace = pin['asa_trace_expected']
        result['trace_passed'] = len(parsed_trace) == len(expected_trace) and all(
            all(actual.get(k) == v for k, v in expected.items())
            for actual, expected in zip(parsed_trace, expected_trace))
        if rc or '\nRUNTIME_DONE\n' not in output or failures or not result['trace_passed']:
            raise RuntimeError('runtime qualification failed: ' + ', '.join(failures))
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
