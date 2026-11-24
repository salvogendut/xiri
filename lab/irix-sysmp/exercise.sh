#!/bin/sh
# Run in a writable directory with meter-n32, a built workload and a mapped xosview.
set -eu
window=${1:?Usage: sh exercise.sh X-window-id}
sample() {
    ./meter-n32 >"$1.meter"
    vmstat -s >"$1.vmstat"
    xwd -silent -id "$window" -out "$1.xwd"
}
sample idle1
sleep 6
sample idle2
./workload &
worker=$!
trap 'kill "$worker" 2>/dev/null || :' EXIT
sleep 5
kill -0 "$worker"
sample busy1
sleep 6
kill -0 "$worker"
sample busy2
wait "$worker"
trap - EXIT
sleep 5
sample released
