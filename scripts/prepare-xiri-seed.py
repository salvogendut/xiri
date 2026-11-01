#!/usr/bin/env python3
"""Materialize a reusable raw automation seed from the prepared CHD once."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('bundle', type=Path)
    p.add_argument('--output-directory', type=Path, default=ROOT/'.work/xiri-image/prepared-seed')
    a = p.parse_args()
    bundle, out = a.bundle.resolve(), a.output_directory.resolve()
    m = json.loads((bundle/'manifest.json').read_text())
    assert m['status'] == 'chd-roundtrip-verified'
    assert sha(bundle/'netbsd-xiri.chd') == m['chd_sha256']
    assert sha(bundle/'seed-result.json') == m['source_result_sha256']
    out.mkdir(parents=True, exist_ok=True)
    disk = out/'disk.raw'
    if disk.exists():
        assert sha(disk) == m['source_raw_sha256'], 'existing seed differs; choose another output directory'
    else:
        partial = out/'disk.partial.raw'
        assert not partial.exists(), 'unfinished extraction exists; inspect it before retrying'
        cached = bundle/'verification/roundtrip.raw'
        if cached.exists() and sha(cached) == m['source_raw_sha256']:
            subprocess.run(['cp', '--reflink=auto', '--sparse=always', str(cached), str(partial)], check=True)
        else:
            subprocess.run(['toolbox','run','-c','xiri-iris','chdman','extracthd',
                            '-i',str(bundle/'netbsd-xiri.chd'),'-o',str(partial)], check=True)
        assert partial.stat().st_size == m['logical_bytes'] and sha(partial) == m['source_raw_sha256']
        partial.rename(disk)
    shutil.copyfile(bundle/'seed-result.json', out/'result.json')
    shutil.copyfile(bundle/'nvram.bin', out/'nvram.bin')
    (out/'image-source.json').write_text(json.dumps(dict(bundle=str(bundle),
        chd_sha256=m['chd_sha256'], raw_sha256=m['source_raw_sha256']), indent=2)+'\n')
    print('Reusable seed:', out)


if __name__ == '__main__':
    main()
