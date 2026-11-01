#!/usr/bin/env python3
"""Record clean source/build artifacts for the sproc checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kernel-abi',choices=['lp64','o32'],default='lp64')
    args = parser.parse_args()
    o32 = args.kernel_abi == 'o32'
    name = 'o32-baseline.json' if o32 else 'baseline.json'
    pin = json.loads((ROOT/'lab/irix-prda'/name).read_text())
    build = ROOT/('.work/netbsd-irix-sproc'+('-o32' if o32 else '')+'-build')
    source = Path((build/'source-path').read_text().strip())
    revision = (build/'source-revision').read_text().strip()
    assert not (build/'source-status').read_text() and not (build/'source.patch').read_text()
    assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip() == revision
    assert not subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
    conf = 'XIRI_IRIX_SPROC'+('_O32' if o32 else '')
    pin.update(description='Measured bounded IRIX share-process lifecycle',
               ident=conf+'_20261101',source_revision=revision,source_branch='xiri',source_dirty=False,
               config_path='lab/irix-sproc/'+conf,config_sha256=sha(ROOT/'lab/irix-sproc'/conf),
               boot_kernel_sha256=sha(build/'tftp/netbsd-XIRI_INDY'),
               native_kernel_sha256=sha(build/'kernel-media/netbsd'),
               debug_kernel_sha256=sha(build/'obj/sys/arch/sgimips/compile'/conf/'netbsd.gdb'))
    (ROOT/'lab/irix-sproc'/name).write_text(json.dumps(pin,indent=2)+'\n')
    print(name,revision)


if __name__ == '__main__':
    main()
