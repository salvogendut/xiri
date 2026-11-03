#!/bin/sh
set -eu
cd "$1"
guard=/usr/local/libexec/xiri/session-guard
wait_file()
{
    tries=0
    while test ! -s "$1"; do
        tries=$((tries+1)); test "$tries" -lt 30
        sleep 1
    done
}
check()
{
    grep 'absent=1 valid=1' "$1.log"
    if test -f "$1.pids"; then
        while read pid; do
            if kill -0 "$pid" 2>/dev/null; then
                # Orphans can briefly be init-owned zombies, already dead.
                ps -p "$pid" -o stat= | grep '^Z' >/dev/null || exit 1
            fi
        done <"$1.pids"
    fi
}
# A separate shell of the same user must survive every guard invocation.
/bin/sh -c 'echo $$ >sentinel.pid; while :; do echo alive >sentinel.heartbeat; sleep 1; done' &
sentinel=$!
trap 'kill "$sentinel" 2>/dev/null || :; wait "$sentinel" 2>/dev/null || :' EXIT
for mode in hold escape live-burst; do
    "$guard" 1200 ./descendants "$mode" "$mode.pids" >"$mode.log" 2>&1
    check "$mode"; kill -0 "$sentinel"
done
grep 'tracked=25 ' live-burst.log
test "$(wc -l <live-burst.pids | tr -d ' ')" = 25
"$guard" 5000 ./descendants burst burst.pids >burst.log 2>&1
check burst; grep 'tracked=49 ' burst.log; kill -0 "$sentinel"
set +e
"$guard" 0 ./descendants fail fail.pids >fail.log 2>&1
rc=$?
set -e
test "$rc" = 7; check fail; kill -0 "$sentinel"
set +e
"$guard" 0 ./missing-command >exec-fail.log 2>&1
rc=$?
set -e
test "$rc" = 126; check exec-fail; kill -0 "$sentinel"
XIRI_SESSION_STOP_FILE="$PWD/logout-request" "$guard" 0 ./descendants escape logout.pids >logout.log 2>&1 &
supervisor=$!
wait_file logout.pids
touch logout-request; wait "$supervisor"; check logout; kill -0 "$sentinel"
"$guard" 0 ./descendants escape signal.pids >signal.log 2>&1 &
supervisor=$!
wait_file signal.pids
kill -TERM "$supervisor"; wait "$supervisor"; check signal; kill -0 "$sentinel"
echo SESSION_GUARD_TESTS_OK
