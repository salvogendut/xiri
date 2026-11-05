#!/usr/bin/env python3
"""Compare process-group records with independent IRIX observations."""
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


def normalize(data, key):
    r = contracts.words(data)
    exe, uid, mode = key
    assert r[:6] == [0x58504752, mode, uid, uid, uid, uid], key
    pid, parent, pgid, sid, child = r[6:11]
    assert min(pid, parent, child) > 0 and len({pid, parent, child}) == 3, key
    assert pgid == pid and sid >= 0 and r[11:16] == [0]*5, key
    child_group = child if mode == 2 else pgid
    child_session = child if mode == 2 else sid
    assert r[16:24] == [0x58504743, child, child_group, child_session, uid,
                        child if mode == 2 else 0, 0, 0], (key, r[16:24])
    assert r[24:32] == [0, 9472, 0, 1, child, 37, 0, 0], (key, r[24:32])
    # Validate every success/error and secondary register before normalizing IDs.
    after_first = child if mode == 0 else child_group
    after_join = pgid if mode == 0 else child_group
    permission = 0 if mode == 0 else 13 if mode == 1 else 1
    missing_group = 13 if mode == 1 else 1
    expected = [
        (64, pgid, 0), (64, pgid, 0), (64, child_group, 0),
        (64, r[44], 0), (64, 22, 1), (64, 22, 1),
        (21, 0, 0), (21, 0, 0), (21, 3, 1), (21, 22, 1),
        (21, 3, 1), (21, 3, 1),
        (21, permission, int(mode != 0)), (64, after_first, 0),
        (21, permission, int(mode != 0)), (64, after_join, 0),
        (21, permission, int(mode != 0)), (64, after_first, 0),
        (21, 22, 1), (21, 22, 1), (64, 22, 1), (21, 3, 1),
        (21, 22, 1), (64, after_first, 0), (65, child_session, 0), (22, 22, 1),
        (64, 3, 1), (64, 22, 1), (64, 22, 1),
        (21, missing_group, 1), (21, missing_group, 1), (21, 22, 1),
        (21, 3, 1), (21, 22, 1), (64, 3, 1),
        (21, missing_group, 1), (21, 3, 1),
    ]
    assert r[44] < 0x7ffffff0, (key, 'parent group')
    for i, (request, value, error) in enumerate(expected):
        actual = r[32+4*i:36+4*i]
        assert actual == [value, contracts.CANARY, error, request], (key, i, actual, expected[i])
    assert r[32+4*len(expected):] == [0]*(256-32-4*len(expected)), key
    for i in [6, 7, 8, 9, 10, 17, 18, 19, 21, 28]:
        r[i] = 0
    for slot in [0, 1, 2, 3, 13, 15, 17, 23, 24]:
        r[32+4*slot] = 0
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    result = dict(schema=1, status='failed', cases=[])
    try:
        old, original = contracts.reference(args.reference, 'group', 1024)
        archive = contracts.archive(args.candidate)
        new = contracts.native(archive['groups.txt'], 1024)
        assert old.keys() == new.keys() and len(old) == 24
        manifest = json.loads(original['manifest.json'])
        assert manifest == json.loads(archive['manifest.json'])
        for path, wanted in manifest['sources'].items():
            assert contracts.digest(ROOT/path) == wanted, path
        for name, item in manifest['files'].items():
            assert hashlib.sha256(original[name]).hexdigest() == item['sha256'], name
            match = re.search(r'^SHA256 \('+re.escape(name)+r'\) = ([0-9a-f]{64})$',
                              archive['digests.txt'].decode(), re.M)
            assert match and match[1] == item['sha256'], name
        for key in old:
            assert normalize(old[key], key) == normalize(new[key], key), key
            result['cases'].append(dict(case=list(key), operations=37, passed=True))
        result.update(status='passed', operations=37*len(old), sources=manifest,
                      inputs={str(path):contracts.digest(path) for path in [args.reference, args.candidate]})
    except Exception as error:
        result['error'] = repr(error)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'], result.get('error', str(len(result['cases']))+' records'))
    return 0 if result['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
