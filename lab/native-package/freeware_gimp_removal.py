"""Exercise GIMP removal while wget still uses the shared Freeware libraries."""
import shlex

from freeware_lifecycle import HOME, PAGE, ROOT, TABLE, WINDOWS, freeware_tab, history, logout, software_manager
from freeware_upgrade import SGI
from mozilla_lifecycle import login_catalog, position

MEDIA = '/mnt/gimp'
LIB = ROOT + '/usr/freeware/lib32/libintl.so.3'
STATE = '/root/gimp-check'
CATALOG = ROOT + '/usr/lib/desktop/iconcatalog/pages'


def catalog(guest, path):
    guest.command(f'(set -e; cd {CATALOG}; find -s . -type l | while IFS= read -r p; do '
                  f'printf "%s -> %s\\n" "$p" "$(readlink "$p")"; done) >{path} && test -s {path}')


def baseline(guest):
    guest.command(f'mkdir -m 700 {STATE} && sha256 {TABLE} >{STATE}/original.sha')
    catalog(guest, STATE + '/original.catalog')


def prepare(guest):
    prefs = HOME + '/.gimp-1.2/gimprc'
    # Use a non-default setting so replacing the profile with a fresh one fails.
    configure = f'test -s {prefs} && echo "(default-image-size 320 200)" >>{prefs}'
    guest.command('su - xiritest -c ' + shlex.quote(configure))
    guest.command(f'sha256 {prefs} {HOME}/gimp-cd2.ppm >{STATE}/user.sha && '
                  f'sha256 {LIB} /usr/freeware/bin/wget >{STATE}/shared.sha && '
                  f'sha256 {TABLE} >{STATE}/installed.sha')
    catalog(guest, STATE + '/installed.catalog')
    guest.command('web=$(mktemp -d /var/tmp/gimp-http.XXXXXX) && chmod 755 "$web" && '
                  'echo "Xiri Freeware dependency check" >"$web/witness.txt" && chmod 644 "$web/witness.txt"')
    guest.command('/usr/libexec/httpd -f -n -i 127.0.0.1 -I 18081 "$web" '
                  '>/root/gimp-http.log 2>&1 </dev/null & server=$!')


def wget(guest):
    fetch = ('set -e; file=$(mktemp); trap \'rm -f "$file"\' EXIT; '
             '/usr/freeware/bin/wget -T 10 -t 1 -O "$file" http://127.0.0.1:18081/witness.txt && '
             'cmp "$file" -')
    guest.command(f'kill -0 "$server" && sha256 -c {STATE}/shared.sha && '
                  'su - xiritest -c ' + shlex.quote(fetch) + ' <"$web/witness.txt"')


def conflict_report(guest, out):
    # Request the same removal in inst. "keep *" explicitly cancels the plan
    # after asking for its conflict list. There is no "go" in this input.
    guest.command(f"""printf '%s\\n' 'keep *' 'remove fw_gettext.sw.lib' conflicts 'keep *' quit >{STATE}/plan""")
    log = guest.read_text(f'{ROOT}/usr/sbin/inst -M -r {ROOT} -f {MEDIA}/dist -c {STATE}/plan </dev/null')
    (out / 'gettext-conflicts.txt').write_text(log)
    for sub in ('fw_gettext.sw.lib cannot be removed because it is needed by other products',
                'Do not remove fw_gettext.sw.lib', 'fw_gimp.sw.gimp', 'fw_gtk+.sw.lib', 'fw_wget.sw.wget'):
        if sub not in log:
            raise ValueError('Missing dependency in the SGI conflict report: ' + sub)
    return log.strip()


def cancel_conflict(guest, out):
    command = f"{SGI} -f {MEDIA}/dist/fw_gettext -K '*' -R fw_gettext.sw.lib"
    guest.command(f'({command} >{STATE}/conflict.log 2>&1; echo $? >{STATE}/conflict.rc) </dev/null & :')
    guest.wait_for(WINDOWS + ' | grep -q "Software Manager 4.1 -"', 150)
    x, y = position(guest, 'Software Manager 4.1 -')
    guest.monitor(f'ptr click {x+310} {y+152} left')
    guest.wait_for(WINDOWS + ' | grep -q "Software Manager 4.1 - Custom Installations"', 60)
    guest.monitor(f'ptr click {x+43} {y+513} left')
    # Start exposes the red Conflicts button. The first radio option keeps gettext.
    guest.monitor(f'ptr click {x+262} {y+513} left')
    dialog = 'Software Manager -- Conflicts'
    guest.wait_for(WINDOWS + f' | grep -q "{dialog}"', 60)
    dx, dy = position(guest, dialog)
    guest.capture(out / 'conflict-details.png')
    guest.monitor(f'ptr click {dx+33} {dy+102} left')
    # Resolving the sole conflict dismisses the dialog automatically.
    dialog_id = f"$({WINDOWS} | awk '/{dialog}/ {{print $1; exit}}')"
    guest.wait_for(f'test -z "{dialog_id}" || ! xwininfo -id "{dialog_id}" | grep -q IsViewable', 45)
    guest.monitor(f'ptr click {x+26} {y+15} left')   # File
    guest.monitor(f'ptr click {x+27} {y+336} left')  # Exit
    guest.wait_for(f'test -s {STATE}/conflict.rc', 60)
    guest.command(f'test "$(cat {STATE}/conflict.rc)" = 0')


def verify_cancel(guest, inventory):
    from freeware_gimp import IMAGE, TITLE, dismiss_tip, quit_gimp, wait_window

    if sorted(history(guest)) != sorted(inventory):
        raise ValueError('Cancelling the dependency conflict changed SGI installation history')
    guest.command(f'sha256 -c {STATE}/user.sha && sha256 -c {STATE}/installed.sha && test -L {PAGE}/gimp')
    wget(guest)
    launch = f'export HOME={HOME} USER=xiritest LOGNAME=xiritest; cd "$HOME" && exec /usr/freeware/bin/gimp {IMAGE}'
    guest.command('su -m xiritest -c ' + shlex.quote(launch) + ' >/tmp/gimp-after-cancel.log 2>&1 </dev/null & :')
    wait_window(guest, TITLE)
    dismiss_tip(guest)
    quit_gimp(guest)


def remove_and_restore(guest, out, inventory, greeter, login):
    command = f'sh {MEDIA}/gimp.sh'
    software_manager(guest, f'{command} --remove {MEDIA}', 'gimp-remove', out)
    removed = history(guest)
    if set(removed) != {name for name in inventory if name.split('.')[0] != 'fw_gimp'}:
        raise ValueError('Unexpected Freeware history after removing GIMP: ' + str(removed))
    guest.command(f'test ! -x /usr/freeware/bin/gimp-1.2 && test ! -L /usr/freeware/bin/gimp && '
                  f'test ! -L {PAGE}/gimp && test ! -e {ROOT}/usr/lib/filetype/install/gimp.ftr && '
                  f'sha256 -c {STATE}/original.sha && sha256 -c {STATE}/user.sha')
    catalog(guest, STATE + '/removed.catalog')
    guest.command(f'cmp {STATE}/original.catalog {STATE}/removed.catalog')
    wget(guest)
    logout(guest)
    login_catalog(guest, greeter, login)
    freeware_tab(guest)
    removed_page = guest.read_text(WINDOWS + ' | grep -m1 "Icon Catalog:"').strip()
    guest.capture(out / 'catalog-after-removal.png')
    software_manager(guest, f'{command} {MEDIA}', 'gimp-reinstall', out)
    if sorted(history(guest)) != sorted(inventory):
        raise ValueError('Reinstallation did not restore the original Freeware history')
    catalog(guest, STATE + '/restored.catalog')
    guest.command(f'cmp {STATE}/installed.catalog {STATE}/restored.catalog && sha256 -c {STATE}/installed.sha && '
                  f'sha256 -c {STATE}/user.sha && test -L {PAGE}/gimp && test {PAGE}/gimp -ef /usr/freeware/bin/gimp')
    wget(guest)
    catalog_hashes = guest.read_text(f'cd {STATE} && sha256 original.catalog removed.catalog installed.catalog restored.catalog').splitlines()
    return dict(after_removal=removed, removed_page=removed_page, catalog_hashes=catalog_hashes,
                user_files=guest.read_text(f'cat {STATE}/user.sha').splitlines(),
                shared_files=guest.read_text(f'cat {STATE}/shared.sha').splitlines(),
                restored_baseline=guest.read_text(f'cat {STATE}/original.sha').strip(),
                wget_fetches=['before-conflict', 'after-cancel', 'after-removal', 'after-reinstall'])


def remove_reinstall(guest, out, inventory, greeter, login):
    prepare(guest)
    try:
        wget(guest)
        report = conflict_report(guest, out)
        cancel_conflict(guest, out)
        verify_cancel(guest, inventory)
        return dict(conflict=report, **remove_and_restore(guest, out, inventory, greeter, login))
    finally:
        guest.command('kill "$server"; wait "$server" || :')
