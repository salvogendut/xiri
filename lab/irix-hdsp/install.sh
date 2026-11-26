#!/bin/sh
# Install or restore the native Indy v6 audio adapter. Activate at next boot.
set -eu
cd "$(dirname "$0")"
fail() { echo "$*" >&2; exit 1; }
digest() { test -f "$1" && test ! -L "$1" && sha256 -q "$1"; }
case $#:${1:-install} in 0:install|1:--restore) ;; *) fail 'Usage: sh install.sh [--restore]' ;; esac
test "$(id -u)" = 0 || fail 'Run as root.'
test "$(uname -m):$(uname -r)" = 'sgimips:11.99.11' || fail 'Indy v6 NetBSD/sgimips 11.99.11 required.'
module=$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod
sha256 -c SHA256 || fail 'Incorrect files on CD.'
lock=/var/run/xiri-hdsp-install.lock
mkdir "$lock" || fail "Another installation holds $lock"
tmp=
trap 'test -z "$tmp" || rm -f "$tmp"; rmdir "$lock"' EXIT
trap 'exit 1' HUP INT TERM

# Validate all three before changing any. A retry can finish a partially
# completed install or restore. Each component is replaced by rename.
stock_digest() {
    case $1 in
    /netbsd) echo e989c42d3469f5d59e2ec759fdb3d7f54d7a893acdc326f6f3a3c4487f19fd22 ;;
    /netbsd.boot) echo a4af41c6d0c83f11f0180fce5cb0424a7a5ea7c3aa898bda9bfaf9f3f7b6f5c9 ;;
    "$module") echo 259386c1487ec501f3345e7e677e4ec1b8a1e13b763741e5ec98af70cae77e44 ;;
    esac
}
for path in "$module" /netbsd /netbsd.boot; do
    stock=$(stock_digest "$path")
    new=$(digest "${path##*/}")
    current=$(digest "$path") || fail "Expected a regular file at $path"
    case $current in "$stock"|"$new") ;; *) fail "Installed $path differs from the Indy v6 release." ;; esac
    backup=$path.pre-hdsp
    if test -e "$backup" || test -L "$backup" || test "$current" = "$new"; then
        test "$(digest "$backup")" = "$stock" || fail "Incorrect or missing backup of $path."
    fi
done
backup=$module.pre-hdsp
dir=/emul/irix/dev/hdsp
master=$dir/hdsp0master
events=$dir/hdsp0events
service=/etc/rc.d/xiri_hdsp
if test -e "$service" || test -L "$service"; then
    test -f "$backup" && test "$(digest "$service")" = "$(digest xiri_hdsp)" ||
        fail "Existing service at $service is outside this update"
fi
if test -e "$events" || test -L "$events"; then
    test -f "$backup" && test -L "$events" && test "$(readlink "$events")" = /../var/run/xiri-hdsp/events ||
        fail "Existing device at $events is outside this update"
fi
for parent in /emul/irix/dev "$dir"; do
    test ! -L "$parent" || fail "Unexpected directory link at $parent"
done
if test -e "$master" || test -L "$master"; then
    test -f "$backup" && test -L "$master" && test "$(readlink "$master")" = /../dev/audioctl0 ||
        fail "Existing device at $master is outside this update"
fi
if test "${1:-}" != --restore; then
    test "$(audioctl -n name)" = HAL2 || fail 'Enable Indy HAL2 before installation.'
    for path in "$module" /netbsd /netbsd.boot; do
        test -e "$path.pre-hdsp" || ln "$path" "$path.pre-hdsp"
    done
    mkdir -p "$dir"
    test -L "$master" || ln -s /../dev/audioctl0 "$master"
    test -L "$events" || ln -s /../var/run/xiri-hdsp/events "$events"
    test -f "$service" || install -o root -g wheel -m 555 xiri_hdsp "$service"
fi
for path in "$module" /netbsd /netbsd.boot; do
    if test "${1:-}" = --restore; then
        source=$path.pre-hdsp
        wanted=$(stock_digest "$path")
    else
        source=${path##*/}
        wanted=$(digest "$source")
    fi
    test "$(digest "$path")" != "$wanted" || continue
    tmp=$(mktemp "$path.XXXXXXXX")
    install -o root -g wheel -m 444 "$source" "$tmp"
    test "$(digest "$tmp")" = "$wanted" || fail "Staging failed for $path"
    mv -f "$tmp" "$path"
    tmp=
done
if test "${1:-}" = --restore; then
    test ! -L "$master" || rm "$master"
    test ! -L "$events" || rm "$events"
    if test -f "$service"; then
        sh "$service" stop
        rm "$service"
    fi
fi
echo 'The selected kernel and module load at the next boot.'
