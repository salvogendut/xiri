# Static o32 compatibility experiment

This lab supplies original, synthetic MIPS ELF fixtures for the first IRIX
system-call experiment. It contains no vendor binaries or runtime. The current
test establishes **native execution and foreign-ELF rejection** on the qualified
NetBSD 11.0 guest; it does not demonstrate IRIX execution.

See the [source audit and implementation plan](../../docs/results/2026-10-30-irix-compat-audit.md)
for the historical references, measured baseline, and next acceptance gate.

## Build and run

Prerequisites are the [NetBSD cross-tools](../netbsd-11.0/README.md), the
`xiri-iris` Toolbox, the [custom-kernel checkpoint](../../docs/results/2026-10-30-netbsd-kernel.md),
and the pinned [IRIS build](../iris/README.md). The installed guest must include
the native C compiler. The scripts use the existing lab's paths and networking.

From the Xiri repository:

```sh
./scripts/build-irix-probe.py
./scripts/probe-irix-baseline.py --mode ci
./scripts/probe-irix-baseline.py --mode ordinary
```

The builder uses `mipseb--netbsd-as` and `ld` with big-endian MIPS III/o32
settings. It writes binaries, disassembly, ELF reports, and a hash/tool manifest
under `.work/irix-o32/`. It verifies the ELF class, byte order, architecture,
ABI flags, branding, loadable entry, and absence of an interpreter/dynamic
segment. The unbranded variant omits `PT_NOTE` entirely.

Each guest run gets a fresh disk/NVRAM copy from `.work/indy-netbsd-kernel/`, a
virtual CD containing just the fixtures and runner source, and its own result
directory under `.work/irix-o32-runs/`. The guest verifies the fixture hashes,
compiles the native runner, runs the checks, and halts. Both modes write their
private disk copies directly; this test does not use snapshot restore or CI
disk rollback.

## Fixtures and expected baseline

All three fixtures have a fixed executable load segment at `0x00400000` and
need only a stack and an inherited writable stdout. They attempt to write the
15-byte string `XIRI_ABI_PROBE\n`, check `a3 == 0` and `v0 == 15`, and exit 37.
A failed/short write selects exit 99. No libc, interpreter, TLS, global pointer,
FPU, arguments, environment, or auxiliary-vector contents are consumed.

| Fixture | Identity and calls | Current expected result |
| --- | --- | --- |
| `native-o32` | NetBSD OSABI, NetBSD version note, calls 4/1 | Exact stdout, exit 37 |
| `irix-o32-marked` | System V OSABI, legacy IRIX o32 flags, Xiri test note, calls 1004/1001 | `execve` fails with `ENOEXEC` |
| `irix-o32-unbranded` | Same foreign ABI and calls, no note | `execve` fails with `ENOEXEC` |

The opt-in note has name `Xiri\0` (`namesz=5`), type `0x49524958`, and a
four-byte big-endian descriptor with value 1. **This is a Xiri test convention,
not an IRIX identification standard.** It permits a future experimental loader
to recognize exactly the intended fixture without treating every unbranded
MIPS ELF as IRIX. General vendor-binary recognition is separate work.

[`runner.c`](runner.c) calls `execve` directly so that a shell cannot hide
`ENOEXEC` by trying to interpret the file. A close-on-exec pipe distinguishes
an execution error from a program's exit status; a second pipe captures stdout.
The runner reports errno, byte count, exit status, and terminating signal. Each
fixed, small-output fixture has a bounded wait of approximately 20 guest
seconds. This runner is tailored to these fixtures, not a general subprocess
capture utility.

`BASELINE_PASS native=works irix=ENOEXEC` means all three expected baseline
outcomes occurred. A future compatibility kernel should change the marked
fixture to successful execution and retain the unbranded rejection; that needs
a separate compatibility test mode and the additional negative cases in the
audit. Do not redefine this baseline's pass marker to mean compatibility.
