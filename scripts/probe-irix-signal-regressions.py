#!/usr/bin/env python3
"""Run an unchanged process/sproc/time matrix against the signal kernel pin."""
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser(description=__doc__, add_help=False)
    parser.add_argument('--suite', choices=['process', 'sproc', 'time'], required=True)
    args, remaining = parser.parse_known_args()
    original = ROOT/'scripts'/('probe-irix-'+args.suite+'.py')
    source = original.read_text()
    # Preserve historical harnesses and fixture hashes. Redirect only the
    # kernel pin/build and output destination; record both harness sources.
    replacements = {
        "ROOT/'lab/irix-"+args.suite+"'/(": "ROOT/'lab/irix-signal'/(",
        "'.work/netbsd-irix-"+args.suite+"'": "'.work/netbsd-irix-signal'",
        "ROOT/'.work/irix-"+args.suite+"/runs'": "ROOT/'.work/irix-signal/regressions/"+args.suite+"'",
    }
    for before, after in replacements.items():
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    anchor = '    for src in '
    assert source.count(anchor) == 1
    source = source.replace(anchor, "    sources.append('scripts/probe-irix-signal-regressions.py')\n"+anchor)
    namespace = {'__name__':'signal_regression', '__file__':str(original)}
    exec(compile(source, str(original), 'exec'), namespace)
    sys.argv = [str(original), *remaining]
    return namespace['main']()


if __name__ == '__main__':
    raise SystemExit(main())
