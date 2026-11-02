# Legacy IRIX seek observations

`probe.c` observes syscall 1019 through the existing direct/indirect assembly
bridge, for o32 and n32. Each execution emits 1,536 bytes: 29 eight-word
records followed by zero padding. Pointer-valued open/read arguments are
normalized; return registers, error flags and read bytes are retained.
Root and UID/GID 1234 runs record their actual identities first.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-lseek.py
tar -C .work/irix-lseek/probes -cf .work/irix-lseek/probes.tar \
  o32-direct-lseek o32-indirect-lseek n32-direct-lseek n32-indirect-lseek
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-filetypes.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-xiri-desktop-icons.py
```

The reference runner uses the supplied original IRIX 6.5.22m installation.
`reference.json` pins the final request-queue outputs, fixtures, reference
identity and exact diagnostic harnesses. The initial reference script also
tried whence 3, which sends SIGSYS on this release; its later valid-whence
rerun is authoritative. Neither original vendor code nor data is modified.
The four rebuilt fixtures match those reference binaries byte for byte.

The paired cases cover SET/CUR/END, actual bytes, negative offsets, invalid
and closed descriptors, pipe ESPIPE, duplicate-descriptor offset sharing,
the signed 32-bit boundary and the offset after errors. `wide.c` uses original
n32 libc and 64-bit `off_t` to test offsets beyond 4 GiB and signed relative
seeks. It is compiled on original IRIX with `gcc -mabi=n32 -mips3 -O2`.

The native adapter uses `sys_lseek` and its descriptor offset state. o32
accepts signed 32-bit offsets and reports EOVERFLOW after a successful seek
beyond INT32_MAX, retaining the advanced offset as measured. n32 syscall 19
accepts a full 64-bit argument and returns a full 64-bit v0 value. Its pointers
and `long` remain 32-bit. Unknown whence values use the measured SIGSYS path.
Explicit large-file syscall variants are outside this qualification.

`qualify-irix-lseek.py LP64_RUN O32_RUN --output REPORT` compares every raw
record byte and fixture binary with the reference, checks the actual kernel
artifact against the clean source pins, and compares the wide-offset output.
The retained native o32 harness is `.work/irix-lseek/probe-seek-o32.py`, pinned
in `reference.json`; the clean LP64 reproduction is part of the maintained
desktop-icons probe. See [the result](../../docs/results/2026-11-02-irix-lseek.json).
