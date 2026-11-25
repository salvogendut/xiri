"""Check the 100-byte big-endian record written by entry.S."""

import struct
import sys


def main():
    record = sys.stdin.buffer.read(101)
    if len(record) != 100:
        sys.exit(f"Expected 100 bytes, received {len(record)}")
    words = struct.unpack(">25I", record)
    pid, stack = words[22], words[24]
    if not 0 < pid <= 0x7fffffff or not 0x1000 <= stack < 0x80000000:
        sys.exit(f"Invalid PID {pid} or stack top {stack:#x}")
    expected = (
        1, 0, 1, 0x556677, 0, 0, 0, 0, 1, (stack & ~15) - 64, 0,
        0x5510, 0x5511, 0x5512, 0x5513, 0x1357, pid, 1, 1, 0, 0,
        0x1357, pid, 0, stack,
    )
    for i, (actual, reference) in enumerate(zip(words, expected)):
        if actual != reference:
            sys.exit(f"Word {i}: received {actual:#x}, expected {reference:#x}")
    print(f"All 25 words match, pid {pid}, worker 1, sp {words[9]:#x}")


if __name__ == "__main__":
    main()
