#!/bin/sh
set -eu
export PATH=/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin DISPLAY=:0
ulimit -c 0
mkdir -p /var/tmp/ip28-xorg
cd /var/tmp/ip28-xorg
cp /cdrom/xorg.conf /cdrom/probe.c .
wsconscfg -f /dev/ttyEcfg 0 2>/dev/null || test -c /dev/ttyE0
cc -O2 -Wall -Wextra -Werror /cdrom/framebuffer.c -o framebuffer
./framebuffer
cc -O2 -Wall -Wextra -I/usr/X11R7/include -L/usr/X11R7/lib \
    -Wl,-rpath,/usr/X11R7/lib probe.c -lX11 -o probe
Xorg :0 -config /var/tmp/ip28-xorg/xorg.conf -nolisten tcp -noreset >server.log 2>&1 &
echo $! >xpid
tries=0
until xdpyinfo >display.txt 2>/dev/null; do
    kill -0 "$(cat xpid)" || { cat server.log; exit 1; }
    tries=$((tries + 1)); test "$tries" -lt 45 || { cat server.log; exit 1; }
    sleep 1
done
grep 'dimensions:.*1280x1024' display.txt
xset s off
xset -dpms || true
./probe >probe.log 2>&1 &
echo $! >probe-pid
tries=0
until grep -q PIXELS_PASS probe.log; do
    kill -0 "$(cat probe-pid)" || { cat probe.log; exit 1; }
    tries=$((tries + 1)); test "$tries" -lt 45 || { cat probe.log; exit 1; }
    sleep 1
done
cat probe.log
sleep 3
echo XIRI_IP28_XORG_READY
