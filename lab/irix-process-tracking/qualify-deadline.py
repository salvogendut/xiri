#!/usr/bin/env python3
"""Verify a measured cleanup-deadline failure and its corrected native replay."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
MODES = ('fast', 'term', 'kill', 'live', 'signal', 'logout', 'leader')
FIXTURES = ('delay.c', 'deadline-case.c', 'deadline-tests.sh')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fields(text, prefix):
    lines = [line[len(prefix):] for line in text.splitlines() if line.startswith(prefix)]
    assert len(lines) == 1, (prefix, lines)
    pairs = [word.split('=', 1) for word in lines[0].split()]
    result = dict(pairs)
    assert len(result) == len(pairs)
    return result


def verify(cases, corrected):
    assert set(cases) == set(MODES)
    for mode, entry in cases.items():
        c, g = entry['case'], entry['guard']
        expected = 2 if mode == 'live' else 37 if mode == 'leader' else 0
        late = mode not in ('fast', 'live')
        assert c['case'] == mode and c['uid'] == '1234'
        assert int(c['expected']) == expected
        assert c['rc'] == str(expected if corrected or not late else 2)
        assert c['live'] == c['expected_live'] == str(int(mode == 'live'))
        assert c['sentinel'] == c['safe_cleanup'] == '1' and c['sentinel_rc'] == '0'
        incomplete = mode == 'live' or (late and not corrected)
        assert g['absent'] == g['valid'] == str(int(not incomplete))
        assert g['remaining'] == str(int(incomplete))
        assert g['tracked'] == ('2' if mode == 'leader' else '1')
        assert g['uid'] == g['gid'] == '1234'
        reason = {'signal':'signal', 'logout':'logout', 'leader':'leader-exit'}.get(mode, 'timeout')
        assert g['reason'] == reason
        assert entry['close']['error'] == '0' and entry['close']['injected'] == '1'
        assert entry['close']['pending'] == str(int(late and not corrected))
        if late:
            assert int(entry['return']['elapsed']) >= 7000
            assert entry['return']['pid'] == c['worker']
            assert entry['return']['present'] == '0' or entry['return']['state'] in ('5', '6')
            assert entry['before']['pending'] == '1'
            if not corrected:
                event = fields(entry['trace'], 'PENDING ')
                assert event['pid'] == c['worker']
                assert int(event['filter']) == 4 and int(event['fflags'],16) == 0x80000000
                assert int(event['data']) == (9 if mode == 'kill' else 15)
            else:
                assert not re.search(r'^PENDING ', entry['trace'], re.M)
                assert g['exit'] == ('37' if mode == 'leader' else '-1')
                assert g['signal'] == ('0' if mode == 'leader' else '9' if mode == 'kill' else '15')
        if mode == 'live':
            assert entry['before']['pending'] == '0'
            assert entry['return']['present'] == entry['return']['uvalid'] == '1'
            assert entry['return']['state'] == '2'
            if corrected:
                left = fields(entry['trace'], 'remaining ')
                assert left['pid'] == c['worker'] and left['present'] == left['identity'] == '1'
                assert left['state'] == '2' and left['uvalid'] == '1'
                assert left['start'] == left['current_start']


def read_run(run, corrected):
    r = json.loads((run/'result.json').read_text())
    assert r['clean_shutdown'] and r['source_unchanged']
    assert 'unmounting done' in r['shutdown_log'] and 'halting...' in r['shutdown_log']
    assert r['status'] == ('passed' if corrected else 'error')
    assert r['deadline_status'] == ('0' if corrected else '1')
    assert len(r['events']) == 4 and all(e['status'] == '0' for e in r['events'])
    assert r['harness_sha256'] == digest((run/'harness.py').read_bytes())
    assert r['archive_sha256'] == digest((run/'observations.tgz').read_bytes())
    cases, binaries = {}, {}
    with tarfile.open(run/'observations.tgz') as archive:
        assert len(archive.getnames()) == len(set(archive.getnames()))
        def read(name): return archive.extractfile('xiri-tracking/'+name).read()
        for name in FIXTURES:
            source = 'lab/irix-process-tracking/'+name
            assert digest(read(name)) == r['sources'][source] == digest((ROOT/source).read_bytes())
        for name in ('delay.so', 'deadline-case'):
            binaries[name] = digest(read(name))
            assert binaries[name] in r['deadline_hashes']
        if corrected:
            for name in ('session-guard', 'session-guard-installed'):
                binaries[name] = digest(read(name))
            assert binaries['session-guard'] == r['candidate_guard_sha256']
            source = 'runtime/libexec/session-guard.c'
            assert digest(read('session-guard.c')) == r['sources'][source] == digest((ROOT/source).read_bytes())
            assert r['guard_tests_status'] == '0' and 'SESSION_GUARD_TESTS_OK' in r['guard_tests']
        for mode in MODES:
            trace = read('deadline/'+mode+'.trace').decode()
            failed = not corrected and mode not in ('fast', 'live')
            assert read('deadline/'+mode+'.status').decode().strip() == str(int(failed))
            cases[mode] = dict(case=fields(read('deadline/'+mode+'.case').decode(), 'DEADLINE '),
                guard=fields(read('deadline/'+mode+'.guard').decode(), 'GUARD '),
                before=fields(trace, 'QUEUE_BEFORE_RETURN '),
                close=fields(trace, 'QUEUE_CLOSE '),
                **{'return':fields(trace, 'DELAY_RETURN ')}, trace=trace)
    verify(cases, corrected)
    return dict(run=str(run.relative_to(ROOT)), result_sha256=digest((run/'result.json').read_bytes()),
        archive_sha256=r['archive_sha256'], harness_sha256=r['harness_sha256'],
        chd_sha256=r['chd_sha256'], manifest_sha256=r['manifest_sha256'],
        kernel_sha256=r['pin']['native_kernel_sha256'], module_sha256=r['module']['sha256'],
        emulator_sha256=r['pin']['emulator_sha256'], source_sha256=r['sources'],
        native_lifecycles=r['rounds']*24*4, guest_hashes=r['guest_hashes'],
        binaries=binaries, cases=cases, clean_shutdown=True, source_unchanged=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--before', type=Path, required=True)
    p.add_argument('--after', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--self-test', action='store_true')
    a = p.parse_args()
    before, after = read_run(a.before.resolve(), False), read_run(a.after.resolve(), True)
    for key in ('chd_sha256','manifest_sha256','kernel_sha256','module_sha256','emulator_sha256'):
        assert before[key] == after[key], key
    for name in ('delay.so', 'deadline-case'):
        assert before['binaries'][name] == after['binaries'][name]
    assert after['binaries']['session-guard-installed'] in before['guest_hashes']
    rejected = []
    if a.self_test:
        for mode, section, field, value in [('term','guard','valid','0'),
                ('term','close','pending','1'), ('live','case','live','0'), ('leader','case','rc','0')]:
            bad = copy.deepcopy(after['cases']); bad[mode][section][field] = value
            try: verify(bad, True)
            except AssertionError: rejected.append('.'.join((mode, section, field)))
            else: raise AssertionError('corrupted outcome accepted')
    result = dict(schema=1, status='qualified', before=before, after=after,
        measured_false_failures=5, corrected_scenarios=7, negative_controls_rejected=rejected,
        historical_compview_cause_resolved=False)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print('Qualified: five reproduced false failures corrected; live-child rejection preserved')


if __name__ == '__main__':
    main()
