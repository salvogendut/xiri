#!/usr/bin/env python3
"""Verify the retained 22-target catalog workload and repeated native controls."""
import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import tarfile

from xiri_lab import ROOT, sha256


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=Path, nargs='+', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    source = ROOT/'scripts/qualify-irix-catalog.py'
    spec = importlib.util.spec_from_file_location('catalog_qualification', source)
    catalog = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(catalog)
    historical_path = ROOT/'docs/results/2026-11-03-irix-catalog-shutdown.json'
    historical = json.loads(historical_path.read_text())
    expected = [entry['case'] for entry in historical['observations']]
    assert len(expected) == 22
    runs = []
    for run in a.runs:
        r = json.loads((run/'result.json').read_text())
        assert r['status'] == 'observed' and r['clean_shutdown'] and r['source_unchanged']
        assert not r.get('error') and not r.get('cleanup_error')
        assert r['control_repetitions'] == len(r['guard_replays']) == 5
        assert [entry['case'] for entry in r['cases']] == expected
        assert sha256(run/'harness.py') == r['harness_sha256']
        assert sha256(run/'observations.tgz') == r['observations_sha256']
        for name, digest in r['media_sources'].items():
            assert sha256(run/'media'/name) == digest
            assert digest == historical['media_sources'][name], name
        for control in r['guard_replays']:
            assert control.count('CATALOG_NATIVE_CHILD_FINISHED') == 1
            guards = re.findall(r'^GUARD (.+)$', control, re.M)
            assert len(guards) == 2
            for index, line in enumerate(guards):
                g = dict(field.split('=', 1) for field in line.split())
                assert all(g[k] == v for k, v in dict(exit='37', signal='0', absent='1',
                    valid='1', tracked='2', remaining='0', uid='1234', gid='1234').items())
                assert g['reason'] == ('leader-exit', 'timeout')[index]
                assert g['stopped'] == str(index)
        assert r['query_timeout_control'] == 'SURVEY_SERVER_HELD\nQUERY_STATUS=142\n'
        assert 'unmounting done' in r['shutdown_log'][-2048:] and 'halting...' in r['shutdown_log'][-256:]
        with tarfile.open(run/'observations.tgz') as archive:
            observations = catalog.summarize(run, r, archive)
        assert all(entry['cleanup_verified'] for entry in observations)
        bundle = Path(r['bundle'])
        candidates = [bundle/'manifest.json', bundle/'verification/build-manifest.json',
                      bundle/'verification'/('manifest-'+r['manifest_sha256']+'.json')]
        frozen = next(path for path in candidates if path.exists() and sha256(path) == r['manifest_sha256'])
        manifest = json.loads(frozen.read_text())
        assert manifest['pin'] == r['pin'] and manifest['irix_module'] == r['module']
        assert sha256(bundle/'netbsd-xiri.chd') == manifest['chd_sha256']
        assert sha256(bundle/'emulator/iris') == r['pin']['emulator_sha256']
        runs.append(dict(run=str(run), result_sha256=sha256(run/'result.json'),
            archive_sha256=r['observations_sha256'], serial_sha256=sha256(run/'serial.log'),
            manifest=str(frozen), manifest_sha256=r['manifest_sha256'],
            chd_sha256=manifest['chd_sha256'], core_sha256=r['pin']['native_kernel_sha256'],
            module_sha256=r['module']['sha256'], emulator_revision=r['pin']['emulator_revision'],
            harness_sha256=r['harness_sha256'], control_repetitions=5, native_launches=10,
            guard_replays=r['guard_replays'], clean_shutdown=True, source_unchanged=True,
            all_launch_cleanup_verified=True, counts=dict(Counter(e['status'] for e in observations)),
            observations=[dict(case=e['case']['id'], target=e['case']['target'], status=e['status'],
                guard=e['guard'], new_window_count=len(e['new_windows']),
                cleanup_verified=True, stdout=e['stdout'], stderr=e['stderr']) for e in observations]))
    assert len({r['emulator_revision'] for r in runs}) == 1
    report = dict(schema=1, status='passed-system-replay', old_failure_resolved=False,
        historical_record=str(historical_path.relative_to(ROOT)), historical_sha256=sha256(historical_path),
        qualifier_sha256=sha256(Path(__file__)), catalog_qualifier_sha256=sha256(source), runs=runs,
        limitations=['The original hang did not recur; these passes do not establish its cause.',
            'Five control pairs precede each 22-target batch; timing differs from the historical single-pair run.',
            'Old/new bundles include cumulative fixes, so this is not an isolated causal experiment.',
            'Application observations cover bounded startup and cleanup, not full application support.'])
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2)+'\n')
    print(f'Verified {len(runs)} complete 22-target replays and {10*len(runs)} native launches')


if __name__ == '__main__':
    main()
