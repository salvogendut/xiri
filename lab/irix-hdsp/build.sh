#!/bin/sh
set -eu
prefix=${1:?Usage: build.sh MIPS-tool-prefix OUTPUT-DIR}
out=${2:?}
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir -p "$out"
"$prefix-as" -EB -mabi=n32 -mips3 -msoft-float -G0 -o "$out/start.o" "$here/start.S"
"$prefix-gcc" -EB -mabi=n32 -mips3 -msoft-float -mno-abicalls -fno-pic -G0 -O2 \
    -ffreestanding -fno-builtin -fno-stack-protector -fno-tree-loop-distribute-patterns \
    -Wall -Wextra -Werror -c "$here/query.c" -o "$out/query.o"
"$prefix-ld" -EB -m elf32btsmipn32 --build-id=none -T "$here/../irix-o32/probe.ld" \
    -o "$out/hdsp-query" "$out/start.o" "$out/query.o"
python3 - "$out/hdsp-query" <<'PY'
from pathlib import Path
import sys, struct
p = Path(sys.argv[1])
data = bytearray(p.read_bytes())
data[7] = 0
struct.pack_into('>I', data, 36, 0x20000021)
p.write_bytes(data)
PY
