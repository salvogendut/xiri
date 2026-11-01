# IRIX pipe ABI and lifecycle

The [qualified result](../../docs/results/2026-11-01-irix-pipe.md) passes 220
native records and 44 controls against 88 original records. This lab measures
trap1042 on the supplied IRIX 6.5.22m installation. The
original syscall accepts no kernel arguments and returns the read/write
endpoints in V0/V1. Its libc wrapper stores those registers into the caller's
array. The NetBSD adapter dispatches to native `sys_pipe`, retaining native
allocation limits, rollback, descriptor ownership and lifetime. No new core
hook is introduced for the eventual compat_linux-style module target.

Eleven cases run as o32/n32, through direct/indirect dispatch, under UID0 and
UID1234: 88 original records. Each record is 64 guarded big-endian words with
identities and return registers. Cases cover ignored NULL/high/wrapped/valid/
read-only argument values, untouched pointed-to storage, lowest available
slots, initial descriptor/access flags, partial reads, EOF, invalid reverse
operations, nonblocking empty reads, dup/last-writer lifetime, inherited fork
endpoints, reaped child status, and EPIPE with SIGPIPE blocked.

The descriptor-limit case runs with RLIMIT_NOFILE=32. It fills every available
slot, checks pipe failure with zero and one free slot, verifies that a failed
second allocation did not leak the first descriptor, then succeeds with two
free slots. All records are compared exactly; no descriptor or error
normalization is used. The independent qualifier also constructs the expected
records separately from the fixture implementation.

Native probes reuse the existing group-owning runner. Each execution must
prove process-group removal. Independent native pipe controls test ordinary
I/O, nonblocking reads, forked writers, EOF and descriptor rollback before and
after the foreign matrix. Native o32 and vendor asa/echo remain controls.
This does not qualify STREAMS, poll, pipe capacity/atomicity under contention,
foreign signal handlers or physical hardware.

## Reproduce

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-pipe.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-pipe.py \
  --seed-directory .work/irix-reference/mkdir-records-runs/ci-xilnl6o7
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-pipe.py \
  --reference .work/irix-reference/pipe-records-runs/ci-3q2rck05 --export-reference
```

Build XIRI_IRIX_PIPE and XIRI_IRIX_PIPE_O32 sequentially, with at most two
jobs, from the NetBSD `xiri` source. Separate outputs are
`.work/netbsd-irix-pipe-build` and `.work/netbsd-irix-pipe-o32-build`; the
matching existing toolchains are linked with explicit mips64eb/mipseb build
stamps. Pins are taken from clean source and completed build artifacts.
Qualified earlier artifacts remain unchanged.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-pipe.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-pipe.py --kernel-abi o32
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-pipe.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-pipe.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-pipe.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --kernel-abi o32
```

`qualify-irix-pipe.py --reference REF RUN... --output REPORT` requires all
three native runs, native/vendor controls, exact records, source hashes and
clean shutdowns. Capturing records alone is not a pass.

`probe-irix-desktop-pipe.py` repeats the original desktop clients with this
kernel. It allows 45 seconds for the terminal handoff and uses a 180-second
session guard, retaining all failures. The earlier 120-second sessions remain
unchanged. Original binaries, disks, traces and disassembly stay in ignored
`.work`; only authored fixtures, decoded records and reports are committed.


The 180-second observer uses the guard copy in this lab; the earlier guard
retains its 120-second ceiling. The pinned native ABI probe verifies the
requested duration is accepted before the desktop is launched. The initial
mismatched-duration attempt and interrupted parallel attempt are retained as
[diagnostics](../../docs/results/2026-11-01-irix-pipe-diagnostics.json).


The [desktop follow-up](../../docs/results/2026-11-01-irix-desktop-pipe.md) now renders FileManager in ordinary mode,
with a repeated select EINVAL loop and an independently retained CI timeout.
