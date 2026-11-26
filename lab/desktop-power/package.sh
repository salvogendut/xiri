#!/bin/sh
set -eu
[ "$#" = 2 ] || { echo 'Usage: sh package.sh NATIVE-SESSION-GUARD OUTPUT.iso' >&2; exit 2; }
root=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
mkdir -p "$(dirname "$2")"
tmp=$(mktemp -d "$(dirname "$2")/.desktop-power.XXXXXXXX")
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' HUP INT TERM
mkdir "$tmp/cd"
cp "$1" "$tmp/cd/session-guard"
cp "$root/runtime/bin/xiri-poweroff" "$root/runtime/libexec/desktop-clients.sh" \
    "$root/runtime/etc/toolchest.chestrc" "$root/lab/desktop-power/install.sh" "$tmp/cd/"
(cd "$tmp/cd" && sha256sum --tag * > SHA256)
genisoimage -quiet -R -V XIRI_POWER -o "$tmp/power.iso" "$tmp/cd"
ln "$tmp/power.iso" "$2"
