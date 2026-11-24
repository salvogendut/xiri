#!/bin/sh
# Update native helpers on a completed installation using the matching upgrade CD.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
umask 077
fail() { echo "Xiri upgrade: $*" >&2; exit 1; }
case "$#:$*" in 0:) side=new;; 1:--rollback) side=old;; *) fail 'usage: sh upgrade.sh [--rollback]';; esac
test "$(id -u)" = 0 && test "$(uname -s)" = NetBSD || fail 'run as root on NetBSD'
cd "$(dirname "$0")"
media=$(pwd -P)
state=/var/db/xiri-install
test -d "$state" && test ! -L "$state" && test "$(stat -f '%u:%Lp' "$state")" = 0:700 || fail 'missing private install state'
shlock -f "$state/lock" -p $$ || fail 'another installer is running'
scratch= staging=
cleanup() {
    test -z "$staging" || rm -f "$staging"
    test -z "$scratch" || rm -rf "$scratch"
    rm -f "$state/lock"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
test ! -e "$state/removing" || fail 'finish the interrupted removal first'
sha256 -c SHA256 >/dev/null || fail 'media checksum mismatch'
for old in "$state"/upgrade-work.*; do
    if test -d "$old" && test ! -L "$old"; then rm -rf "$old"; fi
done
scratch=$(mktemp -d "$state/upgrade-work.XXXXXX")
cd "$scratch"
pax -rz -f "$media/delta.tgz"
. ./target.conf
version=$(sysctl -n kern.version)
test "$(uname -m)" = "$machine" && test "$(uname -r)" = "$kernel_release" &&
    test "$(printf %s "$version" | sha256 -q)" = "$kernel_version_sha256" &&
    test "$(sha256 -q /netbsd)" = "$kernel_sha256" || fail 'boot the matching Xiri kernel'
modstat | grep -Eq '^compat_irix_o32[[:space:]]+exec[[:space:]]+filesys' || fail 'load the matching module'
release=$(cat "$media/release")
native=$(awk '$2=="(native.tgz)" {print $4}' "$media/SHA256")
vendor=$(awk '$2=="(payload.tgz)" {print $4}' "$media/SHA256")
a="$release $(cat previous) $vendor"
b="$release $native $vendor"
if test "$side" = new; then source=$a target=$b; else source=$b target=$a; fi
transaction="$side $source $target"
pending=$state/upgrading
sentinel="pending $transaction"
resume=no
if test -f "$pending"; then
    test "$(cat "$pending")" = "$transaction" || fail 'resume with the same media and direction'
    resume=yes
fi
# Keep each ownership receipt readable at its original mode. Publish the
# completed receipt last. A sentinel makes older install CDs refuse a partial update.
inputs=$state/inputs
installed=$state/installed
trees='/emul/irix/.xiri-install-inputs /usr/local/share/xiri/fonts/.xiri-install-inputs'
for receipt in "$inputs" $trees "$installed"; do
    test -f "$receipt" && test ! -L "$receipt" || fail "missing receipt $receipt"
    identity=$(cat "$receipt")
    if test "$resume" = yes; then
        test "$identity" = "$source" || test "$identity" = "$target" ||
            { test "$receipt" = "$inputs" && test "$identity" = "$sentinel"; } || fail "foreign receipt $receipt"
    else
        cmp -s "$receipt" "$installed" || fail 'inconsistent installation receipts'
        test "$identity" = "$source" || test "$identity" = "$target" || fail 'wrong vendor release or native package'
    fi
done
if test "$resume" = no && test "$identity" = "$target"; then
    echo 'The requested native package is already installed.'
    exit 0
fi
if pgrep -x 4Dwm >/dev/null; then fail 'log out of the IRIX desktop first'; fi
matches() {
    test -f "$dest" && test ! -L "$dest" && test "$(stat -f '%u:%g:%Lp' "$dest")" = "0:0:${1#0}" &&
        test "$(sha256 -q "$dest")" = "$2"
}
# Validate the entire change set before writing any file.
helpers() {
    while IFS='|' read -r dest oldmode oldsha newmode newsha; do
        if test "$side" = new; then
            mode=$newmode digest=$newsha frommode=$oldmode fromsha=$oldsha
        else
            mode=$oldmode digest=$oldsha frommode=$newmode fromsha=$newsha
        fi
        if test "$resume" = yes && matches "$mode" "$digest"; then continue; fi
        matches "$frommode" "$fromsha" || fail "local change at $dest; save or reconcile it first"
        test "$1" = apply || continue
        # A file identical to the old package may have predated a tracked install.
        saved=$state/original$dest
        if test -d "$state/created" && test ! -d "$state/created$dest" &&
            test ! -e "$saved" && test ! -L "$saved"; then
            mkdir -p "$(dirname "$saved")"
            cp -p "$dest" "$scratch/original" && mv "$scratch/original" "$saved"
            sync
        fi
        staging=$(mktemp "$(dirname "$dest")/.xiri-upgrade.XXXXXX")
        install -m "$mode" "$side/root$dest" "$staging"
        test "$(sha256 -q "$staging")" = "$digest" || fail "bad staged helper $dest"
        mv -f "$staging" "$dest"
        staging=
    done < changes
}
write_receipt() {
    staging=$(mktemp "$(dirname "$1")/.xiri-upgrade.XXXXXX")
    cp -p "$1" "$staging"
    printf '%s\n' "$2" > "$staging"
    mv -f "$staging" "$1"
    staging=
}
helpers check
if test "$resume" = no; then
    printf '%s\n' "$transaction" > "$scratch/pending"
    mv "$scratch/pending" "$pending"
    sync
fi
write_receipt "$inputs" "$sentinel"
sync
helpers apply
sync
for receipt in $trees "$inputs" "$installed"; do write_receipt "$receipt" "$target"; done
sync
rm "$pending"
echo "Installed native package $target"
