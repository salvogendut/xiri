#!/usr/bin/env python3
"""Check full action masks without claiming unmapped IRIX signal support."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import re
import struct
import tarfile

ROOT = Path(__file__).resolve().parent.parent


def module(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


reference = module('reference', 'qualify-irix-signal-reference-v2.py')
native = module('native', 'qualify-irix-signal.py')
sha = reference.sha


def decode(data, case, uid, elf, original):
    words = list(struct.unpack('>512I', data))
    symbols = case['symbols']
    assert words[16:22] == [0, 0xfeedface, 0] * 2
    # The independently observed IRIX contract retains signals 1..64 except
    # KILL/STOP. Xiri's stated subset exposes only mapped traditional signals.
    mask = [symbols['MASK0'] & (0xffbffeff if original else 0x7fbffeff),
            symbols['MASK1'] if original else 0, 0, 0]
    assert words[483:487] == mask
    assert words[51:55] == [0x4000, 0, 0, 0]
    if symbols['KIND']:
        active = mask.copy()
        active[0] |= 0x4000 | (0 if symbols['FLAGS'] & 16 else 1 << (symbols['SIGNUM']-1))
        assert words[35:39] == active
        assert words[58:62] == mask
    else:
        active = None
    # After checking the wider mask explicitly, reuse the established oracle
    # for every other field, including actual entry/frame/return/reap bytes.
    normalized = bytearray(data)
    projected = copy.deepcopy(case)
    projected['symbols'].update(MASK0=symbols['MASK0'] & 0x7fbffeff,
                                MASK1=0, MASK2=0, MASK3=0)
    for offset in [483] + ([35, 58] if symbols['KIND'] else []):
        struct.pack_into('>4I', normalized, offset*4, 0x7fbffeff, 0, 0, 0)
    if original:
        result = reference.decode(bytes(normalized), projected, uid, elf)
    else:
        result = native.decode(bytes(normalized), projected, uid, elf, 8192)
    result['action_mask_observed'] = mask
    result['active_mask_observed'] = active
    result['restored_mask'] = words[51:55]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--native-log', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--native-run', type=Path, help='halted diagnostic guest with the candidate module')
    parser.add_argument('--diagnostic', action='store_true')
    parser.add_argument('--regression-log', type=Path)
    parser.add_argument('--regression-manifest', type=Path)
    args = parser.parse_args()
    if not args.diagnostic and args.native_run is None:
        parser.error('--native-run is required for a completed qualification')
    observed = json.loads((args.reference/'result.json').read_text())
    assert observed['status'] == 'observed' and observed['clean_shutdown']
    harness=ROOT/'scripts/probe-irix-gimp-signals-reference.py'
    import hashlib
    # The captured private copy differed only in resolving the repository root.
    private_source=harness.read_text().replace('ROOT = Path(__file__).resolve().parent.parent','ROOT = Path.cwd()')
    assert observed['harness_sha256'] in {sha(harness), hashlib.sha256(private_source.encode()).hexdigest()}
    manifest = observed['manifest']
    assert len(manifest['cases']) == 40 and len(observed['observations']) == 80
    for path, digest in manifest['sources'].items():
        assert sha(ROOT/path) == digest, path
    assert set(observed['checked_files']) == set(manifest['files'])
    log = args.native_log.read_text()
    results = []
    with tarfile.open(args.reference/'outputs.tgz') as archive:
        statuses = dict(re.findall(r'^CASE (\S+) (\d+)$', archive.extractfile('status.txt').read().decode(), re.M))
        assert len(statuses) == 80 and set(statuses.values()) == {'0'}
        for case in manifest['cases']:
            path = args.reference/'fixtures'/case['name']
            assert sha(path) == manifest['files'][case['name']]['sha256']
            elf = path.read_bytes()
            for i in case['identities']:
                name = case['name']+'-'+str(i)
                original = archive.extractfile(name+'.out').read()
                assert not archive.extractfile(name+'.err').read()
                item, = [o for o in observed['observations'] if o['name'] == name]
                assert item['stdout_hex'] == original.hex() and item['exit'] == 0 and not item['stderr']
                block, = re.findall(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+r'$', log, re.M|re.S)
                assert re.search(r'errno_bytes=0 errno=0 exit=0 signal=0 killed=0\n', block)
                assert 'STDERR bytes=0 hex=\n' in block and 'GROUP absent=1' in block
                raw, = re.findall(r'^STDOUT bytes=2048 hex=([0-9a-f]+)$', block, re.M)
                uid = 1234 if i else 0
                try:
                    ref = decode(original, case, uid, elf, True)
                    got = decode(bytes.fromhex(raw), case, uid, elf, False)
                except AssertionError as e:
                    raise AssertionError(name) from e
                results.append(dict(name=name, reference=ref, native=got))
    controls = re.findall(r'^CONTROL (before|after) (0|1234)\n(.*?)(?=^CONTROL |^STARTCASE |\Z)', log, re.M|re.S)
    assert {(phase, uid) for phase, uid, _ in controls} == {(p, u) for p in ['before', 'after'] for u in ['0', '1234']}
    for _, _, block in controls:
        assert re.search(r'errno_bytes=0 errno=0 exit=0 signal=0 killed=0\n', block)
        assert 'GROUP absent=1' in block
        raw, = re.findall(r'^STDOUT bytes=\d+ hex=([0-9a-f]+)$', block, re.M)
        assert bytes.fromhex(raw) == b'NATIVE_SIGNALS handler=1 mask=1 return=1 child=1\n'
    report = dict(schema=1, status='paired-signal-mask-records-passed', paired_records=len(results),
        native_controls=len(controls), qualifier_sha256=sha(Path(__file__)),
        reference_oracle_sha256=sha(ROOT/'scripts/qualify-irix-signal-reference-v2.py'),
        native_oracle_sha256=sha(ROOT/'scripts/qualify-irix-signal.py'),
        reference_run=str(args.reference), reference_result_sha256=sha(args.reference/'result.json'),
        reference_archive_sha256=sha(args.reference/'outputs.tgz'),
        native_log=str(args.native_log), native_log_sha256=sha(args.native_log),
        manifest=manifest, observations=results,
        limitations=['Original IRIX retains the wider mask; Xiri reports only traditional mapped signals.',
                     'No realtime/checkpoint delivery or general multi-LWP support is claimed.',
                     'Application behavior and complete image qualification are separate checks.'])
    if args.regression_log is not None:
        assert args.regression_manifest is not None
        regression_manifest=json.loads(args.regression_manifest.read_text())
        baseline=json.loads((ROOT/'docs/results/2026-11-01-irix-signal-reference-v2.json').read_text())
        assert regression_manifest['files']==baseline['fixtures']
        for path,digest in regression_manifest['sources'].items():
            assert sha(ROOT/path)==digest,path
        log=args.regression_log.read_text();checks=[]
        for case in regression_manifest['cases']:
            fixture=ROOT/'.work/irix-signal-v2/probes'/case['name']
            assert sha(fixture)==regression_manifest['files'][case['name']]['sha256']
            for i in case['identities']:
                name=case['name']+'-'+str(i)
                block,=re.findall(r'^STARTCASE '+re.escape(name)+r'\n(.*?)^ENDCASE '+re.escape(name)+r'$',log,re.M|re.S)
                assert re.search(r'errno_bytes=0 errno=0 exit=0 signal=0 killed=0\n',block)
                assert 'STDERR bytes=0 hex=\n' in block and 'GROUP absent=1' in block
                raw,=re.findall(r'^STDOUT bytes=2048 hex=([0-9a-f]+)$',block,re.M)
                try:
                    checks.append(native.decode(bytes.fromhex(raw),case,1234 if i else 0,fixture.read_bytes(),8192))
                except AssertionError as error:
                    raise AssertionError(name) from error
        assert len(checks)==80
        report['regressions']=dict(records=len(checks),observations=checks,
            manifest_sha256=sha(args.regression_manifest),log_sha256=sha(args.regression_log),
            original_reference_sha256=sha(ROOT/'docs/results/2026-11-01-irix-signal-reference-v2.json'))
    if args.native_run is not None:
        boot=json.loads((args.native_run/'result.json').read_text())
        assert boot['clean_shutdown'] and boot['source_unchanged'] and 'error' not in boot
        report['native_boot']=dict(directory=str(args.native_run),result_sha256=sha(args.native_run/'result.json'),
            module=boot['candidate_module'],initial_sha256=sha(args.native_run/'initial.json'))
    report['diagnostic']=args.diagnostic
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print('Verified', len(results), 'paired records and', len(controls), 'native controls')


if __name__ == '__main__':
    main()
