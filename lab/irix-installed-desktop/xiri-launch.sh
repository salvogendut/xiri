#!/bin/sh
# Native launch policy for the applications qualified in the desktop image.
set -eu
app=${1:-}
case "$app" in
    winterm|xclock|iconcatalog|xmahjongg) ;;
    *) echo 'Usage: xiri-launch winterm|xclock|iconcatalog|xmahjongg' >&2; exit 2;;
esac
test "$#" = 1 || exit 2
job=${XIRI_SESSION_DIR:?Run xiri-launch within a xiri-desktop session.}
launch=$(mktemp -d "$job/launch-$app.XXXXXX")
exec >"$launch/stdout" 2>"$launch/stderr"
printf '%s\n' "$$" >"$launch/pid"
case "$app" in
    winterm)
        # xwsh is the IRIX terminal selected by the vendor winterm script.
        # Each terminal needs its own native controlling-tty handoff report.
        exec /emul/irix/usr/sbin/xwsh -name winterm -title winterm \
            -geometry 80x24 -e /usr/libexec/xiri-shell "$launch/handoff";;
    xclock)
        exec /emul/irix/usr/bin/X11/xclock -update 1 -geometry 180x180 \
            -bg gray -fg black -bd black -hd black -hl black;;
    iconcatalog) exec /emul/irix/usr/sbin/iconcatalog -geometry 600x300;;
    xmahjongg) exec /emul/irix/usr/freeware/bin/xmahjongg;;
esac
