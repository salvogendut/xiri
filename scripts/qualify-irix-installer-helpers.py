#!/usr/bin/env python3
"""Verify helper argv, native exit and the original installer's unreaped child."""
import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


old = module('installer_time', 'qualify-irix-installer-time.py')
trace = module('lp64_trace', 'irix-lp64-ktrace.py')
sha = old.sha


def binary_evidence(manifest):
    """Check the inspected instructions/GOT against the supplied ELF files.

    Only derived interface facts and hashes enter the report; the vendor
    binaries, complete script and disassembly stay in the private workspace.
    """
    installed = ROOT / '.work/irix-freeware/installed'
    paths = ['/usr/lib32/internal/libinst.so', '/usr/lib32/libc.so.1']
    data = {}
    for path in paths:
        assert sha(installed / path.lstrip('/')) == manifest['files'][path]['sha256']
        data[path] = (installed / path.lstrip('/')).read_bytes()

    def word(path, address):
        raw = data[path]
        assert raw[:6] == b'\x7fELF\x01\x02'
        phoff = struct.unpack_from('>I', raw, 28)[0]
        size, count = struct.unpack_from('>HH', raw, 42)
        for i in range(count):
            kind, offset, va, _, length = struct.unpack_from('>IIIII', raw, phoff + i * size)
            if kind == 1 and va <= address and address + 4 <= va + length:
                return struct.unpack_from('>I', raw, offset + address - va)[0]
        raise AssertionError('unmapped vendor address')

    # Reviewed instruction sites: action flags, handler pointer, SIGCHLD test,
    # waitpid(-1, &status, 0x40), then libc's selector/id/options and waitsys call.
    sites = {
        paths[0]: {0x4566578: 0x24020008, 0x456657c: 0xafa20000,
                   0x45665a8: 0x8f81ba34, 0x45665b4: 0xafa10004,
                   0x456660c: 0x8f9983b0, 0x4566618: 0x0320f809,
                   0x43de384: 0x24060012, 0x43de450: 0x8f99838c,
                   0x43de454: 0x24060040, 0x43de458: 0x27a50000,
                   0x43de45c: 0x0320f809, 0x43de460: 0x2404ffff,
                   0x45ca6ec: 0xfa62174, 0x45ca710: 0xfa5c5b8,
                   0x45cdd94: 0x43e605c},
        paths[1]: {0xfa621cc: 0x34d50003, 0xfa621e0: 0x02402025,
                   0xfa621e4: 0x02202825, 0xfa621ec: 0x02a03825,
                   0xfa621f0: 0x0413fc12, 0xfa621f4: 0x00004025,
                   0xfa622fc: 0x24120007, 0xfa62318: 0x00008825},
    }
    for path, entries in sites.items():
        for address, instruction in entries.items():
            assert word(path, address) == instruction, (path, hex(address))
    return dict(kind='static prediction; callback not reached in these runs',
                files={p: manifest['files'][p]['sha256'] for p in paths},
                checked_virtual_addresses={p: [hex(a) for a in entries] for p, entries in sites.items()},
                dispatcher_gp='0x045d2360', sigaction_flags=8, signal=18,
                handler='static_handler__Gi', callback='signal_callback__15iIrixDispatcherGi',
                waitpid=dict(pid=-1, options=64),
                predicted_waitsys=dict(number=1170, selector=7, id=0, options=67, rusage=0))


def qualify(directory, pin):
    run = json.loads((directory / 'result.json').read_text())
    assert run['status'] == 'observed' and run['clean_shutdown'] and run['pin'] == pin
    assert run['seed_result_sha256'] == sha(ROOT / run['seed'] / 'result.json')
    for path, digest in run['sources'].items():
        assert sha(ROOT / path) == digest, path
    assert run['manifest_sha256'] == sha(ROOT / 'lab/irix-installer/manifest.json')
    assert run['inputs_sha256'] == sha(ROOT / 'lab/irix-installer/inputs.json')
    helper_hashes = dict(re.findall(r'SHA256 \(([^)]+)\) = ([0-9a-f]{64})', run['helper_paths_before']))
    assert set(helper_hashes) == {'/bin/sh', '/bin/ls', '/bin/mkdir', '/bin/mv', '/bin/ln', '/usr/bin/stat'}
    assert all('\nABSENT-' + name + '\n' in run['helper_paths_before'] for name in ['ls', 'mkdir', 'mv', 'ln'])
    normal = dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stdout='', stderr='')
    assert len(run['controls']) == 4
    assert {(c['phase'], c['uid']) for c in run['controls']} == {(p, u) for p in ['before', 'after'] for u in [0, 1234]}
    assert all(c['actual'] == dict(normal, exit=37, stdout='XIRI_ABI_PROBE\n') and c['group_absent'] for c in run['controls'])
    for kind, output in [('native', 'XIRI_HOME_NATIVE\n'), ('foreign', 'XIRI_SHARED_HOME\n')]:
        assert old.runtime.observation(run['shared_home'][kind]) == dict(normal, stdout=output)
        assert 'GROUP absent=1' in run['shared_home'][kind]
    assert '\n1234\n' in run['shared_home']['owner']
    assert '\nxiritest:1234:100:/usr/people/xiritest:/bin/ksh\n1234 700\n' in run['home_setup']
    assert (directory / 'media/root.env').read_text().startswith('HOME=/\n')
    assert [c['name'] for c in run['cases']] == ['distribution']
    case = run['cases'][0]
    warnings = 'Internal program error: SIGBUS not handled for mmap.\nInternal program error: SIGSEGV not handled for mmap.\n'
    assert case['actual'] == dict(normal, exit=-1, signal=9, killed=1, stderr=warnings)
    assert case['runner_rc'] == 0 and case['group_absent']
    for suffix, key in [('log', 'log_sha256'), ('kdump', 'trace_sha256'),
                        ('ktrace.gz', 'raw_trace_sha256'), ('processes', 'process_snapshot_sha256')]:
        assert sha(directory / ('distribution.' + suffix)) == case[key]
    events = list(trace.records(gzip.decompress((directory / 'distribution.ktrace.gz').read_bytes())))
    pairs = list(trace.foreign_pairs(events))
    # Independent text decoder must agree on every direct foreign entry/return.
    text = (directory / 'distribution.kdump').read_text()
    assert [p for p in pairs if p['call']['syscall'] != 1000] == old.pairs(text)
    spawn, = [p for p in pairs if p['call']['syscall'] == 1129]
    parent, child = spawn['pid'], spawn['result']['v0']
    assert spawn['result']['a3'] == 0 and parent != child
    argv = [e['text'] for e in events if e['pid'] == child and e['kind'] == 10]
    assert len(argv) == 4 and argv[:2] == ['/bin/sh', '-c'] and argv[3] == '/bin/sh'
    script = argv[2]
    assert "@'mkVarUsr@" in script
    helper_path = '/sbin:/usr/bin:/usr/bsd:/usr/sbin:/etc:/usr/etc:'
    assert 'PATH=' + helper_path in script and '( stat -qd $1 || echo 0 ) 2>/dev/null' in script
    assert 'rbase=/emul/irix' in [e.get('text') for e in events if e['pid'] == child and e['kind'] == 11]
    assert any(e['pid'] == child and e['kind'] == 7 and e['text'] == 'netbsd32' for e in events)
    exited, = [e for e in events if e['pid'] == child and e['kind'] == 1 and e['code'] == 1]
    assert exited['args'] == [0 if run['native_paths'] else 1]
    snapshot = (directory / 'distribution.processes').read_text()
    zombie = re.search(r'^\s*' + str(child) + r'\s+' + str(parent) + r'\s+' + str(child) + r'\s+\S+\s+Z\S*\s+\(sh\)\s*$', snapshot, re.M)
    assert zombie, snapshot
    assert '\nXIRI_TRACED_PIDS_ABSENT\n' in run['post_processes']
    assert not re.search(r'^\s*\d+\s+\d+\s+\d+\s', run['post_processes'], re.M)
    assert sorted({e['pid'] for e in events}) == run['traced_pids']
    pipe_reads = b''.join(e['io'] for e in events if e['kind'] == 4 and e['pid'] == parent and e['fd'] == 5 and e['direction'] == 0)
    expected_error = b'' if run['native_paths'] else b'sh: mkdir: not found\nCannot install under "/emul/irix": No such file or directory\n'
    assert pipe_reads == expected_error
    for fd in [3, 5]:
        assert any(p['pid'] == parent and p['call']['syscall'] == 1160 and p['call']['a1'] == fd and p['result'] == dict(syscall=1160, v0=0, a3=0) for p in pairs)
    sigchld, = [p for p in pairs if p['call']['syscall'] == 1162 and p['call']['a0'] == 18]
    assert sigchld['result'] == dict(syscall=1162, v0=89, a3=1)
    assert not any(e.get('label') == 'irix_o32' and e['values']['syscall'] == 1170 for e in events)
    assert not any(e['kind'] == 3 and e['text'].startswith('/cdrom/dist') for e in events)
    assert [(e['pid'], e['signal']) for e in events if e['kind'] == 5] == [(parent, 9)]
    waiting = [e for e in events if e['ns'] > exited['ns'] and e['pid'] == parent and e.get('label') == 'irix_o32' and e['values']['syscall'] == 1100 and e['values']['a0'] == 0]
    assert len(waiting) >= 3
    times = [p for p in pairs if p['call']['syscall'] == 1128]
    assert len(times) >= 10 and all(p['result'] == dict(syscall=1128, v0=0, a3=0) for p in times)
    utilities = {}
    for e in events:
        if e['kind'] == 10 and e['pid'] != parent and e['pid'] != child:
            utilities.setdefault(e['pid'], []).append(e['text'])
    stat = [pid for pid, args in utilities.items() if args[:2] == ['stat', '-qd']]
    if run['native_paths']:
        assert '\nXIRI_HELPER_CONTROLS_OK\n' in run['helper_setup']
        for name in ['ls', 'mkdir', 'mv', 'ln']:
            assert run['helper_setup'].count('\nXIRI_NATIVE_HELPER /usr/bin/' + name + ' -> /bin/' + name + '\n') == 2
            assert any(args[0] == name for args in utilities.values()), name
        assert len(stat) == 2
        for pid in stat:
            output = b''.join(e['io'] for e in events if e['pid'] == pid and e['kind'] == 4 and e['fd'] == 2 and e['direction'] == 1)
            assert b'unknown option -- d' in output
            assert any(e['pid'] == pid and e['kind'] == 1 and e['code'] == 1 and e['args'] == [1] for e in events)
        assert '/emul/irix/usr/tmp -> ../var/tmp' in run['layout_after']
        for path in ['/emul/irix/tmp', '/emul/irix/var/tmp']:
            assert re.search(r'^d[^\n]* ' + re.escape(path) + r'\n', run['layout_after'], re.M)
    else:
        assert not stat
    return dict(directory=str(directory), mode=run['mode'], native_paths=run['native_paths'],
                result_sha256=sha(directory / 'result.json'), serial_sha256=sha(directory / 'serial.log'),
                sources=run['sources'], artifacts={k: v for k, v in case.items() if k.endswith('_sha256')},
                trace_records=len(events), record_types=dict(Counter(e['kind'] for e in events)),
                parent_pid=parent, helper_pid=child, helper_exit=exited['args'][0],
                helper_argv=['/bin/sh', '-c', '<private script>', '/bin/sh'],
                helper_script_sha256=hashlib.sha256(script.encode()).hexdigest(), helper_path=helper_path,
                native_utility_arguments=list(utilities.values()), native_stat_failures=len(stat),
                native_utility_hashes=helper_hashes,
                parent_helper_stderr=pipe_reads.decode(), zombie_snapshot=zombie[0].strip(),
                sigchld_registration=sigchld, waitsys_calls=0, select_without_fds_after_child_exit=len(waiting),
                gettimeofday_successes=len(times), native_controls=4, shared_home_verified=True,
                traced_pids_absent=True, clean_shutdown=True, installer=case['actual'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs=3, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    pin = json.loads((ROOT / 'lab/irix-time/baseline.json').read_text())
    manifest = json.loads((ROOT / 'lab/irix-installer/manifest.json').read_text())
    for path, info in manifest['files'].items():
        assert sha(ROOT / '.work/irix-freeware/installed' / path.lstrip('/')) == info['sha256']
    runs = [qualify(d, pin) for d in args.runs]
    assert {(r['mode'], r['native_paths']) for r in runs} == {('ci', False), ('ci', True), ('ordinary', True)}
    assert len({r['helper_script_sha256'] for r in runs}) == 1
    source_path = 'sys/compat/irix_o32/irix_o32.c'
    source = subprocess.check_output(['git', '-C', str(ROOT.parent / 'NetBSD-nixbench'), 'show', pin['source_revision'] + ':' + source_path])
    assert b'SCARG(uap, type) != 0 || SCARG(uap, pid) <= 0' in source
    assert b'(flags & ~(1U | 0x40U | 0x80U))' in source
    assert b'No syscall installs foreign handlers' in source
    historical_revision = '5aca2679d78276864d2980a08314887b2058fb2c'
    historical = []
    for path, constants in [
        ('sys/compat/svr4/svr4_signal.h', {'SVR4_SIGCHLD': '18', 'SVR4_SA_SIGINFO': '0x00000008'}),
        ('sys/compat/svr4/svr4_wait.h', {'SVR4_P_ALL': '7', 'SVR4_WEXITED': '0x01', 'SVR4_WTRAPPED': '0x02', 'SVR4_WNOHANG': '0x40'}),
        ('sys/compat/irix/irix_signal.c', {}),
    ]:
        data = subprocess.check_output(['git', '-C', str(ROOT.parent / 'NetBSD-nixbench'), 'show', historical_revision + ':' + path])
        for name, value in constants.items():
            assert re.search(r'#define\s+' + name + r'\s+' + value + r'\b', data.decode())
        historical.append(dict(revision=historical_revision, path=path, sha256=hashlib.sha256(data).hexdigest()))
    report = dict(schema=1, status='helper-path-progress-unreaped-child-boundary',
                  installation_success=False, distribution_read=False, pin=pin, runs=runs,
                  native_controls=12, binary_evidence=binary_evidence(manifest),
                  kernel_evidence=dict(revision=pin['source_revision'], path=source_path,
                                       sha256=hashlib.sha256(source).hexdigest()),
                  historical_source_evidence=historical,
                  qualifier_sha256=sha(Path(__file__)), decoder_sha256=sha(ROOT / 'scripts/irix-lp64-ktrace.py'),
                  limitations=[
                      'Four utility aliases qualify only this disposable bootstrap path; not general IRIX command compatibility.',
                      'Native stat rejects -qd; the original script falls back to zero. Real device comparison is not qualified.',
                      'The child exits zero with aliases but remains a zombie; the parent still requires its 30-second watchdog.',
                      'SIGCHLD registration returns ENOSYS. Signal-frame delivery and return remain unimplemented.',
                      'waitsys selector 7/options 0x43 is a static prediction, not a runtime observation.',
                      'No distribution reading, installation, Freeware catalog entry or graphical login is claimed.'])
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Verified three helper traces, 12 native controls, shared homes and complete guest shutdown')


if __name__ == '__main__':
    main()
