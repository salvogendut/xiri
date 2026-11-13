#!/usr/bin/env python3
"""Package the four independent filesystem-statistics observers."""
import json
from pathlib import Path
import tarfile


def main():
    root = Path(__file__).resolve().parent.parent
    out = root/'.work/irix-statvfs'
    manifest = json.loads((out/'probes/manifest.json').read_text())
    run = '''set -eu
cd /tmp/statvfs
for n in o32-direct o32-indirect n32-direct n32-indirect; do
 ./$n >results/$n-$1.out 2>results/$n-$1.err
done
'''
    (out/'run.sh').write_text(run)
    with tarfile.open(out/'inputs.tgz', 'w:gz') as archive:
        for name in manifest['files']:
            archive.add(out/'probes'/name, arcname=name)
        archive.add(out/'run.sh', arcname='run.sh')
    print(out/'inputs.tgz')


if __name__ == '__main__':
    main()
