#!/usr/bin/env python3
"""Apply, cold-boot or roll back a v6 platform update on a private disk copy."""

import argparse
import socket
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
from xiri_lab import Guest, load_probe, sha256

parser = argparse.ArgumentParser(description=__doc__)
for name in ('bundle', 'disk', 'emulator', 'media', 'probes', 'output'):
    parser.add_argument('--' + name, required=True, type=Path)
parser.add_argument('phase', choices=('update', 'rollback', 'restored', 'desktop'))
args = parser.parse_args()
out = args.output.resolve()
out.mkdir(parents=True)
disk = out / 'netbsd-xiri.chd'
if disk.exists() or (out / 'netbsd-xiri.chd.diff.chd').exists():
    raise RuntimeError('use a new output directory')
subprocess.run(['cp', '--reflink=auto', args.disk, disk], check=True)
for name in ('nvram.bin', 'flash.bin', 'nveeprom.bin'):
    if (args.bundle / name).exists():
        shutil.copyfile(args.bundle / name, out / name)
config = (args.bundle / 'iris.toml').read_text().replace('ci = false', 'ci = true')
model = 'o2' if 'o2_ip32' in config else 'ip30' if 'octane_ip30' in config else 'ip28'
config += f'\n[scsi.4]\ncdrom = true\npath = {json.dumps(str(args.media.resolve()))}\n'
config += f'[scsi.5]\ncdrom = true\npath = {json.dumps(str(args.probes.resolve()))}\n'
if model == 'ip30':
    config = config.replace('[scsi.4]', '[scsi.2]').replace('[scsi.5]', '[scsi.3]')
probe = load_probe()
probe.TOOLBOX = []
probe.IRIS, probe.CI = (args.emulator.resolve() / name for name in ('iris', 'iris-ci'))
lab = probe.Lab(
    SimpleNamespace(mode='ci', debugger=False),
    out,
    config_text=config,
    working_directory=out,
    scsi1_from_config=True,
)
guest = Guest(lab)
record = dict(phase=args.phase, model=model, disk_sha256=sha256(disk), media_sha256=sha256(args.media))
os.environ['IRIS_NO_IDLE'] = '1'
os.environ.pop('IRIS_CHD_DIFF_DIR', None)
signal.signal(signal.SIGTERM, signal.default_int_handler)


def login(user):
    time.sleep(3)
    for _ in range(2):
        if model == 'o2':
            for key in ['Key' + c.upper() for c in user] + ['Enter']:
                for event in ('keydown', 'keyup'):
                    guest.monitor('o2 ' + event + ' ' + key)
                time.sleep(0.16)
        else:
            for char in user:
                guest.monitor('key type ' + char)
                time.sleep(0.075)
            guest.monitor('key Return')
        time.sleep(1)


def greeter():
    guest.command("export DISPLAY=:0 PATH=/bin:/usr/bin:/sbin:/usr/sbin:/usr/X11R7/bin:/usr/local/bin")
    cmd = """$(ps -axww -o args= | awk '$1 ~ /^\\/usr\\/X11R7\\/bin\\/X(org)?$/ && $2==":0" {for(i=1;i<NF;i++) if($i=="-auth") print $(i+1)}')"""
    guest.wait_for(
        'test -s "'
        + cmd
        + '" && XAUTHORITY='
        + cmd
        + " xwininfo -root -tree 2>/dev/null | grep -q '\"xlogin\"'",
        180,
    )
    guest.command('export XAUTHORITY=' + cmd)
    guest.wait_for("""xwininfo -root -tree | grep -q '"xlogin"'""", 180)


def sessions():
    for user, wm in [('xiritest', '4Dwm'), ('netbsdtest', 'ctwm')]:
        greeter()
        login(user)
        guest.wait_for(
            rf"ps -axww -o uid,comm | awk -v u=$(id -u {user}) '$1==u && $2 ~ /(^|\/){wm}$/ {{ok=1}} END {{exit !ok}}'",
            180,
        )
        auth = '/usr/people/xiritest/.Xauthority' if user == 'xiritest' else '/home/netbsdtest/.Xauthority'
        if user == 'xiritest':
            guest.command(
                """job=$(sed -n 's/.*Logs: //p' /usr/people/xiritest/.xsession-errors | tail -1); XAUTHORITY=$(sed -n 's/.* authority=//p' "$job/identity"); test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority; export XAUTHORITY DISPLAY=127.0.0.1:0"""
            )
        else:
            guest.command('export XAUTHORITY=' + auth)
        win = 'Icon Catalog:' if user == 'xiritest' else 'UXTerm'
        guest.wait_for("xwininfo -root -tree | grep -q '" + win + "'", 180)
        guest.command('xdpyinfo | grep dimensions: | grep -q 1280x1024')
        lab.ci('screenshot', str(out / (user + '.png')))
        record[user] = dict(wm=wm, visible=win, dimensions='1280x1024')
        if user == 'xiritest':
            guest.command(
                "job=$(sed -n 's/.*Logs: //p' /usr/people/xiritest/.xsession-errors | tail -1); su -m xiritest -c \"env XIRI_SESSION_DIR='$job' /usr/local/bin/xiri-logout\""
            )
        else:
            guest.command('pkill -u netbsdtest -x /usr/X11R7/bin/ctwm')
        greeter()


def halt():
    if model == 'o2':
        sys.path.insert(0, str(ROOT / 'lab/irix-o2'))
        from o2_console import halt_to_prom

        halt_to_prom(lab)
        return
    lab.send('shutdown -h now')
    lab.wait('Done running shutdown hooks', 180)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        m = re.search(r'PC: 0x([\da-fA-F]+)', guest.monitor('regs'))
        if m and 0x1FC00000 <= int(m[1], 16) & 0x1FFFFFFF < 0x1FC80000:
            break
        time.sleep(1)
    else:
        raise RuntimeError('guest failed to reach PROM')
    lab.logged_in = False
    lab.clean_shutdown = True


try:
    lab.start(boot=False)
    if model == 'ip28':
        transcript = out / 'admin-serial.log'

        def serial_request(command, **arguments):
            with socket.socket(socket.AF_UNIX) as channel:
                channel.settimeout(10)
                channel.connect(str(lab.socket_path))
                message = json.dumps(dict(cmd=command, args=arguments)) + '\n'
                channel.sendall(message.encode())
                reply = json.loads(channel.makefile('rb').readline())
                if not reply.get('ok'):
                    raise RuntimeError(reply)
                return reply.get('data', '')

        def serial_text():
            chunk = serial_request('serial-read')
            if chunk:
                with transcript.open('a') as stream:
                    stream.write(chunk.replace('\r', ''))
            return transcript.read_text() if transcript.exists() else ''

        lab.serial_text = serial_text

        def send_ip28(text, newline=True):
            # Pace serial input while xdm is restarting to avoid overrunning the SCC.
            for start in range(0, len(text), 12):
                serial_request('serial-send', data=text[start : start + 12])
                time.sleep(0.06)
            if newline:
                serial_request('serial-send', data='\r')

        lab.send = send_ip28
    if model == 'ip30':
        sys.path.insert(0, str(ROOT / 'lab/ip30-impact'))
        from xdm_login import qualify

        def check_from_desktop(key):
            # The authenticated graphics terminal is reliable on IOC3. The
            # serial console records stdout and the shell's exit status.
            key('mount -rt cd9660 /dev/cd1a /mnt')
            key(f'(sh /mnt/check.sh {args.phase}; echo XIRI_PLATFORM_RC=$?) >/dev/ttyC0 2>&1')
            rc = lab.wait(r'\nXIRI_PLATFORM_RC=(\d+)\n', 400)[1]
            if rc != '0':
                raise ValueError(lab.serial_text()[-2500:])

        result = qualify(lab, out, before_shutdown=check_from_desktop)
        for entry in result['sessions']:
            record[entry['user']] = entry
        record['kernel'] = re.search(r'NetBSD 11\.99\.\d+ \(XIRI_IP30_DESKTOP\)[^\n]*', lab.serial_text())[0]
        lab.wait('unmounting done', 180)
        lab.wait(r'Option\?', 120)
        lab.clean_shutdown = True
    else:
        lab.wait('login: ', 450)
        lab.send('root')
        lab.wait('xiri-indy# ', 40)
        lab.logged_in = True
        greeter()
        guest.command(
            'mkdir -p /cdrom /mnt/probes && mount -rt cd9660 /dev/cd0a /cdrom && mount -rt cd9660 /dev/cd1a /mnt/probes'
        )
        record['kernel'] = guest.read_text('sysctl -n kern.version').strip()
        new = args.phase in ('desktop', 'rollback')
        guest.command(
            'test "$(sysctl -n kern.osrelease)" = '
            + ('11.99.11' if new else '11.99.9')
            + ' && modstat | grep "^compat_irix_o32 "'
        )
        guest.command(
            't=$(su - xiritest -c "mktemp") && su - xiritest -c "/mnt/probes/n32-direct e $t" && '
            + ('test "$(stat -f %m "$t")" = 1234567890' if new else 'test "$(stat -f %m "$t")" != 1234567890')
            + ' && rm "$t"'
        )
        if new or args.phase == 'restored':
            sessions()
        if args.phase in ('update', 'rollback'):
            flag = ' --rollback' if args.phase == 'rollback' else ''
            for _ in range(2):
                guest.command('sh /cdrom/upgrade.sh' + flag, 300)
        guest.command('sync; cd /; umount /mnt/probes && umount /cdrom')
        halt()
    transcript = lab.serial_text()
    probes = re.findall(r'(?m)^([0-9a-f]{8}(?: [0-9a-f]{8}){7})[ \t]*$', transcript)
    if len(probes) != 1:
        raise ValueError('Expected one complete n32 utime observation')
    words = [int(word, 16) for word in probes[0].split()]
    current = args.phase in ('desktop', 'rollback')
    if words[0] != (0 if current else 89) or (current and words[4] != 1234567890):
        raise ValueError('Unexpected timestamp observation: ' + probes[0])
    record['utime_probe'] = probes[0]
    if args.phase in ('update', 'rollback'):
        count = transcript.count(f'Platform {args.phase} complete.')
        if count != 2:
            raise ValueError(f'Expected two completed {args.phase} operations, got {count}')
        record['completed_operations'] = count
except BaseException as error:
    record['error'] = str(error)
    raise
finally:
    try:
        lab.close()
    finally:
        record.update(
            halted=lab.clean_shutdown, stopped=lab.process is None or lab.process.poll() is not None
        )
        (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')
