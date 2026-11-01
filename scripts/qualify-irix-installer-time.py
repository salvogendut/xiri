#!/usr/bin/env python3
"""Verify original-inst time calls and its remaining helper boundary."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


tcp = module('tcp', 'scripts/probe-irix-tcp.py')
runtime = module('runtime', 'scripts/probe-irix-runtime.py')
time_abi = module('time_abi', 'scripts/qualify-irix-time.py')


def trace_text(raw):
    # head+tail duplicates short files byte-for-byte, including a missing final
    # newline that can concatenate two records on a single displayed line.
    if len(raw) % 2 == 0 and raw[:len(raw)//2] == raw[len(raw)//2:]:
        return raw[:len(raw)//2]
    return raw


def pairs(raw):
    result, pending = [], {}
    pattern = r'^\s*(\d+)\s+(\d+)\s+\S+\s+MISC\s+(irix_o32|irix_ret):\n(?:(?:\t| {8})[^\n]*\n)+'
    for match in re.finditer(pattern, trace_text(raw), re.M):
        pid, lwp = int(match[1]), int(match[2])
        text = tcp.trace_records(match[0], match[3], True)[0]
        values = {k: int(v, 0) for k, v in re.findall(r'(\w+)=(0x[0-9a-f]+|\d+)', text)}
        key = (pid, lwp)
        if match[3] == 'irix_o32':
            pending[key] = values
        elif key in pending and pending[key]['syscall'] == values['syscall']:
            result.append(dict(pid=pid, lwp=lwp, call=pending.pop(key), result=values))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('run', type=Path)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    run = json.loads((a.run / 'result.json').read_text())
    pin = json.loads((ROOT / 'lab/irix-time/baseline.json').read_text())
    assert run['status'] == 'observed' and run['clean_shutdown']
    time_abi.check_pin(run['pin'], pin)
    assert run['seed_result_sha256'] == sha(ROOT / run['seed'] / 'result.json')
    for path, digest in run['sources'].items():
        assert sha(ROOT / path) == digest, path
    manifest_path = ROOT / 'lab/irix-installer/manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert run['manifest_sha256'] == sha(manifest_path)
    assert run['inputs_sha256'] == sha(ROOT / 'lab/irix-installer/inputs.json')
    for path, info in manifest['files'].items():
        assert sha(ROOT / '.work/irix-freeware/installed' / path.lstrip('/')) == info['sha256']
    assert (a.run / 'media/root.env').read_text().splitlines()[0] == 'HOME=/'
    assert len(run['controls']) == 4
    assert {(c['phase'], c['uid']) for c in run['controls']} == {(phase, uid) for phase in ['before', 'after'] for uid in [0, 1234]}
    normal = dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stdout='', stderr='')
    assert all(c['actual'] == dict(normal, exit=37, stdout='XIRI_ABI_PROBE\n') and c['group_absent'] for c in run['controls'])
    assert '\nxiritest:1234:100:/usr/people/xiritest:/bin/ksh\n1234 700\n' in run['home_setup']
    assert 'XIRI_USER created' in run['home_setup'] and 'XIRI_USER existing' in run['home_setup']
    for kind, output in [('native', 'XIRI_HOME_NATIVE\n'), ('foreign', 'XIRI_SHARED_HOME\n')]:
        raw = run['shared_home'][kind]
        assert runtime.observation(raw) == dict(normal, stdout=output) and 'GROUP absent=1' in raw
    assert '\n1234\n' in run['shared_home']['owner']
    assert [c['name'] for c in run['cases']] == ['hardware', 'distribution']
    warnings = 'Internal program error: SIGBUS not handled for mmap.\nInternal program error: SIGSEGV not handled for mmap.\n'
    expected = {
        'hardware': dict(normal, stdout='CPUARCH=\n\nCPUBOARD=\nMODE=32bit\nGFXBOARD=SERVER\nSUBGR=SERVER\n',
            stderr=warnings + 'WARNING: Unrecognized cpu hardware type.  See the "hardware" help topic for details.\nWARNING: Unrecognized cpu architecture type.  See the "hardware" help topic for details.\n'),
        'distribution': dict(normal, exit=-1, signal=9, killed=1, stderr=warnings),
    }
    traces = {}
    for c in run['cases']:
        name = c['name']
        assert c['runner_rc'] == 0 and c['group_absent'] and c['actual'] == expected[name]
        assert sha(a.run / (name + '.log')) == c['log_sha256']
        assert sha(a.run / (name + '.kdump')) == c['trace_sha256']
        raw = trace_text((a.run / (name + '.kdump')).read_text())
        assert 'PSIG  SIGSEGV' not in raw and 'PSIG  SIGBUS' not in raw
        assert 'NAMI  "/dev/zero"' in raw
        events = pairs(raw)
        mmap = [x for x in events if x['call']['syscall'] == 1134 and x['call']['a1'] == 0x100000]
        assert len(mmap) == 1
        request = mmap[0]['call']; result = mmap[0]['result']
        assert [request[k] for k in ['a0', 'a1', 'a2', 'a3']] == [0, 0x100000, 3, 0x141]
        assert result['a3'] == 0 and 0 < result['v0'] < 0x80000000 and result['v0'] % 8192 == 0
        sigactions = [x for x in events if x['call']['syscall'] == 1162 and x['call']['a0'] in [10, 11]]
        assert len(sigactions) == 2 and all(x['result'] == dict(syscall=1162, v0=89, a3=1) for x in sigactions)
        traces[name] = dict(installer_mmap=mmap[0], signal_registration=sigactions,
            unsupported=[x for x in events if x['result']['v0'] == 89 and x['result']['a3'] == 1])
        if name == 'hardware':
            assert 'machfile"' in raw
            file_maps = [x for x in events if x['call']['syscall'] == 1134 and x['call']['a1'] == 5025]
            assert len(file_maps) == 1 and file_maps[0]['call']['a2'] == 1 and file_maps[0]['call']['a3'] == 1 and file_maps[0]['result']['a3'] == 0
            traces[name]['machfile_mmap'] = file_maps[0]
        else:
            spawns = [x for x in events if x['call']['syscall'] == 1129]
            assert len(spawns) == 1
            spawn = spawns[0]
            assert spawn['call']['pc'] == 0xfa75038 and spawn['call']['a0'] == 0xfa750a8 and spawn['call']['a1'] == 0x3000040
            parent, child = spawn['pid'], spawn['result']['v0']
            assert 1 < child < 0x80000000 and child != parent and spawn['result']['a3'] == 0
            arms = [x for x in events if x['pid'] == child and x['call']['syscall'] == 1130 and x['call']['a0'] == 6]
            assert len(arms) == 1 and arms[0]['call']['a1'] == parent and arms[0]['result'] == dict(syscall=1130, v0=0, a3=0)
            executions = [x for x in events if x['pid'] == child and x['call']['syscall'] == 1059]
            assert len(executions) == 1
            # Successful exec replaces registers: its traced a3 is not an
            # ordinary errno flag. Native loader/name records establish handoff.
            assert re.search(r'^\s*'+str(child)+r'\s+\d+\s+sh\s+NAMI  "/bin/sh"', raw, re.M)
            assert re.search(r'^\s*'+str(child)+r'\s+\d+\s+sh\s+NAMI  "/lib/libc.so.12"', raw, re.M)
            assert events.index(arms[0]) < events.index(executions[0]) < events.index(spawn)
            duplicates = [x for x in events if x['pid'] == child and x['call']['syscall'] == 1062 and x['call']['a1'] == 0]
            assert len(duplicates) == 2
            assert [(x['call']['a0'], x['call']['a2']) for x in duplicates] == [(4, 1), (6, 2)]
            assert [x['result'] for x in duplicates] == [dict(syscall=1062, v0=n, a3=0) for n in [1, 2]]
            assert all(events.index(x) < events.index(executions[0]) for x in duplicates)
            clocks = [x for x in events if x['pid'] == parent and x['call']['syscall'] == 1128]
            assert len(clocks) >= 10 and all(x['result'] == dict(syscall=1128, v0=0, a3=0) for x in clocks)
            seconds = [x for x in events if x['pid'] == parent and x['call']['syscall'] == 1013]
            assert len(seconds) >= 1 and all(x['result']['a3'] == 0 and 0 < x['result']['v0'] < 0x80000000 for x in seconds)
            selects = [x for x in events if x['pid'] == parent and x['call']['syscall'] == 1100]
            assert len(selects) >= 3 and any(x['result']['a3'] == 0 for x in selects)
            searches = [m[1] for m in re.finditer(r'^\s*'+str(child)+r'\s+\d+\s+sh\s+NAMI  "([^"\n]+)"', raw, re.M)]
            for utility in ['ls', 'mkdir']:
                assert '/usr/bin/'+utility in searches and utility in searches and '/bin/'+utility not in searches
            assert 'NAMI  "/cdrom/dist' not in raw
            assert 'PSIG  SIGKILL' in raw
            traces[name].update(subcommand_spawn=spawn, armed_release=arms[0], child_exec=executions[0],
                descriptor_duplicates=duplicates, gettimeofday_successes=len(clocks), time_successes=seconds, gettimeofday_example=clocks[-1],
                select_calls=len(selects), helper_searches=searches,
                note='Trace a3 after successful exec belongs to the replacement image; it is not an errno flag.')

    revision = '5aca2679d78276864d2980a08314887b2058fb2c'
    evidence = []
    for path in ['sys/compat/irix/irix_syscall.h', 'sys/compat/irix/irix_fcntl.h', 'sys/compat/svr4/svr4_fcntl.h']:
        data = subprocess.check_output(['git', '-C', str(ROOT.parent/'NetBSD-nixbench'), 'show', revision+':'+path])
        evidence.append(dict(revision=revision, path=path, sha256=hashlib.sha256(data).hexdigest()))
        if path.endswith('svr4_fcntl.h'):
            assert re.search(rb'SVR4_F_DUPFD\s+0', data)
        elif path.endswith('irix_syscall.h'):
            assert re.search(rb'IRIX_SYS_gettimeofday\s+128', data)
        else:
            assert re.search(rb'IRIX_F_DUPFD\s+SVR4_F_DUPFD', data)
    report = dict(schema=1, status='installer-time-progress-helper-boundary',
        installation_success=False, pin_label_note=time_abi.PIN_LABEL_NOTE, hardware_report_printed=True, hardware_identification_complete=False,
        distribution_read=False, qualifier_sha256=sha(Path(__file__)),
        trace_decoder_sha256=sha(ROOT/'scripts/probe-irix-tcp.py'), pin=pin,
        source_evidence=evidence, manifest_sha256=run['manifest_sha256'], inputs_sha256=run['inputs_sha256'],
        root_session_home='/', native_home='/usr/people/xiritest', native_write_foreign_read=True,
        graphical_login_qualified=False, native_controls=4, cases=run['cases'], traces=traces,
        run=dict(directory=str(a.run), result_sha256=sha(a.run/'result.json'),
                 serial_sha256=sha(a.run/'serial.log'), clean_shutdown=True, sources=run['sources']),
        limitations=[
            'Distribution attempt reaches its 30-second watchdog; this is not installation success.',
            'F_DUPFD now creates both requested stdout/stderr descriptors before native shell exec.',
            'Time and gettimeofday now succeed. Helper searches still omit /bin; the continuing timeout needs further helper/output/wait diagnosis.',
            'Signal registration, hardware queries, systeminfo, umask and creat remain unsupported in the trace.',
            'This installer report makes no installation or catalog-entry claim; xclock success is qualified separately.'])
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print('Verified original-inst time success, native shell exec and remaining helper boundary')


if __name__ == '__main__':
    main()
