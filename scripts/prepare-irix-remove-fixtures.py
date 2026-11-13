#!/usr/bin/env python3
"""Stage independent removal fixtures and their disposable-guest setup script."""
import json
from pathlib import Path
import shlex
import tarfile


def main():
    root = Path(__file__).resolve().parent.parent
    out = root/'.work/irix-remove'
    m = json.loads((out/'probes/manifest.json').read_text())
    cases=[]
    for op in ('u','r'):
        for name,path,setup,mode in [
            ('file','target','echo target >target; ln target alias',0),
            ('file-slash','target/','echo target >target; ln target alias',0),
            ('directory','target','mkdir target',0),
            ('directory-slash','target/','mkdir target',0),
            ('nonempty','target','mkdir target; echo item >target/item',0),
            ('symlink-file','target','ln -s keep target',0),
            ('symlink-file-slash','target/','ln -s keep target',0),
            ('symlink-dir','target','mkdir keepdir; ln -s keepdir target',0),
            ('symlink-dir-slash','target/','mkdir keepdir; ln -s keepdir target',0),
            ('dangling','target','ln -s absent target',0),
            ('missing','target',':',0),
            ('empty','',':',0),
            ('dot','.',':',0),
            ('not-directory','target/child','echo target >target',0),
            ('directory-dot','target/.','mkdir target',0),
            ('null','target','echo target >target',1),
            ('high','target','echo target >target',2),
            ('long','target','echo target >target',3),
            ('denied','blocked/target','mkdir blocked; '+('echo target >blocked/target' if op=='u' else 'mkdir blocked/target')+'; chmod 000 blocked',0),
            ('readonly-parent','target',('echo target >target' if op=='u' else 'mkdir target')+'; chmod 555 .',0),
            ('sticky-other','target',('echo target >target' if op=='u' else 'mkdir target')+'; chown 0 . target; chmod 1777 .',0),
        ]:
            cases.append(dict(name=op+'-'+name,op=op,path=path,setup=setup,mode=mode))
    lines=['#!/bin/sh','set -eu','umask 022','base=/tmp/irix-remove','cd "$base"','test ! -e work','mkdir work results','chmod 755 work','account=$1']
    for abi in m['files']:
        for role in ('root','user'):
            uid=0 if role=='root' else 1234
            for c in cases:
                name=abi+'-'+role+'-'+c['name'];cwd='/tmp/irix-remove/work/'+name
                lines+=['mkdir '+shlex.quote(cwd),'cd '+shlex.quote(cwd), 'echo keep >keep',c['setup']]
                # Assign the fixture identity without following symbolic links or touching
                # the protected parent fixtures (their root ownership is intentional).
                lines+=['chown '+str(uid)+':'+str(uid)+' . keep',
                        'if test ! -L target && test -e target; then chown '+str(uid)+':'+str(uid)+' target; fi']
                if c['name'].endswith('sticky-other'):lines+=['chown 0:0 . target']
                if c['name'].endswith('nonempty'):lines+=['chown '+str(uid)+':'+str(uid)+' target/item']
                command='cd '+shlex.quote(cwd)+' && '+shlex.join(['/tmp/irix-remove/'+abi,c['op'],str(c['mode']),c['path']])
                execute=('/bin/sh -c ' if role=='root' else 'su "$account" -c ')+shlex.quote(command)
                lines+=[execute+' >"$base/results/'+name+'.out" 2>"$base/results/'+name+'.err"']
    lines+=['echo REMOVE_FIXTURES_DONE']
    (out/'run.sh').write_text('\n'.join(lines)+'\n')
    (out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
    with tarfile.open(out/'inputs.tgz','w:gz') as tar:
        for name in m['files']:tar.add(out/'probes'/name,arcname=name)
        tar.add(out/'run.sh',arcname='run.sh')
    print(len(cases)*8,'cases')


if __name__ == '__main__':
    main()
