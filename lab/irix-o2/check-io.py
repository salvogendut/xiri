#!/usr/bin/env python3
"""Verify O2 SCSI persistence and full-file MEC transfers on a private CHD overlay."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import random
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

from o2_console import halt_to_prom

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / 'lab/ip30-impact'))
from xiri_lab import Guest, load_probe, sha256
from xiri_lab.io_services import Services
import wsconsole

MIB = 1024 * 1024
ROUNDS = 3


def prepare_cd(work, size):
    share = work / 'share'
    share.mkdir()
    hashes = []
    for i in range(2):
        path = share / f'payload{i}.bin'
        gen = random.Random(20261123 + i)
        with path.open('wb') as stream:
            for _ in range(size):
                stream.write(gen.randbytes(MIB))
        hashes.append(sha256(path))
        path.with_suffix('.bin.sha256').write_text(hashes[-1] + '\n')
    shutil.copyfile(ROOT/'lab/indy-netbsd/disk-probe.sh', share/'disk-probe.sh')
    iso = work / 'payloads.iso'
    subprocess.run(['genisoimage', '-quiet', '-R', '-o', iso, share], check=True)
    return hashes


@contextmanager
def boot(probe, work, out, config, flash, result, *, cold, netbsd):
    out.mkdir()
    shutil.copyfile(flash, out/'nvram.bin')
    lab = probe.Lab(SimpleNamespace(mode='ci', debugger=False), out,
                    config_text=config, working_directory=work, scsi1_from_config=True)
    try:
        lab.start(boot=False)
        if cold:
            reference = wsconsole.console_frame.load_reference(netbsd/'xiri/graphics/sgiconsole.png')
            wsconsole.capture(lab, probe.CI, out/'cold-root.png', wsconsole.glyphs(netbsd),
                              ['/dev/rsd0a: file system is clean; not checking'],
                              timeout=180, reference=reference)
            result['cold_root_clean'] = True
        lab.wait(r'login: ', 300)
        lab.send('root')
        lab.wait(r'xiri-indy# ', 30)
        lab.logged_in = True
        guest = Guest(lab)
        guest.command('test "$(sysctl -n hw.model)" = SGI-IP32 && mount | grep "^/dev/sd0a on / type ffs"')
        yield guest
    finally:
        try:
            if lab.logged_in:
                halt_to_prom(lab)
        finally:
            lab.close()
            result['boots'].append(dict(phase=out.name, halted=lab.clean_shutdown,
                                        stopped=lab.process is None or lab.process.poll() is not None))


def ethernet(guest, work, hashes, size, result):
    result['mec_at_boot'] = guest.read_text('ifconfig mec0').strip()
    if 'inet 192.168.0.2/24 ' not in result['mec_at_boot']:
        raise RuntimeError('mec0 did not acquire the expected IRIS DHCP address at boot')
    result['mec_route'] = guest.read_text('route -n get 192.168.0.1').strip()
    if 'interface: mec0' not in result['mec_route']:
        raise RuntimeError('guest does not route the test traffic through mec0')
    result['default_route'] = guest.read_text('route -n get default').strip()
    if 'gateway: 192.168.0.1' not in result['default_route'] or 'interface: mec0' not in result['default_route']:
        raise RuntimeError('DHCP did not supply the IRIS default route')
    stats = 'netstat -inI mec0; netstat -ibnI mec0'
    result['network_before'] = guest.read_text(stats)
    services = Services(work)
    try:
        start = time.monotonic()
        guest.command(f'ftp -q 45 -o /root/xiri-disk-test/download.bin '
                      f'http://192.168.0.1:{services.http.server_port}/payload1.bin', 300)
        result['download_seconds'] = round(time.monotonic() - start, 2)
        result['download_sha256'] = guest.read_text('sha256 -q /root/xiri-disk-test/download.bin').strip()
        if result['download_sha256'] != hashes[1]:
            raise ValueError('download digest differs from the host source')
        # Upload the file retained across the cold boot, independently of the download.
        start = time.monotonic()
        guest.command(f'nc -N -w 45 192.168.0.1 {services.upload.server_address[1]} '
                      '< /root/xiri-disk-test/first.bin', 300)
        if not services.upload_done.wait(5) or services.upload_error:
            raise RuntimeError(f'TCP upload failed: {services.upload_error}')
        result['upload_seconds'] = round(time.monotonic() - start, 2)
        uploaded = work/'tcp-upload.bin'
        result['upload_sha256'] = sha256(uploaded)
        if uploaded.stat().st_size != size*MIB or result['upload_sha256'] != hashes[0]:
            raise ValueError('host received an incomplete or different file')
        result['bytes_each_direction'] = size*MIB
    finally:
        services.close()
    result['network_after'] = guest.read_text(stats)
    # NetBSD reports one link row and additional rows per address. Use the link row.
    def counters(dump):
        rows = re.findall(r'^mec0\s+\d+\s+<Link>\s+\S+\s+([0-9 ]+)$', dump, re.M)
        packets, octets = [list(map(int, row.split())) for row in rows]
        return dict(zip(('ipackets', 'ierrors', 'opackets', 'oerrors', 'collisions',
                         'ibytes', 'obytes'), packets + octets, strict=True))

    first = counters(result['network_before'])
    last = counters(result['network_after'])
    delta = result['mec_delta'] = {name: last[name] - value for name, value in first.items()}
    if min(delta['ibytes'], delta['obytes']) < size*MIB or delta['ierrors'] or delta['oerrors']:
        raise ValueError(f'unexpected mec0 transfer counters: {delta}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'emulator', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--netbsd', type=Path, default=ROOT.parent/'NetBSD-xiri')
    parser.add_argument('--size-mib', type=int, default=32)
    args = parser.parse_args()
    if not 1 <= args.size_mib <= 128:
        parser.error('--size-mib must be 1–128')
    bundle, emulator, out = (p.resolve() for p in (args.bundle, args.emulator, args.output))
    out.mkdir(parents=True, exist_ok=False)
    probe = load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = emulator/'iris', emulator/'iris-ci'
    disk, flash = bundle/'netbsd-xiri.chd', bundle/'nvram.bin'
    baseline = json.loads((bundle/'qualification.json').read_text())
    inputs = {p: sha256(p) for p in (disk, flash, bundle/'iris.toml', probe.IRIS, probe.CI)}
    if (inputs[disk], inputs[flash]) != (baseline['chd_sha256'], baseline['firmware_sha256']):
        raise ValueError('base CHD or PROM differs from the qualified O2 bundle')
    result = dict(release=baseline['release'], inputs={p.name: v for p, v in inputs.items()},
                  size_mib=args.size_mib, rounds=ROUNDS, boots=[])
    os.environ.pop('IRIS_CHD_DIFF_DIR', None)
    signal.signal(signal.SIGTERM, signal.default_int_handler)
    try:
        with tempfile.TemporaryDirectory(dir=out) as name:
            work = Path(name)
            subprocess.run(['cp', '--reflink=auto', disk, work/disk.name], check=True)
            hashes = result['payload_sha256'] = prepare_cd(work, args.size_mib)
            config = (bundle/'iris.toml').read_text().replace('ci = false', 'ci = true')
            cd = f'\n[scsi.4]\ncdrom = true\npath = {json.dumps(str(work/"payloads.iso"))}\n'
            with boot(probe, work, out/'write', config+cd, flash, result, cold=False, netbsd=args.netbsd) as guest:
                result['mec_before_setup'] = guest.read_text('ifconfig mec0').strip()
                # Enable the O2 port on the private image; its Octane-derived base disables dhcpcd.
                guest.command("printf '%s\\n' dhcpcd=YES 'dhcpcd_flags=\"-q -4 mec0\"' > /etc/rc.conf.d/dhcpcd")
                guest.command('mount -t cd9660 -o ro /dev/cd0a /cdrom')
                start = time.monotonic()
                guest.command(f'sh /cdrom/disk-probe.sh write {ROUNDS}', 900)
                result['write_and_verify_seconds'] = round(time.monotonic()-start, 2)
                result['bytes_written'] = ROUNDS * 2 * args.size_mib * MIB
            # Disconnect the source CD for the independent cold read.
            with boot(probe, work, out/'cold', config, out/'write/nvram.bin', result,
                      cold=True, netbsd=args.netbsd) as guest:
                cold = guest.read_text('cd /root/xiri-disk-test && sha256 -q first.bin second.bin', 180)
                result['cold_sha256'] = cold.splitlines()
                if result['cold_sha256'] != hashes:
                    raise ValueError('cold disk hashes differ from the host sources')
                ethernet(guest, work, hashes, args.size_mib, result)
    except BaseException as error:
        result['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        result['inputs_unchanged'] = all(sha256(p) == digest for p, digest in inputs.items())
        result['passed'] = ('error' not in result and result['inputs_unchanged']
                            and len(result['boots']) == 2 and all(b['halted'] and b['stopped'] for b in result['boots']))
        (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    if not result['passed']:
        raise RuntimeError('O2 qualification incomplete')


if __name__ == '__main__':
    main()
