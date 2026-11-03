#!/bin/sh
# The tested application and its children are owned by session-guard.
set -eu
out=$1
shift
printf '%s\n' "$$" >"$out/app.pid"
exec >"$out/stdout" 2>"$out/stderr"
exec /emul/irix/bin/sh -c 'exec "$@"' xiri-catalog "$@"
