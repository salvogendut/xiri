#!/bin/sh
set -eu
test "$#" = 6 || { echo 'Usage: package.sh MODULE KERNEL-DIR HDSP-QUERY CVT-DIR TRUNC-DIR OUTPUT.iso' >&2; exit 2; }
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
dest=$6
mkdir -p "$(dirname "$dest")"
work=$(mktemp -d "$(dirname "$dest")/.hdsp.XXXXXXXX")
trap 'rm -rf "$work"' EXIT
trap 'exit 1' HUP INT TERM
mkdir "$work/cd"
cp "$1" "$work/cd/compat_irix_o32.kmod"
cp "$2/netbsd" "$work/cd/netbsd"
cp "$2/netbsd.elf32" "$work/cd/netbsd.boot"
cp "$3" "$work/cd/hdsp-query"
cp "$4/cvt-32" "$4/cvt-n32" "$5/trunc-32" "$5/trunc-n32" "$here/install.sh" "$here/xiri_hdsp" "$work/cd/"
(cd "$work/cd" && sha256sum --tag * > SHA256)
genisoimage -quiet -R -V XIRI_HDSP -o "$work/hdsp.iso" "$work/cd"
ln "$work/hdsp.iso" "$dest"
