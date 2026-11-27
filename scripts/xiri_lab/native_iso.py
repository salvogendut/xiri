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

XIRIPREP_PROGRAMS = (
    'usr/local/sbin/xiriprep', 'usr/local/libexec/xiri/xiri-donor-read',
    'usr/local/libexec/xiri/install-shared.sh', 'usr/local/libexec/xiri/setup-xiri-user.sh',
    'usr/local/libexec/xiri/select-desktop.sh', 'usr/local/libexec/xiri/install-audio.sh',
)
XIRIPREP_FILES = (*XIRIPREP_PROGRAMS, 'usr/local/share/xiri/donor-signatures',
                  'usr/local/share/xiri/plans/6.5.22f.plan', 'usr/local/share/xiri/plans/6.5.30f.plan',
                  'usr/local/share/xiri/plans/6.5.22f-ip28.plan', 'usr/local/share/xiri/plans/6.5.30f-ip30.plan',
                  'usr/local/share/xiri/plans/6.5.22m.plan',
                  'usr/local/share/xiri/plans/6.5.22f.audio', 'usr/local/share/xiri/plans/6.5.30f.audio',
                  'usr/local/share/xiri/desktop-runtime.tgz', 'usr/local/share/xiri/xiriprep-source.tgz')


def digest(path, algorithm):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def write_set(path, files, timestamp, *, executables=()):
    with path.open('wb') as raw:
        compressed = (gzip.GzipFile(fileobj=raw, filename='', mode='wb', mtime=timestamp)
                      if path.name.endswith('.tgz') else lzma.LZMAFile(raw, 'wb'))
        with compressed, tarfile.open(fileobj=compressed, mode='w|',
                                      format=tarfile.USTAR_FORMAT) as archive:
            for name, source in sorted(files.items()):
                data = source if isinstance(source, bytes) else source.read_bytes()
                entry = tarfile.TarInfo('./' + name)
                entry.size, entry.mtime = len(data), timestamp
                entry.mode = 0o555 if name in executables else 0o444
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
        for name in XIRIPREP_FILES:
            resources[name] = work / 'xiriprep-stage' / name
        write_set(sets / ('kern-GENERIC32_IP2x' + suffix), resources, stamp, executables=XIRIPREP_PROGRAMS)
        modpath = f'stand/sgimips/{version}/modules/compat_irix_o32/{module.name}'
        write_set(sets / ('modules' + suffix), {modpath: module,
                  'etc/modules.conf': b'compat_irix_o32\n'}, stamp)
        archives = sorted(sets.iterdir())
        for algorithm in ('sha512', 'md5'):
            label = algorithm.upper()
            (sets / label).write_text(''.join(
                f'{label} ({a.name}) = {digest(a, algorithm)}\n' for a in archives))
        shutil.copyfile(release / 'kernel/netbsd-INSTALL32_IP2x.gz', cd / 'ip2x')
        loaders = ('ip2xboot', 'aoutboot')
        for loader in loaders:
            shutil.copyfile(dest / 'usr/mdec' / loader, cd / loader)
        inventory = dict(sources=source_lock, kernel_release=version,
                         kernel_set_files=sorted(resources), module_set_files=[modpath, 'etc/modules.conf'],
                         sha256={str(p.relative_to(cd)): digest(p, 'sha256')
                                 for p in sorted(cd.rglob('*')) if p.is_file()})
        (cd / 'native-media.json').write_text(json.dumps(inventory, sort_keys=True, indent=2) + '\n')
        # Put the volume directory in the ISO system area. A prepended volume
        # header boots in the PROM but hides sector 16 from NetBSD's cd driver.
        image = temp / 'indy.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-V', 'XIRIBSD_INDY', '-mips-boot',
                        'ip2xboot', '-mips-boot', 'aoutboot', '-o', image, cd], check=True)
        sgivol = tools / 'nbsgivol'
        sectors = image.stat().st_size // 512
        subprocess.run([sgivol, '-f', '-p', '0', '0', str(sectors), '4', image], check=True)
        for loader in loaders:
            readback = temp / loader
            subprocess.run([sgivol, '-r', loader, readback, image], check=True)
            # The SGI volume entry may include padding to an optical block.
            original = (cd / loader).read_bytes()
            data = readback.read_bytes()
            if not data.startswith(original) or len(data) - len(original) >= 2048 or any(data[len(original):]):
                raise ValueError(f'SGI bootstrap readback failed: {loader}')
        expected = {p.relative_to(cd).as_posix() for p in cd.rglob('*')}
        listing = subprocess.check_output(['isoinfo', '-R', '-i', image, '-f'], text=True)
        if {p.removeprefix('/') for p in listing.splitlines()} != expected:
            raise ValueError('ISO directory differs from the native inventory')
        for p in sorted(cd.rglob('*')):
            if not p.is_file():
                continue
            member = '/' + p.relative_to(cd).as_posix()
            with subprocess.Popen(['isoinfo', '-R', '-i', image, '-x', member],
                                  stdout=subprocess.PIPE) as reader:
                actual = hashlib.file_digest(reader.stdout, 'sha256').hexdigest()
                if reader.wait() or actual != digest(p, 'sha256'):
                    raise ValueError(f'ISO readback failed: {member}')
        os.link(image, output)
    print(f'{digest(output, "sha256")}  {output}', flush=True)
