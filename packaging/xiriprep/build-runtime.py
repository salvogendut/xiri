#!/usr/bin/env python3
"""Cross-build the desktop services against this native ISO's sgimips release."""
import argparse
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab.native_package import archive_tree


def build(work, tools, sysroot, output):
    spec = importlib.util.spec_from_file_location('build_fam', ROOT / 'scripts/build-native-fam.py')
    fam = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fam)
    source = fam.prepare_source(work / 'fam')
    cc = str(tools / 'bin/mipseb--netbsd-gcc')
    cxx = str(tools / 'bin/mipseb--netbsd-g++')
    env = dict(os.environ, CC=cc + ' --sysroot=' + str(sysroot), CXX=cxx + ' --sysroot=' + str(sysroot),
               CXXFLAGS='-O2 -std=gnu++98')
    with tempfile.TemporaryDirectory(dir=work) as temp:
        tree = Path(temp)
        package = tree / 'package'
        package.mkdir()
        archive_tree(source, package / 'fam-source.tgz')
        fam_build = tree / 'fam-build'
        shutil.copytree(source, fam_build)
        subprocess.run(['sh', fam_build / 'configure', '--host=mipseb--netbsd',
                        '--prefix=/usr/local', '--sysconfdir=/etc', '--disable-shared',
                        '--disable-dependency-tracking'], cwd=fam_build, env=env, check=True)
        subprocess.run(['make', '-j4'], cwd=fam_build, env=env, check=True)
        binaries = package / 'build'
        runtime = ROOT / 'runtime'
        subprocess.run(['make', 'all', f'BUILDDIR={binaries}', 'CC=' + env['CC'],
                        f'X11_CPPFLAGS=-I{sysroot}/usr/X11R7/include',
                        f'X11_LDFLAGS=-L{sysroot}/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib'],
                       cwd=runtime, check=True)
        target = tree / 'desktop-runtime.tgz'
        shutil.copyfile(runtime / 'install.sh', package / 'install.sh')
        for name in ('etc', 'bin', 'sbin', 'libexec', 'rc.d'):
            shutil.copytree(runtime / name, package / name)
        shutil.copy(fam_build / 'src/famd', binaries / 'famd')
        archive_tree(package, target)
        output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(target, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('work', 'tools', 'sysroot', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    args.work.mkdir(parents=True, exist_ok=True)
    build(args.work.resolve(), args.tools.resolve(), args.sysroot.resolve(), args.output.resolve())
