#!/bin/sh
# Install or remove CD 4's game on an installer-qualified Xiri desktop.
set -eu
usage() { echo "Usage: sh $0 [--gui] install|remove /absolute/cd-mount" >&2; exit 2; }
frontend=inst
if test "${1-}" = --gui; then frontend=swmgr; shift; fi
test "$#" = 2 || usage
case "$1" in install|remove) action=$1 ;; *) usage ;; esac
case "$2" in /*) media=$2 ;; *) usage ;; esac
export HOME=/ USER=root LOGNAME=root SHELL=/bin/sh TERM=vt100 LANG=C TZ=UTC
export PATH=/bin:/usr/bin:/sbin:/usr/sbin
root=/emul/irix
state=$root/var/inst/xiri-xmahjongg
types=$root/usr/lib/filetype
table=$types/desktop.otr
rules=$types/install
game=$root/usr/freeware/bin/xmahjongg
link=$root/usr/lib/desktop/iconcatalog/pages/C/Freeware/xmahjongg
fail() { echo "$*" >&2; exit 1; }
test "$(id -u)" = 0 || fail 'Run as root.'
test -f "$media/dist/fw_xmahjongg.sw" || fail 'Mount the May 2004 Freeware CD 4 distribution.'
test -x "$root/usr/sbin/inst" && test -x "$root/usr/sbin/fftr" && test -s "$table" || fail 'Prepare the SGI installer and desktop first.'
if test "$frontend" = swmgr; then
    test -n "${DISPLAY-}" && test -x "$root/usr/sbin/swmgr" || fail 'Software Manager needs the desktop display and the original swmgr program.'
fi
package=xmahjongg
. "$(dirname "$0")/desktop-artwork.sh"
mounted=no
cleanup() {
    if test "$own_game_lock" = yes && test "$types/makefile" -ef "$state/lock/makefile"; then rm "$types/makefile"; fi
    if test "$mounted" = yes; then umount "$root/tmp" || exit 1; fi
    artwork_close
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
artwork_open
# SGI's shell creates /tmp/mkindex.$$; its native child utilities reopen it.
# Share native scratch only for this transaction, without hiding existing files.
mkdir -p "$root/tmp"
if test ! /tmp -ef "$root/tmp"; then
    test -z "$(ls -A "$root/tmp")" || fail "Preserve files in $root/tmp before using this offline installer."
    mount -t null /tmp "$root/tmp"
    mounted=yes
fi
if test "$action" = install; then
    install -m 444 "$(dirname "$0")/package-filetypes.mk" "$state/lock/makefile"
    # SGI make prefers lowercase makefile. An existing site file wins.
    if test -e "$types/makefile" || test -L "$types/makefile"; then
        fail "A site makefile already exists at $types/makefile."
    fi
    ln "$state/lock/makefile" "$types/makefile" || fail "Cannot stage package rules alongside $types/Makefile."
fi
new_package=no
if test ! -f "$art/$package"; then
    test "$action" = install || fail 'No package artwork receipt exists.'
    test ! -e "$rules/xmahjongg.ftr" && test ! -e "$game" || fail 'An existing game needs its own artwork baseline.'
    touch "$art/$package"
    new_package=yes
fi
case "$action" in
    install) set -- -I fw_common.sw.index -I fw_xmahjongg.sw.xmahjongg
             selections='install fw_common.sw.index fw_xmahjongg.sw.xmahjongg' ;;
    remove) set -- -R fw_xmahjongg.sw.xmahjongg
            selections='remove fw_xmahjongg.sw.xmahjongg' ;;
esac
if test "$frontend" = swmgr; then
    # Keep the package rules in place until the user exits Software Manager.
    gui_status=0
    "$root/usr/sbin/swmgr" -V background:off -r "$root" \
        -f "$media/dist/fw_common" -f "$media/dist/fw_xmahjongg" \
        -K '*' "$@" </dev/null >"$state/$action.log" 2>&1 || gui_status=$?
else
    printf '%s\n' 'keep *' "$selections" conflicts go 'keep *' quit >"$state/commands"
    "$root/usr/sbin/inst" -M -r "$root" \
        -f "$media/dist" -c "$state/commands" </dev/null >"$state/$action.log" 2>&1
    grep -q 'No conflicts' "$state/$action.log" || fail "SGI reported a package conflict. See $state/$action.log."
fi
cat "$state/$action.log"
"$root/usr/sbin/versions" -r "$root" fw_xmahjongg >"$state/history"
# inst and its original Makefile can report success after an exit command failed.
if grep -q '^ERROR:' "$state/$action.log"; then fail "SGI exit command failed. See $state/$action.log."; fi
game_in_history() {
    awk '$1=="I" && $2=="fw_xmahjongg.sw.xmahjongg" {found=1} END {exit !found}' "$state/history"
}
if test "$frontend" = swmgr; then
    test "$(sha256 -q "$table")" = "$current" || fail 'The desktop table changed during package maintenance.'
    if test "$action" = install && ! game_in_history && test ! -e "$game" &&
        test ! -L "$link" && test ! -e "$rules/xmahjongg.ftr"; then
        if test "$new_package" = yes; then rm "$art/$package"; artwork_release_base; fi
        fail 'Software Manager closed without installing xmahjongg.'
    fi
    if test "$action" = remove && game_in_history; then
        fail 'Software Manager closed with xmahjongg still installed.'
    fi
    test "$gui_status" = 0 || fail "Software Manager exited with status $gui_status. See $state/$action.log."
    if test "$action" = install; then
        "$root/usr/sbin/versions" -r "$root" fw_common >"$state/common-history"
        awk '$1=="I" && $2=="fw_common.sw.index" {found=1} END {exit !found}' "$state/common-history" &&
            test -L "${link%/*}/FreewareRelnotes" || fail 'Software Manager did not register the shared Freeware index.'
    fi
fi
case "$action" in
    install)
        game_in_history &&
            test -x "$game" && test "$(readlink "$link")" = "$game" &&
            test -s "$rules/xmahjongg.ftr" || fail 'SGI installation or catalog registration failed.'
        if test ! -f "$state/lock/game.otr" && test "$new_package" = no; then
            (cd "$rules" && "$root/usr/sbin/fftr" -o "$state/lock/game.otr" xmahjongg.ftr)
        fi
        test "$(sha256 -q "$state/lock/game.otr")" = 06cc29d04e6f59b675100a1956084858ec3a897493aa7ed3981a25f29232b86a ||
            fail 'SGI make did not build the expected CD 4 artwork.'
        ;;
    remove)
        if game_in_history ||
            test -e "$game" || test -L "$link" || test -e "$rules/xmahjongg.ftr"; then
            fail 'SGI removal is incomplete.'
        fi
        ;;
esac
artwork_publish
