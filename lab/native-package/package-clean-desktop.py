#!/usr/bin/env python3
"""Package one clean, halted install for a graphical cold-boot test."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import sha256


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('installation', 'emulator', 'output'):
        ap.add_argument('--' + name, required=True, type=Path)
    args = ap.parse_args()
    src, emu, out = (p.resolve() for p in (args.installation, args.emulator, args.output))
    report = json.loads((src / 'install/result.json').read_text())
    invocation = json.loads((src / 'install/emulator-command.json').read_text())
    tested = Path(invocation[invocation.index('--config') - 1])
    if (
        'error' in report
        or not report['stopped']
        or not report['halted']
        or not report['checks']['repeated']
        or sha256(tested) != sha256(emu / 'iris')
    ):
        raise ValueError('expected a successful clean installation and its emulator')
    release = report['release']
    port = {'6.5.22f': 20782, '6.5.30f': 20792}[release]
    component = report['checks'].get('mozilla')
    if component:
        port = {'6.5.22f': 21182, '6.5.30f': 21192}[release]
    out.mkdir(parents=True, exist_ok=False)
    chd = out / 'netbsd-xiri.chd'
    tool = ['chdman'] if shutil.which('chdman') else ['toolbox', 'run', '-c', 'xiri-iris', 'chdman']
    with (out / 'chd.log').open('wb') as log:
        for command in (
            ['createhd', '-i', src / 'disk.raw', '-o', chd, '-c', 'zlib', '-np', '2'],
            ['verify', '-i', chd],
        ):
            subprocess.run(tool + command, stdout=log, stderr=subprocess.STDOUT, check=True)
    info = subprocess.check_output(tool + ['info', '-i', chd], text=True)
    with (src / 'disk.raw').open('rb') as stream:
        raw_hash = hashlib.file_digest(stream, 'sha1').hexdigest()
    if not re.search(r'^Data SHA1:\s*' + raw_hash + '$', info, re.M):
        raise ValueError('CHD data digest differs from the halted source disk')
    shutil.copyfile(src / 'nvram.bin', out / 'nvram.bin')
    shutil.copy2(emu / 'iris', out / 'iris')
    config = (src / 'install/iris.toml').read_text().split('[scsi.1]')[0].replace('ci = true', 'ci = false')
    # The installer suppresses audio. On Indy that also removes HAL2 from the guest.
    config = config.replace('no_audio = true', 'no_audio = false')
    (out / 'iris.toml').write_text(
        f'nvram = "nvram.bin"\nmonitor_port = {port}\nserial_port_a = {port+1}\n'
        f'serial_port_b = {port+2}\nheadless = false\n'
        + config
        + '[scsi.1]\noverlay = true\npath = "netbsd-xiri.chd"\n'
    )
    launcher = out / 'run-iris.sh'
    launcher.write_text(
        '#!/bin/sh\nset -eu\ncd "$(dirname "$0")"\nunset IRIS_CHD_DIFF_DIR\n'
        'export IRIS_NO_IDLE=1\nexec ./iris --config iris.toml "$@"\n'
    )
    launcher.chmod(0o755)
    (out / 'manifest.json').write_text(
        json.dumps(
            dict(
                release=release,
                receipt=report['checks']['receipts'],
                **({'mozilla_receipt': component} if component else {}),
                iso_sha256=report['iso_sha256'],
                raw_sha1=raw_hash,
                chd_sha256=sha256(chd),
                nvram_sha256=sha256(out / 'nvram.bin'),
                iris_sha256=sha256(out / 'iris'),
                install_result_sha256=sha256(src / 'install/result.json'),
            ),
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
