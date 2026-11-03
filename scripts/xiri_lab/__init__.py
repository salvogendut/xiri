"""Shared support for the maintained Xiri desktop workflows."""
import hashlib
import importlib.util
from pathlib import Path
import sys

from .guest import Guest

ROOT = Path(__file__).resolve().parents[2]


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def load_probe():
    """Reuse the established boot/process owner without changing old probes."""
    name = '_xiri_netbsd_probe'
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, ROOT/'scripts/probe-netbsd.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def source_hashes():
    paths = ['scripts/xiri_lab/__init__.py', 'scripts/xiri_lab/guest.py',
             'scripts/probe-netbsd.py']
    return {name: sha256(ROOT/name) for name in paths}
