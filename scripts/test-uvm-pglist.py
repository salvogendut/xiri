#!/usr/bin/env python3
"""Exercise the fork's actual contiguous allocator against synthetic RAM holes."""
import argparse
import hashlib
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT.parent/'NetBSD-xiri/sys/uvm/uvm_pglist.c')
    args = parser.parse_args()
    source = args.source.read_text()
    start = source.index('static int\nuvm_pglistalloc_contig_aggressive(')
    end = source.index('\nstatic int\n', start + 1)
    harness = (ROOT/'lab/uvm-pglist/allocator.c').read_text()
    with tempfile.TemporaryDirectory(prefix='xiri-pglist-') as directory:
        path = Path(directory)
        (path/'test.c').write_text(harness.replace('/* ALLOCATOR */', source[start:end]))
        subprocess.run(['cc', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                        str(path/'test.c'), '-o', str(path/'test')], check=True)
        subprocess.run([str(path/'test')], check=True)
    print('Source SHA256:', hashlib.sha256(args.source.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
