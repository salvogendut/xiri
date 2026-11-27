#!/bin/sh
# Check both donor formats and release profiles inside an installed Indy.
set -eu
[ "$#" -eq 5 ] || { echo "usage: $0 account 22-chd 22-raw 30-chd 30-raw" >&2; exit 2; }
user=$1
shift
id "$user" >/dev/null
work=$(mktemp -d /tmp/xiriprep-check.XXXXXX)
trap 'rm -rf "$work"' EXIT
trap 'exit 1' HUP INT TERM
reader=/usr/local/libexec/xiri/xiri-donor-read
signatures=/usr/local/share/xiri/donor-signatures
for release in 6.5.22f 6.5.30f; do
    expected=$(awk -v r="$release" '$1 == r {print $2}' "$signatures")
    for image in "$1" "$2"; do
        /usr/local/sbin/xiriprep --check --source "$image" --user "$user" > "$work/result"
        grep -F "Identified IRIX $release from " "$work/result"
        "$reader" --expect-sha256 "$expected" "$image" /sbin/sh > "$work/sh"
        [ "$(sha256 -q "$work/sh")" = "$expected" ]
        if "$reader" --expect-sha256 "$(printf '%064d' 0)" "$image" /sbin/sh > "$work/mismatch"; then
            echo 'unexpected digest match' >&2
            exit 1
        fi
        [ ! -s "$work/mismatch" ]
    done
    shift 2
done
