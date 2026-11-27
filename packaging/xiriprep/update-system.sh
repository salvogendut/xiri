#!/bin/sh
# Apply a native Indy update to an inactive, separately mounted XiriBSD root.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
umask 077
fail() { echo "XiriBSD update: $*" >&2; exit 1; }
direction=update
if [ "${1-}" = --rollback ]; then direction=rollback; shift; fi
[ "$#" = 1 ] || fail 'usage: sh update-system.sh [--rollback] /mounted/system'
[ "$(uname -sm)" = 'NetBSD sgimips' ] && [ "$(id -u)" = 0 ] || fail 'run as root on the NetBSD maintenance system'
root=$(realpath "$1")
[ "$root" != / ] && [ "$(stat -f %d "$root")" != "$(stat -f %d /)" ] &&
    [ "$(stat -f %d "$root")" != "$(stat -f %d "$root/..")" ] || fail 'mount the inactive system on a separate filesystem'
cd "$(dirname "$0")"
sha256 -c SHA256 >/dev/null || fail 'update CD verification failed'
state=$root/var/db/xiri-install
[ "$(realpath "$state")" = "$state" ] && [ "$(stat -f '%u:%Lp' "$state")" = 0:700 ] || fail 'expected a xiriprep installation'
# Keep the inode in place across retries. The kernel releases this lock
# when the updater exits or the maintenance system reboots.
exec 9>>"$state/.offline-update.lock"
flock -nv 9 9>&9 || fail 'could not lock the offline installation'
scratch=
cleanup() { [ -z "$scratch" ] || rm -f "$scratch"; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
[ ! -e "$state/removing" ] || fail 'finish the pending removal first'
old=$(cat old-runtime)
new=$(cat new-runtime)
from=$old to=$new
if [ "$direction" = rollback ]; then from=$new to=$old; fi
journal=$state/upgrading
transaction="offline-system $direction $(sha256 -q files) $old $new"
resume=no
if [ -e "$journal" ]; then
    [ "$(cat "$journal")" = "$transaction" ] || fail 'resume with the same medium and direction'
    resume=yes
fi
read -r release generation plan extra <"$state/installed"
case "$release" in 6.5.22f|6.5.22m|6.5.30f) ;; *) fail 'unknown installed desktop';; esac
[ -z "$extra" ] && { [ "$generation" = "$from" ] || [ "$generation" = "$to" ]; } || fail 'unexpected runtime generation'
receipts='/var/db/xiri-install/inputs /emul/irix/.xiri-install-inputs /usr/local/share/xiri/fonts/.xiri-install-inputs /var/db/xiri-install/installed'
for path in $receipts; do
    dest=$root$path
    [ "$(realpath "$dest")" = "$dest" ] && [ -f "$dest" ] || fail "invalid receipt $path"
    record=$(cat "$dest")
    if [ "$resume" = yes ]; then
        [ "$record" = "$release $from $plan" ] || [ "$record" = "$release $to $plan" ] || fail "different installation at $path"
    else
        [ "$record" = "$release $generation $plan" ] || fail "inconsistent receipt $path"
    fi
done
# Check every managed file before starting. On retry, only the two published
# generations are valid. The final receipt is the last file to move.
while IFS='|' read -r path mode a b; do
    dest=$root$path
    [ "$(realpath "$dest")" = "$dest" ] && [ -f "$dest" ] &&
        [ "$(stat -f '%u:%g:%Lp' "$dest")" = "0:0:$mode" ] || fail "unexpected type, owner or mode at $path"
    hash=$(sha256 -q "$dest")
    if [ "$resume" = yes ]; then
        [ "$hash" = "$a" ] || [ "$hash" = "$b" ] || fail "locally changed $path"
    elif [ "$generation" = "$old" ]; then
        [ "$hash" = "$a" ] || fail "old generation differs at $path"
    else
        [ "$hash" = "$b" ] || fail "new generation differs at $path"
    fi
done <files
if [ "$resume" = no ] && [ "$generation" = "$to" ]; then
    echo 'Requested system generation already installed.'
    exit 0
fi
if [ "$resume" = no ]; then
    scratch=$(mktemp "$state/.system-update.XXXXXX")
    printf '%s\n' "$transaction" >"$scratch"
    mv -f "$scratch" "$journal"
    scratch=
    sync
fi
while IFS='|' read -r path mode a b; do
    dest=$root$path
    desired=$b
    if [ "$direction" = rollback ]; then desired=$a; fi
    [ "$(sha256 -q "$dest")" != "$desired" ] || continue
    install -r -m "$mode" -o root -g wheel "objects/$desired" "$dest"
    [ "$(sha256 -q "$dest")" = "$desired" ] || fail "write verification failed at $path"
    echo "Installed $path"
done <files
scratch=$(mktemp "$state/.system-update.XXXXXX")
printf '%s %s %s\n' "$release" "$to" "$plan" >"$scratch"
for path in $receipts; do
    dest=$root$path
    install -r -m "$(stat -f %Lp "$dest")" -o root -g wheel "$scratch" "$dest"
done
sync
rm "$journal"
sync
echo "System $direction complete for IRIX $release. Unmount the target before booting it."
