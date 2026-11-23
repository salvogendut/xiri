#!/bin/sh
# Run from single-user mode on the qualification disk's private overlay.
set -eu
export PATH=/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin DISPLAY=:0
ulimit -c 0
mount -u -o rw /
work=$(mktemp -d /var/tmp/ip30-xorg.XXXXXX)
cd "$work"
server='' client=''
cleanup() {
    if [ -n "$client" ]; then kill "$client" 2>/dev/null || true; wait "$client" || true; fi
    if [ -n "$server" ]; then kill "$server" 2>/dev/null || true; wait "$server" || true; fi
    cat server.log probe.log 2>/dev/null || true
}
trap cleanup EXIT
cc -O2 -Wall -o framebuffer /cdrom/framebuffer.c
cc -O2 -Wall -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib \
    /cdrom/probe.c -lX11 -o probe
./framebuffer
echo XIRI_START_XORG
Xorg :0 -config /cdrom/xorg.conf -logfile "$work/Xorg.log" -nolisten tcp -noreset >server.log 2>&1 &
server=$!
i=0
until xdpyinfo >display.txt 2>/dev/null; do
    kill -0 "$server" || { cat Xorg.log; exit 1; }
    i=$((i+1)); test "$i" -lt 60 || { cat Xorg.log; exit 1; }; sleep 1
done
grep -E 'dimensions: +1280x1024 pixels' display.txt
xset s off
./probe >probe.log 2>&1 &
client=$!
i=0
until grep -q '^TEXT_PASS$' probe.log && grep -q '^BUTTON_UP 3 ' probe.log; do
    kill -0 "$client"
    i=$((i+1)); test "$i" -lt 180 || exit 1; sleep 1
done
grep -q '^PIXELS_PASS$' probe.log
grep -q '^KEY_UP Return$' probe.log
for b in 1 2 3; do
    grep -q "^BUTTON_DOWN $b " probe.log
    grep -q "^BUTTON_UP $b " probe.log
done
# The probe warps to (100,360) on startup. Require real motion from there.
awk '$1=="MOTION" && ($2!=100 || $3!=360) { moved=1 } END { exit !moved }' probe.log
