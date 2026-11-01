#!/bin/sh
# One reserved-UID job; the native supervisor owns all descendant cleanup.
set -eu
cd /tmp/xiri-wm/job
/emul/irix/usr/bin/X11/4Dwm -display "$DISPLAY" \
  -xrm '*SG_manageSession: false' -xrm '*SG_autoSave: false' \
  -xrm '*background: #aaaaaa' -xrm '*activeBackground: #c5c1aa' >wm.out 2>wm.err &
wm_pid=$!
# Release client startup only after the native movement check has finished.
# This keeps synthetic titlebar input away from concurrently mapping clients.
while test ! -f launch-clients; do sleep 1; done
/emul/irix/usr/bin/X11/toolchest -display "$DISPLAY" -geometry +10+10 \
  -xrm '*background: #c1c1c1' -xrm '*decalForeground: #555555' >toolchest.out 2>toolchest.err &
/bin/sh /emul/irix/usr/sbin/winterm -name winterm -title winterm \
  -geometry 80x24+10+180 -e /usr/libexec/xiri-shell /tmp/xiri-wm/job/handoff \
  >winterm.out 2>winterm.err &
wait "$wm_pid"
