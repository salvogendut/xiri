#!/usr/bin/env python3
"""Compare independent IRIX terminal observations with the native module run."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import tarfile


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def members(path):
    with tarfile.open(path) as archive:
        return {m.name.removeprefix('./'): archive.extractfile(m).read()
                for m in archive if m.isfile()}


def attributes(data, offset=0):
    """Ignore only padding and obsolete baud bits in the modern flag word.

    IRIX retains legacy baud bits after an old-style setter; NetBSD keeps the
    actual rates separately. The explicit rates and every other flag still
    compare. IRIX's struct padding varies with prior kernel stack contents.
    """
    result = bytearray(data)
    flags, = struct.unpack_from('>I', result, offset+8)
    struct.pack_into('>I', result, offset+8, flags & ~0xf000f)
    result[offset+47] = 0
    return result


def qualify(reference_path, native_path, manifest):
    original, native = members(reference_path), members(native_path)
    for exe, info in manifest['files'].items():
        assert hashlib.sha256(native[exe]).hexdigest() == info['sha256'], exe
        assert hashlib.sha256(original[exe]).hexdigest() == info['sha256'], exe
    statuses = {}
    for uid in [0, 1234]:
        for line in original[f'status-{uid}.txt'].decode().splitlines():
            name, status = line.split()
            assert status == '0', (name, status)
            statuses[name] = uid
    assert len(statuses) == 864, len(statuses)
    results = []
    for name, uid in statuses.items():
        assert not original[name+'.err'] and not native[name+'.err'], name
        reference = original[name+'.out']
        log = native[name+'.log'].decode()
        assert re.search(r'^OBS .* errno_bytes=0 errno=0 exit=0 signal=0 killed=0$', log, re.M), name
        assert 'GROUP absent=1' in log, name
        assert 'STDERR bytes=0 hex=' in log, name
        seen = bytes.fromhex(re.search(r'^STDOUT bytes=1024 hex=([0-9a-f]+)$', log, re.M)[1])
        expected = struct.unpack('>256I', reference)
        actual = struct.unpack('>256I', seen)
        assert actual[:7] == expected[:7] == (*expected[:5], uid, uid), name
        for slot in [11, 14, 17, 20, 29, 47, 50, 53]:
            assert actual[slot+2] == expected[slot+2] == 0, (name, 'setup', slot, actual[slot:slot+3])
        assert actual[26:29:2] == expected[26:29:2], (name, 'return', actual[26:29:2], expected[26:29:2])
        assert attributes(seen[512:560]) == attributes(reference[512:560]), (name, 'attributes', seen[512:560].hex(), reference[512:560].hex())
        cmd, kind, ptr = actual[1:4]
        modern = (cmd & 255) >= 200
        line = (cmd & 255) % 200 < 13
        getter = cmd in [0x5401, 0x540d, 0x54c9, 0x54d5]
        x, y = bytearray(seen[256:336]), bytearray(reference[256:336])
        if getter and actual[28] == 0:
            off = 1 if ptr == 5 else 0
            if modern and not line:
                x, y = attributes(x, off), attributes(y, off)
            elif not line:
                x[off+39] = y[off+39] = 0
        assert x == y, (name, 'memory', x.hex(), y.hex())
        results.append(dict(name=name, passed=True))
    return results



def qualify_sessions(reference_path, native_path, manifest):
    original, native = members(reference_path), members(native_path)
    for exe, info in manifest['files'].items():
        for tree in [original, native]:
            assert hashlib.sha256(tree[exe]).hexdigest() == info['sha256'], exe
    results = []
    for uid in [0, 1234]:
        for line in original[f'status-{uid}.txt'].decode().splitlines():
            name, status = line.split()
            assert status == '0' and not original[name+'.err'] and not native[name+'.err'], name
            log = native[name+'.log'].decode()
            assert re.search(r'^OBS .* errno_bytes=0 errno=0 exit=0 signal=0 killed=0$', log, re.M), name
            assert 'GROUP absent=1' in log and 'STDERR bytes=0 hex=' in log, name
            seen = bytes.fromhex(re.search(r'^STDOUT bytes=1024 hex=([0-9a-f]+)$', log, re.M)[1])
            a = list(struct.unpack('>256I', seen))
            b = list(struct.unpack('>256I', original[name+'.out']))
            mode, pid = a[1], a[17]
            assert a[:5] == b[:5] and a[2:4] == [uid, uid], name
            for slot in [5, 8, 11, 14, 17, 23, 53, 56]:
                assert a[slot+2] == b[slot+2] == 0, (name, 'setup', slot)
            if mode != 2:
                assert a[20] == a[53] == a[56] == pid and a[22] == 0, name
            for slot in [29, 32, 35, 38, 41, 44, 47, 50]:
                expected = [b[slot], b[slot+2]]
                if mode == 7 and slot == 41:
                    expected = [1, 1]  # Native TIOCSPGRP uses EPERM for an absent group.
                assert [a[slot], a[slot+2]] == expected, (name, slot, a[slot:slot+3], expected)
            for slot in [64, 65, 66, 68, 69, 70]:
                expected = pid if b[slot] == b[17] else b[slot]
                assert a[slot] == expected, (name, slot, a[slot], expected)
            results.append(dict(name=name, passed=True))
    assert len(results) == 64
    return results


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference', required=True, type=Path)
    p.add_argument('--sessions', action='store_true')
    p.add_argument('--native', required=True, type=Path)
    p.add_argument('--reference-run', required=True, type=Path)
    p.add_argument('--native-run', required=True, type=Path)
    p.add_argument('--diagnostic', action='store_true')
    p.add_argument('--manifest', type=Path, default=Path('.work/irix-termios/probes/manifest.json'))
    p.add_argument('--output', required=True, type=Path)
    args = p.parse_args()
    manifest = json.loads(args.manifest.read_text())
    original = json.loads((args.reference_run/'result.json').read_text())
    assert original['clean_shutdown'], 'reference must halt cleanly'
    current = json.loads((args.native_run/('initial.json' if args.diagnostic
                                         else 'result.json')).read_text())
    if not args.diagnostic:
        assert current['clean_shutdown'] and current['source_unchanged']
    result = dict(schema=1, status='diagnostic' if args.diagnostic else 'passed',
                  reference_run=str(args.reference_run), native_run=str(args.native_run),
                  candidate_module=current['candidate_module'],
                  reference_sha256=sha(args.reference),
                  native_sha256=sha(args.native), manifest=manifest,
                  qualifier_sha256=sha(Path(__file__)),
                  policies=['Modern flags omit retained legacy baud bits; explicit rates are compared.',
                            'Undefined termios padding is zeroed, not copied from kernel stack contents.'])
    if args.sessions:
        result['policies'] = ['Native TIOCSPGRP returns EPERM for an absent group; measured IRIX returns EINVAL.']
        result['observations'] = qualify_sessions(args.reference, args.native, manifest)
    else:
        result['observations'] = qualify(args.reference, args.native, manifest)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(len(result['observations']), 'paired terminal cases passed')


if __name__ == '__main__':
    main()
