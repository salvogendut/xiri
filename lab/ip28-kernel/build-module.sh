#!/bin/sh
# Build the IRIX personality without changing the shared nbmake wrapper.
set -eu
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 NetBSD-source NetBSD-tools output-directory" >&2
    exit 2
fi
src=$(cd "$1" && pwd)
task_tools=$(cd "$2" && pwd)
mkdir -p "$3"
build=$(cd "$3" && pwd)
export TOOLDIR="$task_tools" NETBSDSRCDIR="$src" DESTDIR="$build/dest"
export MACHINE=sgimips MACHINE_ARCH=mips64eb
export MAKECONF=/dev/null USETOOLS=yes MKUNPRIVED=yes MKUPDATE=yes MKX11=no
export HOST_SH=/bin/sh CONFIG_SHELL=/bin/sh LC_ALL=C TZ=UTC
export MAKE_OBJDIR_CHECK_WRITABLE=no MAKEOBJDIR="$build/module"
mkdir -p "$MAKEOBJDIR" "$DESTDIR"
exec "$task_tools/bin/nbmake" -m "$src/share/mk" \
    -C "$src/sys/modules/compat_irix_o32" MKDEPFLAGS=-mabi=64 -j2 dependall
