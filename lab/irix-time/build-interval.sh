#!/bin/sh
set -eu
test "$#" = 2 || { echo "usage: sh $0 TOOLDIR OUTPUT" >&2; exit 2; }
here=$(cd "$(dirname "$0")" && pwd)
common=$here/../irix-prda
tools=$1/bin/mips64--netbsd
out=$2
mkdir -p "$out"
for abi in n32 32; do
    case $abi in
        n32) n32=1; emu=elf32btsmipn32; flags=0x20000021 ;;
        32)  n32=0; emu=elf32btsmip; flags=0x20000101 ;;
    esac
    for src in "$common/start.S" "$common/call.S" "$here/interval.c"; do
        obj=$(basename "$src")
        "$tools-gcc" -mabi="$abi" -march=mips3 -G0 -mno-abicalls -fno-pic \
            -ffreestanding -fno-stack-protector -O2 -Wall -Wextra -Werror \
            -DN32="$n32" -DINDIRECT=0 -c "$src" -o "$out/$obj.o"
    done
    "$tools-ld" -EB -m "$emu" -z max-page-size=8192 -T "$common/probe.ld" \
        -o "$out/timer-$abi" "$out/start.S.o" "$out/call.S.o" "$out/interval.c.o"
    python3 -c 'import pathlib,struct,sys; p=pathlib.Path(sys.argv[1]); d=bytearray(p.read_bytes()); d[7]=0; struct.pack_into(">I",d,36,int(sys.argv[2],0)); p.write_bytes(d)' "$out/timer-$abi" "$flags"
done
rm "$out/start.S.o" "$out/call.S.o" "$out/interval.c.o"
