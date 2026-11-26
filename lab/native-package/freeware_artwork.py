"""Check coexisting CD 4 desktop types and the surviving user action."""
import json
import shlex

from freeware_lifecycle import GAME, HOME, PAGE, ROOT, TABLE, WINDOWS, freeware_tab, game_window, logout, software_manager, transaction
from freeware_upgrade import BIN, CD4, OLD, SGI, VERSIONS, mount, unzip
from mozilla_lifecycle import login_catalog, position
from xiri_lab import ROOT as PROJECT


def file_manager_zip(guest, out):
    directory = HOME + '/ZipCheck'
    archive = directory + '/sample.zip'
    member = directory + '/sample_extracted/sample.txt'
    guest.command('su -m xiritest -c ' + shlex.quote(f'mkdir {directory} && cp {OLD}/sample.zip {archive}'))
    # Launch through the current login's winterm so fm inherits all SGI desktop resources.
    x, y = position(guest, '"winterm"')
    guest.monitor(f'ptr click {x + 40} {y + 40} left')
    guest.monitor(f'key type /emul/irix/usr/sbin/fm {directory}')
    guest.monitor('key Return')
    title = 'xiri-indy:' + directory
    guest.wait_for(f'{WINDOWS} | grep -Fq "{title}"', 90)
    # position() matches the window tree with awk. The final path component
    # identifies this window without putting path separators in that expression.
    x, y = position(guest, 'ZipCheck"')
    guest.command('sleep 2')
    guest.capture(out / 'zip-before.png')
    guest.monitor(f'ptr click {x + 100} {y + 125} left 2')
    # Record the actual desktop response even if this package action fails.
    guest.command(f'for n in 1 2 3 4 5 6 7 8 9 10; do test ! -f {member} || break; sleep 1; done')
    windows = guest.read_text(WINDOWS + ' | grep -Ei "ZipCheck|xconfirm|error|unzip|alert|dialog"')
    guest.capture(out / 'zip-open.png')
    result = guest.read_text(f'if test -f {member} && cmp {member} {OLD}/sample.txt; then /usr/bin/stat -f %Su {member}; fi').strip()
    (out / 'zip-windows.txt').write_text(windows)
    return dict(owner=result, archive=archive, member=member, windows=windows.splitlines())


def check(guest, out, release, first, greeter, login):
    mount(guest)
    transaction(guest, 'sh /cdrom/prepare-live-base.sh /cdrom', 'freeware-base')
    baseline = guest.read_text(f'sha256 -q {TABLE}').strip()
    prev = PROJECT / 'docs/results'
    game_only = json.loads((prev / '2026-11-24-live-inst.json').read_text())['releases'][release]['installed_and_reinstalled_table']
    zip_only = json.loads((prev / '2026-11-26-freeware-upgrade.json').read_text())['releases'][release]['upgraded_table_sha256']
    guest.command(f'sha256 {TABLE} > /root/initial-table.sha')
    if first == 'xmahjongg':
        # Install with the original supplement to exercise migration of a live receipt.
        transaction(guest, f'sh /cdrom/xmahjongg.sh install {CD4}', 'original-game')
        guest.command(f'test "$(sha256 -q {TABLE})" = {game_only} && test -s {ROOT}/var/inst/xiri-xmahjongg/baseline.otr')
    login_catalog(guest, greeter, login)
    software_manager(guest, f"{SGI} -f {OLD}/dist/fw_unzip -K '*' -I fw_unzip.sw.unzip", 'unzip-old', out)
    software_manager(guest, f'sh {OLD}/unzip-upgrade.sh upgrade {CD4}', 'unzip-upgrade', out)
    if first == 'unzip':
        guest.command(f'test "$(sha256 -q {TABLE})" = {zip_only}')
        transaction(guest, f'sh {OLD}/xmahjongg.sh install {CD4}', 'game-install')
    art = ROOT + '/var/inst/xiri-filetypes'
    guest.command(f'test -e {art}/xmahjongg && test -e {art}/unzip && test "$(readlink {PAGE}/xmahjongg)" = {GAME} && '
                  f'test "$(sha256 -q {art}/baseline.otr)" = {baseline}')
    both = guest.read_text(f'sha256 -q {TABLE}').strip()
    if both in (game_only, zip_only, baseline):
        raise ValueError('The combined table lacks one or both package contributions')
    names = guest.read_text(f"strings -a {TABLE} | grep -Ex 'XMahjonggExecutable|ZipArchive|UnZipExecutable' | sort -u").splitlines()
    if names != ['UnZipExecutable', 'XMahjonggExecutable', 'ZipArchive']:
        raise ValueError('Combined SGI table lacks a package type: ' + repr(names))
    result = dict(first_installed_and_removed=first, baseline=baseline, combined=both, combined_types=names)
    def remove_game():
        transaction(guest, f'sh {OLD}/xmahjongg.sh remove {CD4}', 'remove-game')
    def remove_zip():
        software_manager(guest, f'sh {OLD}/unzip-upgrade.sh remove {CD4}', 'unzip-remove', out)
    if first == 'xmahjongg':
        remove_game()
        guest.command(f'test ! -e {GAME} && test ! -L {PAGE}/xmahjongg && test "$(sha256 -q {TABLE})" = {zip_only}')
        result['surviving_table'] = zip_only
        result['surviving_unzip'] = unzip(guest, '5.50')
    else:
        remove_zip()
        guest.command(f'test ! -e {BIN}/unzip && test "$(sha256 -q {TABLE})" = {game_only}')
        result['surviving_table'] = game_only
    logout(guest)
    login_catalog(guest, greeter, login)
    if first == 'xmahjongg':
        result['zip_action'] = file_manager_zip(guest, out)
        remove_zip()
    else:
        x, y = freeware_tab(guest)
        guest.monitor(f'ptr click {x + 215} {y + 80} left 2')
        guest.wait_for(WINDOWS + ' | grep -q XMahjongg', 120)
        result['game'] = game_window(guest, out)
        pid = int(result['game']['process'].split()[1])
        guest.command(f'kill {pid}')
        remove_game()
    guest.command(f'sha256 -c /root/initial-table.sha && test ! -e {art} && test ! -e {GAME} && test ! -e {BIN}/unzip')
    rows = guest.read_text(VERSIONS + " | awk '$1==\"I\" && $2 ~ /^fw_/ {print $2}'").splitlines()
    if set(rows) != {'fw_common', 'fw_common.sw', 'fw_common.sw.index'}:
        raise ValueError('Unexpected final SGI inventory: ' + repr(rows))
    result['final_freeware'] = rows
    (out / 'artwork.json').write_text(json.dumps(result, indent=2) + '\n')
    logout(guest)
    greeter(guest)
    if first == 'xmahjongg' and result['zip_action']['owner'] != 'xiritest':
        raise ValueError('File Manager did not extract the reference file as xiritest')
    return result
