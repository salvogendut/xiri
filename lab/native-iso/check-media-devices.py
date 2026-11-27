#!/usr/bin/env python3
"""Check native devices and launch their original IRIX clients on an isolated Indy."""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory

spec = importlib.util.spec_from_file_location('desktop', Path(__file__).with_name('check-desktop.py'))
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)
APPS = ('soundeditor', 'videoin', 'videopanel', 'mediarecorder', 'cdman', 'cdplayer', 'datman', 'datplayer')


def run(args):
    bundle = args.bundle.resolve()
    record = json.loads((bundle / 'qualification.json').read_text())
    if desktop.sha256(bundle / 'netbsd-xiri.chd') != record['chd_sha256']:
        raise ValueError('Unexpected base disk')
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=False)
    probe = desktop.load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = (args.emulator.resolve() / name for name in ('iris', 'iris-ci'))
    result = dict(release=record['release'], cpu=record['cpu'], chd_sha256=record['chd_sha256'],
                  emulator_sha256=desktop.sha256(probe.IRIS), apps={})
    with TemporaryDirectory(dir=out) as tmp:
        work = Path(tmp)
        os.environ.update(IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(work / 'profile'))
        data = work / 'sample.txt'
        data.write_text('Xiri Indy CD-ROM media check\n')
        runner = work / 'media-check.sh'
        runner.write_text("""#!/bin/sh
umask 077
ulimit -c 0
dir="$HOME/.media-check/$1"
mkdir -p "$dir" || exit 1
# Some SGI launchers fork and exit. Keep their descendants alive while
# observing X, and let the guard clean up after the observation interval.
/usr/local/libexec/xiri/session-guard 18000 /bin/sh -c '
    "$1"
    echo "launcher_status=$?"
    sleep 14
' media-check "/emul/irix/usr/sbin/$1" >"$dir/log" 2>&1
echo $? >"$dir/status"
""")
        cd = work / 'data.iso'
        subprocess.run(['genisoimage', '-quiet', '-R', '-o', cd, data, runner], check=True)
        disk = work / 'system.chd'
        subprocess.run(['cp', '--reflink=auto', bundle / 'netbsd-xiri.chd', disk], check=True)
        lab = desktop.native.open_lab(probe, work / 'lab', record['cpu'], disk, bundle / 'nvram.bin', cd)
        lab.config_text = lab.config_text.replace('overlay = false', 'overlay = true')
        lab.config_text = lab.config_text.replace('no_audio = true', 'no_audio = false')
        lab.config_text += '[audio]\nhost = "null"\n[vino]\nsource = "test_pattern"\n'
        try:
            guest = desktop.cold_root(lab)
            guest.command('usermod -G operator xiritest && /usr/local/sbin/xiri-sync-users')
            q = desktop.saver.desktop
            desktop.saver.login_catalog(guest, q.greeter, q.login)
            guest.command('mkdir -p /cdrom && mount -rt cd9660 /dev/cd0a /cdrom && '
                          f"""test "$(su -f xiritest -c 'sha256 -q /cdrom/sample.txt')" = {desktop.sha256(data)} && """
                          'install -m 555 /cdrom/media-check.sh /tmp/media-check && umount /cdrom')
            result['cd9660_data_read'] = True
            guest.command("dmesg | grep -q 'haltwo0 at hpc0'")
            result['native'] = guest.read_text(
                "audiocfg list 2>&1; su -f xiritest -c 'id; audiorecord -t 1 /tmp/check.wav 2>&1; "
                "echo audiorecord_rc=$?; /usr/bin/cdplay -f /dev/rcd0c info 2>&1; echo cdplay_rc=$?; "
                "mt -f /dev/nrst0 status 2>&1; echo mt_rc=$?'; "
                "cdplay -f /dev/rcd0c info 2>&1; echo root_cdplay_rc=$?; "
                "dmesg | grep -Ei 'haltwo|vino|video[0-9]|cd0 at|st[0-9] at'").strip()
            for app in APPS:
                print(record['release'], app, flush=True)
                target = '/emul/irix/usr/sbin/' + app
                guest.command(f'test -x {target}')
                report = f'/usr/people/xiritest/.media-check/{app}'
                x, y = desktop.saver.position(guest, '"winterm"')
                guest.monitor(f'ptr click {x + 40} {y + 40} left')
                guest.command('xwininfo -root -tree >/tmp/before')
                guest.monitor('key type /tmp/media-check ' + app)
                guest.monitor('key Return')
                guest.wait_for(f'test -f {report}/log', 45)
                guest.command('sleep 5; xwininfo -root -tree >/tmp/during', 45)
                guest.wait_for(f'test -s {report}/status', 60)
                log = guest.read_text(f'cat {report}/log').strip()
                if not re.search(r'absent=1 valid=1 .*remaining=0', log):
                    raise ValueError(f'{app}: incomplete process cleanup: {log}')
                windows = guest.read_text("""awk 'NR==FNR {seen[$1]=1; next} !($1 in seen) && /"/ {print}' """
                                          "/tmp/before /tmp/during").strip()
                result['apps'][app] = dict(log=log, windows=windows)
            desktop.poweroff(lab)
        finally:
            lab.close()
    (out / 'result.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('bundle', 'emulator', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    run(parser.parse_args())
