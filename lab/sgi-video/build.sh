#!/bin/sh
set -eu
[ "$#" = 4 ] || { echo 'Usage: build.sh NETBSD_CC SYSROOT X11_INCLUDE OUTPUT.so' >&2; exit 2; }
src=$(dirname "$0")/sgivc.c
"$1" --sysroot="$2" -mabi=32 -std=gnu99 -O2 -Wall -Wextra -Werror \
    -isystem "$3/xorg" -isystem "$3/pixman-1" -isystem "$3" -fPIC -shared -o "$4" "$src"
