#!/bin/sh
# Start Software Manager with the GIMP 1.2.5 base, scripts and plug-ins selected.
set -eu
root=/emul/irix
types=$root/usr/lib/filetype
table=$types/desktop.otr
package=gimp
action=install
fail() { echo "$*" >&2; exit 1; }
test "$#" = 1 && test "$(id -u)" = 0 && test -n "${DISPLAY-}" ||
    fail "Usage from the root console with desktop X authority: sh $0 /absolute/gimp-cd"
media=$1
case "$media" in /*) ;; *) fail 'Use an absolute CD mount path.' ;; esac
test -s "$root/var/inst/hist" && test -x "$root/usr/sbin/swmgr" || fail 'Prepare the matching SGI installer and base history first.'
test -s "$media/selections" && test -s "$media/dist/fw_gimp.data" || fail 'Mount the GIMP distribution CD.'
export HOME=/ USER=root LOGNAME=root SHELL=/bin/sh TERM=vt100 LANG=C TZ=UTC PATH=/bin:/usr/bin:/sbin:/usr/sbin
. "$(dirname "$0")/desktop-artwork.sh"
new_package=no
rule=$types/install/gimp.ftr
program=$root/usr/freeware/bin/gimp
cleanup() {
    if test "$new_package" = yes && test ! -e "$rule" && test ! -e "$program" && test ! -L "$program"; then rm -f "$art/gimp"; fi
    if test "$own_game_lock" = yes && test "$types/makefile" -ef "$game_state/lock/gimp.mk"; then rm "$types/makefile"; fi
    artwork_close
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
artwork_open
if test ! -f "$art/gimp"; then
    test ! -e "$program" && test ! -L "$program" && test ! -e "$rule" || fail 'An existing GIMP installation needs its own artwork baseline.'
    touch "$art/gimp"
    new_package=yes
fi
test ! -e "$types/makefile" && test ! -L "$types/makefile" || fail 'A site makefile already occupies the package hook path.'
printf 'all:\n\tcd install && /usr/sbin/fftr -o /var/inst/xiri-xmahjongg/lock/gimp.otr gimp.ftr\n' >"$game_state/lock/gimp.mk"
ln "$game_state/lock/gimp.mk" "$types/makefile" || fail 'A site makefile already occupies the package hook path.'
set --
for file in "$media"/dist/*.idb; do set -- "$@" -f "${file%.idb}"; done
set -- "$@" -K '*'
while read -r sub; do set -- "$@" -I "$sub"; done <"$media/selections"
"$root/usr/sbin/swmgr" -V background:off -r "$root" "$@" </dev/null
"$root/usr/sbin/versions" -r "$root" >"$game_state/lock/history"
while read -r sub; do
    awk -v want="$sub" '$1=="I" && $2==want {ok=1} END {exit !ok}' "$game_state/lock/history" ||
        fail "Software Manager did not install $sub."
done <"$media/selections"
test -x "$program" && test -s "$rule" || fail 'GIMP program or filetype is missing.'
link=$root/usr/lib/desktop/iconcatalog/pages/C/Freeware/gimp
test -L "$link" && test "$link" -ef "$program" || fail 'SGI did not register GIMP on the Freeware page.'
# SGI ships these eight n32 shared objects as mode 0644. Xiri requires
# execute permission to map their text, as it does for imported desktop DSOs.
for name in libintl.so.3 libglib-1.2.so.1 libgmodule-1.2.so.1 libgthread-1.2.so.1 \
    libgdk-1.2.so.1 libgtk-1.2.so.1 libpng.so.1 libz.so.1; do
    path=$root/usr/freeware/lib32/$name
    test -f "$path" && test ! -L "$path" || fail "Missing package library $name."
    chmod 555 "$path"
done
artwork_publish
