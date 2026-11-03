#!/bin/sh
# Request cleanup by the supervisor of this development desktop session.
set -eu
job=${XIRI_SESSION_DIR:?Run xiri-logout within a xiri-desktop session.}
test -d "$job" && test -w "$job"
: >"$job/logout"
