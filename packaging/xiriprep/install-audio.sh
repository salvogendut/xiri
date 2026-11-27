#!/bin/sh
# Import the release-matched analog audio clients into an existing desktop.
set -eu
image=$1
plan=$2
root=/emul/irix
reader=/usr/local/libexec/xiri/xiri-donor-read
matches() {
    test -f "$1" && test ! -L "$1" && test "$(sha256 -q "$1")" = "$2"
}
dirs="usr usr/lib32 usr/lib32/dmedia usr/lib32/dmedia/audioconverters usr/sbin"
for dir in $dirs; do
    test ! -L "$root/$dir" || { echo "Unexpected directory link: $root/$dir" >&2; exit 1; }
done
missing=no
while IFS='|' read -r kind mode source dest hash; do
    if test -e "$root$source" || test -L "$root$source"; then
        matches "$root$source" "$hash" || { echo "Preserve conflicting $root$source" >&2; exit 1; }
    else
        missing=yes
    fi
done < "$plan"
test "$missing" = yes || exit 0
# Stage on the destination filesystem. A concurrent or interrupted installation
# can only leave verified files and the next run can finish the set.
stage=$(mktemp -d "$root/.xiri-audio.XXXXXX")
trap 'rm -rf "$stage"' EXIT
trap 'exit 1' HUP INT TERM
"$reader" --extract "$plan" "$image" "$stage"
for dir in $dirs; do
    test -d "$root/$dir" || install -d -m 755 "$root/$dir"
done
while IFS='|' read -r kind mode source dest hash; do
    matches "$root$source" "$hash" && continue
    ln "$stage/emul/irix$source" "$root$source" || matches "$root$source" "$hash"
done < "$plan"
