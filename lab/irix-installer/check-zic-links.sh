#!/bin/sh
# Run on NetBSD with the release's SGI zic and IRIX runtime installed.
set -eu
if [ "$#" -ne 1 ]; then
    echo "usage: sh check-zic-links.sh /absolute/path/to/irix-zic" >&2
    exit 2
fi
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir "$work/zones"
printf 'Zone Xiri/Primary 0 - UTC\nLink Xiri/Primary Xiri/Alias\n' > "$work/source"
"$1" -d "$work/zones" "$work/source"
primary=$work/zones/Xiri/Primary
alias=$work/zones/Xiri/Alias
test -s "$primary"
test -s "$alias"
test ! -L "$primary"
test ! -L "$alias"
test "$(stat -f '%d:%i' "$primary")" = "$(stat -f '%d:%i' "$alias")"
test "$(stat -f %l "$alias")" = 2
rm "$primary"
test -s "$alias"
test "$(stat -f %l "$alias")" = 1
echo 'SGI zic created a timezone alias that survives unlinking the primary.'
