#!/usr/bin/env python3
"""Check legacy ELF loading and all retained loader/ELF-map regression records."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import tarfile

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('subpage', ROOT/'scripts/qualify-irix-elfmap-subpage.py')
subpage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(subpage)
runtime = subpage.old.rt


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, default=ROOT/'.work/irix-acrobat-probes/manifest.json')
    p.add_argument('--fixtures', type=Path, default=ROOT/'.work/irix-acrobat-probes')
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--run', type=Path, required=True)
    p.add_argument('--reference', type=Path, default=ROOT/'lab/irix-acrobat/reference.json')
    p.add_argument('--diagnostic', action='store_true')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    manifest = json.loads(a.manifest.read_text())
    for name, item in manifest['files'].items():
        assert sha(a.fixtures/name) == item['sha256'], name
    run = json.loads((a.run/('initial.json' if a.diagnostic else 'result.json')).read_text())
    reference = json.loads(a.reference.read_text())
    assert reference['clean_shutdown'] and reference['status'] == 'observed'
    oracle = {o['name']:o for o in reference['observations']}
    assert len(oracle) == 44
    for name, item in reference['fixtures'].items():
        assert item == manifest['files'][name], name
    if not a.diagnostic:
        assert run['clean_shutdown'] and run['source_unchanged']
    expected_logs = {'loader-'+c['name']+'-'+str(uid)+'.log'
                     for c in manifest['loader_cases'] for uid in [0, 1234]}
    expected_logs |= {'map-'+abi+'-'+c['name']+'-'+str(uid)+'.log'
                      for c in manifest['mapping_cases'] for abi in ['o32', 'n32'] for uid in [0, 1234]}
    records = []
    with tarfile.open(a.archive) as archive:
        logs = {m.name.removeprefix('./'): archive.extractfile(m).read().decode()
                for m in archive if m.isfile()}
    assert set(logs) == expected_logs, (set(logs)-expected_logs, expected_logs-set(logs))

    def observe(name, expected, case=None):
        log = logs[name+'.log']
        actual = runtime.observation(log)
        error = None
        record = None
        try:
            assert 'GROUP absent=1' in log
            if case:
                raw = bytes.fromhex(re.search(r'^STDOUT bytes=48 hex=([0-9a-f]+)$', log, re.M)[1])
                record = runtime.elfmap_record(raw)
                data = (a.fixtures/case['input']).read_bytes()
                layout = [struct.unpack_from('>8I', data, 52+32*i) for i in range(2)]
                subpage.check(case, record, layout, 8192)
                if case['name'].startswith('elfmap-legacy-'):
                    original = runtime.elfmap_record(bytes.fromhex(oracle[name.removeprefix('map-')]['stdout_hex']))
                    allowed = {'v0'} if case['block'] else set()
                    if case['action'] in [5, 6, 7]:
                        allowed.add('second_v0')
                    if case['action'] == 7:
                        allowed.add('third_v0')
                    assert all(value == original[key] for key, value in record.items() if key not in allowed), (record, original)
                actual = {k:v for k,v in actual.items() if k != 'stdout'}
            assert actual == expected, (actual, expected)
        except (AssertionError, TypeError) as e:
            error = str(e) or 'record or cleanup mismatch'
        records.append(dict(name=name, passed=error is None, actual=actual, record=record, error=error))

    for case in manifest['loader_cases']:
        success = case['expect'] == 'output'
        expected = dict(errno_bytes=0 if success else 4, errno=0 if success else 8,
                        exit=37 if success else 126, signal=0, killed=0,
                        stdout='XIRI_ABI_PROBE\n' if success else '', stderr='')
        for uid in [0, 1234]:
            observe('loader-'+case['name']+'-'+str(uid), expected)
    for case in manifest['mapping_cases']:
        signal = case['netbsd']['signal']
        expected = dict(errno_bytes=0, errno=0, exit=-1 if signal else 0,
                        signal=signal, killed=0, stderr='')
        for abi in ['o32', 'n32']:
            for uid in [0, 1234]:
                observe('map-'+abi+'-'+case['name']+'-'+str(uid), expected, case)
    passed = all(r['passed'] for r in records)
    result = dict(schema=1, status=('diagnostic' if a.diagnostic else 'passed') if passed else 'mismatch',
                  qualifier_sha256=sha(Path(__file__)), manifest=manifest,
                  reference_sha256=sha(a.reference), paired_legacy_records=len(oracle),
                  archive_sha256=sha(a.archive), run=str(a.run),
                  candidate_module=run['candidate_module'], observations=records)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print(sum(r['passed'] for r in records), '/', len(records), 'ELF executions passed')
    for r in records:
        if not r['passed']:
            print(r['name'], r['error'])
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
