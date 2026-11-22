#!/bin/sh
# Cross-build the two ARCS loaders and a small, vendor-free IP28 disk fixture.
set -eu
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 NetBSD-source NetBSD-tools output-directory" >&2
    exit 2
fi
src=$(cd "$1" && pwd)
task_tools=$(cd "$2" && pwd)
mkdir -p "$3"
build=$(cd "$3" && pwd)
lab=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export NETBSDSRCDIR="$src" TOOLDIR="$task_tools" DESTDIR="$build/dest"
export XIRI_BOOT_OBJROOT="$build/obj"
export MACHINE=sgimips MACHINE_ARCH=mips64eb
export MAKECONF=/dev/null USETOOLS=yes MKUNPRIVED=yes MKUPDATE=yes MKX11=no
export HOST_SH=/bin/sh CONFIG_SHELL=/bin/sh LC_ALL=C TZ=UTC
export MAKE_OBJDIR_CHECK_WRITABLE=no
MAKEOBJDIR='${.CURDIR:S,^${NETBSDSRCDIR},${XIRI_BOOT_OBJROOT},}'
export MAKEOBJDIR
mkdir -p "$DESTDIR" "$build/obj/sys/arch/sgimips/stand/boot64" \
    "$build/obj/sys/arch/sgimips/stand/boot" "$build/fixture/root"
for target in boot64 boot; do
    "$task_tools/bin/nbmake" -m "$src/share/mk" \
        -C "$src/sys/arch/sgimips/stand/$target" -j2 dependall
done
cp "$build/obj/sys/arch/sgimips/stand/boot64/ip28boot" "$build/ip28boot"
for file in handoff.c handoff.S; do
    "$task_tools/bin/mips64--netbsd-gcc" -mabi=64 -mips3 -msoft-float \
        -mno-abicalls -G0 -ffreestanding -fno-pic -fno-stack-protector \
        -Os -Wall -Wextra -c "$lab/$file" -o "$build/fixture/$file.o"
done
"$task_tools/bin/mips64--netbsd-ld" -N -m elf64btsmip \
    -T "$src/sys/arch/mips/conf/stand.ldscript" \
    -Ttext 0xa800000020080000 -e _start \
    -o "$build/fixture/root/xiri-ip28-probe" \
    "$build/fixture/handoff.S.o" "$build/fixture/handoff.c.o"
"$task_tools/bin/nbmakefs" -t ffs -B be -s 16m -o version=1 \
    "$build/fixture/root.ffs" "$build/fixture/root"
rm -f "$build/fixture/disk.raw"
truncate -s 32M "$build/fixture/disk.raw"
"$task_tools/bin/nbsgivol" -q -i -h 4096 "$build/fixture/disk.raw"
"$task_tools/bin/nbsgivol" -q -w boot "$build/ip28boot" "$build/fixture/disk.raw"
dd if="$build/fixture/root.ffs" of="$build/fixture/disk.raw" \
    bs=512 seek=4096 conv=notrunc
