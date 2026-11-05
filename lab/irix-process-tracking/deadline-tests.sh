#!/bin/sh
set -u
cd "$1" || exit 90
guard=$2
failed=0
for mode in fast term kill live signal logout leader; do
    ./deadline-case "$guard" ./delay.so "$mode" >"$mode.case" 2>&1
    rc=$?
    printf '%s\n' "$rc" >"$mode.status"
    cat "$mode.case" "$mode.guard" "$mode.trace"
    test "$rc" -eq 0 || failed=1
done
exit "$failed"
