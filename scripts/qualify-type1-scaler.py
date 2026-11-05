#!/usr/bin/env python3
"""Validate the native FPU comparison, font churn and Type1 winterm evidence."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import shutil

from xiri_lab import ROOT, sha256


def registers(output, fixed):
    rows = re.findall(
        r'^REGISTERS kind=(-?\d+) touch=(\d) mode=(\d) delivered=(\d) '
        r'bad=(\d+) csr=([0-9a-f]+) expected=([0-9a-f]+) rc=(\d+) pass=(\d)$',
        output, re.M)
    assert len(rows) == 24
    seen = set()
    for kind, touch, mode, delivered, bad, csr, expected, rc, passed in rows:
        kind, touch, mode = int(kind), int(touch), int(mode)
        seen.add((kind, touch, mode))
        good = fixed or kind == -1
        assert int(delivered) == int(kind != -1) and int(rc) == 0
        assert int(expected, 16) == (mode | 4)
        assert int(csr, 16) == ((mode | 4) if good else 0)
        assert int(bad) == (0 if good else 33) and int(passed) == int(good)
    assert seen == {(k, t, m) for k in [-1, 0, 1] for t in [0, 1] for m in range(4)}
    assert output.endswith('REGISTERS_RESULT cases=24 failures='+('0\n0\n' if fixed else '16\n1\n'))
    return dict(cases=24, failures=0 if fixed else 16, output=output)


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--irix-fixtures', type=Path, default=ROOT/'.work/irix-signal-v2/probes')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--png', type=Path, required=True)
    args = parser.parse_args()
    run = args.run.resolve()
    result = json.loads((run/'result.json').read_text())
    desktop = json.loads((run/'desktop.json').read_text())
    assert not result.get('error') and not result.get('cleanup_error')
    assert result['clean_shutdown'] and result['source_unchanged']
    assert 'unmounting done' in result['shutdown_log'][-2048:]
    assert 'halting...' in result['shutdown_log'][-256:]
    assert sha256(run/'disk.chd') == result['chd_sha256']
    assert sha256(ROOT/result['bundle']/'netbsd-xiri.chd') == result['chd_sha256']
    assert sha256(run/'harness.py') == result['harness_sha256']
    build = json.loads((ROOT/'lab/type1-scaler/build.json').read_text())
    assert result['candidate_kernel'] == build
    pin = json.loads((ROOT/'lab/type1-scaler/baseline.json').read_text())
    assert sha256(ROOT/pin['module_build_manifest']) == pin['module_build_manifest_sha256']
    for name in ('netbsd', 'netbsd.boot'):
        assert f"SHA256 (/{name}) = {build['artifacts'][name]['sha256']}" in result['libraries']
    assert re.search(r'^compat_irix_o32\s+exec\s+filesys\s', result['libraries'], re.M)

    before, after = (result['phases'][name] for name in ['baseline', 'candidate'])
    controls = dict(baseline=registers(before['registers'], False),
                    candidate=registers(after['registers'], True))
    assert re.fullmatch(r'FP_FAIL iteration=\d+ scale=14\.5 result=0 signals=[1-9]\d*\n1\n', before['fp'])
    match = re.fullmatch(r'FP_PASS iterations=200000 signals=([1-9]\d*)\n0\n', after['fp'])
    assert match
    assert after['churn'].endswith('STRESS_PASS iterations=560\n0\n')
    assert after['churn'].count('PIXMAP ink=643 bbox=10,31,140,47 ') == 20
    assert after['churn'].count('ascent=17 descent=4 min=-1,0,12,-2,-11 max=6,13,12,17,4') == 20
    sizes = re.findall(r'^FTSIZE call=(\d+) .* request=(\d+),(\d+) dpi=(\d+),(\d+) '
                       r'rc=(\d+) ppem=(\d+),(\d+) scale=(\d+),(\d+)$', after['trace'], re.M)
    assert len(sizes) == 588 and [int(s[0]) for s in sizes] == list(range(1, 589))
    expected = {371:(8,33751), 557:(12,50725), 646:(14,58786), 742:(16,67568),
                928:(20,84476), 1107:(24,100794), 1478:(32,134545)}
    counts = dict.fromkeys(expected, 0)
    for row in sizes:
        _, width, height, dx, dy, rc, px, py, sx, sy = map(int, row)
        assert width in expected and width == height
        assert dx == dy == 100 and rc == 0
        assert px == py == expected[width][0] and sx == sy == expected[width][1]
        counts[width] += 1
    assert all(counts.values()) and 'request=0,0' not in after['trace']
    assert before['standalone'] == after['standalone']
    for text in ['SIZE ppem=20,20 scale=83886,83886',
                 'GLYPH char=M advance=768,0 bitmap=12,12 left=0 top=12',
                 'GLYPH char=g advance=768,0 bitmap=12,12 left=0 top=9']:
        assert after['standalone'].count(text) == 6

    assert desktop['status'] == 'passed' and not desktop.get('error')
    for key, count in [('native_metrics', 6), ('irix_metrics', 12)]:
        lines = desktop[key].splitlines()
        sets = [line for line in lines if line.startswith('SET ')]
        fonts = [line for line in lines if line.startswith('FONT ')]
        assert len(sets) == 6 and all('width=48 ink=-1,-17,14,21 logical=0,-17,12,21' in s for s in sets)
        assert len(fonts) == count and all(s.endswith('ascent=17 descent=4 width=12,12 glyph=17,4') for s in fonts)
    assert 'PIXMAP ink=643 bbox=10,31,140,47 ' in desktop['native_pixels']
    assert 'resize increment: 12 by 21' in desktop['hints'] and desktop['size'] == '24 80'
    assert desktop['resize'] == ['READY rows=24 cols=80 foreground=1', 'RESIZED rows=21 cols=66 SIGWINCH=1']
    assert desktop['exit'] == '0' and not desktop['stderr']
    hashes = dict(re.findall(r'^SHA256 \((.+)\) = ([0-9a-f]{64})$', desktop['fixture_hashes'], re.M))
    fixture_sources = [*sorted((ROOT/'lab/type1-scaler').glob('*.c')),
                       ROOT/'lab/type1-scaler/registers.S', ROOT/'lab/type1-scaler/Makefile']
    for path in fixture_sources:
        assert hashes[path.name] == sha256(path), path

    manifest = json.loads((args.irix_fixtures/'manifest.json').read_text())
    for path, digest in manifest['sources'].items():
        assert sha256(ROOT/path) == digest, path
    cases = [case for case in manifest['cases'] if case['name'].split('-', 2)[2] in
             {'fpu-legacy', 'fpu-siginfo', 'fpu-child'}]
    assert len(cases) == 12
    runtime = load_module('runtime', 'scripts/probe-irix-runtime.py')
    decoder = load_module('signal_check', 'scripts/qualify-irix-signal.py')
    log = (run/'irix-controls.log').read_text()
    decoded = []
    for case in cases:
        fixture = args.irix_fixtures/case['name']
        assert sha256(fixture) == manifest['files'][case['name']]['sha256']
        for uid in [0, 1234]:
            name = case['name']+'-'+str(uid)
            raw, = re.findall(r'^STARTCASE '+name+r'\n(.*?)^ENDCASE '+name+r'$', log, re.M|re.S)
            seen = runtime.observation(raw); seen.pop('stdout')
            assert seen == dict(errno_bytes=0, errno=0, exit=0, signal=0, killed=0, stderr='')
            assert 'GROUP absent=1' in raw
            data = bytes.fromhex(re.search(r'^STDOUT bytes=2048 hex=([0-9a-f]+)$', raw, re.M)[1])
            decoded.append(decoder.decode(data, case, uid, fixture.read_bytes(), 8192))
    assert decoded == desktop['irix_signals'] and len(desktop['native_controls']) == 4
    controls_by_name = {c['name']:c['observed'] for c in desktop['native_controls']}
    assert set(controls_by_name) == {exe+'-'+str(uid) for exe in ['native-signals', 'native-control'] for uid in [0,1234]}
    for uid in [0, 1234]:
        for exe, expected_text in [
            ('native-signals', 'NATIVE_SIGNALS handler=1 mask=1 return=1 child=1\n'),
            ('native-control', f'NATIVE_TIME uid={uid} seconds=1 microseconds=1 progression=1 select=1\n'),
        ]:
            name = exe+'-'+str(uid)
            raw, = re.findall(r'^STARTCASE '+name+r'\n(.*?)^ENDCASE '+name+r'$', log, re.M|re.S)
            seen = runtime.observation(raw)
            assert seen == controls_by_name[name] == dict(errno_bytes=0, errno=0, exit=0,
                signal=0, killed=0, stderr='', stdout=expected_text)
            assert 'GROUP absent=1' in raw
    shot = run/'type1-courier.png'
    assert sha256(shot) == desktop['screenshots'][shot.name]
    shutil.copyfile(shot, args.png)
    evidence = ['result.json', 'harness.py', 'media-update.json', 'baseline.json', 'candidate.json',
                'desktop-first.json', 'desktop-harness.py', 'desktop-resume-harness.py', 'desktop.json',
                'irix-controls.sh', 'irix-controls.log', 'serial.log', 'reboot/serial.log']
    report = dict(schema=1, status='passed', run=str(run.relative_to(ROOT)),
        evidence={name:sha256(run/name) for name in evidence}, input_chd_sha256=result['chd_sha256'],
        pin=pin, build_manifest_sha256=sha256(ROOT/'lab/type1-scaler/build.json'),
        native_registers=controls, arithmetic=dict(baseline=before['fp'], candidate=after['fp']),
        fonts=dict(iterations=560, size_requests=588, request_counts=counts, pixel_checks=20,
                   baseline_churn=before['churn'], candidate_churn=after['churn'],
                   direct_freetype=after['standalone']), desktop=desktop, irix_fpu_records=len(decoded),
        clean_shutdown=True, source_unchanged=True,
        screenshot=dict(path=str(args.png), sha256=sha256(args.png), method='IRIS ordinary GL scanout'),
        sources={str(p.relative_to(ROOT)):sha256(p) for p in fixture_sources + [Path(__file__).resolve(),
                 ROOT/'scripts/qualify-irix-signal.py', ROOT/'scripts/qualify-irix-signal-reference-v2.py']},
        limitations=['Native o32 execution controls; native n64, ptrace and legacy NetBSD trampolines untested.',
                     'Seven sizes and four IBM Courier faces; not every scalable font or physical SGI hardware.',
                     'Xorg round-robin scheduling and the default bitmap Courier remain unchanged.',
                     'The original IRIX fontset has two matching fonts; the initial one-font checker was corrected.'])
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print('Native FPU, Type1 churn, IRIX signal records and winterm checks passed')


if __name__ == '__main__':
    main()
