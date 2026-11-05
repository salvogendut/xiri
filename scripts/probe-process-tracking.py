#!/usr/bin/env python3
"""Check native child notifications against a pipe oracle in a disposable CHD."""
import argparse
import json
from pathlib import Path
import re
import shlex
import shutil
import signal
import tempfile
from types import SimpleNamespace

from xiri_lab import Guest, ROOT, load_probe, sha256
from xiri_lab.kernel_log import KernelLog


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, required=True)
    parser.add_argument('--rounds', type=int, default=16, choices=range(1, 65))
    parser.add_argument('--guard-tests', action='store_true')
    parser.add_argument('--deadline-tests', action='store_true',
                        help='Test delayed supervisor signals with real queue/state observations')
    parser.add_argument('--candidate-guard', action='store_true',
                        help='Build the maintained guard and install only in this disposable guest')
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    manifest = json.loads((bundle/'manifest.json').read_text())
    assert sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
    assert sha256(bundle/'seed-result.json') == manifest['source_result_sha256']
    assert sha256(bundle/'iris.toml') == manifest['config_sha256']
    assert manifest['session_manager'] == 'xdm'
    p = load_probe()
    p.IRIS, p.CI = bundle/'emulator/iris', bundle/'emulator/iris-ci'
    for path, key in [(p.IRIS, 'emulator_sha256'), (p.CI, 'ci_client_sha256')]:
        assert sha256(path) == manifest['pin'][key]
    runs = ROOT/'.work/process-tracking'; runs.mkdir(exist_ok=True)
    d = Path(tempfile.mkdtemp(prefix='native-', dir=runs))
    print('Results: '+str(d.relative_to(ROOT)), flush=True)
    shutil.copyfile(__file__, d/'harness.py')
    media = d/'media'; media.mkdir()
    sources = ['lab/irix-process-tracking/events.c']
    if args.guard_tests:
        sources += ['lab/irix-session/descendants.c', 'lab/irix-session/guard-tests.sh']
    if args.deadline_tests:
        sources += ['lab/irix-process-tracking/delay.c',
                    'lab/irix-process-tracking/deadline-case.c',
                    'lab/irix-process-tracking/deadline-tests.sh']
    if args.candidate_guard:
        sources += ['runtime/libexec/session-guard.c']
    for source in sources:
        shutil.copyfile(ROOT/source, media/Path(source).name)
    p.run(['genisoimage', '-quiet', '-R', '-J', '-o', d/'probe.iso', media])
    p.run(['cp', '--reflink=auto', '--sparse=always', bundle/'netbsd-xiri.chd', d/'disk.chd'])
    profile = bundle/manifest['qualification_nvram']
    assert sha256(profile) == manifest['qualification_nvram_sha256']
    shutil.copyfile(profile, d/'nvram.bin')
    config = (bundle/'iris.toml').read_text().replace('tftp_dir = "tftp"',
        'tftp_dir = '+json.dumps(str(d/'no-tftp')))
    assert 'tftp_dir = '+json.dumps(str(d/'no-tftp')) in config
    config += '\n[scsi.4]\npath = '+json.dumps(str(d/'probe.iso'))+'\ncdrom = true\n'
    lab = p.Lab(SimpleNamespace(mode='ordinary', debugger=False, boot_timeout=600), d, config_text=config)
    launch = lab.launch
    def disk_launch(command, name):
        if name == 'emulator':
            command = list(command); command[command.index('--scsi1')+1] = str(d/'disk.chd')
        return launch(command, name)
    lab.launch = disk_launch
    guest = Guest(lab)
    cmd, get = guest.command, guest.read_text
    record = dict(schema=1, status='error', bundle=str(bundle.relative_to(ROOT)),
        chd_sha256=manifest['chd_sha256'], manifest_sha256=sha256(bundle/'manifest.json'),
        pin=manifest['pin'], module=manifest['irix_module'],
        harness_sha256=sha256(d/'harness.py'), sources={s:sha256(ROOT/s) for s in sources},
        rounds=args.rounds, events=[], clean_shutdown=False)
    def interrupted(signum, frame):
        raise RuntimeError('Interrupted by signal '+str(signum))
    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        lab.start(boot=False); lab.wait('login: ', 600)
        lab.send('root'); lab.wait('xiri-indy# ', 30); lab.logged_in = True
        print('Native serial login ready', flush=True)
        cmd('export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin; '
            'ulimit -c 0; mount -t cd9660 -o ro /dev/cd0a /cdrom; '
            'mkdir -p /tmp/xiri-tracking/out; cd /tmp/xiri-tracking; '
            'install -m 444 /cdrom/* .; chown xiritest:xiritest out; '
            'cc -O2 -Wall -Wextra -Werror events.c -o events', 180)
        record['guest_hashes'] = get('sha256 /netbsd /netbsd.boot '+manifest['irix_module']['path']+
            ' /usr/local/libexec/xiri/session-guard events events.c')
        for digest in [manifest['pin']['native_kernel_sha256'], manifest['pin']['boot_kernel_sha256'],
                       manifest['irix_module']['sha256'], record['sources'][sources[0]]]:
            assert digest in record['guest_hashes']
        seed = json.loads((bundle/'seed-result.json').read_text())
        guard_hash = seed['installed_files']['/usr/local/libexec/xiri/session-guard']
        assert guard_hash in record['guest_hashes']
        if args.candidate_guard:
            cmd('cp /usr/local/libexec/xiri/session-guard session-guard-installed; '
                'cc -O2 -Wall -Wextra -Werror session-guard.c -o session-guard && '
                'install -m 555 session-guard /usr/local/libexec/xiri/session-guard', 120)
            record['candidate_guard_sha256'] = get('sha256 -q /usr/local/libexec/xiri/session-guard').strip()
        for uid, user in [(0, 'root'), (1234, 'xiritest')]:
            for batch in (1, 64):
                name = f'events-{uid}-{batch}'
                command = 'cd /tmp/xiri-tracking; ./events '+str(batch)+' '+str(args.rounds)
                invocation = shlex.join(['su', '-l', user, '-c', command])
                cmd(invocation+' >out/'+name+'.log 2>&1; status=$?; '
                    'echo "$status" >out/'+name+'.status', 300)
                output = get('cat out/'+name+'.log')
                status = get('cat out/'+name+'.status').strip()
                entry = dict(uid=uid, batch=batch, status=status, output=output)
                record['events'].append(entry)
                assert status == '0', entry
                expected = [f'EVENT_PASS uid={uid} mode={mode} batch={batch} rounds={args.rounds} '
                    f'births={args.rounds*8} exits={args.rounds*8}' for mode in ('fast', 'orphan', 'held')]
                assert output.splitlines() == expected, entry
                print(f'uid={uid} batch={batch}: {args.rounds*24} child lifecycles passed', flush=True)
        if args.guard_tests:
            cmd('cc -O2 -Wall -Wextra -Werror descendants.c -o descendants; '
                'cp descendants out/; chown xiritest:xiritest out/descendants', 120)
            cmd("su -l xiritest -c '/bin/sh /tmp/xiri-tracking/guard-tests.sh /tmp/xiri-tracking/out' "
                '>guard-tests.log 2>&1; status=$?; echo "$status" >guard-tests.status', 300)
            record['guard_tests'] = get('cat guard-tests.log')
            record['guard_tests_status'] = get('cat guard-tests.status').strip()
            assert record['guard_tests_status'] == '0', record['guard_tests']
            assert 'SESSION_GUARD_TESTS_OK' in record['guard_tests']
            assert len(re.findall(r'^GUARD .*absent=1 valid=1 .*remaining=0 ', record['guard_tests'], re.M)) == 10
            print('Installed session guard adversarial controls passed', flush=True)
        if args.deadline_tests:
            cmd('cc -O2 -Wall -Wextra -Werror -fPIC -shared delay.c -o delay.so && '
                'cc -O2 -Wall -Wextra -Werror deadline-case.c -o deadline-case && '
                'mkdir deadline && cp deadline-case delay.so deadline/ && '
                'chown xiritest:xiritest deadline', 120)
            record['deadline_hashes'] = get('sha256 delay.so deadline-case')
            cmd("su -l xiritest -c '/bin/sh /tmp/xiri-tracking/deadline-tests.sh "
                "/tmp/xiri-tracking/deadline /usr/local/libexec/xiri/session-guard' "
                '>deadline-tests.log 2>&1; status=$?; echo "$status" >deadline-tests.status', 300)
            record['deadline_tests'] = get('cat deadline-tests.log')
            record['deadline_status'] = get('cat deadline-tests.status').strip()
            assert record['deadline_status'] == '0', record['deadline_tests']
            cases = re.findall(r'^DEADLINE case=(\S+) uid=1234 ', record['deadline_tests'], re.M)
            assert cases == ['fast', 'term', 'kill', 'live', 'signal', 'logout', 'leader'], cases
            print('Seven delayed-cleanup scenarios passed', flush=True)
        record['status'] = 'passed'
    except Exception as error:
        record['error'] = str(error)
        try:
            guest.monitor('stop')
            record['failure_cpu'] = guest.monitor('regs')
            record['failure_stack'] = guest.monitor('bt 20')
        except Exception as capture_error:
            record['capture_error'] = str(capture_error)
        finally:
            try: guest.monitor('start')
            except Exception: pass
        try:
            log = d/'failure-kernel.log'
            log.write_text(KernelLog(lab, int(manifest['kernel_msgbuf_symbol'], 16)).read())
            record['failure_kernel_sha256'] = sha256(log)
            path = d/'failure.png'; guest.capture(path)
            record['failure_png_sha256'] = sha256(path)
        except Exception as capture_error:
            record['capture_error'] = str(capture_error)
        raise
    finally:
        if lab.logged_in:
            try:
                archive = d/'observations.tgz'
                archive.write_bytes(guest.read('tar czf - -C /tmp xiri-tracking', 180))
                record['archive_sha256'] = sha256(archive)
            except Exception as error: record['archive_error'] = str(error)
            try:
                record['shutdown_log'] = KernelLog(lab, int(manifest['kernel_msgbuf_symbol'], 16)).halt()
            except Exception as error: record['cleanup_error'] = str(error)
        lab.close(); record['clean_shutdown'] = lab.clean_shutdown
        record['source_unchanged'] = sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
        if record['status'] == 'passed' and (not record['clean_shutdown'] or
                not record['source_unchanged'] or record.get('archive_error')):
            record.update(status='error', error='Missing clean halt, unchanged source or observations')
        (d/'result.json').write_text(json.dumps(record, indent=2)+'\n')
    if record['status'] != 'passed': raise RuntimeError(record['error'])


if __name__ == '__main__':
    main()
