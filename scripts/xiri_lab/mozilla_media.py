"""Build the optional browser component for a release-matched clean Indy CD."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile

from . import ROOT, sha256
from .native_package import archive_tree

BROWSER = '/emul/irix/var/netscape/mozilla'
PRIVATE = '/emul/irix/usr/lib32/internal/mozilla'
LAUNCHER = '/emul/irix/usr/bin/X11/mozilla'
MODULE = '/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod'
NETWORK = {
    'compat_irix_o32.kmod': (MODULE, '8be760a6e36bb163c83d5038654841b86572bc49645ebdcfbd997f9377dcb7fc', 0o444),
    'mount_xiri_hosts': ('/usr/local/libexec/xiri/mount_xiri_hosts', '641d725861b180b9894979481fafeb0184273a426ed98a22a369a3414637ceef', 0o555),
    'xiri_hosts': ('/etc/rc.d/xiri_hosts', '82c77d51e49db104f9eb9ab1ff5d862ba14006257949d970caa50ea19aab148e', 0o555),
}


def browser_archive(directory, base):
    release = base['release']
    manifest = json.loads((directory / 'manifest.json').read_text())
    profile = ROOT / 'profiles' / f'irix-{release}-mozilla-v1.json'
    records = json.loads((ROOT / 'docs/results/2026-11-25-mozilla-sigpoll.json').read_text())
    pins = records['releases'][release]['image']
    archive = directory / 'payload.tar.gz'
    if (manifest['release'] != release or manifest['profile'] != profile.stem
            or manifest['profile_sha256'] != sha256(profile) or manifest['donor'] != base['donor']
            or manifest['payload_sha256'] != pins['browser_payload_sha256']
            or sha256(archive) != pins['browser_payload_sha256']):
        raise ValueError('Expected the qualified Mozilla import for ' + release)
    return archive, pins


def add_mozilla(args, base, native, work, inputs):
    from .install_media import UTIME
    native_owns_kernel = native['profile'] == UTIME
    archive, pins = browser_archive(args.mozilla_payload, base)
    package = work / 'mozilla'
    tree = package / 'root'
    tree.mkdir(parents=True)
    groups = {}
    with tarfile.open(archive) as donor:
        for item in donor:
            if item.isdir():
                continue
            dest = '/' + item.name
            if dest == LAUNCHER:
                if not item.issym() or item.linkname != '../../../var/netscape/mozilla/mozilla':
                    raise ValueError('Unexpected vendor Mozilla launcher')
                groups[dest] = base['files'][dest]['sha256']
            elif dest in base['files']:
                continue  # The verified base owns its shared libraries and shell.
            elif dest.startswith(BROWSER + '/'):
                groups[BROWSER + '/' + dest[len(BROWSER) + 1:].split('/')[0]] = 'add'
            elif dest.startswith(PRIVATE + '/'):
                groups[PRIVATE] = 'add'
            elif dest in ('/emul/irix/usr/lib32/libsocket.so', '/emul/irix/usr/lib32/libz.so'):
                groups[dest] = 'add'
            else:
                raise ValueError('Unexpected Mozilla destination: ' + dest)
            donor.extract(item, tree, filter='data')
            if item.isreg():
                (tree / item.name).chmod(item.mode)

    # The setup script checks for the vendor binary, then seeds only new profiles.
    subprocess.run(['sh', ROOT / 'packaging/mozilla/install-mozilla-defaults.sh'],
                   env=dict(os.environ, DESTDIR=str(tree)), check=True)
    groups[BROWSER + '/xiri-welcome.html'] = 'add'
    for name, (dest, digest, mode) in NETWORK.items():
        if native_owns_kernel and dest == MODULE:
            continue
        path = tree / dest.lstrip('/')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as output:
            subprocess.run(['isoinfo', '-R', '-i', args.mozilla_network, '-x', '/' + name],
                           stdout=output, check=True)
        if sha256(path) != digest:
            raise ValueError('Unexpected Mozilla network artifact: ' + name)
        path.chmod(mode)
        if dest != MODULE:
            groups[dest] = 'add'
    conf = '/etc/rc.conf.d/xiri_hosts'
    (tree / conf[1:]).parent.mkdir(parents=True, exist_ok=True)
    (tree / conf[1:]).write_text('xiri_hosts=YES\n')
    (tree / conf[1:]).chmod(0o644)
    groups[conf] = 'config'

    # Install the bootable wrapper last after preparing both kernel generations.
    boot = {}
    if not native_owns_kernel:
        with tarfile.open(args.mozilla_kernel) as source:
            for member, key in [('netbsd', 'kernel'), ('netbsd.boot', 'boot')]:
                path = tree / member
                with source.extractfile(member) as reader, path.open('xb') as output:
                    shutil.copyfileobj(reader, output)
                if sha256(path) != pins[key + '_sha256']:
                    raise ValueError('Unexpected Mozilla kernel artifact: ' + member)
                path.chmod(0o444)
                boot['/' + member] = native['artifacts'][key]['sha256']
        groups[MODULE] = native['artifacts']['module']['sha256']
        groups.update(boot)
    plan = package / 'groups'
    plan.write_text(''.join(f'{policy}|{dest}\n' for dest, policy in groups.items()))
    plan.chmod(0o644)
    kib = sum((p.lstat().st_size + 1023) // 1024 + 8 for p in tree.rglob('*'))
    (work / 'mozilla-space').write_text(str(kib) + '\n')
    archive_tree(package, work / 'mozilla.tgz')
    inputs.update({'mozilla.tgz': work / 'mozilla.tgz', 'mozilla-space': work / 'mozilla-space',
                   'mozilla.sh': ROOT / 'packaging/mozilla/component.sh'})
