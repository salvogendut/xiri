#!/bin/sh
# Use the SGI installer and the package history of the running Xiri desktop.
set -eu
media=${1:-/cdrom}
root=/emul/irix
test "$(id -u)" -eq 0 || { echo 'Run as NetBSD root.' >&2; exit 1; }
test -f "$root/var/inst/hist" && test -x "$root/usr/sbin/inst" || {
    echo 'This desktop needs the initialized SGI installer and base history.' >&2; exit 1;
}
test -r "$media/dist/fw_xosview.sw" || { echo 'Mount the xosview distribution first.' >&2; exit 1; }
(cd "$media/dist" &&
    test "$(sha256 -q fw_xosview)" = 834ad4f31ece781fb1becc18a864dab3960d6b1ef6d5f3b0843854652a0c23b0 &&
    test "$(sha256 -q fw_xosview.idb)" = 05adc72c218a28f4ec2815d95de8facf5b90bf7cfcd7158ddf6282993d9d240f &&
    test "$(sha256 -q fw_xosview.sw)" = 9e1912f31c55948833278c90d6fe4b9ffe0b0e521a4a7131bd28ecc6388716a6) || {
    echo 'Expected the May 2004 CD 4 xosview distribution.' >&2; exit 1;
}
export HOME=/ USER=root LOGNAME=root PATH=/bin:/usr/bin:/sbin:/usr/sbin LANG=C TZ=UTC
work=$(mktemp -d /var/tmp/xiri-xosview.XXXXXX)
trap 'rm -rf "$work"' EXIT
printf '%s\n' 'keep *' 'install fw_xosview.sw.xosview' conflicts go 'keep *' quit >"$work/commands"
"$root/usr/sbin/inst" -M -r "$root" -f "$media/dist" -c "$work/commands" </dev/null >"$work/log" 2>&1 || {
    cat "$work/log" >&2; exit 1;
}
cat "$work/log"
grep -q 'No conflicts' "$work/log"
"$root/usr/sbin/versions" -r "$root" fw_xosview >"$work/history"
cat "$work/history"
awk '$1=="I" && $2=="fw_xosview.sw.xosview" {found=1} END {exit !found}' "$work/history"
test -x "$root/usr/freeware/bin/xosview" && test -r "$root/usr/freeware/lib/X11/app-defaults/XOsview"
