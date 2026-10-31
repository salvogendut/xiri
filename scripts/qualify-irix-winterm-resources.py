#!/usr/bin/env python3
"""Verify original SGI font import controls and paired xwsh resource attempts."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('resources', ROOT / 'scripts/probe-irix-winterm-resources.py')
resources = importlib.util.module_from_spec(spec)
spec.loader.exec_module(resources)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs=2, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'lab/irix-x11-fonts/manifest.json').read_text())
    pin = json.loads((ROOT / 'lab/irix-siocnread/baseline.json').read_text())
    report = dict(schema=1, status='native-font-import-observed-xwsh-startup-fault-remains',
                  kernel_pin=pin, manifest_sha256=digest(ROOT / 'lab/irix-x11-fonts/manifest.json'),
                  qualifier_sha256=digest(Path(__file__)), fonts_indexed=22,
                  native_rendered_font=resources.FONT, runs=[])
    modes = set()
    for directory in args.runs:
        directory = directory.resolve()
        run = json.loads((directory / 'result.json').read_text())
        assert run['mode'] not in modes
        modes.add(run['mode'])
        assert run['status'] == 'observed' and run['clean_shutdown'] and run['native_x11_after']
        assert run['pin'] == pin and run['manifest'] == manifest
        assert digest(ROOT / run['seed'] / 'result.json') == run['seed_result_sha256']
        for path, sha in run['sources'].items():
            assert digest(ROOT / path) == sha, path
        for name, sha in run['synthetic_accounts'].items():
            assert digest(directory / 'media' / name) == sha
        assert 'unmatched' in run['fonts_before']
        assert resources.FONT in run['fonts_after']
        lines = run['generated_index'].splitlines()
        assert int(lines[0]) == len(lines) - 1 == 22
        assert {line.split(None, 1)[1] for line in lines[1:]} == {f['xlfd'] for f in manifest['fonts']}
        assert len(run['controls']) == 2
        for control in run['controls']:
            assert 'Map State: IsViewable' in control['window']
            assert control['actual'] == dict(errno_bytes=0, errno=0, exit=-1, signal=9,
                                             killed=1, stdout='', stderr='')
            assert digest(directory / ('native-' + control['phase'] + '.xwd')) == control['frame_sha256']
        assert {c['uid'] for c in run['controls']} == {0, 1234}
        cases = []
        for case in run['cases']:
            name = case['name']
            parent = (directory / (name + '.parent')).read_text()
            assert resources.runtime.observation(parent) == case['actual']
            actual = case['actual']
            assert {k:actual[k] for k in ['errno_bytes','errno','exit','signal','killed']} == dict(
                errno_bytes=0,errno=0,exit=-1,signal=11,killed=0)
            assert 'no password entry' not in actual['stderr']
            assert "X doesn't support locale" in actual['stderr'] and "Can't open font" in actual['stderr']
            raw = (directory / (name + '.kdump')).read_text()
            assert resources.tcp.trace_records(raw, 'irix_o32', True) == case['calls']
            assert resources.tcp.trace_records(raw, 'irix_ret', True) == case['returns']
            assert digest(directory / (name + '.xwd')) == case['frame_sha256']
            assert '0 children.' in case['tree']
            assert case['frame_sha256'] == '7d6c819d66a7d48c67d94a281e4910478db108630bac8d8da98a88653a4a7f6b'
            socket_calls = sum(c.startswith('syscall=1107 ') for c in case['calls'])
            connect_calls = sum(c.startswith('syscall=1091 ') for c in case['calls'])
            assert socket_calls == connect_calls == 1
            cases.append(dict(name=name, stage=case['stage'], uid=case['uid'], font=case['font'],
                              signal=11, intentional_kill=False, locale_warning=True, font_warning=True,
                              account_lookup_failure=False, socket_calls=socket_calls, connect_calls=connect_calls,
                              empty_window_tree=True, frame_sha256=case['frame_sha256'],
                              elapsed_ms=int(re.search(r'^ELAPSED_MS (\d+)$', parent, re.M)[1]),
                              error_returns=dict(Counter(x for x in case['returns'] if 'a3=1' in x)),
                              trace_sha256=digest(directory / (name + '.kdump')),
                              parent_sha256=digest(directory / (name + '.parent'))))
        assert {(c['stage'],c['uid'],c['font']) for c in cases} == {
            (stage,uid,font) for stage in ['fonts','fonts-locale'] for uid in [0,1234] for font in [None,'fixed']}
        report['runs'].append(dict(mode=run['mode'], directory=str(directory.relative_to(ROOT)),
                                  clean_shutdown=True, original_font_previously_absent=True,
                                  native_controls=run['controls'], synthetic_accounts=run['synthetic_accounts'],
                                  generated_index_sha256=hashlib.sha256(run['generated_index'].encode()).hexdigest(),
                                  font_properties_sha256=hashlib.sha256(run['fonts_after'].encode()).hexdigest(),
                                  cases=cases, execution_sources=run['sources'],
                                  result_sha256=digest(directory / 'result.json'),
                                  serial_sha256=digest(directory / 'serial.log')))
    assert modes == {'ci', 'ordinary'}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Checked 22 indexed fonts, four native font controls, 16 xwsh attempts and both shutdowns')


if __name__ == '__main__':
    main()
