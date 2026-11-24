#!/bin/sh
set -eu
test "$#" = 2 || { echo "usage: sh $0 TOOLDIR OUTPUT" >&2; exit 2; }
here=$(cd "$(dirname "$0")" && pwd)
tools=$1/bin/mips64--netbsd
mkdir -p "$2"
for abi in n32 32; do
    case "$abi" in n32) emu=elf32btsmipn32; flags=0x20000021 ;; 32) emu=elf32btsmip; flags=0x20000101 ;; esac
    "$tools-gcc" -mabi="$abi" -march=mips3 -G0 -mno-abicalls -fno-pic -ffreestanding -fno-stack-protector -O2 -Wall -Wextra -Werror -c "$here/probe.c" -o "$2/probe.o"
    "$tools-as" -EB -mabi="$abi" -msoft-float -mips3 -o "$2/start.o" "$here/start.S"
    "$tools-ld" -EB -m "$emu" -z max-page-size=8192 -T "$here/../irix-prda/probe.ld" -o "$2/meter-$abi" "$2/start.o" "$2/probe.o"
    python3 -c 'import pathlib,struct,sys; p=pathlib.Path(sys.argv[1]); d=bytearray(p.read_bytes()); d[7]=0; struct.pack_into(">I",d,36,int(sys.argv[2],0)); p.write_bytes(d)' "$2/meter-$abi" "$flags"
done
rm "$2/start.o" "$2/probe.o"
