#!/bin/sh
# Compile original test sources with the image's own development tools.
set -eu
ulimit -c 0
mkdir -p /tmp/xiri-pty
cd /tmp/xiri-pty
trap 'tar cf /tmp/xiri-pty-results.tar .' 0
/usr/freeware/bin/gcc --version >compiler.txt 2>&1 || true
for abi in n32 32; do
    /usr/freeware/bin/gcc -mabi=$abi -mips3 -O2 -Wall fixture.c -o probe-$abi >build-$abi.txt 2>&1 || {
        echo GCC_FAILED >>build-$abi.txt
        /usr/bin/cc -$abi -mips3 -O2 fixture.c -o probe-$abi >>build-$abi.txt 2>&1 || echo CC_FAILED >>build-$abi.txt
    }
done
printf XIRI_OPEN >regular
mkfifo fifo
chmod 666 regular fifo
ls -l probe-* regular fifo >inputs.txt
: >status.txt
for abi in n32 32; do
    if test ! -x probe-$abi; then continue; fi
    for item in getpty /dev/ptc regular /dev/null fifo; do
        name=`echo "$item" | tr / _`
        for flags in 2 6 130 134; do
            case=$abi-$name-$flags
            /usr/sbin/par -s -SS -t 3 -o "$case.trace" ./probe-$abi "$item" "$flags" >"$case.out" 2>"$case.err" & child=$!
            (sleep 5; kill -9 "$child" 2>/dev/null) & watchdog=$!
            rc=0; wait "$child" || rc=$?
            kill "$watchdog" 2>/dev/null || true
            wait "$watchdog" 2>/dev/null || true
            echo CASE "$case" "$rc" >>status.txt
        done
    done
done
tar cf /tmp/xiri-pty-results.tar .
