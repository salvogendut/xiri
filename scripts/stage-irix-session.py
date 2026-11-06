#!/usr/bin/env python3
"""Stage the original 4Dwm session command helper from the supplied read-only IRIX disk."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parent.parent
SOURCE = '/usr/bin/X11/tellwm'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    out = ROOT/'.work/irix-session-resources'
    out.mkdir(exist_ok=True)
    reference = ROOT/'.work/irix-reference'
    raw = reference/'media/irix65.raw'
    source_manifest = ROOT/'lab/irix-reference/manifest.json'
    assert raw.stat().st_size == json.loads(source_manifest.read_text())['logical_disk_bytes']
    env = dict(os.environ, LIBGUESTFS_BACKEND='direct',
               LIBGUESTFS_CACHEDIR=str(reference/'guestfs-cache'),
               LIBGUESTFS_TMPDIR=str(reference/'tmp'))
    answer = subprocess.check_output(['guestfish', '--ro', '-a', str(raw), '--listen'],
                                     env=env, text=True, timeout=30)
    pid = re.search(r'GUESTFISH_PID=(\d+)', answer)[1]

    def guest(*args):
        return subprocess.check_output(['guestfish', '--remote='+pid, *args],
                                       text=True, timeout=180).strip()

    target = out/'tellwm'
    try:
        guest('run')
        guest('mount-options', 'ro,norecovery', '/dev/sda1', '/')
        guest('download', SOURCE, str(target))
        original_mode = int(re.search(r'^st_mode: (\d+)$', guest('statns', SOURCE), re.M)[1]) & 0o7777
        canonical = guest('realpath', SOURCE)
    finally:
        subprocess.run(['guestfish', '--remote='+pid, 'exit'], check=False, timeout=30)
    spec = importlib.util.spec_from_file_location('inventory', ROOT/'scripts/inventory-irix-desktop.py')
    inventory = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(inventory)
    elf = inventory.elf(target)
    assert elf['abi'] == 'n32' and set(elf['needed']) == {'libX11.so.1', 'libc.so.1'}, elf
    record = dict(irix_source=SOURCE, canonical_source=canonical,
                  netbsd_destination='/emul/irix'+SOURCE, type='file',
                  original_mode=oct(original_mode), mode='0o555', uid=0, gid=0,
                  bytes=target.stat().st_size, sha256=sha(target), elf=elf)
    payload = out/'payload.tgz'
    with tarfile.open(payload, 'w:gz') as tar:
        item = tarfile.TarInfo(record['netbsd_destination'].lstrip('/'))
        item.mode = 0o555
        item.uid = item.gid = item.mtime = 0
        item.size = record['bytes']
        with target.open('rb') as stream:
            tar.addfile(item, stream)
    manifest = dict(schema=1, status='staged-unqualified',
                    extraction='guestfish --ro; mount ro,norecovery',
                    source_image_manifest_sha256=sha(source_manifest),
                    script_sha256=sha(Path(__file__)), payload_sha256=sha(payload),
                    paths={SOURCE: record},
                    limitations=['Resource presence does not qualify saving or restoring an application.',
                                 'No original user session or home directory is imported.'])
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(out/'manifest.json')


if __name__ == '__main__':
    main()
