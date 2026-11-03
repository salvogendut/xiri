#!/bin/sh
# Build the pinned 0.2.4 Newport module with the guest's matching Xorg SDK.
set -eu
src=${1:?Usage: build-driver.sh SOURCE OUTPUT}
out=${2:?Usage: build-driver.sh SOURCE OUTPUT}
mkdir -p "$out"
for name in newport_accel newport_cmap newport_cursor newport_driver newport_regs newport_shadow; do
    cc -O2 -fPIC -D_NETBSD_SOURCE -DHAVE_CONFIG_H \
        -I"$src" -I/usr/X11R7/include/xorg -I/usr/X11R7/include \
        -I/usr/X11R7/include/pixman-1 -c "$src/$name.c" -o "$out/$name.o"
done
cc -shared -Wl,-soname,newport_drv.so -o "$out/newport_drv.so" "$out"/*.o
