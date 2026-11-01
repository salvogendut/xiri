#!/usr/bin/env python3
"""Compare native sproc records with the qualified reference and explicit guards."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import struct
import tomllib

ROOT = Path(__file__).resolve().parent.parent


def module(name, file):
    s = importlib.util.spec_from_file_location(name, ROOT/'scripts'/file)
    m = importlib.util.module_from_spec(s)
    s.loader.exec_module(m)
    return m


reference = module('reference', 'qualify-irix-sproc.py')
runtime = module('runtime', 'probe-irix-runtime.py')
sha = reference.sha
FEED = reference.FEED
NORMAL = dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stderr='')


def records(data):
    assert len(data) % 256 == 0
    return [list(struct.unpack('>64I', data[i:i+256])) for i in range(0, len(data), 256)]


def check_native(case, ids, data):
    kind = case['symbols']['KIND']
    rows = records(data)
    assert [r[2] for r in rows] == ([1, 0] if kind == 0 else [0])
    for row in rows:
        want = [0]*64
        want[:3] = [0x58475350, kind, row[2]]
        want[56:60] = ids
        if row[2] == 1:
            for i in [8, 11, 14, 17, 20, 23, 26, 29, 44]:
                want[i:i+3] = [122, FEED, 1]
            for i, errno in [(32, 22), (35, 3), (41, 22)]:
                want[i:i+3] = [errno, FEED, 1]
            want[38:41] = [0, FEED, 0]
            want[47] = 0x11
        else:
            want[3:7] = [12 if kind == 2 else 1, 0x11, 0x42 if kind == 1 else 0x22, 0x33]
            want[8:15] = [1, FEED, 0, 0x11223344, 0, FEED, 0]
        assert row == want, (case['name'], row[2],
            [(i, hex(a), hex(b)) for i, (a, b) in enumerate(zip(row, want)) if a != b])
    return len(rows)


def bad_entry(case, ids, data):
    """Native policy rejects zero entry with EFAULT; IRIX only showed a timeout."""
    rows = records(data)
    assert len(rows) == 1
    row = rows[0]
    want = [0]*64
    s = case['symbols']
    want[:6] = [0x58535052, s['CASE'], 0, s['FLAGS'], s['ACTION'], s['TRAP']]
    assert 1 < row[6] < 0x80000000
    assert 0x10000 <= row[47] < 0x80000000 and row[47] % 4 == 0
    want[6] = want[20] = row[6]
    want[8:11] = [14, FEED, 1]
    want[21:24] = [0xbabababa, 0x11223344, 0x98765432]
    want[30:36] = [0, FEED, 0, 1, FEED, 0]
    want[41:44] = [0, FEED, 0]
    want[47] = row[47]
    want[56:60] = ids
    assert row == want, (case['name'], row, want)
    return 1


def qualify(directory):
    r = json.loads((directory/'result.json').read_text())
    assert r['status'] == 'observed-uncompared' and r['scope'] == 'full' and r['clean_shutdown']
    assert tomllib.loads((directory/'iris.toml').read_text())['ci'] == (r['mode'] == 'ci')
    assert r['seed_result_sha256'] == sha(ROOT/r['seed']/'result.json')
    assert r['pin'] == json.loads((ROOT/'lab/irix-sproc'/('o32-baseline.json' if r['kernel_abi'] == 'o32' else 'baseline.json')).read_text())
    assert not r['pin']['source_dirty'] and r['pin']['source_branch'] == 'xiri'
    for p, h in r['sources'].items():
        assert sha(ROOT/p) == h, p
    ref = json.loads((ROOT/'lab/irix-sproc/reference-records.json').read_text())
    assert r['manifest'] == ref['manifest']
    log = (directory/'fixtures.log').read_text()
    total, timed, executions = 0, 0, 0
    for key, mkey in [('observations', 'manifest'), ('native_observations', 'native_manifest')]:
        m = r[mkey]
        assert m['identities'] == [[0]*4, [1234]*4]
        if key == 'native_observations':
            kinds = {'guards': 0, 'local-replace': 1, 'repeat': 2}
            names = {abi+'-'+dispatch+'-'+variant for abi in ['o32', 'n32']
                     for dispatch in ['direct', 'indirect'] for variant in kinds}
            assert len(m['cases']) == 12 and {c['name'] for c in m['cases']} == names
            assert all(c['symbols']['KIND'] == kinds[c['name'].split('-', 2)[2]]
                       and c['identities'] == [0, 1] for c in m['cases'])
        for p, h in m['sources'].items():
            assert sha(ROOT/p) == h, p
        cases = [c for c in m['cases'] if r['kernel_abi'] == 'lp64' or c['abi'] == 'o32']
        obs = {o['name']: o for o in r[key]}
        assert len(obs) == len(r[key]) == len(cases)*2
        assert set(obs) == {c['name']+'-'+str(i) for c in cases for i in [0, 1]}
        for c in cases:
            f = directory/'media'/c['name']
            assert sha(f) == m['files'][c['name']]['sha256'] and f.stat().st_size == m['files'][c['name']]['bytes']
            for i in [0, 1]:
                name = c['name']+'-'+str(i)
                o = obs[name]
                raw = re.search(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+r'$', log, re.M|re.S)
                assert raw and o['group_absent'] and 'GROUP absent=1' in raw[1]
                actual = runtime.observation(raw[1])
                rawdata = re.search(r'^STDOUT bytes=(\d+) hex=([0-9a-f]*)$', raw[1], re.M)
                assert rawdata
                data = bytes.fromhex(rawdata[2])
                assert len(data) == int(rawdata[1])
                actual.pop('stdout')
                assert dict(actual, stdout_hex=data.hex()) == o['actual']
                variant = c['name'].split('-', 2)[2]
                watchdog = key == 'observations' and variant in {'exit', 'exec-no-release'}
                assert actual == (dict(NORMAL, exit=-1, signal=9, killed=1) if watchdog else NORMAL), (name, actual)
                ids = m['identities'][i]
                if key == 'native_observations':
                    total += check_native(c, ids, data)
                elif variant == 'bad-entry':
                    total += bad_entry(c, ids, data)
                else:
                    total += len(reference.qualify_case(c, ids, data, 137 if watchdog else 0,
                        '1' if watchdog else '0', b'', 'clear'))
                timed += watchdog
                executions += 1
    controls = r['controls']
    want_controls = {}
    for phase in ['before', 'after']:
        for uid in [0, 1234]:
            for name, want in [
                ('native-o32', dict(NORMAL, exit=37, stdout='XIRI_ABI_PROBE\n')),
                ('vendor-asa', dict(NORMAL, stdout='XIRI_VENDOR_O32\n')),
                ('native-mmap', dict(NORMAL, stdout=f'NATIVE_MMAP uid={uid} zero=1 shared=1 private=1 close=1 file=1 eof=1\n')),
            ] + ([('vendor-echo', dict(NORMAL, stdout='XIRI_VENDOR_N32\n'))] if r['kernel_abi'] == 'lp64' else []):
                want_controls[(phase, uid, name)] = want
    assert len(controls) == len(want_controls)
    assert {(c['phase'], c['uid'], c['name']):c['actual'] for c in controls} == want_controls
    return dict(run=str(directory.relative_to(ROOT)), mode=r['mode'], kernel_abi=r['kernel_abi'],
        source_revision=r['pin']['source_revision'], executions=executions, records=total,
        checked_words=64*total, watchdog_groups=timed, groups_absent=executions,
        controls=len(controls), clean_shutdown=True,
        hashes={str(p.relative_to(ROOT)):sha(p) for p in [directory/'result.json', directory/'fixtures.log']})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', type=Path, nargs='+')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    reports = [qualify(d.resolve()) for d in a.runs]
    assert len({(r['mode'],r['kernel_abi']) for r in reports}) == len(reports)
    report = dict(schema=1, status='passed', scope='bounded two-member sproc lifecycle; zero entry uses explicit native EFAULT policy',
        runs=reports, qualifier_sha256=sha(Path(__file__)), reference_sha256=sha(ROOT/'lab/irix-sproc/reference-records.json'))
    for key in ['executions', 'records', 'checked_words', 'watchdog_groups', 'groups_absent', 'controls']:
        report[key] = sum(r[key] for r in reports)
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print({k:v for k,v in report.items() if k not in ['runs','scope']})


if __name__ == '__main__':
    main()
