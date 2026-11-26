#!/usr/bin/env python3
"""Build o32 and n32 observers for long floating-point conversions with the NetBSD cross tools."""
import argparse
import math
from pathlib import Path
import struct
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
INPUTS = (0, 1, -1, 2**52 - 1, 2**52, 2**52 + 1, 2**53, 2**53 + 1,
          -(2**53 + 1), 2**53 + 3, 2**63 - 1, -2**63, -(2**63 - 1))


def cases():
    for number in INPUTS:
        for mode in range(4):
            rounded = float(number)
            if mode == 1 and abs(rounded) > abs(number):
                rounded = math.nextafter(rounded, 0)
            elif mode == 2 and rounded < number:
                rounded = math.nextafter(rounded, math.inf)
            elif mode == 3 and rounded > number:
                rounded = math.nextafter(rounded, -math.inf)
            bits = struct.unpack('>Q', struct.pack('>d', rounded))[0]
            yield f'.dword 0x{number % 2**64:016x},0x{bits:016x}'
            yield f'.word {mode},{0x1004 if int(rounded) != number else 0}'


def trunc_cases():
    for value in (0., -.5, 1.75, -17.25, float(2**53), float(-2**53),
                  float(2**54), float(-(2**62)), math.nextafter(float(2**63), 0),
                  float(-2**63)):
        bits = struct.unpack('>Q', struct.pack('>d', value))[0]
        for mode in range(4):
            yield f'.dword 0x{bits:016x},0x{int(value) % 2**64:016x}'
            yield f'.word {mode},{0x1004 if int(value) != value else 0}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('tools', type=Path, help='NetBSD TOOLDIR')
    parser.add_argument('output', type=Path, help='new output directory')
    parser.add_argument('--trunc', action='store_true', help='build TRUNC.L.D observers')
    args = parser.parse_args()
    args.output.mkdir(parents=True)
    assembler = args.tools / 'bin/mips64--netbsd-as'
    linker = args.tools / 'bin/mips64--netbsd-ld'
    template = (HERE / 'cvt-long.S').read_text()
    rows = list(trunc_cases() if args.trunc else cases())
    if args.trunc:
        template = template.replace('cvt.d.l', 'trunc.l.d')
    with tempfile.TemporaryDirectory(dir=args.output) as tmp:
        source, obj = Path(tmp) / 'probe.s', Path(tmp) / 'probe.o'
        for abi, fs, fd, emulation, flags in (
                ('32', '$f4', '$f6', 'elf32btsmip', 0x20000101),
                ('n32', '$f5', '$f7', 'elf32btsmipn32', 0x20000021)):
            asm = template.replace('CASE_COUNT+1', str(len(rows) // 2 + 1))
            asm = asm.replace('FS', fs).replace('FD', fd)
            source.write_text(asm + '\n'.join(rows) + '\n')
            subprocess.run([assembler, '-EB', '-mabi=' + abi, '-mips3', '-o', obj, source], check=True)
            elf = args.output / (('trunc-' if args.trunc else 'cvt-') + abi)
            subprocess.run([linker, '-EB', '-m', emulation, '-z', 'max-page-size=8192',
                            '-T', HERE.parent / 'irix-prda/probe.ld', '-o', elf, obj], check=True)
            data = bytearray(elf.read_bytes())
            data[7] = 0
            struct.pack_into('>I', data, 36, flags)
            elf.write_bytes(data)


if __name__ == '__main__':
    main()
