#!/bin/sh
# Run from the read-only update CD on an already qualified O2 desktop.
set -eu
cd /cdrom
sha256 -c SHA256
moddir="$(sysctl -n kern.module.path)/compat_irix_o32"
install -m 444 netbsd /netbsd.new
install -m 444 netbsd.boot /netbsd.boot.new
install -m 444 compat_irix_o32.kmod "$moddir/compat_irix_o32.kmod.new"
mv "$moddir/compat_irix_o32.kmod.new" "$moddir/compat_irix_o32.kmod"
mv /netbsd.new /netbsd
mv /netbsd.boot.new /netbsd.boot
sync
