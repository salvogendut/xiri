#!/bin/sh
# Build freestanding IRIX programs with the NetBSD MIPS cross toolchain.
set -eu
[ "$#" -eq 2 ] || { echo "Usage: $0 NetBSD-mips64-cross-tools output-directory" >&2; exit 2; }
tools=$(cd "$1" && pwd)
src=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$2"
out=$(cd "$2" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
trap 'exit 1' HUP INT TERM
for abi in o32 n32; do
    case $abi in
        o32) option=32; bridge=0; format=elf32btsmip ;;
        n32) option=n32; bridge=1; format=elf32btsmipn32 ;;
    esac
    for input in "$src/../irix-mmap-local/start.S" "$src/../irix-mmap-local/call.S" "$src/socket-error.c"; do
        "$tools/bin/mips64--netbsd-gcc" -EB -march=mips3 -mabi="$option" -msoft-float \
            -mno-abicalls -fno-pic -G0 -O2 -ffreestanding -fno-stack-protector \
            -Wall -Wextra -Werror -DN32="$bridge" -DINDIRECT=0 -c "$input" -o "$tmp/${input##*/}.o"
    done
    "$tools/bin/mips64--netbsd-ld" -EB -m "$format" --build-id=none -z max-page-size=8192 \
        -T "$src/../irix-prda/probe.ld" -o "$out/so-$abi" "$tmp/start.S.o" "$tmp/call.S.o" "$tmp/socket-error.c.o"
    # Match the static IRIX ABI header recognized by Xiri's existing test probes.
    python3 - "$out/so-$abi" "$abi" <<'PY'
import struct
import sys
with open(sys.argv[1], 'r+b') as probe:
    probe.seek(36)
    probe.write(struct.pack('>I', 0x20000101 if sys.argv[2] == 'o32' else 0x20000021))
PY
done
