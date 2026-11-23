#!/bin/sh
# Build the NetBSD xdm bitmap widget with the release's two stock greeter objects.
set -eu
if [ "$#" -ne 2 ]; then
    echo "usage: sh build-greeter.sh path/to/xdm/dist output.so" >&2
    exit 2
fi
src=$(cd "$1" && pwd)
output=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
cc=${CC:-cc}
sysroot=${NETBSD_SYSROOT:-/}
x11=${X11_PREFIX:-/usr/X11R7}
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
cd "$work"

"${AR:-ar}" x "$x11/lib/libXdmGreet.a" greet.o verify.o
"$cc" --sysroot="$sysroot" -mabi=32 -O2 -fPIC -DXPM -DHAVE_SYS_PARAM_H \
    -DHAVE_GETIFADDRS -DUSE_PAM -DHAVE_SECURITY_PAM_APPL_H -DHAVE_SECURITY_PAM_TYPES_H \
    -DIPv6 -DUNIXCONN -DTCPCONN -DRETSIGTYPE=void -DHAVE_ASPRINTF \
    -I"$src/include" -I"$x11/include" -c "$src/greeter/Login.c" -o Login.o
"$cc" --sysroot="$sysroot" -mabi=32 -shared -Wl,-soname,libXiriO2Greet.so \
    -Wl,-rpath,/usr/X11R7/lib -Wl,-rpath-link,"$sysroot/lib" \
    -L"$x11/lib" -Wl,-rpath-link,"$x11/lib" -o "$output" Login.o greet.o verify.o \
    -lXext -lXt -lXdmcp -lXinerama -lXpm -lX11 -lpam -lcrypt -lutil
