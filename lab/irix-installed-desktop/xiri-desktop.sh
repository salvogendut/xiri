#!/bin/sh
# Development-image launcher: native X and a dedicated UID 1234 client session.
set -eu
test "$(id -u)" = 0 || { echo 'Run xiri-desktop as root in the prepared guest.' >&2; exit 1; }
export PATH=/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin
base=/usr/local/libexec/xiri
share=/usr/local/share/xiri
server=${1:-newport}
case "$server" in newport) display=0;; --xvfb) display=98;; *) echo 'Usage: xiri-desktop [newport|--xvfb]' >&2; exit 2;; esac
duration=${XIRI_SESSION_MS:-0}
case "$duration" in ''|*[!0-9]*) echo 'XIRI_SESSION_MS must be milliseconds.' >&2; exit 2;; esac
test ! -f "/tmp/.X$display-lock" || { echo "Display $display is already occupied." >&2; exit 1; }
if test ! -f /var/run/xiri-pty-ready; then
    sh "$base/setup-pty.sh"
    touch /var/run/xiri-pty-ready
fi
mkdir -p /var/tmp/xiri-desktop /usr/people/xiritest
chown 1234:1234 /usr/people/xiritest
chmod 700 /usr/people/xiritest
job=$(mktemp -d /var/tmp/xiri-desktop/session.XXXXXX)
chown 1234:1234 "$job"
chmod 700 "$job"
cat >"$job/desktop.env" <<EOF
HOME=/usr/people/xiritest
USER=xiritest
LOGNAME=xiritest
SHELL=/bin/sh
MWMSHELL=/usr/local/libexec/xiri/command-shell
XIRI_SESSION_DIR=$job
DISPLAY=127.0.0.1:$display
LANG=C
LC_ALL=C
TZ=UTC0
PATH=/bin:/usr/bin:/usr/X11R7/bin:/emul/irix/usr/bin:/emul/irix/usr/bin/X11:/emul/irix/usr/sbin:/emul/irix/usr/freeware/bin
WINTERM=/emul/irix/usr/sbin/xwsh -name winterm
PS1=xiri$ 
EOF
chmod 444 "$job/desktop.env"
xpid=
guardpid=
cleanup()
{
    trap - EXIT INT TERM
    if test -n "$guardpid"; then kill -TERM "$guardpid" 2>/dev/null || true; wait "$guardpid" || true; fi
    if test -n "$xpid"; then kill "$xpid" 2>/dev/null || true; wait "$xpid" || true; fi
    echo "Session logs: $job"
}
trap cleanup EXIT
trap 'exit 130' INT TERM
if test "$server" = newport; then
    wsconscfg -f /dev/ttyEcfg 0 2>/dev/null || true
    Xorg :0 -config "$share/xorg.conf" -ac -noreset >"$job/Xorg.log" 2>&1 &
else
    Xvfb :98 -screen 0 1024x768x24 -ac -noreset >"$job/Xvfb.log" 2>&1 &
fi
xpid=$!
tries=0
until xdpyinfo -display "127.0.0.1:$display" >"$job/display.txt" 2>&1; do
    tries=$((tries+1))
    test "$tries" -lt 30 || { cat "$job/display.txt"; exit 1; }
    kill -0 "$xpid"
    sleep 1
done
xset -display "127.0.0.1:$display" +fp "$share/fonts"
xset -display "127.0.0.1:$display" fp rehash
xset -display "127.0.0.1:$display" s off
xset -display "127.0.0.1:$display" -dpms
xset -display "127.0.0.1:$display" s reset
xsetroot -display "127.0.0.1:$display" -solid '#556677'
echo "Xiri desktop on display $display. Press Ctrl-C here to stop. Logs: $job"
"$base/manual-guard" "$duration" "$base/session" "$job/desktop.env" \
    /bin/sh "$base/manual-session.sh" "$job" >"$job/guard.log" 2>&1 &
guardpid=$!
wait "$guardpid"
