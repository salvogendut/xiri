#!/usr/bin/env python3
"""Build native NetBSD FAM from pinned public source and pkgsrc patches."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
WORK = Path(os.environ.get('XIRI_FAM_BUILD_DIR', ROOT/'.work/native-fam')).resolve()


def digest(path, algorithm='sha256'):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def run(*args, **kw):
    return subprocess.run([str(a) for a in args], check=True, **kw)


def main():
    if os.environ.get('XIRI_FAM_BUILD_TOOLBOX') == '1':
        work = WORK
        source = work/'fam-2.7.0'
        prefix = ROOT/'.work/netbsd-irix-build/tools/bin/mipseb--netbsd-'
        env = dict(os.environ, CC=str(prefix)+'gcc --sysroot='+str(work/'sysroot'),
                   CXX=str(prefix)+'g++ --sysroot='+str(work/'sysroot'), CXXFLAGS='-O2 -std=gnu++98')
        with (work/'configure.log').open('w') as log:
            run('/bin/bash', './configure', '--host=mipseb--netbsd',
                '--build=x86_64-unknown-linux-gnu', '--prefix=/usr/local',
                '--sysconfdir=/etc', '--disable-shared', '--disable-dependency-tracking',
                cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
        with (work/'build.log').open('w') as log:
            run('make', '-j2', cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT)
        test = ROOT/'lab/native-fam/btree-test.cpp'
        run('g++', '-O2', '-std=gnu++98', '-I'+str(source/'include'), '-I'+str(source), test, '-o', work/'btree-host')
        run(work/'btree-host')
        run(str(prefix)+'g++', '--sysroot='+str(work/'sysroot'), '-O2', '-std=gnu++98',
            '-I'+str(source/'include'), '-I'+str(source), test, '-o', work/'btree-native')
        path_test = ROOT/'lab/native-fam/emul-path-test.cpp'
        run('g++', '-O2', '-std=gnu++98', '-Wall', '-Wextra', '-Werror', path_test, '-o', work/'emul-path-host')
        with tempfile.TemporaryDirectory(prefix='xiri-fam-path-') as temp:
            run(work/'emul-path-host', temp)
        run(str(prefix)+'g++', '--sysroot='+str(work/'sysroot'), '-O2', '-std=gnu++98',
            '-Wall', '-Wextra', '-Werror', path_test, '-o', work/'emul-path-native')
        return
    spec = json.loads((ROOT/'lab/native-fam/source.json').read_text())
    work = WORK
    work.mkdir(parents=True, exist_ok=True)
    cache = work/'inputs'; cache.mkdir(exist_ok=True)
    inputs = dict(spec['files'])
    inputs['fam-2.7.0.tar.gz'] = spec['archive']
    for name, pin in inputs.items():
        path = cache/name; path.parent.mkdir(parents=True, exist_ok=True)
        algorithm = 'sha512' if 'sha512' in pin else 'sha256'
        if not path.exists():
            with urllib.request.urlopen(pin['url'], timeout=60) as response:
                data = response.read()
            assert hashlib.new(algorithm, data).hexdigest() == pin[algorithm], name
            path.write_bytes(data)
        assert digest(path, algorithm) == pin[algorithm], name
    for name, expected in spec.get('local_patches', {}).items():
        assert digest(ROOT/name) == expected, name
    for name, expected in spec.get('local_support', {}).items():
        assert digest(ROOT/name) == expected, name
    source = work/'fam-2.7.0'
    if not source.exists():
        with tarfile.open(cache/'fam-2.7.0.tar.gz') as archive:
            for member in archive.getmembers():
                assert (member.name == 'fam-2.7.0' or member.name.startswith('fam-2.7.0/')) \
                    and '..' not in Path(member.name).parts
            archive.extractall(work, filter='data')
        for patch in sorted((cache/'patches').iterdir()):
            run('git', 'apply', '--whitespace=nowarn', '-p0',
                '--directory='+str(source.relative_to(ROOT)), patch, cwd=ROOT)
        for name in spec.get('local_patches', {}):
            run('git', 'apply', '--whitespace=nowarn', '-p0',
                '--directory='+str(source.relative_to(ROOT)), ROOT/name, cwd=ROOT)
        for name in ['imon-compat.h', 'IMonKQueue.c++']:
            shutil.copyfile(cache/'files'/name, source/'src'/name)
        for name in spec.get('local_support', {}):
            shutil.copyfile(ROOT/name, source/'src'/Path(name).name)
        (work/'source-ready.json').write_text(json.dumps(spec, indent=2)+'\n')
    assert json.loads((work/'source-ready.json').read_text()) == spec
    sysroot = work/'sysroot'
    sets = ROOT/'.work/netbsd-11.0/sgimips/binary/sets'
    checksums = (ROOT/'lab/netbsd-11.0/SHA512SUMS').read_text().splitlines()
    hashes = {line.split()[1].lstrip('*'):line.split()[0] for line in checksums if line.strip()}
    for name in ['base.tgz', 'comp.tgz']:
        assert digest(sets/name, 'sha512') == hashes['sgimips/binary/sets/'+name]
    if not sysroot.exists():
        sysroot.mkdir()
        run('tar', '--no-same-owner', '-xzf', sets/'base.tgz', '-C', sysroot, './usr/lib', './lib')
        run('tar', '--no-same-owner', '-xzf', sets/'comp.tgz', '-C', sysroot, './usr/include', './usr/lib')
        (sysroot/'usr/include/machine').symlink_to('sgimips')
    run('toolbox', 'run', '-c', 'xiri-iris', 'env', 'XIRI_FAM_BUILD_TOOLBOX=1',
        'XIRI_FAM_BUILD_DIR='+str(work),
        'PYTHONDONTWRITEBYTECODE=1', 'python3', Path(__file__).resolve())
    result = dict(status='built', source_manifest_sha256=digest(ROOT/'lab/native-fam/source.json'),
                  builder_sha256=digest(Path(__file__).resolve()),
                  btree_test_sha256=digest(ROOT/'lab/native-fam/btree-test.cpp'),
                  btree_host_passed=True, btree_native_sha256=digest(work/'btree-native'),
                  emul_path_host_passed=True, emul_path_native_sha256=digest(work/'emul-path-native'),
                  emul_path_test_sha256=digest(ROOT/'lab/native-fam/emul-path-test.cpp'),
                  files={n:digest(source/n) for n in ['src/famd', 'test/test', 'lib/.libs/libfam.a']},
                  logs={n:digest(work/n) for n in ['configure.log', 'build.log']})
    (work/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('Built native FAM: '+str(source/'src/famd'))


if __name__ == '__main__':
    main()
