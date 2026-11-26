#!/bin/sh
# Build a replacement extmod against the NetBSD 11.0 sgimips Xorg SDK.
set -eu
[ "$#" -eq 4 ] || { echo 'Usage: build.sh nbmake-sgimips XSRCDIR DESTDIR OUTPUT' >&2; exit 2; }
make=$(realpath "$1")
xsrc=$(realpath "$2")
dest=$(realpath "$3")
out=$4
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
[ ! -e "$out" ] && [ ! -L "$out" ] || { echo "Output exists: $out" >&2; exit 1; }
test "$("$make" -V MACHINE_ARCH)" = mipseb
src=$("$make" -V NETBSDSRCDIR)
server=$src/external/mit/xorg/server/xorg-server.old
mkdir -p "$(dirname "$out")"
tmp=$(mktemp -d "$(dirname "$out")/.sgi-saver.XXXXXXXX")
tmp=$(realpath "$tmp")
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' HUP INT TERM
tree=$tmp/xsrc/external/mit/xorg-server.old
mkdir -p "$tree"
cp -R "$xsrc/external/mit/xorg-server.old/dist" "$xsrc/external/mit/xorg-server.old/include" "$tree/"
chmod u+w "$tree/dist/Xext" "$tree/dist/Xext/saver.c"
(cd "$tree/dist" && GIT_CEILING_DIRECTORIES="$tree" git apply "$here/saver.patch")
cp "$here/sgi-saver.inc" "$tree/dist/Xext/"
for subdir in Xext/Xextmodule hw/xfree86/dixmods/extmod; do
    mkdir -p "$tmp/obj$server/$subdir"
    "$make" -C "$server/$subdir" MAKEOBJDIR="$tmp/obj"'${.CURDIR}' MKX11=yes \
        X11SRCDIR="$tmp/xsrc" DESTDIR="$dest" MKDEBUG=no MKDEBUGLIB=no MKCTF=no -j4 all
done
ln "$tmp/obj$server/hw/xfree86/dixmods/extmod/libextmod.so.0" "$out"
