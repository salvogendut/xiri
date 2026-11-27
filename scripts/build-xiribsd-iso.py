#!/usr/bin/env python3
"""Build a native XiriBSD Indy installation CD from pinned NetBSD sources."""
import argparse
from datetime import date
import fcntl
import os
from pathlib import Path
import re
import shutil
import subprocess

from xiri_lab.native_iso import assemble
from xiri_lab.native_sources import ROOT, prepare


def installer_filename(src, xiri_version, build_date):
    release = subprocess.check_output(['sh', src / 'sys/conf/osrelease.sh'], text=True).strip()
    parts = re.fullmatch(r'([0-9]+)\.([0-9]+)(?:\.([0-9]+))?(?:_[A-Za-z0-9_]+)?', release)
    if not parts:
        raise ValueError(f'Cannot determine the numeric NetBSD release from {release!r}')
    version = '.'.join(f'{int(part):02d}' for part in parts.groups(default='0'))
    return f'xiribsd-{version}-{xiri_version:02d}-{build_date.isoformat()}.iso'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True, help='dedicated build directory')
    dest = parser.add_mutually_exclusive_group()
    dest.add_argument('--output-dir', type=Path, default=ROOT / '.work/images',
                      help='directory for the versioned ISO (default: .work/images)')
    dest.add_argument('--output', type=Path, help='explicit path matching the versioned installer filename')
    parser.add_argument('--xiri-version', type=int, default=1,
                        help='XiriBSD installer revision, 00–99 (default: 01)')
    parser.add_argument('--lock', type=Path, help='replay a previous sources.json')
    parser.add_argument('--src-reference', type=Path, help='local NetBSD fork object cache')
    parser.add_argument('--xsrc-reference', type=Path, help='local NetBSD xsrc object cache')
    parser.add_argument('--prepare-only', action='store_true', help='resolve, merge and record the sources')
    parser.add_argument('--tools64', type=Path, help='reuse an existing NetBSD mips64eb TOOLDIR')
    parser.add_argument('--toolbox', metavar='NAME', help='run NetBSD compilation in this Fedora Toolbox')
    parser.add_argument('-j', type=int, default=min(os.cpu_count() or 1, 12), metavar='JOBS')
    args = parser.parse_args()
    if args.j < 1:
        parser.error('use a positive job count')
    if not 0 <= args.xiri_version <= 99:
        parser.error('--xiri-version must be between 00 and 99')
    work = args.work.resolve()
    work.mkdir(parents=True, exist_ok=True)
    with (work / '.build.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error(f'another build is using {work}')
        run_build(args, work)


def run_build(args, work):
    if not args.prepare_only:
        for tool in ['genisoimage', 'isoinfo'] + (['toolbox'] if args.toolbox else []):
            if shutil.which(tool) is None:
                raise ValueError(f'Install {tool} on the workstation before building the CD.')
    pins = prepare(work, args.lock, args.src_reference, args.xsrc_reference)
    print(f'Native source lock: {work / "sources.json"}', flush=True)
    if args.prepare_only:
        return

    src = work / 'src'
    name = installer_filename(src, args.xiri_version, date.today())
    output = args.output.absolute() if args.output else args.output_dir.absolute() / name
    if output.name != name:
        raise ValueError(f'Expected installer filename {name}. Use --output-dir to select its directory.')
    if output.exists() or output.is_symlink():
        raise ValueError(f'Output exists: {output}')

    tmp = work / 'tmp'
    tmp.mkdir(exist_ok=True)
    settings = dict(TMPDIR=str(tmp), MAKECONF='/dev/null', LC_ALL='C', TZ='UTC')
    env = dict(os.environ, **settings)
    prefix = (['toolbox', 'run', '-c', args.toolbox, 'env']
              + [f'{key}={value}' for key, value in settings.items()] if args.toolbox else [])

    def build(bits, operation):
        target = 'mipseb' if bits == 32 else 'mips64eb'
        cmd = ['sh', 'build.sh', '-U', '-u', '-m', 'sgimips', '-a', target, '-j', str(args.j),
               '-O', work / f'obj{bits}', '-T', work / f'tools{bits}', '-D', work / f'dest{bits}',
               '-R', work / 'release', '-V', 'HOST_CC=cc -std=gnu17', '-V', 'HOST_CFLAGS=-O2 -std=gnu17']
        if bits == 32:
            cmd.extend(['-x', '-X', work / 'xsrc'])
        for option in ('MKDEBUG', 'MKDEBUGLIB', 'MKDEBUGKERNEL', 'MKCTF', 'MKTESTS', 'MKGDB', 'MKLLVM'):
            cmd.extend(['-V', option + '=no'])
        subprocess.run(prefix + cmd + [operation], cwd=src, env=env, check=True)

    tools64 = args.tools64.resolve() if args.tools64 else work / 'tools64'
    if not args.tools64:
        build(64, 'tools')
    subprocess.run(prefix + ['sh', ROOT / 'lab/ip28-kernel/build.sh', src, tools64, work / 'kernel64',
                    ROOT / 'lab/irix-module/XIRI_IRIX_MODULE'], env=env, check=True)
    subprocess.run(prefix + ['sh', ROOT / 'lab/ip28-kernel/build-module.sh', src, tools64, work / 'module64'],
                   env=env, check=True)
    build(32, 'release')
    reader = work / 'xiriprep-build'
    for cmd in (
            ['cmake', '-S', ROOT / 'packaging/xiriprep', '-B', reader,
             f'-DNETBSD_SRC={src}', '-DCMAKE_BUILD_TYPE=Release', '-DCMAKE_SYSTEM_NAME=NetBSD',
             '-DCMAKE_SYSTEM_PROCESSOR=mips', f'-DCMAKE_SYSROOT={work / "dest32"}',
             f'-DCMAKE_C_COMPILER={work / "tools32/bin/mipseb--netbsd-gcc"}'],
            ['cmake', '--build', reader, '--target', 'xiri-donor-read', '-j', str(args.j)],
            ['cmake', '--install', reader, '--prefix', work / 'xiriprep-stage/usr/local'],
            ['python3', ROOT / 'packaging/xiriprep/build-runtime.py', '--work', work / 'desktop-build',
             '--tools', work / 'tools32', '--sysroot', work / 'dest32',
             '--output', work / 'xiriprep-stage/usr/local/share/xiri/desktop-runtime.tgz']):
        subprocess.run(prefix + cmd, env=env, check=True)
    assemble(work, output, pins)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
