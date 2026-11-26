#!/usr/bin/env python3
"""Boot the original stock Indy checkpoint, stage the X sets and verify a modular cold boot."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts'))
from xiri_lab import Guest, load_probe, sha256

STOCK = {'disk.raw': '8f896ab101a1cb27e29bfe87cc4048cc61c17f2a148f58d24bba0fb1d0c21926',
         'nvram.bin': '602d954b2e8f076887c54ed301dff7dbd9cc0c6be138e537e5bc732c948d344e'}
XSETS = ('xbase.tgz', 'xetc.tgz', 'xfont.tgz', 'xserver.tgz')


def media(work, sets, build, native):
    signed = {}
    for line in (ROOT/'lab/netbsd-11.0/SHA512SUMS').read_text().splitlines():
        digest, relative_path = line.split()
        signed[relative_path] = digest
    release = '11.99.9'
    if native:
        from xiri_lab.install_media import validate_native
        validate_native(native)
        manifest = json.loads((native/'manifest.json').read_text())
        profile = json.loads((ROOT/'profiles'/(manifest['profile']+'.json')).read_text())
        release = profile['target']['kernel_release']
        pins = {}
        with tarfile.open(native/'native.tar.gz') as archive:
            for key in ('kernel', 'boot', 'module'):
                row = profile['artifacts'][key]
                name = Path(row['destination']).name
                member = ('root' if key == 'module' else 'kernel') + row['destination']
                with archive.extractfile(member) as stream:
                    (work/name).write_bytes(stream.read())
                pins[name] = dict(path=name, sha256=row['sha256'])
        build = work
    else:
        pins = json.loads((ROOT/'lab/irix-mips4/module-build.json').read_text())['artifacts']
    files = {}
    for name in XSETS:
        path = sets/name
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha512').hexdigest()
        if digest != signed['sgimips/binary/sets/' + name]:
            raise ValueError('wrong release set: ' + name)
        files[name] = path
    for name, pin in pins.items():
        path = build/pin['path']
        if sha256(path) != pin['sha256']:
            raise ValueError('wrong native build artifact: ' + name)
        files[name] = path
    manifest = work/'SHA256'
    manifest.write_text(''.join(f'SHA256 ({k}) = {sha256(p)}\n' for k, p in files.items()))
    subprocess.run(['genisoimage', '-quiet', '-R', '-o', work/'bootstrap.iso', '-graft-points',
                    f'SHA256={manifest}', *(f'{k}={p}' for k, p in files.items())], check=True)
    return release, {k: v['sha256'] for k, v in pins.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base', 'sets', 'emulator', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--build', type=Path, help='original 11.99.9 build directory')
    source.add_argument('--native-package', type=Path, help='11.99.11 Indy native package')
    parser.add_argument('--keep-target', action='store_true', help='retain the clean stopped disk and PROM in the output')
    args = parser.parse_args()
    base, sets, emulator, out = (p.resolve() for p in
                                 (args.base, args.sets, args.emulator, args.output))
    out.mkdir(parents=True, exist_ok=False)
    probe = load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = emulator/'iris', emulator/'iris-ci'
    result = dict(stock=STOCK, xsets=XSETS, boots=[], iris_sha256=sha256(probe.IRIS))
    os.environ.pop('IRIS_CHD_DIFF_DIR', None)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        if any(sha256(base/n) != h for n, h in STOCK.items()):
            raise ValueError('original stock NetBSD checkpoint differs from its recorded hashes')
        with tempfile.TemporaryDirectory(dir=out) as scratch:
            work = Path(scratch)
            release, pins = media(work, sets, args.build, args.native_package)
            result['native_sha256'] = pins
            subprocess.run(['cp', '--reflink=auto', '--sparse=always', base/'disk.raw', work/'disk.raw'], check=True)
            firmware = base/'nvram.bin'
            for phase in ('stock', 'modular'):
                run = out/phase
                run.mkdir()
                shutil.copyfile(firmware, run/'nvram.bin')
                firmware = run/'nvram.bin'
                config = ('ci = true\nno_audio = true\nbanks = [128,128,0,0]\n'
                          'nat_subnet = "192.168.231.0/24"\n[machine]\nprofile = "indy_ip24"\n'
                          'cpu = "r4400"\n[graphics]\nboard = "newport"\n[scsi.1]\n'
                          f'path = {json.dumps(str(work/"disk.raw"))}\noverlay = false\n')
                if phase == 'stock':
                    config += f'[scsi.4]\ncdrom = true\npath = {json.dumps(str(work/"bootstrap.iso"))}\n'
                lab = probe.Lab(SimpleNamespace(mode='ci', debugger=False), run,
                                config_text=config, working_directory=work, scsi1_from_config=True)
                try:
                    lab.start(boot=False)
                    # The first boot with xfont builds the entire runtime font cache.
                    lab.wait(r'login: ', 900 if phase == 'modular' else 300)
                    lab.send('root')
                    lab.wait(r'xiri-indy# ', 40)
                    lab.logged_in = True
                    g = Guest(lab)
                    g.command('test ! -e /emul/irix && test ! -e /usr/people/xiritest')
                    result[phase + '_kernel'] = g.read_text('uname -v').strip()
                    if phase == 'stock':
                        g.command('test "$(uname -r)" = 11.0 && test ! -f /usr/X11R7/bin/Xorg')
                        g.command('mkdir -p /cdrom && mount -r -t cd9660 /dev/cd0a /cdrom')
                        g.command('cd /cdrom && sha256 -c SHA256', 240)
                        for name in XSETS:
                            g.command(f'cd / && pax -rzpe -f /cdrom/{name}', 420)
                        g.command('test ! -e /netbsd.stock && cp -p /netbsd /netbsd.stock && '
                                  'install -m 444 /cdrom/netbsd /netbsd && install -m 444 /cdrom/netbsd.boot /netbsd.boot')
                        g.command(f'm=/stand/sgimips/{release}/modules/compat_irix_o32; mkdir -p "$m" && '
                                  'install -m 444 /cdrom/compat_irix_o32.kmod "$m/compat_irix_o32.kmod"')
                        g.command('grep -qx compat_irix_o32 /etc/modules.conf 2>/dev/null || '
                                  'echo compat_irix_o32 >> /etc/modules.conf')
                        g.command('sync')
                    else:
                        g.command(f'test "$(uname -r)" = {release} && test -x /usr/X11R7/bin/Xorg && '
                                  'test -x /usr/X11R7/bin/xdm && test -f /netbsd.stock')
                        g.command('test "$(sha256 -q /netbsd)" = ' + pins['netbsd'])
                        g.command('test "$(sha256 -q /netbsd.boot)" = ' + pins['netbsd.boot'])
                        g.command('m=$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod; '
                                  'test "$(sha256 -q "$m")" = ' + pins['compat_irix_o32.kmod'])
                        result['module'] = g.read_text('modstat | grep "^compat_irix_o32 "').strip()
                        if result['module'].split()[:3] != ['compat_irix_o32', 'exec', 'filesys']:
                            raise RuntimeError('configured exec module did not load from the filesystem')
                        result['securelevel'] = int(g.read_text('sysctl -n kern.securelevel'))
                        if result['securelevel'] != 1:
                            raise RuntimeError('expected securelevel 1 after multiuser boot')
                    lab.send('shutdown -h now')
                    lab.wait('unmounting done', 120)
                    lab.wait(r'Option\?', 45)
                    lab.logged_in = False
                    lab.clean_shutdown = True
                    if phase == 'stock':
                        lab.send('5')
                        lab.wait(r'\n>>? ', 30)
                        lab.send('setenv OSLoadFilename netbsd.boot')
                        lab.wait(r'\n>>? ', 30)
                        lab.ci('rtc-save')
                finally:
                    lab.close()
                    result['boots'].append(dict(phase=phase, halted=lab.clean_shutdown,
                                                stopped=lab.process is None or lab.process.poll() is not None))
            if args.keep_target:
                (work/'disk.raw').rename(out/'disk.raw')
                shutil.copyfile(firmware, out/'nvram.bin')
    except BaseException as error:
        result['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        result['originals_unchanged'] = all(sha256(base/n) == h for n, h in STOCK.items())
        result['passed'] = ('error' not in result and result['originals_unchanged'] and len(result['boots']) == 2
                            and all(b['halted'] and b['stopped'] for b in result['boots']))
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    if not result['passed']:
        raise RuntimeError('incomplete clean bootstrap')


if __name__ == '__main__':
    main()
