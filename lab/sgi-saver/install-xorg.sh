#!/bin/sh
# Replace or restore the NetBSD 11.0/sgimips Xorg 1.10.6 extension module.
set -eu
cd "$(dirname "$0")"
stock=7e9dab4962f13ceac4c1c87d95f1a4019a74ec19d013cb70baa3383497b215f2
ext=/usr/X11R7/lib/modules/extensions/libextmod.so.0
backup=$ext.xiri-original
fail() { echo "$*" >&2; exit 1; }
digest() { [ -f "$1" ] && [ ! -L "$1" ] && sha256 -q "$1"; }
[ "$(id -u)" = 0 ] || fail 'Run as root.'
updated=$(cat module.sha256)
[ "$(digest libextmod.so.0)" = "$updated" ] || fail 'Damaged Screen Saver CD.'
current=$(digest "$ext") || fail "Expected a regular file at $ext"
if [ -e "$backup" ] || [ -L "$backup" ]; then
    [ "$(digest "$backup")" = "$stock" ] || fail "Existing backup differs: $backup"
fi
case $current in
    "$stock") ;;
    "$updated") [ "$(digest "$backup")" = "$stock" ] || fail 'Original module backup is missing.' ;;
    *) fail 'This update requires the stock NetBSD 11.0/sgimips extmod.' ;;
esac
case ${1:-install} in
    check) exit 0 ;;
    restore) [ "$current" != "$stock" ] || exit 0; source=$backup ;;
    install)
        [ "$current" != "$updated" ] || exit 0
        [ -e "$backup" ] || ln "$ext" "$backup" || [ "$(digest "$backup")" = "$stock" ]
        source=libextmod.so.0 ;;
    *) fail 'Expected check, install, or restore.' ;;
esac
tmp=$(mktemp "${ext}.XXXXXXXX")
trap 'rm -f "$tmp"' EXIT
trap 'exit 1' HUP INT TERM
install -o root -g wheel -m 444 "$source" "$tmp"
mv -f "$tmp" "$ext"
echo 'The module takes effect when Xorg next starts.'
