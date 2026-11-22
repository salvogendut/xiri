#!/bin/sh
# Source this in the serial administrative shell after xdm login.
set -e
job=$(sed -n 's/.*Logs: //p' /usr/people/xiritest/.xsession-errors | head -1)
XAUTHORITY=$(sed -n 's/.* authority=//p' "$job/identity")
test "$XAUTHORITY" != default || XAUTHORITY=/usr/people/xiritest/.Xauthority
export DISPLAY=127.0.0.1:0 XAUTHORITY
n=0
until test -s "$job/handoff" && /usr/local/libexec/xiri/x11-check ready && xwininfo -name winterm >/dev/null 2>&1; do
    n=$((n+1)); test "$n" -lt 150 || return 1; sleep 1
done
dir=/var/tmp/xiri-desktop-latency
mkdir "$dir"
cd "$dir"
cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/desktop-latency.c -lX11 -lXtst -o bench
cc -O2 -I/usr/X11R7/include -L/usr/X11R7/lib -Wl,-rpath,/usr/X11R7/lib /cdrom/place-window.c -lX11 -o place
./place winterm 170 160 640 300
sleep 2
id=$(xwininfo -name winterm | awk '/Window id:/ {print $4;exit}')
tty=$(sed -n 's/.* tty=\([^ ]*\).*/\1/p' "$job/handoff" | head -1)
test -c "$tty"
mkfifo input
exec 7<>input
./bench "$id" "$tty" <input 7>&- >bench.log 2>&1 &
bench_pid=$!
n=0
until grep '^READY ' bench.log; do
    kill -0 "$bench_pid" || return 1
    n=$((n+1)); test "$n" -lt 60 || return 1; sleep 1
done
set +e
