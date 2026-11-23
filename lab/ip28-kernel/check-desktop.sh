#!/bin/sh
# Native IMPACT server, existing service/session runtime and imported desktop.
set -eu
export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin
ulimit -c 0
# A single-user boot also skips mountall and cleanvar. Discard the inherited
# readiness marker before preparing this guest's newly mounted PTY namespace.
mount -a
rm -f /var/run/xiri-pty-ready
# Single-user boot has not run rc.d/network; FAM and X use loopback.
ifconfig lo0 inet 127.0.0.1 up
ifconfig -w 20
( . /etc/rc.conf; hostname "${hostname:-xiri-ip28}" )
mkdir -p /var/tmp/ip28-desktop
cd /var/tmp/ip28-desktop
modstat | grep '^compat_irix_o32 ' >/dev/null || modload /cdrom/compat_irix_o32.kmod
# Preserve the qualified image's font and input configuration.
cp /usr/local/share/xiri/xorg.conf xorg.before
sed 's/Driver "newport"/Driver "wsfb"/' xorg.before >/usr/local/share/xiri/xorg.conf
grep 'Driver "wsfb"' /usr/local/share/xiri/xorg.conf
module_dir=$(sysctl -n kern.module.path)/compat_irix_o32
mkdir -p "$module_dir"
install -m 444 /cdrom/compat_irix_o32.kmod "$module_dir/compat_irix_o32.kmod"
cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib \
    -Wl,-rpath,/usr/X11R7/lib /cdrom/type-ready.c -lX11 -lXtst -o type
XIRI_SESSION_MS=300000 xiri-desktop >desktop.log 2>&1 &
echo $! >desktop-pid
tries=0
until grep -q 'Logs: ' desktop.log 2>/dev/null; do
    kill -0 "$(cat desktop-pid)" || { cat desktop.log; exit 1; }
    tries=$((tries + 1)); test "$tries" -lt "${XIRI_DESKTOP_START_TIMEOUT:-30}" || { cat desktop.log; ps -ax -o pid,ppid,comm,args; exit 1; }
    sleep 1
done
job=$(sed -n 's/.*Logs: //p' desktop.log | head -1)
printf '%s\n' "$job" >job
trap 'rc=$?; if test "$rc" -ne 0; then cat desktop.log "$job/identity" "$job/handoff"; ps -ax -o pid,ppid,uid,comm; ls -l "$job"/ip28-*; cat "$job"/ip28-*; fi' EXIT
export DISPLAY=127.0.0.1:0 XAUTHORITY="$job/Xauthority"
tries=0
until xwininfo -name winterm >winterm.txt 2>/dev/null &&
    xwininfo -root -tree >windows.txt 2>/dev/null && grep -qi 'iconcatalog\|Icon Catalog\|of 18' windows.txt; do
    kill -0 "$(cat desktop-pid)" || { cat desktop.log "$job"/*.err; exit 1; }
    tries=$((tries + 1)); test "$tries" -lt 90 || { cat desktop.log "$job"/*.err; exit 1; }
    sleep 1
done
tries=0
until test -s "$job/handoff"; do
    tries=$((tries + 1)); test "$tries" -lt 30
    sleep 1
done
shell_pid=$(sed -n 's/^NATIVE_HANDOFF pid=\([0-9][0-9]*\).*/\1/p' "$job/handoff")
test -n "$shell_pid"
tries=0
until ps -p "$shell_pid" -o comm= | grep -Eq '^[[:space:]]*sh[[:space:]]*$'; do
    tries=$((tries + 1)); test "$tries" -lt 30
    sleep 1
done
# Let restored clients finish mapping before selecting the terminal's focus.
sleep 3
./type "$DISPLAY" winterm 'echo XIRI_IP28_WINTERM_OK; pwd | tee "$XIRI_SESSION_DIR/ip28-home"; id -u | tee "$XIRI_SESSION_DIR/ip28-uid"
'
tries=0
until test -s "$job/ip28-home" && test -s "$job/ip28-uid"; do
    tries=$((tries + 1)); test "$tries" -lt 20
    sleep 1
done
test "$(cat "$job/ip28-home")" = /usr/people/xiritest
test "$(cat "$job/ip28-uid")" = 1234
cat "$job/identity" "$job/ip28-home" "$job/ip28-uid"
xwininfo -root -tree
sleep 5
./type "$DISPLAY" winterm ''
sleep 1
echo XIRI_IP28_DESKTOP_READY
