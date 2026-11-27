"""Assemble the Indy sysinst CD from a native sgimips release and its N64 kernel."""
import gzip
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile

from .native_sources import ROOT

# Keep this list in sync with the menu in lab/native-iso/indy-sysinst.patch.
SYSTEM_SETS = ('base', 'etc', 'comp', 'rescue', 'games', 'man', 'misc', 'text',
               'xbase', 'xetc', 'xfont', 'xserver', 'xcomp')
SGI_HEADER_SECTORS = 4096


def digest(path, algorithm):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def write_set(path, files, timestamp):
    with path.open('wb') as raw:
        compressed = (gzip.GzipFile(fileobj=raw, filename='', mode='wb', mtime=timestamp)
                      if path.name.endswith('.tgz') else lzma.LZMAFile(raw, 'wb'))
        with compressed, tarfile.open(fileobj=compressed, mode='w|',
                                      format=tarfile.USTAR_FORMAT) as archive:
            for name, source in sorted(files.items()):
                data = source if isinstance(source, bytes) else source.read_bytes()
                entry = tarfile.TarInfo('./' + name)
                entry.size, entry.mode, entry.mtime = len(data), 0o444, timestamp
                entry.uname, entry.gname = 'root', 'wheel'
                archive.addfile(entry, io.BytesIO(data))


def assemble(work, output, source_lock):
    release = work / 'release/sgimips/binary'
    source_sets = release / 'sets'
    kernel = work / 'kernel64/kernel'
    module = work / 'module64/module/compat_irix_o32.kmod'
    tools = work / 'tools32/bin'
    dest = work / 'dest32'
    version = subprocess.check_output(['sh', work / 'src/sys/conf/osrelease.sh', '-k'],
                                      text=True).strip()
    stamp = int(subprocess.check_output(['git', '-C', work / 'src', 'show', '-s',
                                         '--format=%ct', source_lock['commits']['src']]))
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        raise ValueError(f'Output exists: {output}')
    with tempfile.TemporaryDirectory(prefix='.native-iso-', dir=output.parent) as tmp:
        temp = Path(tmp)
        cd = temp / 'cd'
        sets = cd / 'sgimips/binary/sets'
        sets.mkdir(parents=True)
        # release runs NetBSD checkflist against DESTDIR and the source set lists.
        # Accept only named sysinst sets from this release, and verify their hashes.
        sums = (source_sets / 'SHA512').read_text().splitlines()
        if (source_sets / 'base.tgz').is_file():
            suffix = '.tgz'
        else:
            suffix = '.tar.xz'
        for name in SYSTEM_SETS:
            source = source_sets / (name + suffix)
            if f'SHA512 ({source.name}) = {digest(source, "sha512")}' not in sums:
                raise ValueError(f'Release checksum mismatch: {source}')
            shutil.copyfile(source, sets / source.name)
        stock = gzip.decompress((release / 'kernel/netbsd-GENERIC32_IP2x.gz').read_bytes())
        resources = {
            'netbsd': kernel / 'netbsd', 'netbsd.boot': kernel / 'netbsd.elf32',
            'netbsd.stock': stock,
            'etc/xiri/xdm/Xservers': ROOT / 'runtime/etc/xdm-Xservers',
            'etc/xiri/xdm/Xresources': ROOT / 'runtime/etc/xdm-Xresources',
            'usr/local/share/xiri/xdm-logo.xpm': ROOT / 'runtime/etc/xiri-logo.xpm',
            'usr/local/share/xiri/xorg.conf': ROOT / 'lab/newport-accel/xorg.conf',
            'etc/rc.conf.d/xdm': b'xdm_flags="-server /etc/xiri/xdm/Xservers -resources /etc/xiri/xdm/Xresources"\n',
        }
        # Keep the resettable machine-specific kernel selection sysinst already
        # uses. The 32-bit bootstrap loads netbsd.boot; /netbsd retains symbols.
        write_set(sets / ('kern-GENERIC32_IP2x' + suffix), resources, stamp)
        modpath = f'stand/sgimips/{version}/modules/compat_irix_o32/{module.name}'
        write_set(sets / ('modules' + suffix), {modpath: module,
                  'etc/modules.conf': b'compat_irix_o32\n'}, stamp)
        archives = sorted(sets.iterdir())
        for algorithm in ('sha512', 'md5'):
            label = algorithm.upper()
            (sets / label).write_text(''.join(
                f'{label} ({a.name}) = {digest(a, algorithm)}\n' for a in archives))
        shutil.copyfile(release / 'kernel/netbsd-INSTALL32_IP2x.gz', cd / 'ip2x')
        inventory = dict(sources=source_lock, kernel_release=version,
                         kernel_set_files=sorted(resources), module_set_files=[modpath, 'etc/modules.conf'],
                         sha256={str(p.relative_to(cd)): digest(p, 'sha256')
                                 for p in sorted(cd.rglob('*')) if p.is_file()})
        (cd / 'native-media.json').write_text(json.dumps(inventory, sort_keys=True, indent=2) + '\n')
        payload = temp / 'filesystem.iso'
        subprocess.run([tools / 'nbmakefs', '-t', 'cd9660', '-T', str(stamp), '-o',
                        'rockridge,label=XIRIBSD_INDY', payload, cd], check=True)
        image = temp / 'indy.iso'
        # Mirror NetBSD distrib/sgimips/cdroms/installcd. CD partition 8 holds
        # the bootstrap and partition 0 starts at the ISO9660 filesystem.
        with image.open('wb') as out, payload.open('rb') as inp:
            out.seek(SGI_HEADER_SECTORS * 512)
            shutil.copyfileobj(inp, out)
        sgivol = tools / 'nbsgivol'
        subprocess.run([sgivol, '-f', '-i', '-h', str(SGI_HEADER_SECTORS), image], check=True)
        for loader in ('aoutboot', 'ip2xboot'):
            original = dest / 'usr/mdec' / loader
            subprocess.run([sgivol, '-f', '-w', loader, original, image], check=True)
            readback = temp / loader
            subprocess.run([sgivol, '-r', loader, readback, image], check=True)
            if digest(readback, 'sha256') != digest(original, 'sha256'):
                raise ValueError(f'SGI bootstrap readback failed: {loader}')
        with image.open('rb') as out:
            out.seek(SGI_HEADER_SECTORS * 512)
            if hashlib.file_digest(out, 'sha256').hexdigest() != digest(payload, 'sha256'):
                raise ValueError('ISO data partition readback failed')
        os.link(image, output)
    print(f'{digest(output, "sha256")}  {output}', flush=True)
