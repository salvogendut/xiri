#!/usr/bin/env python3
"""Compare ordinary-stop selection with original IRIX, reporting empty selection."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('contracts', ROOT/'scripts/qualify-irix-job-control.py')
contracts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contracts)


def normalize(data, key, *, original):
    r = contracts.words(data)
    exe, uid, mode = key
    signal = [23, 24, 26][mode]
    assert r[:6] == [0x58574f50, signal, uid, uid, uid, uid], key
    parent, child = r[6:8]
    assert parent > 0 and child > 0 and parent != child, key
    assert r[8:16] == [0, 0, 5, signal, 0, 0, 1, 37], key
    assert r[16:32] == [0]*16 and r[608:] == [0]*32, key
    r[6:8] = [0, 0]
    for option in range(16):
        at = 32 + 36*option
        # NetBSD rejects an empty event selection. Keep this existing limit
        # explicit instead of presenting the diagnostic matrix as full parity.
        reply = [22, contracts.CANARY, 1] if option == 0 and not original else [0, contracts.CANARY, 0]
        assert r[at:at+4] == reply+[option | 0xc0], (key, option, r[at:at+4])
        info = r[at+4:at+36]
        wanted = [18, 5, 0, child, 0, signal] if option & 4 else [0]*5
        assert info[:len(wanted)] == wanted, (key, option, info[:6])
        if not original:
            assert info[6:] == [0]*26, (key, option, 'unused fields')
            if not option & 4:
                assert info[5] == (0 if option == 0 else 0xffffffff), (key, option, info[5])
        # IRIX's unused siginfo/accounting and no-event status are undefined.
        # Normalize only after checking the meaningful fields and the delta.
        r[at:at+3] = [0, contracts.CANARY, 0]
        r[at+4:at+36] = ([18, 5, 0, 0, 0, signal] if option & 4 else [0]*6)+[0]*26
    return r


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference', required=True, type=Path)
    parser.add_argument('--candidate', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = dict(schema=1, status='failed', cases=[], differences=[])
    try:
        old, original = contracts.reference(args.reference, 'group', 2560)
        archive = contracts.archive(args.candidate)
        new = contracts.native(archive['groups.txt'], 2560)
        assert old.keys() == new.keys() and len(old) == 24
        manifest = json.loads(original['manifest.json'])
        assert manifest == json.loads(archive['manifest.json'])
        for path, wanted in manifest['sources'].items():
            assert contracts.digest(ROOT/path) == wanted, path
        for name, item in manifest['files'].items():
            assert hashlib.sha256(original[name]).hexdigest() == item['sha256'], name
            match = re.search(r'^SHA256 \('+re.escape(name)+r'\) = ([0-9a-f]{64})$', archive['digests.txt'].decode(), re.M)
            assert match and match[1] == item['sha256'], name
        for key in old:
            assert normalize(old[key], key, original=True) == normalize(new[key], key, original=False), key
            result['cases'].append(dict(case=list(key), matching_selections=15, passed=True))
            result['differences'].append(dict(case=list(key), options=192,
                original='success, no event', candidate='EINVAL',
                reason='No event classes selected; retained native validation'))
        result.update(status='passed-with-differences', matching_selections=360,
                      empty_selection_differences=24, sources=manifest,
                      inputs={str(path):contracts.digest(path) for path in [args.reference, args.candidate]})
    except Exception as error:
        result['error'] = repr(error)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'], result.get('error', '360 selections match; 24 empty-selection differences'))
    return 0 if result['status'] == 'passed-with-differences' else 1


if __name__ == '__main__':
    raise SystemExit(main())
