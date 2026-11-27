#!/usr/bin/env python3
"""Build a native XiriBSD Indy installation CD from pinned NetBSD sources."""
import argparse
import fcntl
import os
from pathlib import Path
import subprocess

from xiri_lab.native_iso import assemble
from xiri_lab.native_sources import ROOT, prepare


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--work', type=Path, required=True, help='dedicated build directory')
    parser.add_argument('--output', type=Path, help='new .iso path')
    parser.add_argument('--lock', type=Path, help='replay a previous sources.json')
    parser.add_argument('--src-reference', type=Path, help='local NetBSD fork object cache')
    parser.add_argument('--xsrc-reference', type=Path, help='local NetBSD xsrc object cache')
    parser.add_argument('--prepare-only', action='store_true', help='resolve, merge and record the sources')
    parser.add_argument('--tools64', type=Path, help='reuse an existing NetBSD mips64eb TOOLDIR')
    parser.add_argument('-j', type=int, default=min(os.cpu_count() or 1, 12), metavar='JOBS')
    args = parser.parse_args()
    if args.j < 1 or (not args.prepare_only and not args.output):
        parser.error('use a positive job count and specify --output for an ISO build')
    work = args.work.resolve()
    output = args.output.absolute() if args.output else None
    if output and (output.exists() or output.is_symlink()):
        parser.error('choose a new output filename')
    work.mkdir(parents=True, exist_ok=True)
    with (work / '.build.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            parser.error(f'another build is using {work}')
        run_build(args, work, output)


def run_build(args, work, output):
    pins = prepare(work, args.lock, args.src_reference, args.xsrc_reference)
    print(f'Native source lock: {work / "sources.json"}', flush=True)
    if args.prepare_only:
        return

    tmp = work / 'tmp'
    tmp.mkdir(exist_ok=True)
    env = dict(os.environ, TMPDIR=str(tmp), MAKECONF='/dev/null', LC_ALL='C', TZ='UTC')
    src = work / 'src'

    def build(bits, operation):
        target = 'mipseb' if bits == 32 else 'mips64eb'
        cmd = ['sh', 'build.sh', '-U', '-u', '-m', 'sgimips', '-a', target, '-j', str(args.j),
               '-O', work / f'obj{bits}', '-T', work / f'tools{bits}', '-D', work / f'dest{bits}',
               '-R', work / 'release', '-V', 'HOST_CC=cc -std=gnu17', '-V', 'HOST_CFLAGS=-O2 -std=gnu17']
        if bits == 32:
            cmd.extend(['-x', '-X', work / 'xsrc'])
        for option in ('MKDEBUG', 'MKDEBUGLIB', 'MKDEBUGKERNEL', 'MKCTF', 'MKTESTS', 'MKGDB', 'MKLLVM'):
            cmd.extend(['-V', option + '=no'])
        subprocess.run(cmd + [operation], cwd=src, env=env, check=True)

    tools64 = args.tools64.resolve() if args.tools64 else work / 'tools64'
    if not args.tools64:
        build(64, 'tools')
    subprocess.run(['sh', ROOT / 'lab/ip28-kernel/build.sh', src, tools64, work / 'kernel64',
                    ROOT / 'lab/irix-module/XIRI_IRIX_MODULE'], env=env, check=True)
    subprocess.run(['sh', ROOT / 'lab/ip28-kernel/build-module.sh', src, tools64, work / 'module64'],
                   env=env, check=True)
    build(32, 'release')
    assemble(work, output, pins)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error))
