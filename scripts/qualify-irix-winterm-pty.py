#!/usr/bin/env python3
"""Check original libc allocation, xwsh's fork boundary and native controls."""
import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('access', ROOT/'scripts/qualify-irix-winterm-access.py')
access = importlib.util.module_from_spec(spec)
spec.loader.exec_module(access)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normal(stdout='', code=0, stderr=''):
    return dict(errno_bytes=0, errno=0, exit=code, signal=0, killed=0,
                stdout=stdout, stderr=stderr)


def native_controls(controls):
    assert len(controls) == 4
    assert {(c['phase'], c['uid']) for c in controls} == {
        (phase, uid) for phase in ['before', 'after'] for uid in [0, 1234]}
    for c in controls:
        uid = c['uid']
        text = ''.join(
            f'ROUND {i} uid={uid} gid={uid}\n'
            'MASTER fd=3 mode=020666 uid=0 gid=0 major=23 minor=0 flags=0x6\n'
            'SLAVE_PATH /dev/pts/0\n'
            f'SLAVE fd=4 mode=020600 uid={uid} gid=0 major=22 minor=0 flags=0x6\n'
            'TRANSFER XIRI_MASTER_TO_SLAVE\nTRANSFER XIRI_SLAVE_TO_MASTER\n'
            'EMPTY n=-1 errno=35\n' for i in range(3)) + 'NATIVE_PTY_PASS\n'
        assert c['actual'] == normal(text)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--winterm', nargs=2, type=Path, required=True)
    p.add_argument('--libc', nargs=2, type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    pin = json.loads((ROOT/'lab/irix-pty/baseline.json').read_text())
    fixture = json.loads((ROOT/'lab/irix-pty/libc-fixture.json').read_text())
    assert sha(ROOT/'lab/irix-pty/fixture.c') == fixture['source_sha256']
    reference = ROOT/fixture['reference_directory']
    assert sha(reference/'result.json') == fixture['reference_result_sha256']
    original = json.loads((reference/'result.json').read_text())
    assert original['status'] == 'observed' and original['clean_shutdown']
    assert sha(reference/'outputs.tar') == original['archive_sha256']
    assert sha(reference/'probe-n32') == fixture['fixture_sha256']
    assert sha(ROOT/'lab/irix-pty/reference-measure.sh') == original['payload_sha256']
    assert sha(ROOT/'scripts/probe-irix-reference-pty.py') == original['harness_sha256']
    statuses = re.findall(r'^CASE (\S+) (\d+)$', (reference/'status.txt').read_text(), re.M)
    expected_names = {f'n32-{item}-{flags}' for item in ['getpty', '_dev_ptc', 'regular', '_dev_null', 'fifo'] for flags in [2, 6, 130, 134]}
    assert len(statuses) == 20 and {n for n, _ in statuses} == expected_names
    original_cases = []
    for name, status in statuses:
        assert status == '0' and not (reference/(name+'.err')).read_text()
        text = (reference/(name+'.out')).read_text()
        assert text.startswith('IDENTITY uid=0 euid=0 gid=0 egid=0 abi=2\n')
        flags = int(name.rsplit('-', 1)[1])
        observed_flags = re.findall(r'^FLAGS value=(\S+) errno=0$', text, re.M)
        expected_flags = ['0x'+format(130 if flags == 134 else flags, 'x')]
        if name.startswith('n32-getpty-'):
            assert 'GETPTY success=1 errno=0 path=/dev/ttyq0\n' in text
            assert 'SLAVE_OPEN success=1 errno=0\n' in text
            assert 'STAT master rc=0 errno=0 mode=020000 uid=0 gid=0 rdev=0x380000\n' in text
            assert 'STAT slave rc=0 errno=0 mode=020600 uid=0 gid=0 rdev=0x3c0000\n' in text
            assert re.search(r'^TERM rc=0 errno=0 size=48 hex=[0-9a-f]{96}$', text, re.M)
        else:
            assert 'OPEN success=1 errno=0\n' in text
            expected_flags += ['0x6', '0x82', '0x82', '0x2']
        assert observed_flags == expected_flags, name
        original_cases.append(dict(name=name, exit=0, flags=observed_flags,
                                   stdout_sha256=sha(reference/(name+'.out'))))
    report = dict(schema=1, status='pty-allocation-qualified-fork-blocked', kernel_pin=pin,
                  terminal_window_qualified=False, libc_fixture=fixture,
                  original_libc_cases=original_cases, libc_runs=[], winterm_runs=[])
    for group, directories in [('libc', a.libc), ('winterm', a.winterm)]:
        seen = set()
        for d in directories:
            r = json.loads((d/'result.json').read_text())
            assert r['status'] == 'observed' and r['clean_shutdown'] and r['pin'] == pin
            assert r['mode'] not in seen
            seen.add(r['mode'])
            for path, h in r['sources'].items():
                assert sha(ROOT/path) == h
            native_controls(r['controls'] if group == 'libc' else r['native_pty_controls'])
            checked = []
            if group == 'libc':
                assert r['fixture'] == fixture and len(r['cases']) == 40
                assert {(c['uid'], c['item'], c['flags']) for c in r['cases']} == {
                    (u, item, f) for u in [0, 1234]
                    for item in ['getpty', '/dev/ptc', 'regular', '/dev/null', 'fifo']
                    for f in [2, 6, 130, 134]}
                for c in r['cases']:
                    uid, item, flags = c['uid'], c['item'], c['flags']
                    initial_flags = '0x2' if flags == 2 else '0x82'
                    text = f'IDENTITY uid={uid} euid={uid} gid={uid} egid={uid} abi=2\n'
                    if item == 'getpty':
                        text += ('GETPTY success=1 errno=89 path=/dev/ttyq0\n'
                                 'STAT master rc=0 errno=0 mode=020666 uid=0 gid=0 rdev=0x380000\n'
                                 f'FLAGS value={initial_flags} errno=0\n'
                                 'SLAVE_OPEN success=1 errno=0\n'
                                 f'STAT slave rc=0 errno=0 mode=020600 uid={uid} gid=0 rdev=0x3c0000\n'
                                 'TERM rc=-1 errno=89 size=48 hex=' + 'a5'*48 + '\n')
                        code = 12
                    else:
                        mode, dev = {'/dev/ptc': ('020666', '0x380000'),
                                     'regular': ('0100666', '0'),
                                     '/dev/null': ('020666', '0x500002'),
                                     'fifo': ('010666', '0')}[item]
                        text += ('OPEN success=1 errno=0\n'
                                 f'STAT open rc=0 errno=0 mode={mode} uid=0 gid=0 rdev={dev}\n'
                                 f'FLAGS value={initial_flags} errno=0\n')
                        for arg, value in [('0x4', '0x82'), ('0x80', '0x82'), ('0x84', '0x82'), ('0', '0x2')]:
                            text += f'SETFL arg={arg} rc=0 errno=0\nFLAGS value={value} errno=0\n'
                        code = 0
                    assert c['actual'] == normal(text, code), c['name']
                    trace = d/(c['name']+'.kdump')
                    assert sha(trace) == c['trace_sha256']
                    if item == 'getpty':
                        ev = access.events(trace.read_text())
                        assert any(e['call']['syscall'] == 1054 and e['call']['a1'] == 0x54d5
                                   and e['ret'] == dict(syscall=1054, v0=89, a3=1) for e in ev)
                    checked.append(c)
            else:
                assert r['native_x11_after'] and len(r['controls']) == len(r['native_font_controls']) == 2
                for key in ['controls', 'native_font_controls']:
                    assert {c['phase'] for c in r[key]} == {'before', 'after'}
                    for c in r[key]:
                        assert 'Map State: IsViewable' in c['window'] and not c['stderr']
                for c in r['controls']:
                    assert c['guards_intact'] and c['entry_exit'] == 37
                assert len(r['cases']) == 4
                assert {(c['uid'], c['font']) for c in r['cases']} == {
                    (u, f) for u in [0, 1234] for f in [None, 'fixed']}
                for c in r['cases']:
                    assert c['actual'] == normal('', 255, "/emul/irix/usr/sbin/xwsh: Function not implemented: can't start command\n")
                    assert '0 children.' in c['tree'] and 'fault' not in c
                    trace = d/(c['name']+'.kdump')
                    ev = access.events(trace.read_text())
                    starts = [i for i,e in enumerate(ev) if e['call']['syscall'] == 1005 and '/emul/irix/dev/ptc' in e['paths']]
                    assert len(starts) == 1
                    tail = ev[starts[0]:]
                    assert tail[0]['call']['a1'] == 6 and tail[0]['ret']['a3'] == 0
                    fd = tail[0]['ret']['v0']
                    for path in ['/emul/irix/dev/ttyq0', '/emul/irix/dev/pts/0']:
                        assert any(e['call']['syscall'] == 1015 and path in e['paths']
                                   and e['call']['a1'] == 0o622 and e['ret'] == dict(syscall=1015, v0=0, a3=0) for e in tail)
                    unlock = [i for i,e in enumerate(tail) if e['call']['syscall'] == 1054 and e['call']['a1'] == 0x5308]
                    fork = [i for i,e in enumerate(tail) if e['call']['syscall'] == 1002]
                    assert len(unlock) == len(fork) == 1 and unlock[0] < fork[0]
                    assert tail[unlock[0]]['call']['a0'] == fd
                    assert tail[unlock[0]]['ret'] == dict(syscall=1054, v0=0, a3=0)
                    assert tail[fork[0]]['ret'] == dict(syscall=1002, v0=89, a3=1)
                    assert all(e['ret'] == dict(syscall=1164, v0=89, a3=1)
                               for e in tail if e['call']['syscall'] == 1164)
                    assert sha(d/(c['name']+'.xwd')) == c['frame_sha256']
                    checked.append(dict(name=c['name'], uid=c['uid'], font=c['font'], actual=c['actual'],
                                        pty_events=tail[:fork[0]+1], trace_sha256=sha(trace), frame_sha256=c['frame_sha256']))
            report[group+'_runs'].append(dict(directory=str(d), mode=r['mode'], clean_shutdown=True,
                result_sha256=sha(d/'result.json'), native_pty_controls=4, native_pty_cycles=12,
                cases=checked, sources=r['sources']))
        assert seen == {'ci', 'ordinary'}
    report['qualifier_sha256'] = sha(Path(__file__))
    report['next_priority'] = 'Measure fork, signal masks and native exec/session behavior; then terminal modes and interactive shell/input; evaluate 4Dwm afterward'
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print('80 libc cases and eight xwsh starts checked; allocation succeeds, terminal modes/fork remain unsupported')


if __name__ == '__main__':
    main()
