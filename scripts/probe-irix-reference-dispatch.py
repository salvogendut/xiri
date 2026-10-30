#!/usr/bin/env python3
"""Measure original dispatcher/hint probes and asa on disposable IRIX."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('reference', Path(__file__).with_name('probe-irix-reference-elfmap.py'))
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)

if __name__ == '__main__':
    raise SystemExit(reference.main('dispatch'))
