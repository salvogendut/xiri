#!/bin/sh
# Install or remove CD 4's game on an installer-qualified Xiri desktop.
set -eu
usage() { echo "Usage: sh $0 install|remove /absolute/cd-mount" >&2; exit 2; }
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
mkdir -p "$state"
chmod 700 "$state"
mkdir "$state/lock" || fail "Check for an active installer at $state/lock."
stage=
mounted=no
cleanup() {
    if test -n "$stage"; then rm -f "$stage/desktop.otr"; rmdir "$stage"; fi
    if test "$types/makefile" -ef "$state/lock/makefile"; then rm "$types/makefile"; fi
    if test "$mounted" = yes; then umount "$root/tmp" || exit 1; fi
    rm -f "$state/lock/game.otr" "$state/lock/makefile" "$state/lock/next"
    rmdir "$state/lock"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
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
current=$(sha256 -q "$table")
if test -f "$state/baseline.otr"; then
    previous=$(cat "$state/published.sha256")
    base=$(sha256 -q "$state/baseline.otr")
    pending=
    if test -f "$state/pending.sha256"; then pending=$(cat "$state/pending.sha256"); fi
    test "$current" = "$previous" || test "$current" = "$base" || test "$current" = "$pending" ||
        fail 'The desktop table changed independently. Review the saved table before continuing.'
else
    test "$action" = install || fail 'No package artwork baseline exists.'
    test ! -e "$rules/xmahjongg.ftr" && test ! -e "$game" || fail 'An existing game needs its own artwork baseline.'
    cp -p "$table" "$state/base.tmp"
    echo "$current" >"$state/published.sha256"
    mv "$state/base.tmp" "$state/baseline.otr"
fi
case "$action" in
    install) selections='install fw_common.sw.index fw_xmahjongg.sw.xmahjongg' ;;
    remove) selections='remove fw_xmahjongg.sw.xmahjongg' ;;
esac
printf '%s\n' 'keep *' "$selections" conflicts go 'keep *' quit >"$state/commands"
"$root/usr/sbin/inst" -M -r "$root" \
    -f "$media/dist" -c "$state/commands" </dev/null >"$state/$action.log" 2>&1
cat "$state/$action.log"
"$root/usr/sbin/versions" -r "$root" fw_xmahjongg >"$state/history"
# inst and its original Makefile can report success after an exit command failed.
grep -q 'No conflicts' "$state/$action.log" || fail 'SGI reported a package conflict.'
if grep -q '^ERROR:' "$state/$action.log"; then fail "SGI exit command failed. See $state/$action.log."; fi
stage=$(mktemp -d "$types/.xiri-package.XXXXXX")
tmp=$stage/desktop.otr
case "$action" in
    install)
        awk '$1=="I" && $2=="fw_xmahjongg.sw.xmahjongg" {found=1} END {exit !found}' "$state/history" &&
            test -x "$game" && test "$(readlink "$link")" = "$game" &&
            test -s "$rules/xmahjongg.ftr" || fail 'SGI installation or catalog registration failed.'
        test "$(sha256 -q "$state/lock/game.otr")" = 06cc29d04e6f59b675100a1956084858ec3a897493aa7ed3981a25f29232b86a ||
            fail 'SGI make did not build the expected CD 4 artwork.'
        "$root/usr/sbin/fftr" -o "$tmp" "$state/lock/game.otr" "$state/baseline.otr"
        ;;
    remove)
        if awk '$1=="I" && $2=="fw_xmahjongg.sw.xmahjongg" {found=1} END {exit !found}' "$state/history" ||
            test -e "$game" || test -L "$link" || test -e "$rules/xmahjongg.ftr"; then
            fail 'SGI removal is incomplete.'
        fi
        cp -p "$state/baseline.otr" "$tmp"
        ;;
esac
test -s "$tmp"
chmod 444 "$tmp"
next=$(sha256 -q "$tmp")
echo "$next" >"$state/lock/next"
mv "$state/lock/next" "$state/pending.sha256"
mv -f "$tmp" "$table"
mv "$state/pending.sha256" "$state/published.sha256"
if test "$action" = remove; then
    rm -f "$state/baseline.otr" "$state/published.sha256"
fi
echo "Desktop table $next. Log in again to load it."
