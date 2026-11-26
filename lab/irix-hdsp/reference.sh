#!/bin/sh
# Run only on a private copy of an installed IRIX disk with audio enabled.
exec > /tmp/xiri-hdsp-reference 2>&1
PATH=/usr/bsd:/usr/sbin:/usr/bin:/usr/bin/X11:/sbin
export PATH
DISPLAY=:0
export DISPLAY
uname -R
hinv -c audio
ls -l /dev/hdsp/hdsp0master /dev/hdsp/hdsp0events
chmod 700 /tmp/hdsp-query
/tmp/hdsp-query || exit 1
# Both the graphical Indy and the serial O2 donor can exercise this client.
sample=/usr/share/data/sounds/soundscheme/soundfiles/emptyDumpster.aiff
if test -x /usr/sbin/sfplay && test -r "$sample"; then
    trace=/tmp/xiri-sfplay.par
    echo 'BEGIN sfplay'
    par -s -SS -i -t 15 /usr/sbin/sfplay "$sample" > "$trace" 2>&1
    egrep '"/dev/hdsp/|MAP_SHARED|ioctl\([0-9]+, 0x|munmap\(|exit\(' "$trace"
    echo 'END sfplay'
fi
if test "${1-}" = --query-only; then
    /tmp/hdsp-query --mute-test || exit 1
    echo 'HDSP reference complete'
    exit 0
fi
/tmp/hdsp-query --event-test || exit 1
/tmp/hdsp-query --mute-test || exit 1
for program in dtSounds audiopanel; do
    trace=/tmp/xiri-${program}.par
    par -s -i -SS -t 18 /usr/sbin/"$program" > "$trace" 2>&1 &
    tracer=$!
    sleep 22
    echo "BEGIN $program"
    xwininfo -root -tree | egrep -i 'sound|audio|apanel' | sed -n '1,12p'
    egrep '"/dev/hdsp/|ioctl\([0-9]+, 0x(1[89abc]|6[5-9a-f]|7[0-6]),' "$trace" | sed -n '1,240p'
    tail -4 "$trace"
    kill "$tracer" 2>/dev/null
    echo "END $program"
done
echo 'HDSP reference complete'
