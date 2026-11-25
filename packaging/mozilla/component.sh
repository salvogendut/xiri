#!/bin/sh
# Internal to install-desktop.sh. Its parent holds the desktop transaction lock.
set -eu
umask 022
action=$1
media=$2
work=$3
state=/var/db/xiri-install
record=$state/mozilla
fail() { echo "Xiri Mozilla: $*" >&2; exit 1; }
exists() { test -e "$1" || test -L "$1"; }
test "$(cat "$state/lock")" -eq "$PPID" || fail 'use install.sh --mozilla or --remove-mozilla'
identity="$(cat "$state/installed") $(awk '$2=="(mozilla.tgz)" {print $4}' "$media/SHA256")"
if test -d "$record"; then
    test ! -L "$record" && test "$(cat "$record/identity")" = "$identity" || fail 'use the matching component media'
elif test "$action" = remove; then
    echo 'No Mozilla component is installed.'
    exit 0
fi
test "$(uname -smr)" = 'NetBSD 11.99.11 sgimips' || fail 'requires the 11.99.11 Indy'
if pgrep -x mozilla-bin >/dev/null; then fail 'quit Mozilla before changing the component'; fi
bytes=$(cat "$media/mozilla-space")
space() {
    available=$(df -Pk "$1" | awk 'END {print $4}')
    test "$available" -ge "$2" || fail "$1 requires $2 KiB free ($available available)"
}
space "$work" "$((bytes + 8192))"
mkdir "$work/bundle"
(cd "$work/bundle" && pax -rzpe -f "$media/mozilla.tgz")
bundle=$work/bundle
staging=
cleanup() { test -z "$staging" || rm -rf "$staging"; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

# Compare link targets without following them, including links inside trees.
same() {
    if test -L "$1"; then test -L "$2" && test "$(readlink "$1")" = "$(readlink "$2")"
    elif test -L "$2"; then return 1
    elif test -d "$1"; then
        # NetBSD mtree reports extra and missing files on stdout.
        test -d "$2" && mtree -c -k type,mode,link,sha256 -p "$1" > "$work/tree.spec" &&
            mtree -f "$work/tree.spec" -p "$2" > "$work/tree.diff" && test ! -s "$work/tree.diff"
    else
        test -f "$1" && test -f "$2" && cmp -s "$1" "$2" &&
            test "$(stat -f %Lp "$1")" = "$(stat -f %Lp "$2")"
    fi
}
# Stage on the destination filesystem and publish with a rename.
publish() {
    parent=${2%/*}
    test -n "$parent" || parent=/
    mkdir -p "$parent"
    test "$(cd "$parent" && pwd -P)" = "$parent" || fail "unexpected symlink in $parent"
    staging=$(mktemp -d "$parent/.xiri-mozilla.XXXXXX")
    cp -RPp "$1" "$staging/item"
    mv -fh "$staging/item" "$2"
    rmdir "$staging"
    staging=
}
phase() {
    echo "$1" > "$record/phase.new"
    mv "$record/phase.new" "$record/phase"
}
if test ! -d "$record"; then
    # Check the entire write set and save original regular files before activation.
    space /usr "$((bytes + 8192))"
    space / 16384
    mkdir -m 700 "$work/receipt"
    printf '%s\n' "$identity" > "$work/receipt/identity"
    while IFS='|' read -r policy dest; do
        if ! exists "$dest"; then
            case $policy in add|config) kind=add;; *) fail "missing baseline $dest";; esac
        elif test "$policy" = config; then
            test -f "$dest" || fail "unexpected configuration $dest"
            kind=keep
        elif same "$bundle/root$dest" "$dest"; then
            kind=keep
        elif test -f "$dest" && test ! -L "$dest" && test "$(sha256 -q "$dest")" = "$policy"; then
            kind=replace
            backup=$work/receipt/original$dest
            mkdir -p "${backup%/*}"
            cp -p "$dest" "$backup"
        else
            fail "existing $dest differs from the supplied component and its desktop baseline"
        fi
        printf '%s|%s|%s\n' "$kind" "$policy" "$dest" >> "$work/receipt/plan"
    done < "$bundle/groups"
    echo enabling > "$work/receipt/phase"
    mv "$work/receipt" "$record"
fi
current=$(cat "$record/phase")
case "$action:$current" in
    enable:enabled|enable:enabling|remove:enabled|remove:disabling) ;;
    *) fail "resume the $current operation first";;
esac
if test "$action" = remove; then
    # Refuse changed owned files before restoring the kernel. Local rc settings
    # are preserved. Files already in their old state are valid on a retry.
    while IFS='|' read -r kind policy dest; do
        case $kind in
            keep) continue;;
            add) exists "$dest" || continue; test "$policy" != config || continue;;
            replace) same "$record/original$dest" "$dest" && continue;;
        esac
        same "$bundle/root$dest" "$dest" || fail "save local changes to $dest before rollback"
    done < "$record/plan"
    phase disabling
    if grep -q '^add|add|/etc/rc.d/xiri_hosts$' "$record/plan" && test -x /etc/rc.d/xiri_hosts; then
        /etc/rc.d/xiri_hosts onestop
    fi
fi
while IFS='|' read -r kind policy dest; do
    source=$bundle/root$dest
    if test "$action" = enable; then
        if test "$kind" = keep && test "$policy" = config; then continue; fi
        if test "$policy" = config && exists "$dest"; then continue; fi
        if same "$source" "$dest"; then continue; fi
        test "$current" != enabled || fail "installed component changed: $dest"
        case $kind in
            add) ! exists "$dest" || fail "conflict at $dest";;
            replace) same "$record/original$dest" "$dest" || fail "conflict at $dest";;
            *) fail "pre-existing component changed: $dest";;
        esac
        publish "$source" "$dest"
    else
        case $kind in
            replace) same "$record/original$dest" "$dest" || publish "$record/original$dest" "$dest";;
            add)
                if exists "$dest"; then
                    if same "$source" "$dest"; then
                        # Rename first; an interrupted directory deletion can be retried.
                        parent=${dest%/*}
                        staging=$(mktemp -d "$parent/.xiri-mozilla.XXXXXX")
                        mv "$dest" "$staging/item"
                        rm -rf "$staging"
                        staging=
                    else echo "Kept local setting $dest"; fi
                fi;;
        esac
    fi
done < "$record/plan"
sync
if test "$action" = enable; then
    phase enabled
    echo 'Mozilla installed. Reboot before launching it from Applications.'
else
    mv "$record" "$work/removed"
    echo 'Restored the previous desktop files. Reboot to load its kernel and module.'
fi
