#!/bin/sh
set -eu
prefix="${1:?mips64--netbsd tool prefix required}"
out=${2:?output ELF path required}
src=$(CDPATH='' cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
for file in "$src/../irix-mmap-local/start.S" "$src/../irix-mmap-local/call.S" "$src/recorder-arena.c"; do
    "$prefix-gcc" -EB -mabi=n32 -mips3 -msoft-float -mno-abicalls -fno-pic -G0 \
        -DN32=1 -DINDIRECT=0 -O2 -ffreestanding -fno-builtin -Wall -Wextra -Werror \
        -c "$file" -o "$tmp/$(basename "$file").o"
done
"$prefix-ld" -EB -m elf32btsmipn32 --build-id=none -T "$src/../irix-mmap-local/probe.ld" \
    -o "$tmp/probe" "$tmp/start.S.o" "$tmp/call.S.o" "$tmp/recorder-arena.c.o"
python3 - "$tmp/probe" "$out" <<'PY'
from pathlib import Path
import struct
import sys
data = bytearray(Path(sys.argv[1]).read_bytes())
data[7] = 0
struct.pack_into('>I', data, 36, 0x20000021)
output = Path(sys.argv[2])
output.write_bytes(data)
output.chmod(0o755)
PY
