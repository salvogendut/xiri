#!/bin/sh
set -eu
cd "$1"
# Preserve the vendor menus, routing their logout action through our supervisor.
sed 's|/usr/bin/X11/endsession|/usr/local/bin/xiri-logout|g' \
    /emul/irix/usr/lib/X11/system.4Dwmrc >"$PWD/4Dwmrc"
observe()
{
    name=$1
    shift
    "$@" >"$name.out" 2>"$name.err" &
    child=$!
    printf '%s\n' "$child" >"$name.pid"
    if wait "$child"; then status=0; else status=$?; fi
    printf '%s\n' "$status" >"$name.exit"
}
observe wm /emul/irix/usr/bin/X11/4Dwm -display "$DISPLAY" \
    -xrm "*configFile: $PWD/4Dwmrc" \
    -xrm '*SG_manageSession: false' -xrm '*SG_autoSave: false' \
    -xrm '*background: #aaaaaa' -xrm '*activeBackground: #c5c1aa' &
tries=0
until xprop -display "$DISPLAY" -root _MOTIF_WM_INFO >wm-ready.txt 2>&1 &&
    grep -q ' = ' wm-ready.txt; do
    tries=$((tries+1))
    if test "$tries" -ge 60; then
        echo '4Dwm did not publish its root-window property.' >&2
        touch "$PWD/logout"
        exit 1
    fi
    sleep 1
done
observe toolchest /emul/irix/usr/bin/X11/toolchest -display "$DISPLAY" \
    -geometry +10+10 -xrm '*background: #c1c1c1' -xrm '*decalForeground: #555555' \
    /usr/local/share/xiri/toolchest.chestrc &
observe winterm /bin/sh /emul/irix/usr/sbin/winterm -name winterm \
    -title winterm -geometry 80x24+10+180 \
    -e /usr/libexec/xiri-shell "$PWD/handoff" &
observe xclock /emul/irix/usr/bin/X11/xclock -display "$DISPLAY" \
    -update 1 -geometry 180x180+820+20 -bg gray -fg black -bd black -hd black -hl black &
observe iconcatalog /emul/irix/usr/sbin/iconcatalog -geometry 600x300+400+450 &
observe xmahjongg /emul/irix/usr/freeware/bin/xmahjongg &
wait
