#!/bin/sh
# Move an installed v5 Indy to the v6 native boot set, or restore v5.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
umask 077
fail() { echo "Xiri kernel update: $*" >&2; exit 1; }
case "$#:$*" in 0:) direction=update;; 1:--rollback) direction=rollback;; *) fail 'usage: sh upgrade.sh [--rollback]';; esac
test "$(id -u):$(uname -smr)" = '0:NetBSD 11.99.11 sgimips' || fail 'requires root on the NetBSD 11.99.11 Indy'
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
# Work directories are private to this updater under the shared install lock.
for old in "$state"/kernel-work.*; do
    if test -d "$old" && test ! -L "$old"; then rm -rf "$old"; fi
done
scratch=$(mktemp -d "$state/kernel-work.XXXXXX")
cd "$scratch"
pax -rz -f "$media/delta.tgz"
a=$(cat previous)
b="$(cat "$media/release") $(cat new-native) ${a##* }"
pending=$state/upgrading
browser=no
record=$state/mozilla
if test -d "$record"; then
    test ! -L "$record" && grep -qx enabled "$record/phase" || fail 'finish the pending Mozilla operation first'
    browser=yes
    old_browser=$(cat previous-mozilla)
    hash=$(awk '$2=="(mozilla.tgz)" {print $4}' "$media/SHA256")
    test -n "$hash" || fail 'use the v6 CD with the Mozilla option'
    new_browser="$b $hash"
fi
source=$a target=$b
if test "$direction" = rollback; then source=$b target=$a; fi
transaction="indy-kernel $direction $a $b $browser"
resume=no
if test -f "$pending"; then
    test "$(cat "$pending")" = "$transaction" || fail 'resume with the same CD and direction'
    resume=yes
fi
receipts="$state/inputs /emul/irix/.xiri-install-inputs /usr/local/share/xiri/fonts/.xiri-install-inputs $state/installed"
current=$(cat "$state/installed")
for receipt in $receipts; do
    test ! -L "$receipt" && test -f "$receipt" || fail "missing desktop receipt $receipt"
    id=$(cat "$receipt")
    test "$id" = "$a" || test "$id" = "$b" || fail "wrong release or native package in $receipt"
    test "$resume" = yes || test "$id" = "$current" || fail 'inconsistent desktop receipts'
done

# Validate the full set before replacing anything. During recovery each file
# may already have been published. Unknown bytes always require review.
check_generation() {
    old_value=$1 new_value=$2 observed=$3
    if test "$resume" = yes; then test "$observed" = "$old_value" || test "$observed" = "$new_value"
    elif test "$current" = "$a"; then test "$observed" = "$old_value"
    else test "$observed" = "$new_value"; fi
}
if test "$browser" = yes; then
    check_generation "$old_browser" "$new_browser" "$(cat "$record/identity")" || fail 'unexpected Mozilla receipt'
    awk -F '|' 'NR==FNR {boot[$1]=1; next} !($3 in boot) {print}' files "$record/plan" >plan.new
    cp plan.new plan.old
fi
while IFS='|' read -r path base legacy new; do
    old=$base
    if test "$browser" = yes; then
        old=$legacy
        printf 'replace|%s|%s\n' "$base" "$path" >>plan.old
        backup=$record/original$path
        if test -e "$backup" || test -L "$backup"; then
            test -f "$backup" && test ! -L "$backup" && test "$(sha256 -q "$backup")" = "$base" || fail "changed Mozilla backup $backup"
        fi
    fi
    test -f "$path" && test ! -L "$path" && test "$(stat -f '%u:%g:%Lp' "$path")" = 0:0:444 &&
        check_generation "$old" "$new" "$(sha256 -q "$path")" || fail "unexpected boot file $path"
done <files
if test "$browser" = yes; then
    check_generation "$(sha256 -q plan.old)" "$(sha256 -q plan.new)" "$(sha256 -q "$record/plan")" ||
        fail 'unexpected Mozilla boot-file ownership plan'
fi
if test "$resume" = no && test "$current" = "$target"; then
    echo 'The requested kernel generation is already installed.'
    exit 0
fi
publish() {
    dest=$2
    staging=$(mktemp "${dest%/*}/.xiri-kernel.XXXXXX")
    install -m "$3" "$1" "$staging"
    mv -f "$staging" "$dest"
    staging=
}
# Publish the marker before the first change so other installer entry points
# refuse a partially applied update. The PROM boot wrapper is published last.
echo "$transaction" >transaction
publish transaction "$pending" 600
while IFS='|' read -r path base legacy new; do
    want=$new
    if test "$direction" = rollback; then
        want=$base
        if test "$browser" = yes; then
            want=$legacy
            backup=$record/original$path
            if test ! -f "$backup"; then
                mkdir -p "${backup%/*}"
                publish "$base" "$backup" 444
            fi
        fi
    fi
    if test "$(sha256 -q "$path")" != "$want"; then publish "$want" "$path" 444; fi
done <files
if test "$browser" = yes; then
    plan=plan.new; identity=$new_browser
    if test "$direction" = rollback; then plan=plan.old; identity=$old_browser; fi
    echo "$identity" >browser-id
    publish "$plan" "$record/plan" "$(stat -f %Lp "$record/plan")"
    publish browser-id "$record/identity" "$(stat -f %Lp "$record/identity")"
fi
echo "$target" >desktop-id
for receipt in $receipts; do publish desktop-id "$receipt" "$(stat -f %Lp "$receipt")"; done
sync
rm "$pending"
echo 'Kernel update complete. Reboot the Indy to load the selected module.'
