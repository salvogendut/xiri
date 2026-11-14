#!/usr/bin/env python3
"""Stage symlink and nanosecond timestamp cases for disposable paired guests."""
import json
from pathlib import Path
import shlex
import tarfile


def main():
    root = Path(__file__).resolve().parent.parent
    out = root/'.work/irix-filemeta'
    manifest = json.loads((out/'probes/manifest.json').read_text())
    cases = []
    for name, target, link, setup, mode in [
        ('relative', 'file', 'node', ':', 0),
        ('dangling', 'absent', 'node', ':', 0),
        ('absolute', '/tmp/filemeta-absent', 'node', ':', 0),
        ('parent', '../file', 'node', ':', 0),
        ('empty-target', '', 'node', ':', 0),
        ('empty-link', 'file', '', ':', 0),
        ('existing-file', 'file', 'node', 'echo existing >node', 0),
        ('existing-directory', 'file', 'node', 'mkdir node', 0),
        ('existing-link', 'file', 'node', 'ln -s absent node', 0),
        ('link-slash', 'file', 'node/', ':', 0),
        ('target-slash', 'file/', 'node', ':', 0),
        ('missing-parent', 'file', 'missing/node', ':', 0),
        ('not-directory', 'file', 'file/node', ':', 0),
        ('readonly-parent', 'file', 'node', 'chmod 555 .', 0),
        ('denied-parent', 'file', 'blocked/node', 'mkdir blocked; chmod 000 blocked', 0),
    ] + [(name, 'file', 'node', ':', mode) for mode, name in enumerate(
        ('null-target', 'high-target', 'null-link', 'high-link', 'long-target', 'long-link'), 1)]:
        cases.append(dict(name='s-'+name, op='s', a=target, b=link, setup=setup, mode=mode))
    for name, path, setup, mode in [
        ('file', 'node', 'ln file node', 0),
        ('directory', 'node', 'mkdir node', 0),
        ('follow-link', 'link', ':', 0),
        ('file-slash', 'node/', 'ln file node', 0),
        ('link-slash', 'link/', ':', 0),
        ('missing', 'node', ':', 0),
        ('dangling', 'node', 'ln -s absent node', 0),
        ('readonly-file', 'node', 'ln file node; chmod 444 file', 0),
        ('foreign-owner', 'node', 'ln file node; chmod 666 file', 0),
        ('foreign-now', 'node', 'ln file node; chmod 666 file', 1),
        ('denied-parent', 'blocked/node', 'mkdir blocked; ln file blocked/node; chmod 000 blocked', 0),
    ] + [(name, 'node', 'ln file node', mode) for mode, name in enumerate(
        ('now', 'bad-times', 'negative-nsec', 'large-nsec', 'negative-sec',
         'null-path', 'high-path', 'long-path', 'zero-nsec'), 1)]:
        cases.append(dict(name='t-'+name, op='t', a=path, b=path.rstrip('/'), setup=setup, mode=mode))
    lines = ['#!/bin/sh', 'set -eu', 'umask 022', 'base=/tmp/irix-filemeta',
             'cd "$base"', 'test ! -e work', 'mkdir work results', 'chmod 755 work', 'account=$1']
    for abi in manifest['files']:
        for role, uid in [('root', 0), ('user', 1234)]:
            for case in cases:
                name = abi+'-'+role+'-'+case['name']
                cwd = '/tmp/irix-filemeta/work/'+name
                lines += ['mkdir '+shlex.quote(cwd), 'cd '+shlex.quote(cwd),
                          'echo payload >file', 'ln -s file link', case['setup'],
                          'chown '+str(uid)+':'+str(uid)+' . file']
                if case['name'] in ('t-foreign-owner', 't-foreign-now'):
                    lines += ['chown 0:0 file']
                if case['name'] == 't-directory':
                    lines += ['chown '+str(uid)+':'+str(uid)+' node']
                command = 'cd '+shlex.quote(cwd)+' && '+shlex.join([
                    '/tmp/irix-filemeta/'+abi, case['op'], str(case['mode']), case['a'], case['b']])
                execute = ('/bin/sh -c ' if role == 'root' else 'su "$account" -c ')+shlex.quote(command)
                lines += [execute+' >"$base/results/'+name+'.out" 2>"$base/results/'+name+'.err"']
    lines += ['echo FILEMETA_FIXTURES_DONE']
    (out/'run.sh').write_text('\n'.join(lines)+'\n')
    (out/'cases.json').write_text(json.dumps(cases, indent=2)+'\n')
    with tarfile.open(out/'inputs.tgz', 'w:gz') as archive:
        for name in manifest['files']:
            archive.add(out/'probes'/name, arcname=name)
        for name in ('run.sh', 'cases.json'):
            archive.add(out/name, arcname=name)
    print(len(cases)*8, 'cases')


if __name__ == '__main__':
    main()
