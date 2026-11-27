#!/bin/sh
# Install the v8 session replay correction and the release-matched saver files.
set -eu
cd "$(dirname "$0")"
fail() { echo "Xiri Screen Saver: $*" >&2; exit 1; }
test "$(id -u)" = 0 || fail 'run as root'
sha256 -c SHA256 >/dev/null || fail 'damaged repair CD'
read -r release native vendor </var/db/xiri-install/installed
test "$release" = "$(cat release)" && test "$native" = "$(cat native.sha256)" ||
    fail 'use the repair CD for this audio-v8 desktop and IRIX release'
clients=/usr/local/libexec/xiri/desktop-clients.sh
old=ed85110089b07f19c32f265b181458e77088fc35c42e9dd98a998568981de2dd
new=$(sha256 -q desktop-clients.sh)
backup=$clients.pre-saver-v8
digest() { test -f "$1" && test ! -L "$1" && sha256 -q "$1"; }
current=$(digest "$clients") || fail "expected a regular file at $clients"
case $current in "$old"|"$new") ;; *) fail "locally changed $clients (see the installation guide)";; esac
if test -e "$backup" || test -L "$backup"; then
    test "$(digest "$backup")" = "$old" || fail "unexpected backup $backup"
fi
case "$#:$*" in
0:)
    sh ./install-savers.sh
    test "$current" != "$new" || exit 0
    test -e "$backup" || ln "$clients" "$backup"
    source=desktop-clients.sh ;;
1:--restore-session)
    test "$current" != "$old" || exit 0
    test "$(digest "$backup")" = "$old" || fail 'no saved audio-v8 session script'
    source=$backup ;;
1:--restore-xorg) exec sh ./install-savers.sh --restore-xorg ;;
*) fail 'usage: sh install.sh [--restore-session | --restore-xorg]' ;;
esac
temp=$(mktemp "${clients}.XXXXXXXX")
trap 'rm -f "$temp"' EXIT
trap 'exit 1' HUP INT TERM
install -o root -g wheel -m "$(stat -f '%Lp' "$clients")" "$source" "$temp"
mv -f "$temp" "$clients"
