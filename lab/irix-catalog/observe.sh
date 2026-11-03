#!/bin/sh
# Run as xiritest, with the authenticated desktop's DISPLAY/XAUTHORITY.
set -u
id=$1
shift
out="$HOME/.xiri-catalog/$id"
mkdir -p "$out"
cd "$HOME" || exit 2
umask 077
ulimit -c 0
ulimit -f 2048
export PATH=/bin:/usr/bin:/usr/X11R7/bin:/emul/irix/usr/bin:/emul/irix/usr/bin/X11:/emul/irix/usr/sbin:/emul/irix/usr/freeware/bin
export LANG=C LC_ALL=C TZ=UTC0
export XIRI_SESSION_STOP_FILE="$out/stop"
export WINTERM='/emul/irix/usr/sbin/xwsh -name winterm'
export MWMSHELL=/usr/local/libexec/xiri/command-shell
snapshot()
{
    /tmp/xiri-catalog/windows >"$out/$1.windows" 2>"$out/$1.windows.err"
    printf '%s\n' "$?" >"$out/$1.windows.status"
    # A client can hold the X server while awaiting input. The bounded helper
    # must not prevent process sampling or the owned launch's timed cleanup.
    ps -axww -o pid,ppid,uid,stat,time,pcpu,args >"$out/$1.ps"
}
snapshot before
test "$(cat "$out/before.windows.status")" = 0 || exit 2
printf '%s\n' "$@" >"$out/argv"
(
    /tmp/xiri-catalog/app-guard 45000 /bin/sh /tmp/xiri-catalog/app.sh "$out" "$@" >"$out/guard" 2>"$out/guard.err"
    printf '%s\n' "$?" >"$out/guard.status"
) </dev/null &
owner=$!
n=0
while test "$n" -lt 40 && test ! -f "$out/guard.status"; do
    sleep 1
    n=$((n+1))
    case "$n" in 3|15|35) snapshot "$n";; esac
done
snapshot last
# Observation timeout is a bounded test stop, never a normal application exit.
test -f "$out/guard.status" || touch "$out/stop"
wait "$owner"
snapshot after
printf 'CASE %s\n' "$id"
cat "$out/guard"
cat "$out/guard.err"
grep -q 'absent=1 valid=1' "$out/guard" || exit 2
