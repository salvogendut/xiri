# Toolchest session and fault diagnosis

Follow-up: the [select checkpoint](../../docs/results/2026-10-31-irix-select.md) implements the measured readiness/timeout subset. The [xstat follow-up](../../docs/results/2026-10-31-irix-xstat.md) now enables app-defaults loading and reaches an allocator fault before the menu stage. The [fxstat follow-up](../../docs/results/2026-10-31-irix-fxstat.md) supplies descriptor metadata, removes that observed allocator fault and reaches an unsupported `SIOCNREAD` ioctl after the full menu read. The [SIOCNREAD follow-up](../../docs/results/2026-10-31-irix-siocnread.md) removes that XIO exit and produces a rendered, live Toolchest client in bounded tests. The diagnosis below records the earlier recvmsg kernel.

This follows the [recvmsg checkpoint](../irix-recvmsg/README.md), without changing
its kernel or emulator. The [findings](../../docs/results/2026-10-31-irix-toolchest-session.md)
distinguish an empty-environment crash from unsupported `select` and `xstat`.
A Toolchest window and event handling remain unqualified.

`session.c` runs a program with an explicit environment file, one `NAME=value`
per line, at most 32 entries. It inherits the IDs, descriptors and deadline
established by the existing [runner](../irix-lp64/runner.c). Its environment
replaces the inherited environment completely. An environment-file error exits
125; a failed second exec exits 126 and prints an error. The outer runner's
exec-error pipe covers entry into the native wrapper, so these later failures
must be read from the wrapper's status/stderr. This is a diagnostic launcher,
not a complete desktop login/session manager.

`trace.c` captures an exec stop and a later fault using native ptrace. It is
specific to the pinned LP64 MIPS kernel: its netbsd32 ptrace path returns 38
64-bit register slots, with raw trap-frame PC in slot 37. A trailing guard and
two native controls check this interpretation: the known static ELF entry and
the labelled null load in `fault.c`. The tracer kills and reaps a stopped child
after capture; its final signal 9 is deliberate cleanup, not the original fault.
Raw register memory, vendor instructions, cores and disassembly remain private.

Use a clean qualified LP64 recvmsg `--x11` run as the seed. It must contain the
installed native X sets, original libraries and vendor controls. Input hashes
are checked before use, including inherited guest programs/libraries. Each
invocation copies the stopped disk and NVRAM, mounts a read-only ISO, compiles
the native helpers, checks native/vendor execution before and after, and halts
the guest in `finally`. Run the two modes sequentially:

```sh
python3 scripts/probe-irix-toolchest.py \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw --mode ci
python3 scripts/probe-irix-toolchest.py \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw --mode ordinary
```

A different local qualified seed directory can replace the example. The harness
reads `qualified-result.json` from that directory. If a fresh recvmsg run already
has `status: passed` in `result.json`, preserve a copy as `qualified-result.json`
after reviewing it. An `observed` run needs explicit comparison and review; do
not relabel it solely because the guest booted or shut down cleanly. Output is
under `.work/irix-toolchest/runs/`; `result.json` records source hashes, seed
provenance, cases and decoded syscall records. The harness returns `observed`
after its controls pass: review the boundary observations before claiming a
compatibility result. Preserve every attempt, including earlier X I/O failures.

The staged environment is only `HOME=/tmp/xiri-home`. Tests first omit vendor
resources, then install `system.chestrc`, then app-defaults and locale indexes.
The supplied resource bytes are verified against the desktop inventory and
set readable explicitly after copying from ISO. This does not establish that
all required resources are installed or successfully used.

The diagnostic cases use nice increment 20 to give Xvfb more opportunity to
respond, with a separate ordinary-priority resource case. This changes timing,
not compatibility: unsupported `select` can still stop any launch early.
There is a five-second child deadline, and the tracer waits at most 30 seconds
per stop. No original-IRIX syscall oracle or kernel implementation is added in
this checkpoint; pair and qualify `select`/`xstat` separately next.
