#!/bin/sh
# Run in the Xiri build Toolbox with a mips64--netbsd tool directory.
set -eu
tools=$(cd "${1:?NetBSD tool directory required}" && pwd)
out=${2:?output ELF path required}
src=$(CDPATH='' cd "$(dirname "$0")" && pwd)
tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' 0
for file in "$src/../irix-mmap-local/start.S" "$src/../irix-mmap-local/call.S" \
    "$src/spawn.S" "$src/entry.S" "$src/fullshare.c"; do
    "$tools/bin/mips64--netbsd-gcc" -EB -mabi=32 -mips3 -msoft-float -mno-abicalls \
        -fno-pic -G0 -ffreestanding -fno-builtin -fno-stack-protector -O2 -Wall -Wextra \
        -Werror -DN32=0 -DINDIRECT=0 -c "$file" -o "$tmp/$(basename "$file").o"
done
"$tools/bin/mips64--netbsd-ld" -EB -m elf32btsmip --build-id=none -z max-page-size=8192 \
    -T "$src/../irix-mmap-local/probe.ld" -o "$tmp/probe" "$tmp"/*.o
# Use the same SGI ELF header as the other freestanding o32 controls.
python3 - "$tmp/probe" "$out" <<'PY'
from pathlib import Path
import struct
import sys
data = bytearray(Path(sys.argv[1]).read_bytes())
data[7] = 0
struct.pack_into('>I', data, 36, 0x20000101)
p = Path(sys.argv[2])
p.write_bytes(data)
p.chmod(0o755)
PY
