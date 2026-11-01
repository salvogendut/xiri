# IRIX signal reference lab

Measure raw sigaction (1162), trampoline delivery, sigreturn (1088) and
SIGCHLD wait-any (1170) on the supplied IRIX 6.5.22m installation. The
[result](../../docs/results/2026-11-01-irix-signal-reference.md) separates
observed behavior from the pending NetBSD implementation.

`probe.c`, `start.S`, `trampoline.S` and `fpu.S` are independent, libc-free
fixtures. They share only the existing six-argument syscall bridge and link
script from `irix-mmap-local`. The builder uses the pinned NetBSD cross tools
in the `xiri-iris` toolbox, sequentially, and writes hashes to
`.work/irix-signal/probes/manifest.json`.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-signal.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-signal.py \
  --seed-directory .work/irix-reference/time-records-runs/ci-cmkx7nzx
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-signal-reference.py \
  .work/irix-reference/signal-records-runs/ci-owmvsiu2 \
  --output docs/results/2026-11-01-irix-signal-reference.json
```

Use the newly printed run directory when reproducing. `--smoke` selects five
variants for an initial check; it does not qualify the full matrix. The
reference runner clones a halted seed, freezes fixture ELFs, checks every
guest upload, collects outputs and halts the guest before exiting. All accepted
executions complete within their ten-second per-process watchdog. Child cases
create one immediately exiting child and explicitly reap it. The watchdog
does not establish general descendant cleanup for arbitrary new fixtures;
extend supervision if adding persistent descendants. Respect the four-IRIS
ceiling and verify no owned emulators remain afterward.

## Matrix

Sixty variants × two ABIs × direct/indirect dispatch × root/UID1234 give 480
executions. Forty-five variants cover registration, signal bounds, flags,
handler values, null/high trampoline, mask filtering, null/unaligned/high/
cross-page/read-only pointers and combined errors. Fifteen exercise legacy
and SA_SIGINFO delivery, NODEFER, RESETHAND, action masks, child notification,
reaping, FPU restoration and four invalid sigreturn pointer combinations.

An independently written trampoline records full GPR values before its C
handler. `save_gpr` emits real MIPS III SD instructions because o32 GAS's `sd`
macro otherwise stores two 32-bit registers. k0 is used for capture and its
slot is zero. No installed IRIX headers or libraries enter the build. The
start code leaves readable stack headroom for the 1024-byte frame observation.
FPU instructions are explicit despite the C observer using soft-float.

## Record format

Each output is 512 big-endian 32-bit words (2048 bytes). Return triples are
V0, V1 and A3; V1 is seeded with `0xfeedface`. Indices below are words unless
stated otherwise. Consult the source for unused zeros.

| Words | Meaning |
| --- | --- |
| 0–3 | Magic `58534947`, case, kind (registration/self/child), flags |
| 4–9 | Real/effective UID/GID, PID, parent PID |
| 10–15 | Signal, handler, trampoline, page size, mapped base, handler count |
| 16–24 | Registration, query and trigger return triples |
| 25–31 | Child PID; pre-delivery WNOWAIT and final positive-child wait returns |
| 32–38 | Handler mask-query return and four mask words |
| 39–47 | Handler action-query, wait-any and local-mask-change returns |
| 48–54 | Post-return mask-query result and restored mask |
| 56–63 | Handler's queried action (interpret for delivery cases only) |
| 64–73 | Old-action buffer, including guard bytes |
| 80–111 | Handler wait-any siginfo, 128 bytes |
| 112–119 | Last 32 bytes before the inaccessible page |
| 120–122 | Invalid sigreturn's error triple |
| 128–191 | Entry GPRs: 32 × 64-bit; k0 excluded |
| 192–447 | 1024 context bytes, including unqualified padding |
| 448–479 | SA_SIGINFO record, 128 bytes |
| 480–489 | Pre-delivery action query, including guards |
| 490–498 | Four seeded 64-bit FPU values and FCSR before delivery |
| 500–508 | Same FPU values and FCSR after return |
| 509–510 | FPU mode and bad-return variant |

The independent qualifier computes expected fields instead of accepting
observer success alone. It verifies partial copyouts, unchanged dispositions
after output faults, signal masks, entry relationships, ABI-specific frame
offsets, saved syscall PC, successful return dispatch, FPU restoration and
child reaping. Reserved action bytes and unrelated frame contents are not
promoted to an interface contract. The normalized public JSON pins sources,
fixtures, tool versions, emulator, firmware, seed and raw archive hashes.
Vendor binaries, full contexts and the diagnostic smoke archive remain local.
