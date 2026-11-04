#!/bin/sh
# Exercise the catalog's original native detached-child controls repeatedly.
set -eu
cd "$1"
count=$2
i=1
while test "$i" -le "$count"; do
    echo "CHILD_BEGIN iteration=$i mode=normal"
    if ./app-guard 10000 ./guard-control >"child-$i-normal.log" 2>&1; then
        rc=0
    else
        rc=$?
    fi
    cat "child-$i-normal.log"
    test "$rc" = 37
    grep -q CATALOG_NATIVE_CHILD_FINISHED "child-$i-normal.log"
    grep -q 'absent=1 valid=1 .*remaining=0 ' "child-$i-normal.log"
    echo "CHILD_END iteration=$i mode=normal rc=$rc"
    echo "CHILD_BEGIN iteration=$i mode=timeout"
    ./app-guard 1000 ./guard-control linger >"child-$i-timeout.log" 2>&1
    cat "child-$i-timeout.log"
    grep -q 'absent=1 valid=1 .*remaining=0 reason=timeout ' "child-$i-timeout.log"
    echo "CHILD_END iteration=$i mode=timeout rc=0"
    i=$((i+1))
done
echo "CHILD_PASS iterations=$count launches=$((count*2))"
