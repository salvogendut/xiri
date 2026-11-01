#!/bin/sh
# Native supervisor owns UID 1234 and reaps this entire test session.
set -eu
cd /tmp/xiri-import/job
observe()
{
    name=$1
    shift
    "$@" >"$name.out" 2>"$name.err" &
    child=$!
    printf '%s\n' "$child" >"$name.pid"
    if wait "$child"; then status=0; else status=$?; fi
    printf '%s\n' "$status" >"$name.exit"
}
observe wm /emul/irix/usr/bin/X11/4Dwm -display "$DISPLAY" \
    -xrm '*SG_manageSession: false' -xrm '*SG_autoSave: false' \
    -xrm '*background: #aaaaaa' -xrm '*activeBackground: #c5c1aa' &
sleep 4
observe xmahjongg /emul/irix/usr/freeware/bin/xmahjongg &
observe iconcatalog /emul/irix/usr/sbin/iconcatalog -geometry 700x330+300+420 &
wait
