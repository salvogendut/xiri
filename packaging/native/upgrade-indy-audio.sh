#!/bin/sh
# Switch one installed Indy between the published v6 and audio-v7 generations.
set -eu
PATH=/bin:/sbin:/usr/bin:/usr/sbin
export PATH
umask 077
fail() { echo "Xiri audio upgrade: $*" >&2; exit 1; }
case "$#:$*" in 0:) side=v7;; 1:--rollback) side=v6;; *) fail 'usage: sh upgrade.sh [--rollback]';; esac
test "$(id -u):$(uname -smr)" = '0:NetBSD 11.99.11 sgimips' || fail 'requires root on the 11.99.11 Indy'
test "$(sysctl -n hw.model)" = 'SGI-IP22' || test "$(sysctl -n hw.model)" = 'SGI-IP24' || fail 'requires an Indy'
cd "$(dirname "$0")"
media=$(pwd -P)
sha256 -c SHA256 >/dev/null || fail 'media checksum mismatch'
state=/var/db/xiri-install
test ! -L "$state" && test "$(stat -f '%u:%Lp' "$state")" = 0:700 && test -d "$state/created" || fail 'missing tracked desktop installation'
shlock -f "$state/lock" -p $$ || fail 'another installer is running'
scratch= staging=
cleanup() {
    test -z "$staging" || rm -rf "$staging"
    test -z "$scratch" || rm -rf "$scratch"
    rm -f "$state/lock"
}
trap cleanup EXIT
trap 'exit 1' HUP INT TERM
test ! -e "$state/removing" || fail 'finish the pending desktop removal'
if pgrep -x 4Dwm >/dev/null || pgrep -x mozilla-bin >/dev/null; then fail 'log out of the IRIX desktop and close Mozilla first'; fi
for work in "$state"/audio-work.*; do
    if test -d "$work" && test ! -L "$work"; then rm -rf "$work"; fi
done
scratch=$(mktemp -d "$state/audio-work.XXXXXX")
pending=$state/upgrading
created=$state/created
origin=$created/.indy-audio-from-v6
mixer=/etc/rc.conf.d/mixerctl
firstboot=$(cat mixer-firstboot)
old=$(cat v6)
new=$(cat v7)
target=$(cat "$side")
browser=no
if test -d "$state/mozilla"; then
    grep -qx enabled "$state/mozilla/phase" || fail 'finish the pending Mozilla operation'
    browser=yes
fi
transaction="indy-audio $side $old $new $browser"
resume=no
if test -e "$pending"; then
    test "$(head -n 1 "$pending")" = "$transaction" || fail 'resume with the same CD and direction'
    resume=yes
fi
receipts="$state/inputs /emul/irix/.xiri-install-inputs /usr/local/share/xiri/fonts/.xiri-install-inputs $state/installed"
current=$(cat "$state/installed")
for receipt in $receipts; do
    test -f "$receipt" && test ! -L "$receipt" || fail "missing receipt $receipt"
    id=$(cat "$receipt")
    test "$id" = "$old" || test "$id" = "$new" || fail "unexpected release or base package in $receipt"
    test "$resume" = yes || test "$id" = "$current" || fail 'inconsistent desktop receipts'
done
if test "$browser" = yes; then
    component=$(cat browser)
    id=$(cat "$state/mozilla/identity")
    test "$id" = "$old $component" || test "$id" = "$new $component" || fail 'unexpected browser receipt'
    test "$resume" = yes || test "$id" = "$current $component" || fail 'inconsistent browser receipt'
fi
if test "$resume" = no && test "$side" = v6 && test "$current" = "$new"; then
    test -f "$origin" && test "$(cat "$origin")" = "$old" ||
        fail 'rollback requires an Indy previously upgraded from v6 with this CD'
fi
if test "$resume" = no && test "$current" = "$target"; then
    echo "The $side generation is already installed."
    exit 0
fi
exists() { test -e "$1" || test -L "$1"; }
matches() {
    case "$2" in
    -) ! exists "$1";;
    link) test -L "$1" && test "$(readlink "$1")" = "$3";;
    *) test -f "$1" && test ! -L "$1" && test "$(stat -f '%u:%g:%Mp%03Lp' "$1")" = "0:0:$2" || return 1
       observed=$(sha256 -q "$1")
       test "$observed" = "$3" || { test "$1" = "$mixer" && test "$observed" = "$firstboot"; };;
    esac
}
# Record directory and file ownership decisions before modifying any live path.
# A durable plan also distinguishes our additions from identical site files.
echo "$transaction" > "$scratch/plan"
while read -r dir; do
    marker="$created$dir/.audio-directory"
    if exists "$dir"; then
        test -d "$dir" && test ! -L "$dir" || fail "unexpected directory entry $dir"
    elif test "$side" = v7; then
        echo "mkdir|$dir" >> "$scratch/plan"
    fi
    if test "$side" = v6 && test -d "$marker"; then echo "rmdir|$dir" >> "$scratch/plan"; fi
done <parents
if test "$resume" = no; then
    while IFS='|' read -r path a av b bv; do
        action=write
        if test "$side" = v7; then
            if test "$a" = - && exists "$path"; then
                if test "$path" = /etc/rc.conf.d/mixerctl && test -f "$path" && test ! -L "$path"; then continue; fi
                matches "$path" "$b" "$bv" || fail "occupied path $path"
                continue
            fi
            matches "$path" "$a" "$av" || fail "local change at $path"
            if test "$a" = -; then action=add; fi
        else
            if test "$a" = - && test ! -d "$created$path"; then continue; fi
            if test "$a" = -; then action=remove; fi
            if ! matches "$path" "$b" "$bv"; then
                if test "$path" = /etc/rc.conf.d/mixerctl; then action=keep; else fail "local change at $path"; fi
            fi
        fi
        echo "$action|$path|$a|$av|$b|$bv" >> "$scratch/plan"
    done < changes
    mv "$scratch/plan" "$pending"
    sync
fi
# Validate all outstanding writes on a retry before continuing the transaction.
sed '1d' "$pending" > "$scratch/steps"
while IFS='|' read -r action path a av b bv; do
    case "$action" in mkdir|rmdir|keep) continue;; esac
    matches "$path" "$a" "$av" || matches "$path" "$b" "$bv" || fail "unexpected bytes or type at $path"
done < "$scratch/steps"
publish_receipt() {
    staging=$(mktemp -d "${1%/*}/.xiri-audio.XXXXXX")
    cp -p "$1" "$staging/item"
    printf '%s\n' "$2" > "$staging/item"
    mv -f "$staging/item" "$1"
    rmdir "$staging"
    staging=
}
while IFS='|' read -r action path a av b bv; do
    case "$action" in
    mkdir)
        test -d "$path" || mkdir -m 755 "$path"
        mkdir -p "$created$path/.audio-directory"
        continue;;
    rmdir) continue;;
    keep) if test -d "$created$path"; then rmdir "$created$path"; fi; continue;;
    esac
    mode=$b value=$bv
    if test "$side" = v6; then mode=$a value=$av; fi
    if ! matches "$path" "$mode" "$value"; then
        if test "$mode" = -; then
            rm "$path"
        else
            if test "$path" = "$mixer" && test "$action" = add; then
                value=$firstboot
                printf '%s\n' "$firstboot" >"$scratch/mixer-stamp"
                mv "$scratch/mixer-stamp" "$created/.indy-audio-mixer"
            fi
            staging=$(mktemp -d "${path%/*}/.xiri-audio.XXXXXX")
            if test "$mode" = link; then ln -s "$value" "$staging/item"
            else install -o root -g wheel -m "$mode" "$media/files/$value" "$staging/item"; fi
            matches "$staging/item" "$mode" "$value" || fail "bad staged file $path"
            mv -fh "$staging/item" "$path"
            rmdir "$staging"
            staging=
        fi
    fi
    if test "$action" = add; then mkdir -p "$created$path"; fi
    if test "$action" = remove && test -d "$created$path"; then rmdir "$created$path"; fi
done < "$scratch/steps"
# Remove empty directories created by the update, deepest first. A new local
# entry keeps its directory when the audio files are removed.
awk -F '|' '$1=="rmdir" {dirs[++n]=$2} END {while(n) print dirs[n--]}' "$scratch/steps" > "$scratch/dirs"
while read -r dir; do
    if test -d "$dir" && test -z "$(ls -A "$dir")"; then rmdir "$dir"; fi
    if test -d "$created$dir/.audio-directory"; then rmdir "$created$dir/.audio-directory"; fi
done < "$scratch/dirs"
if test "$side" = v7; then
    printf '%s\n' "$old" >"$scratch/origin"
    mv "$scratch/origin" "$origin"
fi
if test "$browser" = yes; then publish_receipt "$state/mozilla/identity" "$target $component"; fi
for receipt in $receipts; do publish_receipt "$receipt" "$target"; done
if test "$side" = v6; then rm -f "$origin" "$created/.indy-audio-mixer"; fi
sync
rm "$pending"
echo "Installed $side. Reboot the Indy to activate its kernel and audio services."
