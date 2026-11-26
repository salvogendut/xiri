#!/bin/sh
# Update the framed Indigo2, Octane or O2 disk from its matching read-only CD.
set -eu
export PATH=/bin:/usr/bin:/sbin:/usr/sbin
umask 077
fail() { echo "$*" >&2; exit 1; }
case "$#:${1-}" in 0:) action=update ;; 1:--rollback) action=rollback ;; *) fail "Usage: sh $0 [--rollback]" ;; esac
test "$(id -u)" = 0 || fail 'Run from the root console.'
cd "$(dirname "$0")"
test "$(sysctl -n hw.model)" = "$(cat model)" || fail 'This update CD belongs to another machine.'
sha256 -c SHA256
case "$(cat model)" in
    SGI-IP28) kernel=/netbsd.ip28 ;;
    IP30) kernel=/netbsd.ip30 ;;
    SGI-IP32) kernel=/netbsd ;;
    *) fail 'Unknown platform.' ;;
esac
module=/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod
state=/var/db/xiri-platform-v6
mkdir -p -m 700 "$state"
# shlock discards a dead owner's lock. The saved transaction survives a reboot.
/usr/bin/shlock -p $$ -f "$state/lock" || fail 'Another platform update is running.'
trap 'rm -f "$state/lock"' EXIT
trap 'exit 1' HUP INT TERM
names="module kernel"
if test "$kernel" = /netbsd; then names="module kernel boot"; fi
destination() {
    case "$1" in module) echo "$module" ;; kernel) echo "$kernel" ;; boot) echo /netbsd.boot ;; esac
}
digest() {
    if test -f "$1" && test ! -L "$1"; then sha256 -q "$1"
    elif test ! -e "$1" && test ! -L "$1"; then echo absent
    else fail "Expected an ordinary file at $1"; fi
}
if test ! -d "$state/original"; then
    test "$action" = update || fail 'This machine has no saved v6 update.'
    test "$(sysctl -n kern.osrelease)" = 11.99.9 || fail 'Expected the framed 11.99.9 desktop.'
    test "$(digest "$kernel")" = "$(cat previous-kernel)" || fail 'Previous kernel differs from the qualified platform build.'
    stage=$(mktemp -d "$state/save.XXXXXX")
    for name in $names; do
        dest=$(destination "$name")
        hash=$(digest "$dest")
        if test "$hash" != absent; then cp -p "$dest" "$stage/$name"; fi
        echo "$hash" >"$stage/$name.sha256"
    done
    cp SHA256 "$stage/media"
    sync
    mv "$stage" "$state/original"
fi
cmp -s SHA256 "$state/original/media" || fail 'Use the same platform update CD.'
if test -e "$state/pending"; then
    test "$(cat "$state/pending")" = "$action" || fail "Finish the pending $(cat "$state/pending") first."
fi
for name in $names; do
    dest=$(destination "$name")
    old=$(cat "$state/original/$name.sha256")
    test "$(digest "$state/original/$name")" = "$old" || fail "Backup changed for $dest."
    new=$(sha256 -q "$name")
    current=$(digest "$dest")
    test "$current" = "$old" || test "$current" = "$new" || fail "Locally changed $dest."
done
echo "$action" >"$state/next"
mv -f "$state/next" "$state/pending"
sync
# On rollback, restore the bootable kernel before retiring its new module.
if test "$action" = rollback; then
    names="kernel module"
    if test "$kernel" = /netbsd; then names="boot kernel module"; fi
fi
for name in $names; do
    dest=$(destination "$name")
    source=$name
    if test "$action" = rollback; then source=$state/original/$name; fi
    desired=$(digest "$source")
    test "$(digest "$dest")" != "$desired" || continue
    if test "$desired" = absent; then rm -f "$dest"; continue; fi
    mkdir -p -m 755 "${dest%/*}/."
    tmp=$(mktemp "${dest}.xiri.XXXXXX")
    if ! install -m 444 "$source" "$tmp" || test "$(sha256 -q "$tmp")" != "$desired"; then
        rm -f "$tmp"; fail "Failed staging $dest."
    fi
    mv -f "$tmp" "$dest"
done
sync
mv -f "$state/pending" "$state/last"
echo "Platform $action complete. Reboot to use the selected kernel."
