#!/usr/bin/env python3
"""Package the pinned NetBSD components and cross-build the Xiri runtime."""
import argparse
from xiri_lab.native_package import add_arguments, run

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    run(parser.parse_args())
