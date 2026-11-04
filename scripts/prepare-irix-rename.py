#!/usr/bin/env python3
"""Package identical rename observers and case setup for IRIX and NetBSD."""
import json
from pathlib import Path
import shlex
import tarfile

ROOT = Path(__file__).resolve().parent.parent


def main():
    out = ROOT/'.work/irix-rename'
    cases = json.loads((ROOT/'lab/irix-pathops/rename-cases.json').read_text())
    manifest = json.loads((out/'probes/manifest.json').read_text())
    base = '/tmp/xiri-pathops'
    setup = ['set -eu', 'cd '+base, 'umask 022']
    reference = ['set -eu', 'cd '+base, ': >status-$1.txt']
    native = ['set -eu', 'cd '+base, 'ulimit -c 0']
    for executable in manifest['files']:
        for case in cases:
            name = executable+'-'+case['name']+'-$1'
            directory = 'cases/'+name
            # The bounded native parent opens this before executing the probe.
            setup += ['mkdir '+directory,
                      '(cd '+directory+'; : >input.txt; '+case['setup']+')']
            args = shlex.join([str(case['mode']), case['source'], case['destination']])
            program = base+'/'+executable
            reference += ['(cd '+directory+'; '+program+' '+args+') >'+name+
                          '.out 2>'+name+'.err; echo '+name+' "$?" >>status-$1.txt']
            native += ['(cd '+directory+'; '+base+'/runner '+program+
                       ' "$1" "$1" "$1" "$1" -- '+args+') >'+name+'.log 2>'+name+'.err']
    scripts = [('setup.sh', setup), ('reference-run.sh', reference), ('native-run.sh', native)]
    for name, lines in scripts:
        (out/name).write_text('\n'.join(lines)+'\n')
    with tarfile.open(out/'probes.tar', 'w') as archive:
        for executable in manifest['files']:
            archive.add(out/'probes'/executable, arcname=executable)
        archive.add(ROOT/'lab/irix-process/runner.c', arcname='runner.c')
        for name, _ in scripts:
            archive.add(out/name, arcname=name)
    print(out/'probes.tar')


if __name__ == '__main__':
    main()
