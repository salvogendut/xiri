#!/bin/sh
# Remove the userspace installed from this CD. Kernel activation is separate.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
umask 077
fail() { echo "Xiri uninstaller: $*" >&2; exit 1; }
exists() { test -e "$1" || test -L "$1"; }
legacy=no
case "$#" in
0) ;;
1) test "$1" = --legacy-clean-indy || fail 'unknown option'; legacy=yes;;
*) fail 'usage: sh uninstall.sh [--legacy-clean-indy]';;
esac
test "$(id -u)" = 0 && test "$(uname -s)" = NetBSD || fail 'run as root on NetBSD'
cd "$(dirname "$0")"
media=$(pwd -P)
sha256 -c SHA256 >/dev/null || fail 'media checksum mismatch'
state=/var/db/xiri-install
test -d "$state" && test ! -L "$state" && test "$(stat -f '%u:%Lp' "$state")" = 0:700 || fail 'missing private install state'
shlock -f "$state/lock" -p $$ || fail 'another installer is running'
scratch=
cleanup() { test -z "$scratch" || rm -rf "$scratch"; rm -f "$state/lock"; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
test ! -e "$state/upgrading" || fail 'resume the pending native upgrade first'
identity="$(cat release) $(awk '$2=="(native.tgz)" {print $4}' SHA256) $(awk '$2=="(payload.tgz)" {print $4}' SHA256)"
if test -f "$state/removing"; then
    trx=$(cat "$state/removing")
    case "$trx" in */*|'') fail 'invalid pending uninstall';; history.*) ;; *) fail 'invalid pending uninstall';; esac
    history=$state/$trx
    test "$(cat "$history/receipt")" = "$identity" || fail 'pending uninstall needs the matching media'
else
    if test ! -e "$state/inputs" && test ! -e "$state/installed"; then
        echo 'No desktop installation is active.'
        exit 0
    fi
    test -f "$state/installed" && cmp -s "$state/inputs" "$state/installed" &&
        test "$(cat "$state/installed")" = "$identity" || fail 'requires a completed installation and its matching media'
    test -d "$state/created" || test "$legacy" = yes || fail 'older receipt: use --legacy-clean-indy only on a documented clean Indy installation'
    if pgrep -x 4Dwm >/dev/null; then fail 'log out of the active IRIX desktop before removal'; fi
    for dest in /emul/irix /usr/local/share/xiri/fonts; do
        test -d "$dest" && test ! -L "$dest" &&
            cmp -s "$state/installed" "$dest/.xiri-install-inputs" || fail "unmanaged tree $dest"
        test "$(stat -f %d "$dest")" = "$(stat -f %d "$(dirname "$dest")")" || fail "cannot detach a mount point: $dest"
    done
    history=$(mktemp -d "$state/history.XXXXXX")
    trx=${history##*/}
    cp "$state/installed" "$history/receipt"
    echo "$trx" >"$history/pending"
    mv "$history/pending" "$state/removing"
fi
scratch=$(mktemp -d "$state/work.XXXXXX")
# Restore originals using a rename on their own filesystem. Preserve local
# replacements before the rename, even if the operator interrupts this run.
copy_entry() {
    if test -L "$1"; then ln -s "$(readlink "$1")" "$2"
    else test -f "$1" && cp -p "$1" "$2"; fi
}
matches() {
    case "$2" in
    symlink) test -L "$1" && test "$(readlink "$1")" = "$4";;
    file) test ! -L "$1" && test -f "$1" && test "$(stat -f '%u:%g:%Lp' "$1")" = "0:0:${3#0}" &&
        test "$(sha256 -q "$1")" = "$4";;
    *) return 1;;
    esac
}
undo() {
    dest=$1 kind=$2 mode=$3 value=$4 policy=$5
    original=$state/original$dest
    if exists "$original"; then
        # A retry can find the original already restored.
        if test -L "$original"; then
            matches "$dest" symlink 0 "$(readlink "$original")" && return 0
        elif test -f "$dest" && test ! -L "$dest" && cmp -s "$dest" "$original" &&
            test "$(stat -f '%u:%g:%Lp' "$dest")" = "$(stat -f '%u:%g:%Lp' "$original")"; then return 0
        fi
        if exists "$dest" && ! matches "$dest" "$kind" "$mode" "$value"; then
            backup=$history/edits$dest
            if ! exists "$backup"; then
                mkdir -p "$(dirname "$backup")"
                copy_entry "$dest" "$scratch/entry" || fail "review changed $dest"
                mv "$scratch/entry" "$backup"
            fi
        fi
        tmp=$(mktemp -d "$(dirname "$dest")/.xiri-restore.XXXXXX")
        (copy_entry "$original" "$tmp/entry" && mv -fh "$tmp/entry" "$dest") || { rm -rf "$tmp"; fail "restore $dest"; }
        rmdir "$tmp"
    elif test -d "$state/created$dest" || { test ! -d "$state/created" && test "$policy" != preserve-config; }; then
        if matches "$dest" "$kind" "$mode" "$value"; then rm -f "$dest"
        elif exists "$dest"; then echo "Kept local change $dest"; fi
    fi
}
if test ! -f "$history/complete"; then
    # Preserve any extra applications, generated databases and local edits in
    # these trees. Each rename stays on the source filesystem.
    for dest in /emul/irix /usr/local/share/xiri/fonts; do
        holding=$(dirname "$dest")/.xiri-removed-${trx#history.}
        if ! test -d "$holding"; then mkdir -m 700 "$holding"; fi
        test ! -L "$holding" && test "$(stat -f '%u:%Lp' "$holding")" = 0:700 || fail "unexpected $holding"
        if ! exists "$holding/tree"; then
            test ! -L "$dest" && cmp -s "$history/receipt" "$dest/.xiri-install-inputs" || fail "ownership changed: $dest"
            mv "$dest" "$holding/tree"
        fi
        test ! -L "$holding/tree" && cmp -s "$history/receipt" "$holding/tree/.xiri-install-inputs" &&
            ! exists "$dest" || fail "unfinished tree move: $dest"
        echo "$holding/tree" >>"$scratch/trees"
    done
    mv "$scratch/trees" "$history/trees"
    for alias in /usr/lib/desktop /usr/adobe /usr/freeware; do undo "$alias" symlink 0 "/emul/irix$alias" managed; done
    undo /usr/bin/nawk symlink 0 awk managed
    (cd "$scratch" && pax -rz -f "$media/native.tgz" files.tsv)
    for service in rpcbind xdm xiri_devices xiri_famd xiri_sessions; do
        hash=$(awk -F'|' -v p="root/usr/local/share/xiri/examples/rc.conf.d/$service" '$1==p {print $4}' "$scratch/files.tsv")
        test -n "$hash" || fail "missing service default $service"
        undo "/etc/rc.conf.d/$service" file 0644 "$hash" managed
    done
    while IFS='|' read -r path kind mode value policy; do
        case "$path" in kernel/*|root/stand/*) continue;; root/*) dest=/${path#root/};; *) fail "$path";; esac
        undo "$dest" "$kind" "$mode" "$value" "$policy"
    done <"$scratch/files.tsv"
    touch "$history/complete"
fi
for name in original created upgrade-progress installed inputs; do
    if exists "$state/$name"; then mv "$state/$name" "$history/$name"; fi
done
rm "$state/removing"
echo "Removed the Xiri desktop. Recovery records and detached tree locations: $history"
