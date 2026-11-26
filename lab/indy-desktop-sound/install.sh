#!/bin/sh
# Apply the private release-matched update to an Indy with the power-menu runtime.
set -eu
cd "$(dirname "$0")"
fail() { echo "$*" >&2; exit 1; }
test "$#" = 0 && test "$(id -u)" = 0 || fail 'Run sh install.sh as root.'
sha256 -c SHA256 >/dev/null || fail 'Incorrect update media.'
test "$(awk 'NR == 1 { print $1 }' /var/db/xiri-install/installed)" = "$(cat release)" ||
    fail 'Use the CD that matches this desktop release.'
test "$(audioctl -n name)" = HAL2 && grep -Eq 'Driver[[:space:]]+"newport"' /usr/local/share/xiri/xorg.conf ||
    fail 'An Indy desktop with Newport and HAL2 is required.'
run=/usr/local/libexec/xiri
share=/usr/local/share/xiri
module=/usr/X11R7/lib/modules/extensions/libsgivc.so
conf=/etc/X11/xorg.conf.d/91-xiri-sgivc.conf
sgi=/emul/irix/usr/sbin/ssplay
clients=$run/desktop-clients.sh
base=0e8526125a07e7585ebeb98ea7bd86af529dac5a9b6bc7a06c796feb6ca96491
lock=/var/run/xiri-indy-panels.lock
mkdir "$lock" || fail 'Another Indy panel update is running.'
trap 'rmdir "$lock"' EXIT
trap 'exit 1' HUP INT TERM
check() {
    if test -e "$2" || test -L "$2"; then
        test -f "$2" && test ! -L "$2" && cmp -s "$1" "$2" || fail "Local file differs at $2"
    fi
}
for dir in "$share/sounds" /etc/X11/xorg.conf.d; do
    test ! -L "$dir" || fail "Unexpected directory link at $dir"
done
test -f "$clients" && test ! -L "$clients" || fail "Expected the desktop session launcher."
test "$(sha256 -q "$clients")" = "$base" || cmp -s desktop-clients.sh "$clients" ||
    fail 'Install the shutdown-menu update first, or merge locally edited desktop-clients.sh.'
check desktop-sound "$run/desktop-sound"
check libsgivc.so "$module"
check 91-xiri-sgivc.conf "$conf"
check ssplay "$sgi"
for f in sounds/*; do check "$f" "$share/$f"; done
install -d -m 755 "$share/sounds" /etc/X11/xorg.conf.d
install -r -m 444 libsgivc.so "$module"
install -r -m 444 91-xiri-sgivc.conf "$conf"
install -r -m 555 desktop-sound "$run/desktop-sound"
install -r -m 555 ssplay "$sgi"
for f in sounds/*.pcm sounds/effects; do install -r -m 444 "$f" "$share/$f"; done
install -r -m 555 desktop-clients.sh "$clients"
echo 'Restart xdm or reboot. Set the speaker level in Audio Panel.'
