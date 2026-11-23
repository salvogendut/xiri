#!/bin/sh
# Check both the foreground user session and the return to the console.
set -eu
exec 3>&1
export PATH=/usr/local/bin:/usr/X11R7/bin:/bin:/sbin:/usr/bin:/usr/sbin
test "$(sysctl -n hw.model)" = IP30
mount -u -w /
sh /cdrom/check-module.sh
state=/var/tmp/ip28-desktop
record=$(mktemp /var/tmp/ip30-desktop.XXXXXX)
rm -f "$state/job"
finish()
{
    if [ -s "$state/job" ]; then
        job=$(cat "$state/job")
        touch "$job/logout"
        i=0
        while pgrep -x Xorg >/dev/null && [ "$i" -lt 90 ]; do
            i=$((i+1))
            sleep 1
        done
    fi
    cat "$record" >&3
}
trap finish EXIT
# Prepare the 400 IRIX PTY aliases on the newly mounted QLogic disk.
XIRI_DESKTOP_START_TIMEOUT=180 sh /cdrom/check-desktop.sh >"$record" 2>&1
job=$(cat "$state/job")
export DISPLAY=127.0.0.1:0 XAUTHORITY="$job/Xauthority"
pgrep -u 1234 -f '^/emul/irix/usr/bin/X11/4Dwm( |$)' >>"$record"
xdpyinfo | grep -E 'dimensions: +1280x1024 pixels' >>"$record"
# The first catalog window may exist before the Applications page is mapped.
# Query the live tree again instead of reusing the initial readiness snapshot.
i=0
while :; do
    xwininfo -root -tree >"$state/octane-windows"
    if grep -F '"4Dwm" "4DWm"' "$state/octane-windows" >>"$record" &&
       grep -F '"toolchest" "Toolchest"' "$state/octane-windows" >>"$record" &&
       grep -F '"IconCatalog" "IconCatalog"' "$state/octane-windows" >>"$record"; then
        break
    fi
    i=$((i+1)); [ "$i" -lt 45 ]; sleep 1
done
"$state/type" "$DISPLAY" winterm 'clear; /sbin/sysctl hw.model; id -un; pwd; touch "$XIRI_SESSION_DIR/ip30-visible"
'
i=0
until [ -f "$job/ip30-visible" ]; do
    i=$((i+1)); [ "$i" -lt 30 ]; sleep 1
done
sleep 2
# Userland writes to /dev/console are discarded in wsdisplay graphics mode.
printf '\nOCTANE_FRAME_READY\n' >/dev/dtyC0
i=0
until [ -f "$job/ip30-captured" ]; do
    i=$((i+1)); [ "$i" -lt 90 ]; sleep 1
done
finish
trap - EXIT
if pgrep -x Xorg || pgrep -u 1234 -x 4Dwm; then exit 1; fi
echo OCTANE_LOGOUT_OK
