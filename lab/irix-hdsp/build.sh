#!/bin/sh
set -eu
prefix=${1:?Usage: build.sh MIPS-tool-prefix OUTPUT-DIR}
out=${2:?}
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$out"
build_probe() {
    name=$1 src=$2 abi=$3 emu=$4 flags=$5
    shift 5
    "$prefix-as" -EB -mabi="$abi" -mips3 -msoft-float -G0 -o "$out/start.o" "$here/start.S"
    "$prefix-gcc" -EB -mabi="$abi" -mips3 -msoft-float -mno-abicalls -fno-pic -G0 -O2 \
        -ffreestanding -fno-builtin -fno-stack-protector -fno-tree-loop-distribute-patterns \
        -Wall -Wextra -Werror "$@" -c "$here/$src.c" -o "$out/$src.o"
    "$prefix-ld" -EB -m "$emu" --build-id=none -T "$here/../irix-o32/probe.ld" \
        -o "$out/$name" "$out/start.o" "$out/$src.o"
    python3 - "$out/$name" "$flags" <<'PYCODE'
from pathlib import Path
import sys, struct
p = Path(sys.argv[1])
data = bytearray(p.read_bytes())
data[7] = 0
struct.pack_into('>I', data, 36, int(sys.argv[2], 0))
p.write_bytes(data)
PYCODE
}

build_probe hdsp-query query n32 elf32btsmipn32 0x20000021
build_probe arena-n32 arena-check n32 elf32btsmipn32 0x20000021 -DN32
build_probe arena-o32 arena-check 32 elf32btsmip 0x20000101
