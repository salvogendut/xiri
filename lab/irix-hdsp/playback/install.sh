#!/bin/sh
# Apply to an Indy v6 guest which has the qualified HDSP kernel and module.
set -eu
cd "$(dirname "$0")"
fail() { echo "$*" >&2; exit 1; }
test "$#" = 0 && test "$(id -u)" = 0 || fail 'Run sh install.sh as root.'
sha256 -c SHA256 >/dev/null || fail 'Incorrect update media.'
test "$(uname -m):$(uname -r)" = sgimips:11.99.11 || fail 'Expected Indy v6 NetBSD.'
test "$(awk 'NR==1 {print $1}' /var/db/xiri-install/installed)" = "$(cat release)" ||
    fail 'Use the CD for the installed IRIX release.'
test "$(audioctl -n name)" = HAL2 && test -f /etc/rc.d/xiri_hdsp ||
    fail 'Install and boot the HDSP update on an Indy with HAL2.'
module=$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod
base=1d42db0f2d867a8218f54773e6243fc4c1c8706bfcaf0854520e39d4f76fa716
desired=$(sha256 -q compat_irix_o32.kmod)
case $(sha256 -q "$module") in "$base"|"$desired") ;; *) fail "Unexpected installed $module." ;; esac
test ! -L "$module" || fail "Unexpected module link."
lock=/var/run/xiri-pcm-install.lock
mkdir "$lock" || fail 'Another playback update is running.'
trap 'rmdir "$lock"' EXIT
trap 'exit 1' HUP INT TERM
sgi=/emul/irix
port=$sgi/dev/hdsp/hdsp0r2
service=/etc/rc.d/xiri_pcm
case $(readlink "$port" || :) in /../var/run/xiri-hdsp/pcm) ;; '')
    test ! -e "$port" || fail "Existing $port." ;; *) fail "Unexpected link at $port." ;; esac
check() {
    if test -e "$2" || test -L "$2"; then
        test -f "$2" && cmp -s "$1" "$2" || fail "Existing $2 differs from the CD."
    fi
}
check sfplay "$sgi/usr/sbin/sfplay"
check xiri_pcm "$service"
for f in lib32/*.so lib32/libC.so.2 lib32/dmedia/audioconverters/*.so; do check "$f" "$sgi/usr/$f"; done
install -d -m 755 "$sgi/usr/lib32/dmedia/audioconverters"
for f in lib32/*.so lib32/libC.so.2 lib32/dmedia/audioconverters/*.so; do
    test -e "$sgi/usr/$f" || install -m 555 "$f" "$sgi/usr/$f"
done
test -e "$sgi/usr/sbin/sfplay" || install -m 555 sfplay "$sgi/usr/sbin/sfplay"
test -f "$service" || install -m 555 xiri_pcm "$service"
test -L "$port" || ln -s /../var/run/xiri-hdsp/pcm "$port"
install -r -m 444 compat_irix_o32.kmod "$module"
echo 'Reboot to load the playback module and create the IRIX playback port.'
