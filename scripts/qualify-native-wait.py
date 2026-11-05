#!/usr/bin/env python3
"""Compare native multi-child wait regressions on the unfixed and fixed cores."""
import argparse
import json
from pathlib import Path
import re

from xiri_lab import ROOT, sha256

CASES = ('wait6_continued_multiple', 'wait6_stop_exit_after_continue',
         'wait6_stop_and_go', 'wait6_stopgo_loop')


def decode(path, *, fixed):
    blocks = re.split(r'^CASE=', path.read_text(), flags=re.M)
    assert not blocks[0].strip()
    result = {}
    for block in blocks[1:]:
        label, body = block.split('\n', 1)
        assert label not in result, label
        case, uid = label.split(':')
        assert case in CASES and uid in ('0', '1234'), label
        match = re.fullmatch(r'OBS path=\./t_wait errno_bytes=0 errno=0 exit=([01]) signal=0 killed=0\n'
            r'STDOUT bytes=(\d+) hex=([0-9a-f]*)\nSTDERR bytes=(\d+) hex=([0-9a-f]*)\n'
            r'GROUP absent=1\n\s*', body)
        assert match, label
        out, err = bytes.fromhex(match[3]), bytes.fromhex(match[5])
        assert len(out) == int(match[2]) and len(err) == int(match[4]), label
        expected = 0 if fixed or case in CASES[2:] else 1
        assert int(match[1]) == expected, (label, match[1], expected)
        if expected:
            failures = 4 if case == CASES[0] else 2
            assert out == f'failed: {failures} checks failed; see output for more details\n'.encode(), label
            assert err.count(b'*** Check failed:') == failures, label
            assert b'found != pid: selector' in err, label
        else:
            assert out.startswith(b'passed\n'), label
            assert b'Check failed' not in err and b'FATAL' not in err, label
        result[label] = dict(exit=int(match[1]), stdout=out.decode(), stderr=err.decode(),
                             group_absent=True)
    assert set(result) == {f'{case}:{uid}' for case in CASES for uid in (0, 1234)}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, default=ROOT/'.work/job-control')
    p.add_argument('--regressions', type=Path, default=ROOT/'.work/native-wait')
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    observations, inputs, binaries = {}, {}, []
    for phase in ('baseline', 'fixed'):
        path = a.directory/f'native-wait-tests-{phase}.txt'
        meta_path = a.directory/f'native-wait-{phase}-inputs.json'
        meta = json.loads(meta_path.read_text())
        assert sha256(path) == meta['records_sha256']
        for name in ('binary_sha256', 'source_sha256'):
            assert re.fullmatch('[0-9a-f]{64}', meta[name])
            assert meta[name] in meta['guest_hashes']
        binaries.append((meta['binary_sha256'], meta['source_sha256']))
        observations[phase] = decode(path, fixed=phase == 'fixed')
        inputs[phase] = dict(records=str(path), sha256=sha256(path),
            metadata=str(meta_path), metadata_sha256=sha256(meta_path), **meta)
    assert binaries[0] == binaries[1], 'The same native ELF and source must be compared'
    assert sha256(a.directory/'native-t_wait') == binaries[0][0]
    assert sha256(a.directory/'native-t_wait.c') == binaries[0][1]
    build = ROOT/'lab/native-wait/build.json'
    assert sha256(build) == inputs['fixed']['build_manifest_sha256']
    core = json.loads(build.read_text())['artifacts']['netbsd']['sha256']
    assert core in inputs['fixed']['guest_hashes'] and core != inputs['baseline']['core']
    assert inputs['baseline']['core'] in inputs['baseline']['guest_hashes']
    equivalence = build.with_name('source-equivalence.json')
    committed = json.loads(equivalence.read_text())
    assert committed['build_manifest_sha256'] == sha256(build)
    assert committed['source_files'] == json.loads(build.read_text())['source_files']
    assert committed['tracked_clean'] and committed['branch'] == 'xiri'
    assert committed['regression_source_sha256'] == binaries[0][1]
    guest = Path(inputs['fixed']['guest'])/'result.json'
    state = json.loads(guest.read_text())
    assert state['clean_shutdown'] and state['source_unchanged'] and not state.get('error')
    abi = a.regressions/'abi.json'
    abi_result = json.loads(abi.read_text())
    assert abi_result['status'] == 'passed'
    assert len(abi_result['sleep']) == 264 and len(abi_result['children']) == 256
    regression = a.regressions/'regression-result.json'
    regression_result = json.loads(regression.read_text())
    assert regression_result['status'] == 'passed'
    assert regression_result['counts'] == dict(signal=48, sproc=48, process=144)
    result = dict(schema=1, status='passed', inputs=inputs, observations=observations,
                  baseline_new_case_failures=4, baseline_old_case_passes=4,
                  fixed_case_passes=8, binary_identical=True,
                  source_equivalence=dict(path=str(equivalence.relative_to(ROOT)),
                      sha256=sha256(equivalence), commit=committed['commit']),
                  guest=dict(path=str(guest), sha256=sha256(guest), clean_shutdown=True),
                  abi=dict(path=str(abi), sha256=sha256(abi), sleep_cases=264, child_cases=256),
                  regressions=dict(path=str(regression), sha256=sha256(regression),
                      counts=regression_result['counts']),
                  source=str(Path(__file__).relative_to(ROOT)), source_sha256=sha256(Path(__file__)),
                  scope='Native wait selection/accounting; not proof of the older catalog stall cause')
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2)+'\n')
    print('Verified four baseline failures, four old controls and eight fixed-core passes')


if __name__ == '__main__':
    main()
