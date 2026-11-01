#!/usr/bin/env python3
"""Compare native signal records with the measured original IRIX contract."""
import argparse
import importlib.util
import json
from pathlib import Path
import re
import struct
import tomllib

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('reference', ROOT/'scripts/qualify-irix-signal-reference-v2.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)
sha = reference.sha


def decode(data, case, uid, elf, page):
    w = list(struct.unpack('>512I', data))
    s = case['symbols']
    assert w[13] == page
    assert w[:4] == [0x58534947, s['CASE'], s['KIND'], s['FLAGS']]
    assert w[4:8] == [uid] * 4
    assert w[48:55] == [0, 0xfeedface, 0, 0x4000, 0, 0, 0]
    unsupported_number = 32 <= s['SIGNUM'] <= 64
    unsupported_mask = any([s['MASK0'] & 0x80000000, s['MASK1'], s['MASK2'], s['MASK3']])
    if unsupported_number or unsupported_mask:
        assert w[16:19] == [122, 0xfeedface, 1]
        assert w[19:22] == [122 if unsupported_number else 0, 0xfeedface, int(unsupported_number)]
        assert w[15] == 0 and not any(w[128:480])
        assert data[256:296] == b'\xa5' * 40
        assert data[448:480] == b'\x5a' * 32
        query = data[1920:1960]
        assert query == (b'\xa5' * 40 if unsupported_number else b'\xa5' * 4 + b'\0' * 32 + b'\xa5' * 4)
        return dict(name=case['name'], identity=uid, kind=0, policy='unmapped signal/mask rejected', errno=122)
    # Compare the same actual bytes after asserting only explicit environment
    # and reserved-byte differences. Do not normalize handler/frame contents.
    normalized = bytearray(data)
    struct.pack_into('>I', normalized, 13 * 4, 4096)
    if s['SIGNUM'] == 18:
        # The native runner does not inherit the reference shell's NOCLDSTOP.
        assert w[65] == 0
        struct.pack_into('>I', normalized, 65 * 4, 0x20000)
    if s['OLD_KIND'] == 5:
        assert data[476:480] == b'\0' * 4
        normalized[476:480] = bytes.fromhex('12345678')
    result = reference.decode(bytes(normalized), case, uid, elf)
    # Native serializers initialize all reserved action output bytes.
    if w[18] == 0 and s['OLD_KIND'] in [0, 3]:
        start = 261 if s['OLD_KIND'] == 3 else 260
        assert data[start + 24:start + 32] == b'\0' * 8
    if w[21] == 0:
        assert data[1948:1956] == b'\0' * 8
    if s['KIND']:
        assert data[248:256] == b'\0' * 8
    if s.get('EXTRA') == 1:
        result['inherited_handler_in_child'] = True
    if s.get('EXTRA') == 2:
        for i, error in enumerate([22, 22, 22, 22, 122, 22, 14]):
            assert w[80+3*i:83+3*i] == [error, 0xfeedface, 1]
        assert w[101:110] == [0, 0xfeedface, 0, 0x1c000, 0, 0, 0, 0x56414c44, int(case['abi']=='n32')]
        result['invalid_context_checks'] = 7
        result['user_status_ignored'] = case['abi'] == 'n32'
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs', nargs='+', type=Path)
    p.add_argument('--diagnostic', action='store_true')
    p.add_argument('--extra', type=Path)
    p.add_argument('--reference-report', type=Path,
                   default=ROOT/'docs/results/2026-11-01-irix-signal-reference-v2.json')
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    report = dict(schema=1, status='diagnostic' if args.diagnostic else 'passed',
                  qualifier_sha256=sha(Path(__file__)), reference_qualifier_sha256=sha(ROOT/'scripts/qualify-irix-signal-reference-v2.py'),
                  records=0, controls=0, runs=[])
    coverage = set()
    ref = json.loads(args.reference_report.read_text())
    assert ref['status'] == 'original-signal-reference' and ref['executions'] == 480
    assert ref['qualifier_sha256'] == sha(ROOT/'scripts/qualify-irix-signal-reference-v2.py')
    refdir = ROOT/ref['run']['directory']
    assert sha(refdir/'result.json') == ref['run']['result_sha256']
    assert sha(refdir/'outputs.tgz') == ref['run']['archive_sha256']
    for path, digest in ref['sources'].items():
        assert sha(ROOT/path) == digest, path
    report['original_reference'] = dict(report_sha256=sha(args.reference_report),
        run=ref['run'], executions=ref['executions'])
    for directory in args.runs + ([args.extra] if args.extra else []):
        r = json.loads((directory/'result.json').read_text())
        assert r['status'] == 'observed-uncompared' and r['clean_shutdown']
        key = r['kernel_abi'], r['mode']
        coverage.add(key)
        assert tomllib.loads((directory/'iris.toml').read_text())['ci'] == (key[1] == 'ci')
        if not args.diagnostic:
            assert r['scope'] == 'full' and not r['pin']['source_dirty']
            pinfile = 'o32-baseline.json' if key[0] == 'o32' else 'baseline.json'
            assert r['pin'] == json.loads((ROOT/'lab/irix-signal'/pinfile).read_text())
        for path, digest in r['sources'].items():
            assert sha(ROOT/path) == digest, path
        assert sha(ROOT/r['seed']/'result.json') == r['seed_result_sha256']
        manifest = r['manifest']
        if directory != args.extra:
            assert manifest['files'] == ref['fixtures']
        for path, digest in manifest['sources'].items():
            assert sha(ROOT/path) == digest, path
        cases = {c['name']: c for c in manifest['cases'] if c['name'] in r['selected_cases']}
        assert len(r['observations']) == len(cases) * 2
        assert {o['name'] for o in r['observations']} == {n+'-'+str(i) for n in cases for i in [0,1]}
        log = (directory/'fixtures.log').read_text()
        decoded = []
        for observation in r['observations']:
            name = observation['name']
            case = cases[name[:-2]]
            uid = 1234 if name.endswith('-1') else 0
            x = observation['actual']
            assert x['errno_bytes'] == x['errno'] == x['exit'] == x['signal'] == x['killed'] == 0
            assert not x['stderr'] and observation['group_absent']
            raw, = re.findall(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+r'$', log, re.M|re.S)
            hexdata, = re.findall(r'^STDOUT bytes=2048 hex=([0-9a-f]+)$', raw, re.M)
            assert hexdata == x['stdout_hex'] and 'GROUP absent=1' in raw
            fixture = directory/'media'/case['name']
            assert sha(fixture) == manifest['files'][case['name']]['sha256']
            try:
                decoded.append(decode(bytes.fromhex(hexdata), case, uid, fixture.read_bytes(), 8192 if key[0] == 'lp64' else 4096))
            except AssertionError as error:
                raise AssertionError(str(directory)+' '+name) from error
        expected = {'native-o32', 'vendor-asa', 'native-time', 'native-signals'}
        if key[0] == 'lp64': expected.add('vendor-echo')
        assert {(c['phase'], c['uid'], c['name']) for c in r['controls']} == {
            (phase, uid, name) for phase in ['before', 'after'] for uid in [0, 1234] for name in expected}
        assert len(r['controls']) == len(expected) * 4
        for c in r['controls']:
            output = {'native-o32':'XIRI_ABI_PROBE\n', 'vendor-asa':'XIRI_VENDOR_O32\n',
                      'vendor-echo':'XIRI_VENDOR_N32\n', 'native-signals':'NATIVE_SIGNALS handler=1 mask=1 return=1 child=1\n',
                      'native-time':f'NATIVE_TIME uid={c["uid"]} seconds=1 microseconds=1 progression=1 select=1\n'}[c['name']]
            assert c['actual'] == dict(errno_bytes=0, errno=0, exit=37 if c['name']=='native-o32' else 0,
                signal=0, killed=0, stdout=output, stderr='')
            if c['name'].startswith('native-') and c['name'] != 'native-o32': assert c['group_absent']
        report['records'] += len(decoded)
        report['controls'] += len(r['controls'])
        report['runs'].append(dict(directory=str(directory), result_sha256=sha(directory/'result.json'),
            serial_sha256=sha(directory/'serial.log'), fixtures_log_sha256=sha(directory/'fixtures.log'),
            pin=r['pin'], clean_shutdown=True, observations=decoded))
    if not args.diagnostic:
        assert coverage == {('lp64','ci'), ('lp64','ordinary'), ('o32','ci')}
        assert report['records'] == 1200 + (16 if args.extra else 0)
    report['differences'] = ['Only traditional signals 1..31; unmapped signals/masks return EOPNOTSUPP.',
        'Native-runner initial SIGCHLD flags are zero, unlike the reference shell NOCLDSTOP.',
        'Reserved action words are zeroed rather than reproducing unrelated reference bytes.',
        'Frame allocation is 1024 bytes; measured field offsets and entry alignment are retained.',
        'LP64 native pages are 8192 bytes; the reference and o32 kernel use 4096.']
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print('Verified', report['records'], 'signal records and', report['controls'], 'controls')


if __name__ == '__main__':
    main()
