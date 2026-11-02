#!/bin/sh
set -eu
job=$(cd "$1" && pwd)
cd "${HOME:?Desktop session needs a home directory.}"
# The vendor workspace reads Desktop links; the marker selects Dumpster's FTR.
# Seed a new desktop once, preserving later user additions and removals.
if test ! -d "$HOME/Desktop"; then
    mkdir -p "$HOME/Desktop" "$HOME/dumpster"
    touch "$HOME/dumpster/.dumpster"
    ln -s / "$HOME/Desktop/UnixRoot"
    ln -s "$HOME" "$HOME/Desktop/$(id -un)"
    ln -s ../dumpster "$HOME/Desktop/dumpster"
fi
/emul/irix/usr/sbin/bgicons -overlay >"$job/bgicons.out" 2>"$job/bgicons.err"
# Preserve the vendor menus, routing their logout action through our supervisor.
sed 's|/usr/bin/X11/endsession|/usr/local/bin/xiri-logout|g' \
    /emul/irix/usr/lib/X11/system.4Dwmrc >"$job/4Dwmrc"
observe()
{
    name=$1
    shift
    "$@" >"$job/$name.out" 2>"$job/$name.err" &
    child=$!
    printf '%s\n' "$child" >"$job/$name.pid"
    if wait "$child"; then status=0; else status=$?; fi
    printf '%s\n' "$status" >"$job/$name.exit"
}
observe wm /emul/irix/usr/bin/X11/4Dwm -display "$DISPLAY" \
    -xrm "*configFile: $job/4Dwmrc" \
    -xrm '*SG_useBackgrounds: true' \
    -xrm '*Global*backgroundDescription: -bitmap /usr/include/X11/bitmaps/granite -bg #69b5b5 -fg #868686' \
    -xrm '*defaultBackgroundDescription: -bitmap /usr/include/X11/bitmaps/granite -bg #69b5b5 -fg #868686' \
    -xrm '*SG_manageSession: false' -xrm '*SG_autoSave: false' \
    -xrm '*background: #aaaaaa' -xrm '*activeBackground: #c5c1aa' &
tries=0
until xprop -display "$DISPLAY" -root _MOTIF_WM_INFO >"$job/wm-ready.txt" 2>&1 &&
    grep -q ' = ' "$job/wm-ready.txt"; do
    tries=$((tries+1))
    if test "$tries" -ge 60; then
        echo '4Dwm did not publish its root-window property.' >&2
        touch "$job/logout"
        exit 1
    fi
    sleep 1
done
tries=0
until xprop -display "$DISPLAY" -root _SGI_DESKS_BACKGROUND >"$job/backdrop-ready.txt" 2>&1 &&
    grep -Eq 'pixmap id # 0x[1-9a-f][0-9a-f]*' "$job/backdrop-ready.txt"; do
    tries=$((tries+1))
    if test "$tries" -ge 60; then
        echo '4Dwm did not publish its backdrop pixmap; check the granite resource.' >&2
        touch "$job/logout"
        exit 1
    fi
    sleep 1
done
observe background /emul/irix/usr/sbin/fm -b &
observe toolchest /emul/irix/usr/bin/X11/toolchest -display "$DISPLAY" \
    -geometry +10+10 -xrm '*background: #c1c1c1' -xrm '*decalForeground: #555555' \
    /usr/local/share/xiri/toolchest.chestrc &
observe winterm /bin/sh /emul/irix/usr/sbin/winterm -name winterm \
    -title winterm -geometry 80x24+10+180 \
    -e /usr/libexec/xiri-shell "$job/handoff" &
observe xclock /emul/irix/usr/bin/X11/xclock -display "$DISPLAY" \
    -update 1 -geometry 180x180+820+20 -bg gray -fg black -bd black -hd black -hl black &
observe iconcatalog /emul/irix/usr/sbin/iconcatalog -geometry 600x300+400+450 &
observe xmahjongg /emul/irix/usr/freeware/bin/xmahjongg &
wait
