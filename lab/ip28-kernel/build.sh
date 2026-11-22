#!/bin/sh
# Build an isolated kernel using an existing NetBSD cross-toolchain.
# Do not invoke its shared nbmake-sgimips wrapper or change its source pin.
set -eu
if [ "$#" -lt 3 ] || [ "$#" -gt 4 ]; then
    echo "Usage: $0 NetBSD-source NetBSD-tools output-directory [kernel-config]" >&2
    exit 2
fi
src=$(cd "$1" && pwd)
task_tools=$(cd "$2" && pwd)
mkdir -p "$3"
build=$(cd "$3" && pwd)
config=${4:-"$src/sys/arch/sgimips/conf/GENERIC64_IP28"}
export TOOLDIR="$task_tools" NETBSDSRCDIR="$src" DESTDIR="$build/dest"
export MACHINE=sgimips MACHINE_ARCH=mips64eb
export MAKECONF=/dev/null USETOOLS=yes MKUNPRIVED=yes MKUPDATE=yes MKX11=no
export HOST_SH=/bin/sh CONFIG_SHELL=/bin/sh LC_ALL=C TZ=UTC
export MAKE_OBJDIR_CHECK_WRITABLE=no
mkdir -p "$build/kernel" "$DESTDIR"
"$task_tools/bin/nbconfig" -s "$src/sys" -b "$build/kernel" "$config"
"$task_tools/bin/nbmake" -m "$src/share/mk" -C "$build/kernel" -j2 depend
exec "$task_tools/bin/nbmake" -m "$src/share/mk" -C "$build/kernel" -j2 netbsd
