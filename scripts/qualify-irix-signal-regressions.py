#!/usr/bin/env python3
"""Reuse existing regression oracles with the signal kernel pin (LP64 CI)."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser(description=__doc__, add_help=False)
    p.add_argument('--suite', choices=['process', 'sproc', 'time'], required=True)
    p.add_argument('--kernel-checkpoint', choices=['regression', 'final'], default='regression')
    args, rest = p.parse_known_args()
    original = ROOT/'scripts'/('qualify-irix-sproc-kernel.py' if args.suite == 'sproc'
                              else 'qualify-irix-'+args.suite+'.py')
    source = original.read_text()
    # Preserve the exact tested build: these runs preceded the isolated o32
    # sigaction copyout correction. Never relabel an earlier regression run.
    pinroot = 'lab/irix-signal' + ('/regression' if args.kernel_checkpoint == 'regression' else '')
    source = source.replace("ROOT/'lab/irix-"+args.suite+"'/", "ROOT/'"+pinroot+"'/") if args.suite != 'sproc' else source.replace("ROOT/'lab/irix-sproc'/(", "ROOT/'"+pinroot+"'/(")
    # This is one affected-kernel regression, not a new three-mode baseline.
    if args.suite == 'process':
        old = "assert seen == {('lp64', 'ci'), ('lp64', 'ordinary'), ('o32', 'ci')}"
        assert old in source
        source = source.replace(old, "assert seen == {('lp64', 'ci')}")
    if args.suite == 'time':
        old = "assert coverage=={('lp64','ci'),('lp64','ordinary'),('o32','ci')}"
        assert old in source
        source = source.replace(old, "assert coverage=={('lp64','ci')}")
        source = source.replace("assert expected['description']=='Measured IRIX time and gettimeofday'", "assert expected['description']=='IRIX traditional signals and child completion'")
        source = source.replace("assert actual==expected or actual==dict(expected,description='Measured IRIX F_TIME descriptor allocation')", "assert actual==expected")
        # Retain the original time-record oracle rather than looking for it
        # in the signal lab after the pin-only redirection.
        source = source.replace("ROOT/'"+pinroot+"/reference.json'", "ROOT/'lab/irix-time/reference.json'")
    namespace = {'__name__':'signal_regression', '__file__':str(original)}
    exec(compile(source, str(original), 'exec'), namespace)
    sys.argv = [str(original), *rest]
    namespace['main']()
    output = Path(rest[rest.index('--output')+1])
    report = json.loads(output.read_text())
    report['regression_driver_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['regression_scope'] = ('Existing oracle and controls on 1e29ed231349; before the isolated sigaction partial-copyout fix. LP64 CI only; no claim these ran on the final rebuild.'
        if args.kernel_checkpoint == 'regression' else 'Existing oracle and controls on the final signal kernel; LP64 CI only.')
    output.write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
