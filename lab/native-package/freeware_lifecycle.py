"""Exercise an original CD 4 transaction on a clean Mozilla desktop."""
import json
import shlex
from functools import partial
from pathlib import Path

from mozilla_lifecycle import login_catalog, open_browser, position, raise_catalog, reboot
from xiri_lab import ROOT as PROJECT

ROOT = '/emul/irix'
HOME = '/usr/people/xiritest'
PAGE = ROOT + '/usr/lib/desktop/iconcatalog/pages/C/Freeware'
TABLE = ROOT + '/usr/lib/filetype/desktop.otr'
GAME = ROOT + '/usr/freeware/bin/xmahjongg'
WINDOWS = 'xwininfo -root -tree'
TITLE = 'My Freeware Desktop'
CHECKSUMS = 'sha256 -c /root/freeware-user.sha && sha256 -c /root/freeware-system.sha'


def mount_media(guest):
    guest.command('mkdir -p /cdrom /mnt/freeware && mount -rt cd9660 /dev/cd0a /cdrom && '
                  'mount -rt cd9660 /dev/cd1a /mnt/freeware && '
                  'test "$(find /mnt/freeware/dist -name \'*.idb\' | wc -l)" -eq 144')


def verify_products(guest):
    inputs = json.loads((PROJECT / 'lab/irix-installer/inputs.json').read_text())
    products = {Path(path).name: row['sha256'] for path, row in inputs.items() if row['source'] == 'media'}
    names = sorted(products)
    rows = guest.read_text('cd /mnt/freeware/dist && sha256 -q ' + ' '.join(names))
    if rows.splitlines() != [products[name] for name in names]:
        raise ValueError('CD 4 game or shared index differs from the verified distribution')


def logout(guest):
    guest.command('su -m xiritest -c "env XIRI_SESSION_DIR=\'$job\' /usr/local/bin/xiri-logout"')


def close_browser(guest, title):
    x, y = position(guest, title)
    guest.monitor(f'ptr click {x + 240} {y + 200} left')
    guest.monitor('key ctrl+q')
    guest.wait_for('! pgrep -x mozilla-bin >/dev/null', 90)


def baseline(guest, release, greeter, login):
    mount_media(guest)
    verify_products(guest)
    guest.command(f'test ! -e {GAME} && test ! -L {PAGE}/xmahjongg && test ! -e {ROOT}/var/inst/hist')
    login_catalog(guest, greeter, login)
    open_browser(guest, release, 'Welcome to Xiri')
    close_browser(guest, 'Welcome to Xiri')
    save_profile(guest)
    logout(guest)
    greeter(guest)


def save_profile(guest):
    custom_page = HOME + '/freeware-home.html'
    html = shlex.quote(f'<title>{TITLE}</title><h1>{TITLE}</h1>')
    pref = shlex.quote(f'user_pref("browser.startup.homepage", "file://{custom_page}");')
    configure = ('set -e; pref=$(find "$HOME/.mozilla" -name prefs.js); test -f "$pref"; '
                 f'printf "%s\\n" {html} > {custom_page}; printf "%s\\n" {pref} >> "$pref"')
    guest.command('su - xiritest -c ' + shlex.quote(configure))
    guest.command(f'p=$(find {HOME}/.mozilla -name prefs.js); b=$(find {HOME}/.mozilla -name bookmarks.html); '
                  f'sha256 "$p" "$b" {custom_page} {HOME}/.xsession >/root/freeware-user.sha && '
                  'sha256 /netbsd /netbsd.boot /stand/sgimips/*/modules/compat_irix_o32/*.kmod '
                  '/etc/rc.d/xiri_hosts /etc/master.passwd /var/db/xiri-install/installed '
                  '/var/db/xiri-install/mozilla/identity >/root/freeware-system.sha', 240)


def transaction(guest, command, log, timeout=1800):
    guest.command(f'{command} >/root/{log}.log 2>&1; status=$?; tail -10 /root/{log}.log; '
                  'test "$status" -eq 0', timeout)


def command_line_package(guest, action):
    transaction(guest, f'sh /cdrom/xmahjongg.sh {action} /mnt/freeware', 'freeware-' + action)


def graphical_package(guest, action, out, greeter, login):
    guest.command('(test -b /dev/cd2a || (cd /dev && sh MAKEDEV cd2)) && '
                  'mkdir -p /mnt/gui && mount -rt cd9660 /dev/cd2a /mnt/gui')
    login_catalog(guest, greeter, login)
    log = '/root/freeware-' + action
    guest.command(f'(sh /mnt/gui/xmahjongg.sh --gui {action} /mnt/freeware >{log}.log 2>&1; '
                  f'echo $? >{log}.rc) </dev/null & :')
    main = 'Software Manager 4.1 -'
    guest.wait_for(f'test -s {log}.rc || {WINDOWS} | grep -q "{main}"', 150)
    guest.command(f'test ! -e {log}.rc || (cat {log}.log; exit 1)')
    x, y = position(guest, main)
    guest.monitor(f'ptr click {x + 310} {y + 152} left')
    guest.wait_for(WINDOWS + ' | grep -q "Software Manager 4.1 - Custom Installations"', 60)
    guest.capture(out / f'swmgr-{action}-selection.png')
    guest.monitor(f'ptr click {x + 43} {y + 513} left')
    # SGI presents a modal completion dialog for both installation and removal.
    dialog = 'askUser_popup.*550x244'
    dialog_id = f"$({WINDOWS} | awk '/{dialog}/ {{print $1; exit}}')"
    guest.wait_for(f'test -n "{dialog_id}" && xwininfo -id "{dialog_id}" | grep -q IsViewable', 240)
    guest.capture(out / f'swmgr-{action}-complete.png')
    x, y = position(guest, dialog)
    guest.monitor(f'ptr click {x + 25} {y + 155} left')
    guest.monitor(f'ptr click {x + 508} {y + 209} left')
    guest.wait_for(f'test -s {log}.rc', 120)
    guest.command(f'cat {log}.log; test "$(cat {log}.rc)" = 0 && umount /mnt/gui')
    logout(guest)
    greeter(guest)


def install(guest, expected, run_package):
    transaction(guest, 'sh /cdrom/prepare-live-base.sh /cdrom', 'freeware-base')
    guest.command(f'test "$(sha256 -q {TABLE})" = {expected["original_and_restored_table"]}')
    run_package(guest, 'install')
    installed(guest, expected)


def installed(guest, expected):
    guest.command(f'test "$(sha256 -q {GAME})" = {expected["game_sha256"]} && '
                  f'test "$(sha256 -q {TABLE})" = {expected["installed_and_reinstalled_table"]} && '
                  f'test "$(readlink {PAGE}/xmahjongg)" = {GAME} && {CHECKSUMS}', 240)
    guest.command(f"{ROOT}/usr/sbin/versions -r {ROOT} | awk "
                  "'$1==\"I\" && $2==\"fw_xmahjongg.sw.xmahjongg\" {game=1} "
                  "$1==\"I\" && $2==\"fw_common.sw.index\" {notes=1} END {exit !(game && notes)}'")


def freeware_tab(guest):
    x, y = raise_catalog(guest)
    guest.monitor(f'ptr click {x + 550} {y + 461} left')
    guest.wait_for(WINDOWS + ' | grep -q "Icon Catalog: Freeware"', 45)
    return x, y


def play(guest, out, greeter, login, expected):
    reboot(guest)
    installed(guest, expected)
    login_catalog(guest, greeter, login)
    x, y = freeware_tab(guest)
    guest.monitor(f'ptr click {x + 215} {y + 80} left 2')
    guest.wait_for(WINDOWS + ' | grep -q XMahjongg', 180)
    return game_window(guest, out)


def game_window(guest, out):
    window = guest.read_text(WINDOWS + ' | grep -m1 XMahjongg').strip()
    process = guest.read_text('ps -axww -o uid,pid,args | awk -v uid="$(id -u xiritest)" '
                              "'$1==uid && $3 ~ /\\/Freeware\\/xmahjongg$/ {print}'").strip()
    if '1006x614' not in window or not process:
        raise RuntimeError('Unexpected game window or process: ' + window + ' ' + process)
    guest.capture(out / 'game.png')
    return dict(window=window, process=process)


def remove(guest, expected, greeter, run_package):
    logout(guest)
    greeter(guest)
    mount_media(guest)
    run_package(guest, 'remove')
    guest.command(f'test ! -e {GAME} && test ! -L {PAGE}/xmahjongg && test -L {PAGE}/FreewareRelnotes && '
                  f'test "$(sha256 -q {TABLE})" = {expected["original_and_restored_table"]} && {CHECKSUMS}', 240)
    guest.command(f"{ROOT}/usr/sbin/versions -r {ROOT} | awk "
                  "'$1==\"I\" && $2 ~ /^fw_xmahjongg/ {game=1} "
                  "$1==\"I\" && $2==\"fw_common.sw.index\" {notes=1} END {exit game || !notes}'")


def after_removal(guest, out, release, greeter, login):
    login_catalog(guest, greeter, login)
    freeware_tab(guest)
    guest.capture(out / 'removed.png')
    open_browser(guest, release, TITLE)
    window = guest.read_text(WINDOWS + ' | grep -m1 "' + TITLE + '"').strip()
    guest.capture(out / 'browser.png')
    close_browser(guest, TITLE)
    logout(guest)
    greeter(guest)
    return window


def history(guest):
    return guest.read_text(f"{ROOT}/usr/sbin/versions -r {ROOT} | awk "
                           "'$1==\"I\" && $2 ~ /^fw_/ {print $2}'").splitlines()


def check(guest, out, package, greeter, login, graphical=False):
    release = package['release']
    expected = json.loads((PROJECT / 'docs/results/2026-11-24-live-inst.json').read_text())['releases'][release]
    if guest.read_text('cat /var/db/xiri-install/mozilla/identity').strip() != package['mozilla_receipt']:
        raise ValueError('Mozilla component does not match the clean CHD')
    baseline(guest, release, greeter, login)
    if graphical:
        run_package = partial(graphical_package, out=out, greeter=greeter, login=login)
    else:
        run_package = command_line_package
    install(guest, expected, run_package)
    before_reboot = history(guest)
    common = {'fw_common', 'fw_common.sw', 'fw_common.sw.index'}
    if set(before_reboot) != common.union(expected['history']):
        raise ValueError('Unexpected products installed from CD 4')
    played = play(guest, out, greeter, login, expected)
    if history(guest) != before_reboot:
        raise ValueError('Freeware history changed across reboot')
    remove(guest, expected, greeter, run_package)
    after = history(guest)
    if set(after) != common:
        raise ValueError('Unexpected Freeware installation history')
    user_files = guest.read_text('cat /root/freeware-user.sha').splitlines()
    system_files = guest.read_text('cat /root/freeware-system.sha').splitlines()
    for name in ('freeware-base', 'freeware-install', 'freeware-remove'):
        (out / (name + '.log')).write_text(guest.read_text('cat /root/' + name + '.log'))
    browser = after_removal(guest, out, release, greeter, login)
    return dict(frontend='swmgr' if graphical else 'inst', installed=before_reboot, removed=after,
                game=played, browser=browser, user_files=user_files, system_files=system_files)
