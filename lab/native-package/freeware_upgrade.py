"""Exercise CD 4 xosview and a two-version SGI UnZip transaction on a private Indy."""
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

from freeware_lifecycle import ROOT, TABLE, WINDOWS, logout, mount_media, software_manager, transaction
from mozilla_lifecycle import login_catalog, reboot

OLD = '/mnt/previous'
CD4 = '/mnt/freeware'
BIN = ROOT + '/usr/freeware/bin'
VERSIONS = ROOT + '/usr/sbin/versions -r ' + ROOT
SGI = ROOT + '/usr/sbin/swmgr -V background:off -r ' + ROOT
UNZIP = {
    '5.40': '0f198a50f346a1154501ac2da96e611378f23a29d3c54ec69222c812efaee0da',
    '5.50': '208ba0c7ecd5a032156be45263a982e77815e6f887ed7b2774219ff6f2685eb9',
}
XOSVIEW = '0fd6a1f98b7dfdfeba2780d483edbe14eff930d8a936f1c4565bb8bc29434a22'


def verify_media(iso):
    helper = Path(__file__).resolve().parents[1] / 'irix-installer/unzip-upgrade.sh'
    pins = {
        'unzip-upgrade.sh': hashlib.sha256(helper.read_bytes()).hexdigest(),
        'dist/fw_unzip': '5b0341f1241e615b08602263a95d43eeb18bc06ebc3b1a3d2f53f4f3dd42169b',
        'dist/fw_unzip.idb': '7280d3afa520d2f64686f366e09057b4e3073bf10731eb78304f553b2a74eeca',
        'dist/fw_unzip.sw': '32d261d6c54354c8402d11d5352a2ee5675ffe719eacafcf80e1e88211f289ef',
    }
    for name, expected in pins.items():
        data = subprocess.check_output(['isoinfo', '-R', '-i', iso, '-x', '/' + name])
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Unexpected UnZip helper CD file: ' + name)


def mount(guest):
    mount_media(guest)
    guest.command(f'(test -b /dev/cd2a || (cd /dev && sh MAKEDEV cd2)) && '
                  f'mkdir -p {OLD} && mount -rt cd9660 /dev/cd2a {OLD}')


def unzip(guest, version):
    rows = guest.read_text(f'{VERSIONS} fw_unzip').strip()
    if not any('fw_unzip.sw.unzip' in row and version in row for row in rows.splitlines()):
        raise ValueError('Unexpected SGI UnZip history: ' + rows)
    guest.command(f'test "$(sha256 -q {BIN}/unzip)" = {UNZIP[version]} && test "$(readlink {BIN}/zipinfo)" = unzip')
    # Check both the binary's version and actual decompression as the desktop user.
    extract = (f'set -e; cd "$(mktemp -d)"; {BIN}/unzip -v | head -1; '
               f'{BIN}/unzip -o {OLD}/sample.zip && cmp sample.txt {OLD}/sample.txt; '
               'status=$?; rm -f sample.txt; dir=$PWD; cd /; rmdir "$dir"; exit "$status"')
    tested = guest.command('su - xiritest -c ' + shlex.quote(extract))
    if 'UnZip ' + version not in tested:
        raise ValueError('Executable did not report its expected version')
    return dict(history=rows.splitlines(), binary_sha256=UNZIP[version], extraction_user='xiritest')


def meters(guest, out):
    guest.command(f'test "$(sha256 -q {BIN}/xosview)" = {XOSVIEW} && '
                  f'test -s {ROOT}/usr/freeware/lib/X11/app-defaults/XOsview')
    run = f'exec {BIN}/xosview -xrm "xosview*load: False" -xrm "xosview*gfx: False"'
    guest.command('su -m xiritest -c ' + shlex.quote(run) + ' >/root/xosview.log 2>&1 </dev/null & :')
    guest.wait_for(WINDOWS + " | grep -iq '(\"xosview\"'", 100)
    window = guest.read_text(WINDOWS + " | grep -im1 '(\"xosview\"'").strip()
    process = guest.read_text('ps -axww -o uid,pid,args | awk -v uid="$(id -u xiritest)" '
                              "'$1==uid && $3 ~ /\\/xosview$/ {print}'").strip()
    if not process:
        raise ValueError('Missing normal-user xosview process for ' + window)
    (out / 'xosview.log').write_text(guest.read_text('cat /root/xosview.log'))
    guest.monitor('disp compositor sw')
    guest.monitor('screen shot ' + str(out / 'xosview.png'))
    pid = int(process.split()[1])
    guest.command(f'kill -TERM {pid}')
    guest.wait_for(f'! kill -0 {pid} 2>/dev/null', 40)
    return dict(window=window, process=process)


def check(guest, out, greeter, login):
    mount(guest)
    guest.command(f'test ! -e {ROOT}/var/inst/hist && test ! -e {BIN}/unzip && test ! -e {BIN}/xosview')
    transaction(guest, 'sh /cdrom/prepare-live-base.sh /cdrom', 'freeware-base')
    guest.command(f'sha256 {TABLE} /etc/master.passwd /usr/people/xiritest/.xsession '
                  '/var/db/xiri-install/installed /var/db/xiri-install/mozilla/identity >/root/before-upgrade.sha')
    base_history = guest.read_text(VERSIONS)
    login_catalog(guest, greeter, login)
    xos_dist = CD4 + '/dist/fw_xosview'
    software_manager(guest, f"{SGI} -f {xos_dist} -K '*' -I fw_xosview.sw.xosview", 'xosview-install', out)
    result = dict(xosview=meters(guest, out), xosview_sha256=XOSVIEW)
    result['xosview_history'] = guest.read_text(VERSIONS + ' fw_xosview').strip().splitlines()
    if not any('fw_xosview.sw.xosview' in line for line in result['xosview_history']):
        raise ValueError('Missing xosview subsystem')
    software_manager(guest, f"{SGI} -f {OLD}/dist/fw_unzip -K '*' -I fw_unzip.sw.unzip", 'unzip-install', out)
    result['old'] = unzip(guest, '5.40')
    software_manager(guest, f'sh {OLD}/unzip-upgrade.sh upgrade {CD4}', 'unzip-upgrade', out)
    result['new'] = unzip(guest, '5.50')
    state = ROOT + '/var/inst/xiri-unzip'
    guest.command(f'test "$(sha256 -q {TABLE})" = "$(cat {state}/published.sha256)" && '
                  f'test "$(sha256 -q {TABLE})" != "$(sha256 -q {state}/baseline.otr)"')
    result['upgraded_table_sha256'] = guest.read_text(f'sha256 -q {TABLE}').strip()
    (out / 'installed.json').write_text(json.dumps(result, indent=2) + '\n')
    logout(guest)
    greeter(guest)
    reboot(guest)
    mount(guest)
    if unzip(guest, '5.50') != result['new']:
        raise ValueError('Upgraded UnZip changed across reboot')
    guest.command(f'test "$(sha256 -q {TABLE})" = {result["upgraded_table_sha256"]} && '
                  f'test "$(sha256 -q {BIN}/xosview)" = {XOSVIEW}')
    login_catalog(guest, greeter, login)
    software_manager(guest, f'sh {OLD}/unzip-upgrade.sh remove {CD4}', 'unzip-remove', out)
    guest.command(f'test ! -e {BIN}/zipinfo && test ! -L {BIN}/zipinfo && sha256 -c /root/before-upgrade.sha && '
                  f'test "$(sha256 -q {BIN}/xosview)" = {XOSVIEW}')
    software_manager(guest, f"{SGI} -f {xos_dist} -K '*' -R fw_xosview.sw.xosview", 'xosview-remove', out)
    guest.command(f'test ! -e {BIN}/xosview && test ! -e {ROOT}/usr/freeware/lib/X11/app-defaults/XOsview && '
                  f'test ! -e {state}/baseline.otr && sha256 -c /root/before-upgrade.sha')
    if guest.read_text(VERSIONS) != base_history:
        raise ValueError('SGI history after removal differs from the base installation')
    result['restored_table_sha256'] = guest.read_text(f'sha256 -q {TABLE}').strip()
    logout(guest)
    greeter(guest)
    return result
