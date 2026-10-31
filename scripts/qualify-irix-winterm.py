#!/usr/bin/env python3
"""Verify retained original winterm/xwsh opening attempts and native controls."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def module(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / filename)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


tcp = module('tcp', 'probe-irix-tcp.py')
runtime = module('runtime', 'probe-irix-runtime.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs=2, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    pin = json.loads((ROOT / 'lab/irix-siocnread/baseline.json').read_text())
    manifest = ROOT / 'lab/irix-winterm/manifest.json'
    report = dict(schema=1, status='opening-attempts-observed', kernel_pin=pin,
                  manifest_sha256=digest(manifest), qualifier_sha256=digest(Path(__file__)),
                  original_irix_shell_tested=False, runs=[])
    modes = set()
    for directory in args.runs:
        directory = directory.resolve()
        run = json.loads((directory / 'result.json').read_text())
        assert run['mode'] not in modes
        modes.add(run['mode'])
        assert run['status'] == 'observed' and run['clean_shutdown'] and run['native_x11_after']
        assert run['pin'] == pin and run['manifest_sha256'] == digest(manifest)
        assert digest(ROOT / run['seed'] / 'result.json') == run['seed_result_sha256']
        for path, sha in run['sources'].items():
            assert digest(ROOT / path) == sha, path
        assert len(run['controls']) == 2
        for control in run['controls']:
            assert 'Map State: IsViewable' in control['window']
            assert control['actual'] == dict(errno_bytes=0, errno=0, exit=-1, signal=9,
                                             killed=1, stdout='', stderr='')
            assert digest(directory / ('native-' + control['phase'] + '.xwd')) == control['frame_sha256']
        assert {c['uid'] for c in run['controls']} == {0, 1234}
        assert all('/bin/' + s in run['shells'] for s in ['sh', 'ksh', 'csh'])
        assert re.search(r'^root:[^\n]*:/bin/sh$', run['shells'], re.M)
        cases = []
        for case in run['cases']:
            name = case['kind'] + ('-font' if case['font'] else '') + '-' + str(case['uid'])
            parent = (directory / (name + '.parent')).read_text()
            assert runtime.observation(parent) == case['actual']
            assert case['actual']['errno_bytes'] == 0 and case['actual']['errno'] == 0
            assert case['actual']['exit'] != 125, 'native session setup failed'
            raw = (directory / (name + '.kdump')).read_text()
            assert tcp.trace_records(raw, 'irix_o32', True) == case['calls']
            assert tcp.trace_records(raw, 'irix_ret', True) == case['returns']
            assert digest(directory / (name + '.xwd')) == case['frame_sha256']
            failures = Counter(x for x in case['returns'] if 'a3=1' in x)
            stderr = case['actual']['stderr']
            assert '0 children.' in case['tree']
            assert case['frame_sha256'] == '7d6c819d66a7d48c67d94a281e4910478db108630bac8d8da98a88653a4a7f6b'
            socket_calls = sum(c.startswith('syscall=1107 ') for c in case['calls'])
            connect_calls = sum(c.startswith('syscall=1091 ') for c in case['calls'])
            assert socket_calls == connect_calls == (1 if case['uid'] == 0 else 0)
            if case['kind'] == 'xwsh':
                assert (case['actual']['exit'], case['actual']['signal'], case['actual']['killed']) == (
                    (-1, 11, 0) if case['uid'] == 0 else (255, 0, 0))
                if case['uid'] == 0:
                    assert "X doesn't support locale" in stderr and "Can't open font" in stderr
                else:
                    assert 'no password entry for you' in stderr
            else:
                assert (case['actual']['exit'], case['actual']['signal'], case['actual']['killed']) == (0, 0, 0)
                assert 'Cannot execute ELF binary' in stderr
            cases.append(dict(kind=case['kind'], uid=case['uid'], font=case['font'],
                              parent={k:case['actual'][k] for k in ['errno_bytes','errno','exit','signal','killed']},
                              elapsed_ms=int(re.search(r'^ELAPSED_MS (\d+)$', parent, re.M)[1]),
                              locale_warning="X doesn't support locale" in stderr,
                              font_warning="Can't open font" in stderr,
                              helper_exec_error='Cannot execute ELF binary' in stderr,
                              account_lookup_failure='no password entry for you' in stderr,
                              empty_window_tree='0 children.' in case['tree'],
                              frame_sha256=case['frame_sha256'],
                              socket_calls=socket_calls, connect_calls=connect_calls,
                              error_returns=dict(failures),
                              trace_sha256=digest(directory / (name + '.kdump')),
                              parent_sha256=digest(directory / (name + '.parent'))))
        expected = {(kind, uid, font) for kind in ['winterm', 'xwsh'] for uid in [0, 1234]
                    for font in ([None, run['font']] if run['font'] else [None])}
        assert {(c['kind'], c['uid'], c['font']) for c in cases} == expected
        report['runs'].append(dict(mode=run['mode'], directory=str(directory.relative_to(ROOT)),
                                  clean_shutdown=True, native_terminal_controls=run['controls'],
                                  available_shells=['/bin/sh', '/bin/ksh', '/bin/csh'], root_shell='/bin/sh',
                                  cases=cases, execution_sources=run['sources'],
                                  result_sha256=digest(directory / 'result.json'),
                                  serial_sha256=digest(directory / 'serial.log')))
    assert modes == {'ci', 'ordinary'}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Checked', sum(len(r['cases']) for r in report['runs']), 'terminal attempts and four native terminal controls')


if __name__ == '__main__':
    main()
