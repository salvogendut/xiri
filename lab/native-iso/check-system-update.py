#!/usr/bin/env python3
"""Exercise an offline Indy kernel/module/runtime update on private xiriprep disks."""
import argparse
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import time

spec = importlib.util.spec_from_file_location('desktop', Path(__file__).with_name('check-desktop.py'))
desktop = importlib.util.module_from_spec(spec)
spec.loader.exec_module(desktop)
MODULE = '/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod'


def run(args):
    bundle = args.bundle.resolve()
    work = args.output.resolve()
    work.mkdir(parents=True, exist_ok=False)
    record = json.loads((bundle / 'qualification.json').read_text())
    cpu = record['cpu']
    release = record['release']
    password = next(line.rsplit(' / ', 1)[1] for line in (bundle / 'local-logins.txt').read_text().splitlines()
                    if line.startswith('NetBSD ctwm: native / '))
    probe = desktop.load_probe()
    probe.TOOLBOX = []
    probe.IRIS, probe.CI = (args.emulator.resolve() / name for name in ('iris', 'iris-ci'))
    os.environ.update(IRIS_NO_IDLE='1', IRIS_REX_JIT_PROFILE=str(work / 'profile'))
    disk = work / 'system.chd'
    rescue = work / 'maintenance.chd'
    if desktop.sha256(bundle / 'netbsd-xiri.chd') != record['chd_sha256']:
        raise ValueError('Unexpected base CHD')
    for path in (disk, rescue):
        subprocess.run(['cp', '--reflink=auto', bundle / 'netbsd-xiri.chd', path], check=True)
    result = dict(release=release, cpu=cpu, chd_sha256=record['chd_sha256'], update_sha256=desktop.sha256(args.media))
    color = '#7d9ec0' if cpu == 'r4400' else '#9ddb9d'

    @contextmanager
    def boot(name, maintenance=False):
        print(release, name, flush=True)
        lab = desktop.native.open_lab(probe, work / name, cpu, rescue if maintenance else disk,
                                      bundle / 'nvram.bin', args.media.resolve())
        lab.config_text = lab.config_text.replace('overlay = false', 'overlay = true')
        if maintenance:
            lab.config_text += f'[scsi.2]\noverlay = true\npath = {json.dumps(str(disk))}\n'
        try:
            g = desktop.cold_root(lab)
            g.command('mkdir -p /cdrom && mount -rt cd9660 /dev/cd0a /cdrom')
            if maintenance:
                g.command('modstat | grep -q "^compat_irix_o32 " && mkdir -p /mnt/target && mount /dev/sd1a /mnt/target')
            yield g
            if maintenance:
                g.command('umount /mnt/target')
            desktop.poweroff(lab)
        finally:
            lab.close()

    call = 'sh /cdrom/update-system.sh'
    mnt = '/mnt/target'
    with boot('preferences') as g:
        desktop.saver.desktop.greeter(g)
        g.command('usermod -G operator xiritest && /usr/local/sbin/xiri-sync-users')
        g.command(f"""su -f xiritest -c 'cd && echo "4DWm*curNewBackground: 1" >> .Sgiresources && """
                  f"""echo "4DWm*Desk 1.backgroundDescription: -solid {color}" >> .Sgiresources && echo "{release} document" > update-check.txt'""")
        g.command('sha256 /etc/master.passwd /etc/group /etc/modules.conf /etc/rc.conf /etc/rc.conf.d/xdm '
                  '/etc/xiri/session.conf /usr/people/xiritest/.xsession '
                  '/usr/people/xiritest/update-check.txt /emul/irix/usr/bin/X11/4Dwm >/root/keep.sha')
    with boot('prepare-v7', True) as g:
        g.command(f'{call} --rollback {mnt}', 600)

    def logins(g, stage):
        g.command('sha256 -c /root/keep.sha && modstat | grep -q "^compat_irix_o32 " && '
                  """su -f xiritest -c 'test -x /sbin/shutdown' && su -f native -c 'test ! -x /sbin/shutdown'""")
        q = desktop.saver.desktop
        desktop.saver.login_catalog(g, q.greeter, q.login)
        bg = g.read_text('xprop -root _SGI_DESKS_BACKGROUND_DESCRIPTION').strip()
        if color.lower() not in bg.lower():
            raise ValueError(f'Unexpected 4Dwm backdrop: {bg}')
        handoff = g.read_text('cat "$job/handoff"').strip()
        g.lab.ci('screenshot', str(work / f'{stage}-desktop.png'))
        desktop.saver.logout(g)
        q.greeter(g)
        for key in ('key type native', 'key Return', 'key type ' + password, 'key Return'):
            # The private test password need not be retained in the monitor log.
            g.lab.monitor_command(key)
            time.sleep(.45)
        g.wait_for("pgrep -u native -f '^/usr/X11R7/bin/ctwm( |$)' >/dev/null", 120)
        return dict(kernel=g.read_text('sysctl -n kern.version').strip(), module=g.read_text('sha256 -q '+MODULE).strip(),
                    receipt=g.read_text('cat /var/db/xiri-install/installed').strip(), backdrop=bg,
                    winterm=handoff, native_ctwm=True)

    with boot('start-v7') as g:
        result['previous'] = logins(g, 'start-v7')
    with boot('interrupt', True) as g:
        g.command(f'! {call} /')
        g.command(f'(exec 9>>{mnt}/var/db/xiri-install/.offline-update.lock; '
                  f'flock -n 9 9>&9 && ! {call} {mnt} >/tmp/conflict 2>&1 && '
                  "grep -q 'could not lock the offline installation' /tmp/conflict)", 300)
        # Pipe the updater's progress through a FIFO. Stop it after its first
        # installed file, then check the on-disk partial generation explicitly.
        g.command(f'cd /tmp && mkfifo progress && {{ {call} {mnt} >progress 2>update.err & updater=$!; }}')
        g.command("read line </tmp/progress && test \"$line\" = 'Installed /netbsd' && "
                  "kill -STOP \"$updater\" && kill -KILL \"$updater\"", 600)
        g.command(f'test -s {mnt}/var/db/xiri-install/upgrading && '
                  f"""test "$(sha256 -q {mnt}/netbsd)" = "$(awk -F'|' '$1=="/netbsd" {{print $4}}' /cdrom/files)" && """
                  f"""test "$(sha256 -q {mnt}{MODULE})" = "$(awk -F'|' '$1=="{MODULE}" {{print $3}}' /cdrom/files)" && sync""")
    with boot('recover', True) as g:
        g.command(f'! {call} --rollback {mnt} && {call} {mnt}', 600)
        g.command(f'{call} {mnt} && test ! -e {mnt}/var/db/xiri-install/upgrading', 600)
    with boot('updated') as g:
        result['updated'] = logins(g, 'updated')
    with boot('rollback', True) as g:
        g.command(f'{call} --rollback {mnt} && {call} --rollback {mnt}', 900)
    with boot('restored') as g:
        result['restored'] = logins(g, 'restored')
    for k in ('kernel', 'module', 'receipt'):
        if result['previous'][k] != result['restored'][k] or result['updated'][k] == result['previous'][k]:
            raise ValueError(f'Unexpected {k} at upgrade or rollback')
    if result['updated']['receipt'] != record['receipt']:
        raise ValueError('Upgrade did not restore the current installer receipt')
    (work / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(release, 'system update, interrupted recovery, rollback and logins passed', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('bundle', 'media', 'emulator', 'output'):
        parser.add_argument('--'+key, required=True, type=Path)
    run(parser.parse_args())
