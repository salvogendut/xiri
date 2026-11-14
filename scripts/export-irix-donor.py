#!/usr/bin/env python3
"""Export a stopped Prismatic raw/overlay installation to a verified donor CHD."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

from xiri_lab.donor import export_raw, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path,
                        help='raw base disk; its overlay, dirty map and lease must exist')
    parser.add_argument('--output-directory', required=True, type=Path)
    parser.add_argument('--chdman', default='chdman')
    parser.add_argument('--keep-raw', action='store_true',
                        help='retain merged raw disk for read-only inventory; remove after qualification')
    args = parser.parse_args()
    tool = shutil.which(args.chdman)
    if not tool:
        parser.error('chdman executable not found')
    out = args.output_directory.resolve()
    out.mkdir(parents=True, exist_ok=False)
    raw, chd, roundtrip = (out/name for name in ('disk.raw', 'irix-donor.chd', 'roundtrip.raw'))
    result = {'status': 'incomplete'}
    try:
        print('Exporting merged disk; source files stay read-only', flush=True)
        result.update(export_raw(args.source, raw))
        result['exporter_sha256'] = sha256(__file__)
        result['overlay_reader_sha256'] = sha256(Path(__file__).parent/'xiri_lab/donor.py')
        result['chdman'] = {'path': tool, 'sha256': sha256(tool)}
        result['commands'] = []
        for stage, arguments in [
            ('create', ['createhd', '-i', str(raw), '-o', str(chd), '-ss', '512',
                        '-hs', '16384', '-c', 'zlib', '-np', '2']),
            ('verify', ['verify', '-i', str(chd)]),
            ('roundtrip', ['extracthd', '-i', str(chd), '-o', str(roundtrip)]),
            ('info', ['info', '-i', str(chd)]),
        ]:
            command = [tool, *arguments]
            result['commands'].append(command)
            print(stage, flush=True)
            with (out/(stage+'.log')).open('wb') as log:
                subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
        if (roundtrip.stat().st_size != result['logical_bytes'] or
                sha256(roundtrip) != result['raw_sha256'] or
                sha256(raw) != result['raw_sha256']):
            raise RuntimeError('CHD round trip did not reproduce the exported disk')
        result.update(status='verified', chd_bytes=chd.stat().st_size,
                      chd_sha256=sha256(chd), roundtrip_verified=True,
                      raw_retained=args.keep_raw)
        print('Verified CHD:', chd, flush=True)
    except BaseException as error:
        result.update(status='failed', error=str(error))
        raise
    finally:
        roundtrip.unlink(missing_ok=True)
        if not args.keep_raw:
            raw.unlink(missing_ok=True)
        (out/'export.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    main()
