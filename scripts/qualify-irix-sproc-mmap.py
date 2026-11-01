#!/usr/bin/env python3
"""Recheck shared mmap records and backing bytes on the sproc checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tomllib

ROOT = Path(__file__).resolve().parent.parent
SENTINEL = 0xfeedface


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


REFERENCE_ERRORS = {
    **{name: 13 for name in ['shared-grow-file-readonly',
       'shared-file-readonly-fd', 'shared-file-writeonly-fd',
       'installer-readonly-fd', 'installer-writeonly-fd',
       'installer-directory', 'installer-bad-protection']},
    **{name: 9 for name in ['installer-invalid-fd', 'installer-closed-fd']},
    **{name: 22 for name in ['installer-negative-offset', 'installer-byte-offset',
       'installer-both-types', 'installer-no-type', 'installer-fixed-unaligned']},
    'installer-empty': 6,
}
# Deliberate native-policy differences, named independently of kernel branching.
NATIVE_ERRORS = dict(REFERENCE_ERRORS, **{
    **{name: 22 for name in ['shared-past-eof-store', 'shared-past-eof-read',
       'private-past-eof-store', 'private-past-eof-read',
       'zero-name-file-past-eof-store', 'zero-name-file-past-eof-read',
       'shared-grow-empty-store', 'shared-grow-within-file',
       'shared-grow-file-readonly', 'installer-directory', 'installer-empty',
       'installer-unknown', 'installer-bad-protection']},
    'installer-readonly-fd': 0, 'installer-writeonly-fd': 0,
})


def expected(case, ids, words, page, native):
    """Independent expected endpoints, wait outcomes and whole backing files."""
    s = case['symbols']
    name = case['name'].split('-', 2)[2]
    error = (NATIVE_ERRORS if native else REFERENCE_ERRORS).get(name, 0)
    if native and page == 8192 and name == 'installer-fixed-halfpage':
        error = 22
    w = [0] * 64
    w[:2] = [0x584d5348, s['CASE']]
    w[5] = page
    w[16:24] = [s[k] for k in ['ADDRESS', 'LENGTH', 'PROTECTION', 'FLAGS',
        'OPEN_MODE', 'OFFSET', 'FILE_KIND', 'ACTION']]
    w[24:26] = [s['BADFD'], s['FILE_SIZE']]
    w[27] = s['TARGET']
    w[54] = s['CLOSE_EARLY']
    w[56:60] = ids
    backing = bytearray([0x3c]) * s['FILE_SIZE']
    regular = s['FILE_KIND'] in [1, 4]
    shared = s['FLAGS'] & 3 == 1

    def reply(at, value=0, err=0, second=SENTINEL):
        w[at:at + 3] = [value, second, err]

    def address(at, fixed=False):
        value = words[at]
        assert 0 < value < 0x80000000 and value % page == 0
        assert value + ((s['LENGTH'] + page - 1) // page) * page <= 0x80000000
        if fixed:
            assert value == s['ADDRESS']
        reply(at, value)

    if s['BADFD'] != 2:
        reply(8)
    if error:
        reply(2, error, 1)
    else:
        address(2, bool(s['FLAGS'] & 0x10))
        action = s['ACTION']
        if action <= 2:
            if s['PROTECTION'] & 1:
                w[6] = (s['LENGTH'] + 4095) // 4096
            first = last = 0x3c if regular else 0
            if s['PROTECTION'] & 2:
                first, last = 0x5a, 0xa6
                w[55] = 1
            if action == 1:
                w[28:31] = [1, 37, 1]
                reply(48, second=37 << 8)
                if shared:
                    first, last = 0x8b, 0xc9
            elif action == 2:
                address(32)
                assert abs(w[32] - w[2]) >= ((s['LENGTH'] + page - 1) // page) * page
                w[40] = first if regular and shared else 0
                w[41] = 0x9b
                if regular and shared:
                    first = 0x9b
                w[39] = first
                reply(42)
            if s['PROTECTION'] & 1:
                w[31], w[35] = first, last
            if regular and shared and s['PROTECTION'] & 2:
                backing[s['OFFSET']] = first
                backing[s['OFFSET'] + s['LENGTH'] - 1] = last
        else:
            if name in ['shared-readonly-store', 'shared-no-access-read']:
                signal = 11
            elif 'no-grow-past-eof' in name:
                signal = 10
            else:
                signal = 0
            w[28:31] = [2, signal, 1] if signal else [1, 37, 1]
            reply(48, second=signal if signal else 37 << 8)
            if regular and shared and not signal:
                # Measured 6.5.22m extends on either read or store here;
                # the older manual's store-only wording is not assumed.
                end = ((s['TARGET'] + 4096) // 4096) * 4096
                backing.extend(bytes(end - len(backing)))
                if action == 3:
                    backing[s['TARGET']] = 0x73
        reply(36)

    if native:
        # Foreign lseek is still ENOSYS (IRIX errno 89). The separate
        # native copies, checked byte-for-byte below, establish file sizes.
        before = mapped = after = [89, SENTINEL, 1]
    else:
        size = s['FILE_SIZE'] if regular else 0
        if s['FILE_KIND'] == 2:
            # Directory size is filesystem metadata, not the mapping object.
            size = words[11]
            assert 0 < size <= 0x100000 and size % 4096 == 0
        before = [size, SENTINEL, 0]
        mapped = [9, SENTINEL, 1] if s['BADFD'] == 2 else before
        after = [9, SENTINEL, 1] if s['BADFD'] == 2 or s['CLOSE_EARLY'] else [len(backing) if regular else size, SENTINEL, 0]
    w[11:14] = before
    w[26], w[52], w[53] = mapped
    w[45:48] = after
    return w, bytes(backing)


def decode(observation, case, ids, page, native=False):
    if native:
        x = observation['actual']
        assert all(x[k] == 0 for k in ['errno_bytes', 'errno', 'exit', 'signal', 'killed'])
        assert not x['stderr'] and observation['group_absent']
    else:
        x = observation
        assert x['exit'] == 0 and not x['stderr']
    raw = bytes.fromhex(x['stdout_hex'])
    assert len(raw) == 256
    words = list(struct.unpack('>64I', raw))
    want, backing = expected(case, ids, words, page, native)
    assert words == want, (observation['name'], [(i, a, b) for i, (a, b) in enumerate(zip(words, want)) if a != b])
    assert bytes.fromhex(observation['backing_hex']) == backing, ('backing', observation['name'])
    return words, backing


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--export-reference', action='store_true')
    parser.add_argument('runs', nargs='*', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    ref = json.loads((args.reference / 'result.json').read_text())
    assert ref['status'] == 'observed' and ref['scope'] == 'full' and ref['clean_shutdown']
    assert ref['harness_sha256'] == sha(ROOT / 'scripts/probe-irix-reference-mmap-shared.py')
    manifest = ref['manifest']
    cases = {c['name'] + '-' + str(i): (c, i) for c in manifest['cases'] for i in c['identities']}
    assert len(cases) == len(ref['observations']) == 472
    assert {o['name'] for o in ref['observations']} == cases.keys()
    for path, digest in manifest['sources'].items():
        assert sha(ROOT / path) == digest, path
    records = {}
    for o in ref['observations']:
        c, i = cases[o['name']]
        words, backing = decode(o, c, manifest['identities'][i], 4096)
        records[o['name']] = dict(words=words, backing_bytes=len(backing), backing_sha256=hashlib.sha256(backing).hexdigest())
    exported = dict(reference='IRIX 6.5.22m', result_sha256=sha(args.reference / 'result.json'),
        harness_sha256=ref['harness_sha256'], sources=manifest['sources'], records=records)
    record_path = ROOT / 'lab/irix-mmap-shared/reference.json'
    if args.export_reference:
        record_path.write_text(json.dumps(exported, indent=2) + '\n')
    assert json.loads(record_path.read_text()) == exported
    if not args.runs:
        assert args.export_reference
        print('472 original records and backing files validated')
        return
    assert args.output
    report = dict(schema=1, status='passed', qualifier_sha256=sha(Path(__file__)),
        reference_directory=str(args.reference), reference_result_sha256=sha(args.reference / 'result.json'),
        reference_records_sha256=sha(record_path), records=0, backing_files=0, controls=0, runs=[], source_evidence=[])
    coverage = set()
    for directory in args.runs:
        r = json.loads((directory / 'result.json').read_text())
        key = (r['kernel_abi'], r['mode'])
        assert key not in coverage
        coverage.add(key)
        assert r['status'] == 'observed-uncompared' and r['clean_shutdown'] and r['manifest'] == manifest
        assert tomllib.loads((directory / 'iris.toml').read_text())['ci'] == (key[1] == 'ci')
        pin = json.loads((ROOT / 'lab/irix-sproc' / ('o32-baseline.json' if key[0] == 'o32' else 'baseline.json')).read_text())
        assert r['pin'] == pin
        for path, digest in r['sources'].items():
            assert sha(ROOT / path) == digest, path
        assert sha(ROOT / r['seed'] / 'result.json') == r['seed_result_sha256']
        names = {n for n, (c, i) in cases.items() if key[0] == 'lp64' or c['abi'] == 'o32'}
        assert len(r['observations']) == len(names) and {o['name'] for o in r['observations']} == names
        for o in r['observations']:
            c, i = cases[o['name']]
            decode(o, c, manifest['identities'][i], pin['page_bytes'], True)
        control_names = ['native-o32', 'vendor-asa', 'native-mmap'] + (['vendor-echo'] if key[0] == 'lp64' else [])
        required = {(phase, uid, name) for phase in ['before', 'after'] for uid in [0, 1234] for name in control_names}
        assert len(r['controls']) == len(required) and {(x['phase'], x['uid'], x['name']) for x in r['controls']} == required
        for x in r['controls']:
            name = x['name']
            output = {'native-o32': 'XIRI_ABI_PROBE\n', 'vendor-asa': 'XIRI_VENDOR_O32\n',
                'vendor-echo': 'XIRI_VENDOR_N32\n',
                'native-mmap': f'NATIVE_MMAP uid={x["uid"]} zero=1 shared=1 private=1 close=1 file=1 eof=1\n'}[name]
            assert x['actual'] == dict(errno_bytes=0, errno=0, exit=37 if name == 'native-o32' else 0,
                signal=0, killed=0, stdout=output, stderr='')
            if name == 'native-mmap':
                assert x['group_absent']
        report['records'] += len(names)
        report['backing_files'] += len(names)
        report['controls'] += len(required)
        report['runs'].append(dict(directory=str(directory), result_sha256=sha(directory / 'result.json'),
            serial_sha256=sha(directory / 'serial.log'), fixtures_log_sha256=sha(directory / 'fixtures.log'),
            backings_sha256=sha(directory / 'backings.tar'), pin=pin, sources=r['sources'],
            kernel_abi=key[0], mode=key[1], records=len(names), controls=len(required), clean_shutdown=True))
    assert coverage == {('lp64', 'ci'), ('lp64', 'ordinary'), ('o32', 'ci')}
    revisions = {r['pin']['source_revision'] for r in report['runs']}
    assert len(revisions) == 1
    revision = revisions.pop()
    for path in ['sys/compat/irix_o32/irix_o32.c', 'sys/uvm/uvm_mmap.c',
                 'sys/kern/vfs_vnops.c', 'sys/kern/kern_descrip.c']:
        data = subprocess.check_output(['git', '-C', str(ROOT.parent / 'NetBSD-nixbench'), 'show', revision + ':' + path])
        report['source_evidence'].append(dict(repository='NetBSD-xiri', revision=revision, path=path, sha256=hashlib.sha256(data).hexdigest()))
    report['limits'] = [
        'Regular-file AUTOGROW remains EINVAL, including the measured IRIX growth on a shared read fault. Only the native zero device qualifies.',
        'Native zero-device descriptor access policy accepts read-only/write-only descriptors rejected by this original shared-map request.',
        'Native page alignment and stricter unknown-flag, bad-protection and empty-request policies remain explicit.',
        'lseek size snapshots return IRIX ENOSYS 89 on NetBSD; independent whole backing-file copies establish final file contents and sizes.',
        'No logical-swap accounting, exhaustion guarantee, general multi-member sharing, large offsets or physical-hardware qualification.',
        'The reference image retains its previously documented XFS alerts; this is a mapping experiment, not filesystem qualification.',
    ]
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print('Passed', report['records'], 'mapping records,', report['backing_files'], 'backing files and', report['controls'], 'controls')


if __name__ == '__main__':
    main()
