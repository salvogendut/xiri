#!/bin/sh
# Add the selected vendor files to an existing desktop of the same release.
set -eu
fail() { echo "$*" >&2; exit 1; }
cd "$(dirname "$0")"
[ "$(id -u)" = 0 ] || fail 'Run from the NetBSD root shell.'
root=/emul/irix
receipt=/var/db/xiri-install/installed
cmp -s "$receipt" "$root/.xiri-install-inputs" || fail 'Expected an installed Xiri desktop.'
[ "$(awk 'NR == 1 {print $1}' "$receipt")" = "$(cat release)" ] || fail 'Use the CD for the installed IRIX release.'

matches() {
    [ ! -L "$1" ] && [ -f "$1" ] && [ "$(sha256 -q "$1")" = "$hash" ] &&
        [ "$(stat -f '%u:%g:%Lp' "$1")" = "0:0:$mode" ]
}

# Check the entire selection before adding files. Require ordinary directories
# under the emulation root, including when an install is retried after interruption.
while read -r hash mode path; do
    [ "$(sha256 -q "files/$path")" = "$hash" ] || fail "Incorrect CD data for $path"
    parent=${path%/*}
    while :; do
        [ ! -L "$root/$parent" ] || fail "Unexpected directory link: $parent"
        if [ -e "$root/$parent" ]; then [ -d "$root/$parent" ] || fail "Expected directory: $parent"; fi
        case $parent in */*) parent=${parent%/*} ;; *) break ;; esac
    done
    dest=$root/$path
    if [ -e "$dest" ] || [ -L "$dest" ]; then matches "$dest" || fail "Existing file differs: $dest"; fi
done < inventory

umask 022
stage=$(mktemp -d "$root/.xiri-savers.XXXXXXXX")
trap 'rm -rf "$stage"' EXIT
trap 'exit 1' HUP INT TERM
while read -r hash mode path; do
    dest=$root/$path
    matches "$dest" && continue
    mkdir -p "${dest%/*}"
    install -m "$mode" -o root -g wheel "files/$path" "$stage/file"
    ln "$stage/file" "$dest" || matches "$dest" || fail "Cannot add $dest"
    rm "$stage/file"
done < inventory
echo 'Close and reopen Screen Saver from Icon Catalog.'
