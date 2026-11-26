#!/usr/bin/env python3
"""Make a private test CD containing the qualified SGI wget executable and its libraries."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('gimp_iso', type=Path, help='local May 2004 GIMP maintenance ISO')
parser.add_argument('instigator', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
spec = json.loads((ROOT/'lab/irix-installer/gimp-cd.json').read_text())
packages = {'fw_wget', 'fw_openssl', 'fw_libz', 'fw_gettext'}
with tempfile.TemporaryDirectory(dir=args.output.parent) as temp:
    work = Path(temp)
    dist = work/'input/dist'
    dist.mkdir(parents=True)
    for key, digest in spec['files'].items():
        name = Path(key).name
        if name.split('.')[0] in packages:
            with (dist/name).open('wb') as out:
                subprocess.run(['isoinfo', '-R', '-i', args.gimp_iso, '-x', '/dist/'+name], stdout=out, check=True)
            if hashlib.sha256((dist/name).read_bytes()).hexdigest() != digest:
                raise ValueError('Unexpected SGI distribution file '+name)
    names = ['bin/wget', 'lib32/libintl.so.3', 'lib32/libz.so.1', 'lib32/libssl.so.0', 'lib32/libcrypto.so.0']
    paths = [arg for name in names for arg in ('--path', 'usr/freeware/'+name)]
    subprocess.run([args.instigator, 'extract', '--unpack', '--name', 'wget', *paths, work/'input', work/'out'], check=True)
    stage = work/'cd'
    stage.mkdir()
    with tarfile.open(stage/'wget.tar', 'w') as archive:
        for name in names:
            source = work/'out/wget/usr/freeware'/name
            if not source.is_file() or source.is_symlink():
                raise ValueError('Expected a real file for '+name)
            if name == 'bin/wget':
                pin = json.loads((ROOT/'docs/results/2026-11-26-irix-utime.json').read_text())['wget']['sha256']
                if hashlib.sha256(source.read_bytes()).hexdigest() != pin:
                    raise ValueError('Unexpected wget executable')
            # Match the installed Freeware library modes. NetBSD requires
            # execute permission for the IRIX loader's executable mappings.
            member = tarfile.TarInfo(source.name)
            member.size, member.mode = source.stat().st_size, 0o555
            with source.open('rb') as data:
                archive.addfile(member, data)
        for lib in ('libssl.so', 'libcrypto.so'):
            member = tarfile.TarInfo(lib)
            member.type, member.linkname, member.mode = tarfile.SYMTYPE, lib+'.0', 0o777
            archive.addfile(member)
    if args.output.exists():
        raise FileExistsError(args.output)
    iso = work/'test.iso'
    subprocess.run(['genisoimage', '-quiet', '-R', '-o', iso, stage], check=True)
    args.output.hardlink_to(iso)
