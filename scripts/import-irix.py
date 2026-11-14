#!/usr/bin/env python3
"""Import a pinned IRIX donor into a reproducible Xiri vendor payload."""
import argparse
from xiri_lab.irix_import import add_arguments, run

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    run(parser.parse_args())
