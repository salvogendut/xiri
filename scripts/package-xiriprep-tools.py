#!/usr/bin/env python3
"""Make an update CD for an existing Indy from the tools in a native XiriBSD ISO."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

from xiri_lab.native_iso import XIRIPREP_FILES, XIRIPREP_PROGRAMS, write_set


def member(iso, name):
    return subprocess.check_output(['isoinfo', '-R', '-i', iso, '-x', '/' + name])


def package(iso, output):
    if output.exists() or output.is_symlink():
        raise ValueError(f'Output already exists: {output}')
    inventory = json.loads(member(iso, 'native-media.json'))
    kernel_set, = (k for k in inventory['sha256'] if '/kern-GENERIC32_IP2x.' in k)
    data = member(iso, kernel_set)
    if hashlib.sha256(data).hexdigest() != inventory['sha256'][kernel_set]:
        raise ValueError('Installer kernel set checksum mismatch')
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        files = {}
        for name in XIRIPREP_FILES:
            # Earlier native ISOs ship just the two reference donor plans.
            if name.endswith(('-ip28.plan', '-ip30.plan')) and name not in inventory['kernel_set_files']:
                continue
            entry = archive.getmember('./' + name)
            if not entry.isfile() or entry.uid or entry.gid or entry.mode != (0o555 if name in XIRIPREP_PROGRAMS else 0o444):
                raise ValueError(f'Unexpected installer entry: {name}')
            files[name] = archive.extractfile(entry).read()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as tmp:
        work = Path(tmp)
        tools = work / 'xiriprep.tgz'
        write_set(tools, files, 0, executables=XIRIPREP_PROGRAMS)
        candidate = work / 'tools.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'XIRIPREP', '-o', candidate, tools], check=True)
        if member(candidate, tools.name) != tools.read_bytes():
            raise ValueError('Tools CD readback differs')
        candidate.rename(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installer', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    package(args.installer, args.output)
