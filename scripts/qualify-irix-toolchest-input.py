#!/usr/bin/env python3
"""Recheck retained Toolchest resource/input observations and private frames."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct

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


def pixels(path):
    data = path.read_bytes()
    h = struct.unpack('>25I', data[:100])
    assert h[1:6] == (7, 2, 24, 640, 480)
    assert h[11] == 32 and h[12] == 2560 and h[14:17] == (0xff0000, 0xff00, 0xff)
    start = h[0] + 12 * h[19]
    bitmap = data[start:]
    assert len(bitmap) == h[12] * h[5]
    colors = [p[0] & 0xffffff for p in struct.iter_unpack('<I' if h[7] == 0 else '>I', bitmap)]
    return dict(sha256=hashlib.sha256(bitmap).hexdigest(),
                sgi_gray76_pixels=colors.count(0xc1c1c1), sgi_dark_gray_pixels=colors.count(0x555555))


def redraw(log):
    match = re.search(r'REDRAW visible=(\d+) before=(\w+) cleared=(\w+) after=(\w+)', log)
    assert match and int(match[1]) >= 1 and match[2] != match[3] and match[2] == match[4]
    return dict(visible=int(match[1]), before=match[2], cleared=match[3], after=match[4])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', nargs=2, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    pin = json.loads((ROOT / 'lab/irix-siocnread/baseline.json').read_text())
    resources = json.loads((ROOT / 'lab/irix-toolchest-input/resources.json').read_text())
    report = dict(schema=1, status='observed', kernel_pin=pin, resources=resources,
                  qualifier_sha256=digest(Path(__file__)), runs=[])
    seen = set()
    for directory in args.runs:
        directory = directory.resolve()
        run = json.loads((directory / 'result.json').read_text())
        assert run['mode'] not in seen
        seen.add(run['mode'])
        assert run['status'] == 'observed' and run['clean_shutdown'] and run['native_x11_after']
        assert run['pin'] == pin and run['resources'] == resources
        assert digest(ROOT / run['seed'] / 'result.json') == run['seed_result_sha256']
        for path, sha in run['sources'].items():
            assert digest(ROOT / path) == sha, path
        assert len(run['controls']) == 2
        for control in run['controls']:
            assert 'BUTTON type=4 button=1 send_event=0 x=40 y=30' in control['input']
            assert 'BUTTON type=5 button=1 send_event=0 x=40 y=30' in control['input']
            assert 'KEY type=2 keysym=0x61 send_event=0' in control['input']
            assert 'KEY type=3 keysym=0xff1b send_event=0' in control['input']
            redraw(control['redraw'])
        cases = []
        for case in run['toolchest']:
            name = case['stage'] + '-' + str(case['uid'])
            parent = (directory / (name + '.parent')).read_text()
            assert runtime.observation(parent) == case['actual']
            assert {k:case['actual'][k] for k in ['errno_bytes','errno','exit','signal','killed']} == dict(errno_bytes=0,errno=0,exit=-1,signal=9,killed=1)
            elapsed = int(re.search(r'^ELAPSED_MS (\d+)$', parent, re.M)[1])
            assert elapsed >= 90000
            raw = (directory / (name + '.kdump')).read_text()
            assert tcp.trace_records(raw, 'irix_o32', True) == case['calls']
            assert tcp.trace_records(raw, 'irix_ret', True) == case['returns']
            frames = {}
            for phase, frame in case['phases'].items():
                path = directory / (name + '-' + phase + '.xwd')
                assert digest(path) == frame['frame_sha256']
                assert int(re.search(r'VISIBLE (\d+)', frame['tree'])[1]) == frame['visible']
                frames[phase] = dict(visible=frame['visible'], frame_sha256=frame['frame_sha256'], pixels=pixels(path))
            assert frames['rest']['visible'] == 8
            assert frames['posted']['visible'] == 13
            assert frames['posted']['pixels']['sha256'] != frames['rest']['pixels']['sha256']
            with_keys = case['stage'] in ['keysyms', 'combined']
            with_colors = case['stage'] in ['colors', 'combined']
            if with_keys:
                assert frames['down']['pixels']['sha256'] != frames['posted']['pixels']['sha256']
                assert [frames[p]['visible'] for p in ['right', 'escape', 'dismissed']] == [15, 13, 8]
            else:
                for phase in ['down', 'right', 'escape', 'dismissed']:
                    assert frames[phase]['pixels']['sha256'] == frames['posted']['pixels']['sha256']
                    assert frames[phase]['visible'] == 13
            assert frames['final']['visible'] == 8
            assert frames['final']['pixels']['sha256'] == frames['rest']['pixels']['sha256']
            assert (frames['rest']['pixels']['sgi_gray76_pixels'] > 1000) == with_colors
            assert (frames['rest']['pixels']['sgi_dark_gray_pixels'] > 0) == with_colors
            if case['stage'] == 'combined':
                assert [frames[p]['visible'] for p in ['keyboard-focus', 'keyboard-f10',
                    'keyboard-down', 'keyboard-right', 'keyboard-escape']] == [8, 8, 13, 15, 13]
                assert frames['keyboard-f10']['pixels']['sha256'] != frames['rest']['pixels']['sha256']
                assert frames['keyboard-down']['pixels']['sha256'] == frames['posted']['pixels']['sha256']
                assert frames['keyboard-escape']['pixels']['sha256'] == frames['posted']['pixels']['sha256']
            stderr = case['actual']['stderr']
            warnings = dict(keysym=stderr.count('translation table syntax error'),
                            gray76=stderr.count('SGIGray76'), darkgray=stderr.count('SGIDarkGray'),
                            default_background=stderr.count('default background'))
            assert ('osfActivate' not in stderr) == with_keys
            assert ('SGIGray76' not in stderr and 'SGIDarkGray' not in stderr) == with_colors
            assert warnings['keysym'] == (0 if with_keys else 6)
            assert warnings['gray76'] == warnings['darkgray'] == (0 if with_colors else 1)
            if case['stage'] == 'combined':
                assert stderr == ''
            cases.append(dict(stage=case['stage'], uid=case['uid'], elapsed_ms=elapsed,
                              intentional_sigkill=True, stderr_bytes=len(stderr.encode()),
                              warnings=warnings, frames=frames, redraw=redraw(case['redraw']),
                              keyboard_traversal_and_escape=with_keys,
                              gettimeofday_enosys=case['returns'].count('syscall=1128 v0=0x59 a3=1'),
                              trace_sha256=digest(directory / (name + '.kdump')),
                              parent_sha256=digest(directory / (name + '.parent'))))
        expected_cases = {('combined', 0), ('combined', 1234)}
        if run['mode'] == 'ci':
            expected_cases |= {(stage, 1234) for stage in ['baseline', 'keysyms', 'colors']}
        assert {(c['stage'], c['uid']) for c in cases} == expected_cases
        report['runs'].append(dict(mode=run['mode'], directory=str(directory.relative_to(ROOT)),
                                  result_sha256=digest(directory / 'result.json'),
                                  serial_sha256=digest(directory / 'serial.log'),
                                  clean_shutdown=True, native_controls=run['controls'],
                                  server_colors=run['server_colors'], cases=cases,
                                  execution_sources=run['sources']))
    assert seen == {'ci', 'ordinary'}
    combined = [c for r in report['runs'] for c in r['cases'] if c['stage'] == 'combined']
    assert len(combined) == 4
    expected_pixels = {phase: frame['pixels']['sha256'] for phase, frame in combined[0]['frames'].items()}
    assert all({phase:frame['pixels']['sha256'] for phase,frame in c['frames'].items()} == expected_pixels
               for c in combined)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Checked', sum(len(r['cases']) for r in report['runs']), 'Toolchest observations and both guest shutdowns')


if __name__ == '__main__':
    main()
