#!/bin/sh
set -eu
job=$(cd "$1" && pwd)
cd "${HOME:?Desktop session needs a home directory.}"
# Original control panels save X server settings as commands, independently
# of Xt resources and 4Dwm's saved windows. Replay them after the session's
# initial xset defaults, inside the user's supervised process group.
panels="$HOME/.desktop-$(hostname)/panelsession"
if test -r "$panels"; then
    # Keyboard also writes SGI repeat timing when its unavailable controls
    # report zero. Xorg has no -art/-ari options; retain its native timing.
    sed -e 's|^/usr/bin/X11/xset -art[[:space:]].*|# Xiri: SGI repeat timing requires XSGI-Misc.|' \
        -e 's|^/usr/bin/X11/xset\([[:space:]]\)|/usr/X11R7/bin/xset\1|' \
        -e 's|^/usr/bin/X11/xmodmap\([[:space:]]\)|/usr/X11R7/bin/xmodmap\1|' \
        "$panels" >"$job/panelsession"
    if . "$job/panelsession" >"$job/panelsession.out" 2>"$job/panelsession.err"; then
        :
    else
        echo 'Some saved panel commands failed; see panelsession.err.' >&2
    fi
fi
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
if test "${XIRI_DROP_BRIDGE:-yes}" = yes; then
    observe drop-bridge /usr/local/libexec/xiri/drop-bridge &
fi
# 4Dwm derives this directory from the display host, display and screen.
# Under xdm our TCP display is normally 127.0.0.1:0, not hostname:0.
display_host=${DISPLAY%%:*}
test -n "$display_host" || display_host=$(hostname)
display_screen=${DISPLAY#*:}
case "$display_screen" in *.*) ;; *) display_screen=$display_screen.0;; esac
saved="$HOME/.desktop-$display_host/$display_screen/4Dwmsession"
restore=no
test ! -f "$saved" || restore=yes
printf 'mode=%s file=%s\n' "$restore" "$saved" >"$job/restore"
observe wm /emul/irix/usr/bin/X11/4Dwm -launch -display "$DISPLAY" \
    -xrm "*configFile: $job/4Dwmrc" \
    -xrm '*SG_useBackgrounds: true' &
tries=0
until /usr/local/libexec/xiri/x11-check ready; do
    tries=$((tries+1))
    if test "$tries" -ge 60 || test -f "$job/wm.exit"; then
        echo '4Dwm did not publish its root-window property.' >&2
        touch "$job/logout"
        exit 1
    fi
    sleep 1
done
tries=0
# A solid background publishes its description but has no backdrop pixmap.
until xprop -display "$DISPLAY" -root _SGI_DESKS_BACKGROUND _SGI_DESKS_BACKGROUND_DESCRIPTION >"$job/backdrop-ready.txt" 2>&1 &&
    grep -Eq 'pixmap id # 0x[1-9a-f][0-9a-f]*|_SGI_DESKS_BACKGROUND_DESCRIPTION\(STRING\) = "-solid ' "$job/backdrop-ready.txt"; do
    tries=$((tries+1))
    if test "$tries" -ge 60 || test -f "$job/wm.exit"; then
        echo '4Dwm did not publish its background; check the saved background and its resources.' >&2
        touch "$job/logout"
        exit 1
    fi
    sleep 1
done
observe background /emul/irix/usr/sbin/fm -b &
observe toolchest /emul/irix/usr/bin/X11/toolchest -display "$DISPLAY" \
    -geometry +10+10 \
    /usr/local/share/xiri/toolchest.chestrc &
# Toolchest and fm -b are desktop services, not restorable applications.
# Seed application windows only when there is no managed saved session.
if test "$restore" = no || ! /emul/irix/usr/bin/X11/tellwm -t end_session; then
    observe winterm /bin/sh /emul/irix/usr/sbin/winterm -name winterm \
    -title winterm -geometry 80x24+10+180 \
    -e /usr/libexec/xiri-shell &
    observe xclock /emul/irix/usr/bin/X11/xclock -display "$DISPLAY" \
    -update 1 -geometry 180x180+820+20 -bg gray -fg black -bd black -hd black -hl black &
    observe iconcatalog /emul/irix/usr/sbin/iconcatalog -geometry 600x300+400+450 &
fi
wait
