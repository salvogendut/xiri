#!/bin/sh
# Preserve the live desktop table around the SGI UnZip 5.50 package hook.
set -eu
fail() { echo "$*" >&2; exit 1; }
test "$#" = 2 || fail "Usage: sh $0 upgrade|remove /absolute/cd4-mount"
action=$1
case "$action" in upgrade|remove) ;; *) fail 'Choose upgrade or remove.' ;; esac
case "$2" in /*) dist=$2/dist ;; *) fail 'Specify the absolute CD mount.' ;; esac
test "$(id -u)" = 0 && test -n "${DISPLAY-}" || fail 'Use the root console with the desktop DISPLAY and XAUTHORITY.'
export HOME=/ USER=root LOGNAME=root PATH=/bin:/usr/bin:/sbin:/usr/sbin LANG=C TZ=UTC
root=/emul/irix
types=$root/usr/lib/filetype
table=$types/desktop.otr
rule=$types/install/unzip.ftr
bin=$root/usr/freeware/bin/unzip
state=$root/var/inst/xiri-unzip
old=0f198a50f346a1154501ac2da96e611378f23a29d3c54ec69222c812efaee0da
new=208ba0c7ecd5a032156be45263a982e77815e6f887ed7b2774219ff6f2685eb9
(cd "$dist" && test "$(sha256 -q fw_unzip)" = 9b00174f5588acabc1166648f795e1a424f10f8ecec0412733843def2c6696d5 &&
 test "$(sha256 -q fw_unzip.idb)" = f827315fe81606b2869228ee5e8cbb8aa5c3de902b1b64e9c1f276c4ecbc5272 &&
 test "$(sha256 -q fw_unzip.sw)" = 4ade04a47bb0b4b82344ebcd71005ce72330db41faebf61fef6e8245c4ff0bb8) || fail 'Expected the May 2004 UnZip 5.50 distribution.'
test -s "$table" && test -x "$root/usr/sbin/swmgr" || fail 'Prepare the installer and desktop first.'
package=unzip
. "$(dirname "$0")/desktop-artwork.sh"
cleanup() {
    if test "$own_zip_lock" = yes && test "$types/makefile" -ef "$state/lock/makefile"; then rm "$types/makefile"; fi
    artwork_close
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
artwork_open
new_package=no
if test ! -f "$art/$package"; then
    test "$action" = upgrade && test -f "$bin" && test "$(sha256 -q "$bin")" = "$old" &&
        test ! -e "$rule" && test ! -L "$rule" || fail 'Install the original 5.40 runtime before upgrading.'
    "$root/usr/sbin/versions" -r "$root" fw_unzip >"$state/history"
    awk '$1=="I" && $2=="fw_unzip.sw.unzip" && /5\.40/ {ok=1} END {exit !ok}' "$state/history" ||
        fail 'Expected SGI installation history for UnZip 5.40.'
    new_package=yes
fi
if test "$action" = upgrade; then
    # The original exit command runs make -u inside the IRIX root.
    test ! -e "$types/makefile" && test ! -L "$types/makefile" || fail 'A site makefile already occupies the package hook path.'
    printf 'all:\n\tcd install && /usr/sbin/fftr -o /var/inst/xiri-unzip/lock/unzip.otr unzip.ftr\n' >"$state/lock/makefile"
    ln "$state/lock/makefile" "$types/makefile" || fail 'A site makefile already occupies the package hook path.'
    selection=-I
else
    selection=-R
fi
if test "$new_package" = yes; then touch "$art/$package"; fi
"$root/usr/sbin/swmgr" -V background:off -r "$root" -f "$dist/fw_unzip" -K '*' "$selection" fw_unzip.sw.unzip
"$root/usr/sbin/versions" -r "$root" fw_unzip >"$state/history"
test "$(sha256 -q "$table")" = "$current" || fail 'The artwork changed while Software Manager was open.'
if test "$action" = upgrade; then
    if test -f "$bin" && test "$(sha256 -q "$bin")" = "$old" && test ! -e "$rule" &&
        test "$new_package" = yes; then
        rm "$art/$package"
        artwork_release_base
        fail 'Software Manager closed with 5.40 still installed.'
    fi
    awk '$1=="I" && $2=="fw_unzip.sw.unzip" && /5\.50/ {ok=1} END {exit !ok}' "$state/history" &&
        test "$(sha256 -q "$bin")" = "$new" && test -s "$rule" || fail 'The 5.50 upgrade was not applied.'
    test "$(sha256 -q "$rule")" = 49d88838b2c9c8d3690628b60f0229c869cd916be08513c2f887f1b0d707e276 ||
        fail 'Unexpected CD 4 ZIP filetype source.'
else
    if awk '$1=="I" && $2 ~ /^fw_unzip(\.|$)/ {ok=1} END {exit !ok}' "$state/history" ||
        test -e "$bin" || test -e "$rule"; then fail 'UnZip is still installed.'; fi
fi
artwork_publish
