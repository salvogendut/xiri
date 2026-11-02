#!/usr/bin/env python3
"""Cross-build NetBSD rpcbind using the established native FAM sysroot."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    source = ROOT.parent/'NetBSD-nixbench'
    work = ROOT/'.work/native-rpcbind'
    work.mkdir(parents=True, exist_ok=True)
    sysroot = ROOT/'.work/native-fam/sysroot'
    assert (sysroot/'usr/include/rpc/rpc.h').exists(), 'Build native FAM first'
    compiler = ROOT/'.work/netbsd-irix-build/tools/bin/mipseb--netbsd-gcc'
    names = ['check_bound', 'rpcb_stat', 'rpcb_svc_4', 'rpcbind', 'pmap_svc',
             'rpcb_svc', 'rpcb_svc_com', 'security', 'warmstart', 'util']
    files = [source/'usr.sbin/rpcbind'/(name+'.c') for name in names]
    command = ['toolbox', 'run', '-c', 'xiri-iris', str(compiler),
               '--sysroot='+str(sysroot), '-O2', '-Wall', '-Wextra',
               '-Werror', '-Wno-cast-function-type', '-DPORTMAP', '-DLIBWRAP',
               '-DWARMSTART', '-DINET6', '-DYP',
               '-I'+str(source/'lib/libc/rpc'), '-I'+str(source/'usr.sbin/rpcbind'),
               *map(str, files), '-lwrap', '-lblocklist', '-lutil',
               '-o', str(work/'rpcbind')]
    with (work/'build.log').open('w') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    inputs = files + list((source/'usr.sbin/rpcbind').glob('*.h'))
    inputs += list((source/'lib/libc/rpc').glob('*.h'))
    result = dict(status='built', builder_sha256=sha(Path(__file__)),
                  source_revision=subprocess.check_output(
                      ['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip(),
                  sources={str(p.relative_to(source)):sha(p) for p in inputs},
                  compiler_sha256=sha(compiler), rpcbind_sha256=sha(work/'rpcbind'),
                  log_sha256=sha(work/'build.log'), command=command)
    (work/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Built '+str(work/'rpcbind'), flush=True)


if __name__ == '__main__':
    main()
