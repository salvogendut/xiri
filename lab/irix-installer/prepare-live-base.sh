#!/bin/sh
# Bootstrap the original inst history on a fresh private v5 Indy desktop.
set -eu
export HOME=/ USER=root LOGNAME=root SHELL=/bin/sh TERM=vt100 LANG=C TZ=UTC
export PATH=/bin:/usr/bin:/sbin:/usr/sbin
test "$#" = 1 && test "$(id -u)" = 0 || { echo "Usage as root: sh $0 /absolute/cd-mount" >&2; exit 2; }
media=$1
case "$media" in /*) ;; *) exit 2 ;; esac
root=/emul/irix
test -s "$media/installer.tgz" && test -d "$media/overlay" && test -d "$media/foundation"
read -r release native vendor </var/db/xiri-install/installed
case "$release" in 6.5.22f|6.5.30f) ;; *) exit 1 ;; esac
test "$(awk -F'"' '/^  "release":/ {print $4}' "$media/vendor.json")" = "$release" ||
    { echo 'The SGI media and installed desktop releases differ.' >&2; exit 1; }
test ! -e "$root/var/inst/hist" || { echo 'Use a fresh target with empty vendor installation history.' >&2; exit 1; }
(cd / && pax -rzkpe -f "$media/installer.tgz")
sh "$media/setup-native-paths.sh"
if test ! -e /sbin/stat && test ! -L /sbin/stat; then ln -s "$root/sbin/stat" /sbin/stat; fi
test /sbin/stat -ef "$root/sbin/stat"
# chroot cannot use the native root fallback for SGI's runtime loader.
for name in null zero; do
    dest=$root/dev/$name
    major=$(/usr/bin/stat -f %Hr "/dev/$name")
    minor=$(/usr/bin/stat -f %Lr "/dev/$name")
    if test ! -e "$dest" && test ! -L "$dest"; then mknod "$dest" c "$major" "$minor"; chmod 666 "$dest"; fi
    test -c "$dest" && test "$(/usr/bin/stat -f '%Hr:%Lr' "$dest")" = "$major:$minor" || exit 1
done
mkdir -p "$root/usr/freeware"
if test ! -e /usr/freeware && test ! -L /usr/freeware; then ln -s "$root/usr/freeware" /usr/freeware; fi
test /usr/freeware -ef "$root/usr/freeware"
work=$root/var/inst/xiri-base
mkdir -m 700 "$work"
# Record real files from each prerequisite subsystem. Do not bulk-install eoe
# over Xiri's devices, accounts or shell. SGI make and nawk run inside chroot.
set --
for path in sbin/make usr/bin/make usr/bin/nawk usr/bin/zic sbin/ncheck \
    lib/cpp usr/cpu/sysgen/root/usr/bin/ld usr/lib32/libfpe.so usr/bin/ldd \
    usr/bin/X11/xdpyinfo usr/lib32/libgen.so usr/lib32/libCsup.so usr/lib32/libC.so.2; do
    set -- "$@" -Y "/$path"
done
printf '%s\n' 'keep *' \
    'install c++_eoe.sw.lib eoe.sw.base eoe.sw.efs compiler_eoe.sw.cpp compiler_eoe.sw.lboot compiler_eoe.sw.lib compiler_eoe.sw.unix x_eoe.sw.eoe' \
    conflicts go 'keep *' quit >"$work/commands"
"$root/usr/sbin/inst" -M -r "$root" "$@" -f "$media/foundation" -f "$media/overlay" \
    -c "$work/commands" </dev/null >"$work/base.log" 2>&1
cat "$work/base.log"
grep -q 'No conflicts' "$work/base.log"
if grep -q '^ERROR:' "$work/base.log"; then exit 1; fi
for name in libgen.so libCsup.so libC.so.2; do
    path=$root/usr/lib32/$name
    test -f "$path" && test ! -L "$path" || exit 1
    chmod 555 "$path"
done
"$root/usr/sbin/versions" -r "$root" >"$work/history"
for sub in c++_eoe.sw.lib eoe.sw.base eoe.sw.efs compiler_eoe.sw.cpp compiler_eoe.sw.lboot compiler_eoe.sw.lib compiler_eoe.sw.unix x_eoe.sw.eoe; do
    awk -v subname="$sub" '$1=="I" && $2==subname {found=1} END {exit !found}' "$work/history"
done
