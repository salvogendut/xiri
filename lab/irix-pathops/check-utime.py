#!/usr/bin/env python3
"""Check the records produced by utime-cases.sh on either supported ABI."""
import argparse
from pathlib import Path

CASES = ('explicit', 'symlink', 'trailing', 'negative', 'minus_one', 'bad_times',
         'missing', 'missing_bad', 'current', 'denied_before', 'denied', 'denied_now',
         'shared_before', 'shared_denied', 'shared_now')


def verify(path, original):
    rows = {}
    for line in path.read_text().splitlines():
        abi, case, *words = line.split()
        if (abi, case) in rows or len(words) != 8:
            raise ValueError(f'Duplicate or incomplete record: {abi} {case}')
        rows[abi, case] = tuple(int(word, 16) for word in words)
    abis = ('o32-direct', 'o32-indirect', 'n32-direct', 'n32-indirect')
    expected = {(abi, case) for abi in abis for case in CASES}
    if rows.keys() != expected:
        raise ValueError(f'Unexpected or missing records: {rows.keys() ^ expected}')
    errors = {'bad_times': 14, 'missing': 2, 'missing_bad': 14,
              'denied': 1, 'denied_now': 13, 'shared_denied': 1}
    if not original:
        errors['minus_one'] = 22
    after_minus_one = 0xffffffff if original else 0xfffffffe
    explicit_access = {'explicit': 946684800, 'symlink': 946684800, 'trailing': 946684800,
                       'negative': 0xfffffffe, 'minus_one': after_minus_one, 'bad_times': after_minus_one}

    def check(ok, detail):
        if not ok:
            raise ValueError(f'{path}: {abi} {case}: {detail}')

    for abi in abis:
        for case in CASES:
            errno, ret, stat, atime, mtime, nsecs, before, after = rows[abi, case]
            check(errno == errors.get(case, 0) and ret == 0, 'utime result')
            check(stat == (2 if case.startswith('missing') else 0), 'xstat result')
            if case in explicit_access:
                check((atime, mtime, nsecs) == (explicit_access[case], 1234567890, 0), 'explicit times')
            if case in ('denied', 'denied_now', 'shared_denied'):
                prior = 'shared_before' if case == 'shared_denied' else 'denied_before'
                check((atime, mtime, nsecs) == rows[abi, prior][3:6], 'timestamps changed on refusal')
            if case in ('current', 'shared_now'):
                check(before <= atime == mtime <= after and nsecs < 1000000000, 'current time')
    return len(rows)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('log', type=Path)
    parser.add_argument('--original', action='store_true', help='expect original IRIX handling of -1 seconds')
    args = parser.parse_args()
    print(f'{verify(args.log, args.original)} timestamp records passed')
