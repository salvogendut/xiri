#!/bin/sh
# Update native helpers on a completed installation using the matching upgrade CD.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
umask 077
fail() { echo "Xiri upgrade: $*" >&2; exit 1; }
side=new legacy=no
for option do
    case "$option" in
        --rollback) side=old;;
        --legacy-clean-indy) legacy=yes;;
        *) fail 'usage: sh upgrade.sh [--rollback] [--legacy-clean-indy]';;
    esac
done
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
test ! -d "$state/mozilla" || fail 'remove the optional browser with its matching install.sh --remove-mozilla first'
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
previous_vendor=$vendor
if test -f previous-vendor; then previous_vendor=$(cat previous-vendor); fi
a="$release $(cat previous) $previous_vendor"
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
if test -f "$media/display-update"; then
    if pgrep '(^|/)(Xorg|X|xdm)$' >/dev/null; then fail 'stop xdm and Xorg before updating the display server'; fi
    while IFS='|' read -r path expected; do
        test "$(sha256 -q "$path")" = "$expected" || fail "native prerequisite differs: $path"
    done < prerequisites.tsv
fi
matches() {
    test -f "$dest" && test ! -L "$dest" && test "$(stat -f '%u:%g:%Mp%03Lp' "$dest")" = "0:0:$1" &&
        test "$(sha256 -q "$dest")" = "$2"
}
# Install newly required helpers before switching their callers. Retire old
# helpers last. Recompute order in each direction, including rollback.
awk -F'|' -v side="$side" 'BEGIN {OFS="|"} {
    if (side=="new") {fm=$2; fh=$3; tm=$4; th=$5}
    else             {fm=$4; fh=$5; tm=$2; th=$3}
    print (fm=="-" ? 1 : tm=="-" ? 3 : 2),$1,fm,fh,tm,th
}' changes > unordered
LC_ALL=C sort unordered > plan
progress=$state/upgrade-progress
created=$state/created
exists() { test -e "$1" || test -L "$1"; }
# The unpackaged state is either a vacant name or the original local file
# displaced by installation. A dangling link is also an occupied name.
unpackaged() {
    if ! exists "$saved"; then ! exists "$dest"; return; fi
    test -f "$saved" && test ! -L "$saved" && test -f "$dest" && test ! -L "$dest" &&
        cmp -s "$dest" "$saved" && test "$(stat -f '%u:%g:%Mp%03Lp' "$dest")" = "$(stat -f '%u:%g:%Mp%03Lp' "$saved")"
}
applied() {
    test "$resume" = yes || return 1
    if test "$frommode" != - && test "$mode" != -; then matches "$mode" "$digest"; return; fi
    test -f "$started" || return 1
    if test "$mode" = -; then unpackaged; return; fi
    matches "$mode" "$digest" && test "$(stat -f '%d:%i' "$dest")" = "$(cat "$started")"
}
ownership() {
    test "$font" = no || return 0
    test -d "$created" || return 0
    if test "$frommode" = - && ! exists "$saved"; then
        mkdir -p "$created$dest"
    elif test "$mode" = - && test -d "$created$dest"; then
        sync
        rmdir "$created$dest"
    fi
}
start_path() {
    mkdir -p "$(dirname "$started")"
    printf '%s\n' "$1" > "$scratch/started"
    mv -f "$scratch/started" "$started"
    sync
}
helpers() {
    while IFS='|' read -r order dest frommode fromsha mode digest; do
        saved=$state/original$dest
        started=$progress$dest
        font=no
        stock=no
        case "$dest" in
        /usr/X11R7/bin/Xorg|/usr/X11R7/lib/modules/extensions/libglx.so.0) stock=yes;;
        /emul/irix/usr/lib/X11/fonts/*)
            font=yes
            for dir in /emul/irix/usr/lib/X11 /emul/irix/usr/lib/X11/fonts /emul/irix/usr/lib/X11/fonts/misc; do
                if exists "$dir"; then test -d "$dir" && test ! -L "$dir" || fail "unexpected font directory $dir"; fi
            done
            if exists "$saved"; then fail "unexpected vendor backup $saved"; fi
        esac
        if exists "$saved" && { test ! -f "$saved" || test -L "$saved"; }; then
            fail "unexpected original helper type at $saved"
        fi
        if applied; then
            if test "$1" = apply; then ownership; fi
            continue
        fi
        if test "$frommode" = -; then
            unpackaged || fail "occupied helper path $dest; save or reconcile it first"
        else
            matches "$frommode" "$fromsha" || fail "local change at $dest; save or reconcile it first"
            if test "$font" = no && test "$mode" = - && test ! -d "$created" &&
                ! exists "$saved" && test "$legacy" != yes; then
                fail "unknown ownership of $dest; use --legacy-clean-indy only on a documented clean Indy installation"
            fi
        fi
        test "$1" = apply || continue
        if test "$font" = no && test "$frommode" != - && ! exists "$saved" &&
            { { test "$stock" = yes && test "$side" = new; } ||
              { test -d "$created" && test ! -d "$created$dest"; }; }; then
            # The display pair predates Xiri, including on older installations
            # without a created-file ledger. Other tracked files may predate it.
            mkdir -p "$(dirname "$saved")"
            cp -p "$dest" "$scratch/original"
            mv "$scratch/original" "$saved"
            sync
        fi
        if test "$mode" = -; then
            start_path retire
            if ! unpackaged; then
                if exists "$saved"; then
                    staging=$(mktemp "$(dirname "$dest")/.xiri-upgrade.XXXXXX")
                    cp -p "$saved" "$staging"
                    mv -f "$staging" "$dest"
                    staging=
                else
                    rm "$dest"
                fi
            fi
        elif test "$frommode" = - && exists "$saved" && matches "$mode" "$digest"; then
            # The site's original file was also the packaged version.
            start_path "$(stat -f '%d:%i' "$dest")"
        else
            if test "$font" = yes; then (umask 022 && mkdir -p "$(dirname "$dest")"); fi
            staging=$(mktemp "$(dirname "$dest")/.xiri-upgrade.XXXXXX")
            install -m "$mode" "$side/root$dest" "$staging"
            test "$(sha256 -q "$staging")" = "$digest" || fail "bad staged helper $dest"
            if test "$frommode" = -; then
                start_path "$(stat -f '%d:%i' "$staging")"
            fi
            if test "$frommode" = - && ! exists "$saved"; then
                # link(2) cannot overwrite a racing local file or follow a directory.
                /usr/sbin/link "$staging" "$dest" && rm "$staging" || fail "cannot publish new helper $dest"
            else
                mv -f "$staging" "$dest"
            fi
            staging=
        fi
        ownership
    done < plan
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
    rm -rf "$progress"
    mkdir "$progress"
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
sync
rm -rf "$progress"
echo "Installed native package $target"
