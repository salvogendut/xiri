#!/usr/bin/env python3
"""Stage hash-checked sleep/child fixtures and scripts for fresh guest directories."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    for group in ['nanosleep', 'children', 'groups', 'wait-options']:
        source = ROOT/'.work/irix-job-control'/group
        manifest = json.loads((source/'manifest.json').read_text())
        for name, digest in manifest['sources'].items():
            assert sha(ROOT/name) == digest, name
        (out/group).mkdir()
        for name, entry in manifest['files'].items():
            assert sha(source/name) == entry['sha256'], name
            shutil.copyfile(source/name, out/group/name)
        shutil.copyfile(source/'manifest.json', out/group/'manifest.json')
    for name, source in {
        'runner.c': 'lab/irix-process/runner.c',
        **{name:'lab/irix-job-control/'+name for name in
           ['guardian.c', 'native-children.c', 'headers.c', 'libc-sleep.c', 'sleep-rounding.c',
            'group-headers.c', 'group-errors.c', 'group-range.c']},
    }.items():
        shutil.copyfile(ROOT/source, out/name)
    native = ['#!/bin/sh', 'set -eu', 'test "$(id -u)" = 0',
              'test ! -e native-results', 'mkdir native-results',
              'cc -O2 -Wall -Wextra -Werror runner.c -o native-results/runner',
              'cc -O2 -Wall -Wextra -Werror native-children.c -o native-results/native-children',
              'cp -R nanosleep children native-results/', 'cd native-results',
              ': >input.txt', 'chmod 644 input.txt',
              'chmod 755 nanosleep/*-direct nanosleep/*-indirect children/*-direct children/*-indirect',
              ': >sleep.txt', ': >children.txt', ': >native.txt',
              'if test "${1:-full}" = baseline; then sleeps="0 20 21"; modes="0 1"; selectors=0; '
              'else sleeps="'+ ' '.join(map(str,range(33)))+'"; modes="0 1 2 3"; selectors="0 1 2 3 4 5 6 7"; fi',
              'for uid in 0 1234; do',
              ' for exe in o32-direct o32-indirect n32-direct n32-indirect; do',
              '  for mode in $sleeps; do',
              '   echo "CASE:$exe:$uid:$mode" >>sleep.txt',
              '   ./runner "./nanosleep/$exe" "$uid" "$uid" "$uid" "$uid" -- "$mode" >>sleep.txt',
              '  done', '  for mode in $modes; do for selector in $selectors; do',
              '   echo "CASE:$exe:$uid:$mode:$selector" >>children.txt',
              '   ./runner "./children/$exe" "$uid" "$uid" "$uid" "$uid" -- "$mode" "$selector" >>children.txt',
              '  done; done', ' done', ' for mode in normal suppress; do',
              '  echo "CASE:native:$uid:$mode" >>native.txt',
              '  if test "$mode" = suppress; then arg=suppress; else arg=; fi',
              '  ./runner ./native-children "$uid" "$uid" "$uid" "$uid" -- $arg >>native.txt',
              ' done', 'done',
              'sha256 nanosleep/*-direct nanosleep/*-indirect children/*-direct children/*-indirect >digests.txt',
              'tar czf ../native-results.tgz sleep.txt children.txt native.txt digests.txt nanosleep/manifest.json children/manifest.json']
    (out/'run-native.sh').write_text('\n'.join(native)+'\n')
    groups = ['#!/bin/sh', 'set -eu', 'test "$(id -u)" = 0',
              'mkdir groups/native-results', 'cc -O2 -Wall -Wextra -Werror runner.c -o groups/native-results/runner',
              'cd groups/native-results', 'cp ../*-direct ../*-indirect ../manifest.json .',
              'chmod 755 *-direct *-indirect', ': >input.txt', 'chmod 644 input.txt', ': >groups.txt',
              'for uid in 0 1234; do for exe in o32-direct o32-indirect n32-direct n32-indirect; do',
              ' for mode in 0 1 2; do', '  echo "CASE:$exe:$uid:$mode" >>groups.txt',
              '  ./runner "./$exe" "$uid" "$uid" "$uid" "$uid" -- "$mode" >>groups.txt',
              ' done', 'done; done', 'sha256 *-direct *-indirect >digests.txt',
              'tar czf ../../groups-native.tgz groups.txt manifest.json digests.txt']
    (out/'run-native-groups.sh').write_text('\n'.join(groups)+'\n')
    (out/'run-native-wait-options.sh').write_text('\n'.join(
        line.replace('groups/', 'wait-options/').replace('groups-native.tgz', 'wait-options-native.tgz')
        for line in groups)+'\n')
    for group in ['nanosleep', 'children', 'groups', 'wait-options']:
        prefix = {'nanosleep':'sleep', 'children':'child', 'groups':'group', 'wait-options':'group'}[group]
        lines = ['#!/bin/sh', 'set -eu', 'cd '+group, 'mkdir reference', 'cd reference',
                 'cp ../*-direct ../*-indirect ../manifest.json ../../guardian.c .',
                 'chmod 755 *-direct *-indirect',
                 '/usr/freeware/bin/gcc -D_SGI_SOURCE -mabi=n32 -O2 -Wall -Werror guardian.c -o guardian',
                 'ulimit -c 0', ': >status.txt', 'cksum *-direct *-indirect >checksums.txt']
        if group == 'nanosleep':
            lines += ['if ./guardian timeout.guard /bin/sleep 30 >timeout.out 2>timeout.err; then exit 1; else echo "TIMEOUT $?" >>status.txt; fi']
        for uid in [0, 1]:
            for exe in ['o32-direct', 'o32-indirect', 'n32-direct', 'n32-indirect']:
                cases = [(str(i), f'{i:02d}') for i in range(33)] if group == 'nanosleep' else [(f'{mode} {selector}', f'{mode}-{selector}') for mode in range(4) for selector in range(8)]
                if group in ['groups', 'wait-options']:
                    cases = [(str(mode), str(mode)) for mode in range(3)]
                for arguments, suffix in cases:
                    label = f'{prefix}-{exe}-{uid}-{suffix}'
                    lines += [f'./guardian {label}.guard ./{exe} {arguments} {uid} >{label}.out 2>{label}.err', f'echo "{label} 0" >>status.txt']
        archive_name = 'wait-options' if group == 'wait-options' else prefix
        lines += ['tar cf ../../'+archive_name+'-reference.tar .']
        (out/('run-reference-'+group+'.sh')).write_text('\n'.join(lines)+'\n')
    (out/'SHA256').write_text(''.join(f'SHA256 ({p.relative_to(out)}) = {sha(p)}\n' for p in sorted(out.rglob('*')) if p.is_file()))
    archive = out.with_suffix('.tgz')
    if archive.exists():
        raise FileExistsError(archive)
    with tarfile.open(archive, 'w:gz') as stream:
        for path in sorted(out.rglob('*')):
            if path.is_file():
                stream.add(path, arcname=str(path.relative_to(out)))
    print(archive)


if __name__ == '__main__':
    main()
