#!/bin/sh
# Build the NetBSD resolver and a local update CD for the Mozilla Indy images.
set -eu
if [ "$#" -ne 4 ]; then
    echo "Usage: $0 NetBSD-cross-tools NetBSD-sgimips-sysroot compat_irix_o32.kmod output.iso" >&2
    exit 2
fi
src=$(cd "$(dirname "$0")" && pwd)
tools=$(cd "$1" && pwd)
sysroot=$(cd "$2" && pwd)
module=$3
iso=$4
test ! -e "$iso" || { echo "Output already exists: $iso" >&2; exit 1; }
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' HUP INT TERM
mkdir "$tmp/cd"
cp "$sysroot/usr/include/rpcsvc/nfs_prot.x" "$tmp/"
(cd "$tmp" && "$tools/bin/nbrpcgen" -c nfs_prot.x > nfs_prot.c)
cc="$tools/bin/mipseb--netbsd-gcc"
"$cc" --sysroot="$sysroot" -Os -ffunction-sections -fdata-sections \
    -I"$sysroot/usr/include/rpcsvc" -c "$tmp/nfs_prot.c" -o "$tmp/nfs_prot.o"
"$cc" --sysroot="$sysroot" -Os -Wall -Wextra -Werror -Wl,--gc-sections -s \
    "$src/mount_xiri_hosts.c" "$tmp/nfs_prot.o" -o "$tmp/cd/mount_xiri_hosts"
cp "$module" "$tmp/cd/compat_irix_o32.kmod"
cp "$src/install.sh" "$src/xiri_hosts" "$tmp/cd/"
(cd "$tmp/cd" && sha256sum compat_irix_o32.kmod mount_xiri_hosts xiri_hosts > SHA256)
genisoimage -quiet -R -V XIRI_BROWSER_NET -o "$iso" "$tmp/cd"
