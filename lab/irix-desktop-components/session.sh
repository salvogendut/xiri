#!/bin/sh
# The native supervisor owns this reserved-UID session and all descendants.
set -eu
cd /tmp/xiri-wm/job
/emul/irix/usr/bin/X11/4Dwm -display "$DISPLAY" \
  -xrm '*SG_manageSession: false' -xrm '*SG_autoSave: false' \
  -xrm '*background: #aaaaaa' -xrm '*activeBackground: #c5c1aa' >wm.out 2>wm.err &
wm_pid=$!
while test ! -f launch-clients; do sleep 1; done
/emul/irix/usr/bin/X11/toolchest -display "$DISPLAY" -geometry +10+10 \
  -xrm '*background: #c1c1c1' -xrm '*decalForeground: #555555' >toolchest.out 2>toolchest.err &
/bin/sh /emul/irix/usr/sbin/winterm -name winterm -title winterm \
  -geometry 80x24+10+180 -e /usr/libexec/xiri-shell /tmp/xiri-wm/job/handoff \
  >winterm.out 2>winterm.err &

# Preserve the terminal interaction check before starting additional clients.
while test ! -f launch-components; do sleep 1; done
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
observe bgicons /emul/irix/usr/sbin/bgicons -overlay &
observe fm-background /emul/irix/usr/sbin/fm -b &
observe iconcatalog /emul/irix/usr/sbin/iconcatalog -geometry 420x280+570+400 &
observe fm-home /emul/irix/usr/sbin/fm "$HOME" &
wait "$wm_pid"
