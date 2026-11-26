#!/bin/sh
# Update the two menu resources on a qualified v6 desktop.
set -eu
cd "$(dirname "$0")"
fail() { echo "$*" >&2; exit 1; }
case $#:${1:-} in 0:|1:--allow-xiritest) ;; *) fail 'Usage: sh install.sh [--allow-xiritest]' ;; esac
[ "$(id -u)" = 0 ] || fail 'Run as root.'
case "$(awk 'NR == 1 {print $1}' /var/db/xiri-install/installed)" in
    6.5.22f|6.5.30f) ;; *) fail 'Expected an installed Xiri desktop.' ;;
esac
sha256 -c SHA256 || fail 'Incorrect menu update CD.'
if [ "$#" = 1 ]; then
    id xiritest >/dev/null && getent group operator >/dev/null || fail 'Missing xiritest or operator.'
fi
clients=/usr/local/libexec/xiri/desktop-clients.sh
guard=/usr/local/libexec/xiri/session-guard
chest=/usr/local/share/xiri/toolchest.chestrc
power=/usr/local/bin/xiri-poweroff
check() {
    [ -f "$1" ] && [ ! -L "$1" ] || fail "Expected a regular file at $1"
    sum=$(sha256 -q "$1")
    [ "$sum" = "$2" ] || [ "$sum" = "$(sha256 -q "${1##*/}")" ] || fail "Local modifications at $1"
}
check "$clients" bbd1b4dbeb1b8efb376159f65e213080c0992888336a08ecc06ba1fccb4f0be2
check "$guard" 7a9f3329da1cb0a3e18a6ef0f66929033920fcfc0600701b797767886df3394d
check "$chest" f390bb6a4a59dfc1b2bfc7ce7db2e9c1a9f5407839ff62a047b314c4fb97d824
if [ -e "$power" ] || [ -L "$power" ]; then check "$power" "$(sha256 -q xiri-poweroff)"; fi
install -r -o root -g wheel -m 555 session-guard "$guard"
install -r -o root -g wheel -m 555 xiri-poweroff "$power"
install -r -o root -g wheel -m 444 toolchest.chestrc "$chest"
install -r -o root -g wheel -m 555 desktop-clients.sh "$clients"
if [ "$#" = 1 ] && ! id -Gn xiritest | tr ' ' '\n' | grep -qx operator; then
    usermod -G operator xiritest
fi
echo 'Log out and back in to reload the menus and account groups.'
