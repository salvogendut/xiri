# Measured IRIX pthread initialization and native signal holds

`prctl(PR_INIT_THREADS=20)` now initializes the first IRIX pthread's signal-hold
state on NetBSD. The adapter follows measured PRDA updates, repeated-call
behavior and fork/exec lifecycle. It synchronizes the hold with native signal
machinery, including changes followed by asynchronous delivery without another
foreign syscall. Thread creation and general pthread support remain open.

The [independent qualification](2026-11-01-irix-init-threads.json) passes
260 NetBSD executions / 860 lifecycle records and 32 asynchronous-signal
controls. Source is `a9e715bb082a755881799234dfdb54abca5a04c1` on the NetBSD
fork's `xiri` branch. The [lab](../../lab/irix-init-threads/README.md) contains
the fixtures, configs, build pins and reproduction commands.

## Original measurements

The accepted IRIX 6.5.22m run is `ci-8hf99523`: 104 executions / 344 records,
covering both ABIs and trap dispatch forms, root and UID1234. It clones the
cleanly halted exploratory run `ci-rmzex766`; its result records the seed hash.
Both reference guests halted cleanly. The exploratory fixtures and sources are
retained privately; they revealed that o32 uses the same hold-word ordering as
n32 on this reference kernel, which the expanded suite then tests explicitly.

| Operation | Observed behavior |
| --- | --- |
| First initialization | Return zero; copy the effective signal mask to PRDA `0x200e70`; OR bit 0 into the flags at `0x200e6c` |
| Unused argument registers | Ignored; the original libpthread call supplies only the operation number |
| Repeated initialization | Return zero without resetting a user-written hold or restoring a cleared validity bit |
| Validity bit forged before initialization | Does not activate the user hold |
| Validity bit cleared after initialization | Does not disable the user hold; kernel state remains authoritative |
| Direct user change / `sigprocmask` change | The effective mask follows the PRDA hold; supported syscall changes update that hold |
| Fork | Child retains the effective mask and hold bytes, gets its own PID, and starts with the validity bit and initialization state cleared |
| Exec | Fresh PRDA contents and initialization state; effective signal mask remains inherited |

Other PRDA fields and unrelated flags survive initialization. The low signal
word is the second word of the big-endian 64-bit hold for both tested ABIs.
This is measured behavior of the supplied kernel, not an assumption from the
host's native `sigset_t` layout. The operation number and PRDA fields also
appear in the historical public NetBSD
[IRIX interface declarations](https://github.com/NetBSD/src/blob/5aca2679d78276864d2980a08314887b2058fb2c/sys/compat/irix/irix_prctl.h).

## Native implementation and boundaries

Per-process emulation data records initialization independently of user memory.
Exec resets it; fork allocates separate child state; exit/native exec frees it.
Only one native LWP and an unshared vmspace are supported. The adapter neither
creates a hidden thread nor substitutes a constant success return for state.

Before foreign syscalls, traps and pending-signal delivery, the adapter copies
the PRDA hold into the existing native mask through `sigprocmask1`. Native-only
bits remain intact, and SIGKILL/SIGSTOP remain unmaskable. A new optional
`emul.e_sigmask` hook in `lwp_userret` handles asynchronous user return. It runs
in the current LWP context without process/LWP locks held. This hook is a core
dependency to upstream or otherwise resolve for the final loadable-module
target; these tests still use built-in custom kernels.

The supported mapping remains traditional IRIX signals 1–31. Realtime signals,
foreign handlers/contexts, thread creation, scheduling and synchronization are
not established by initialization. `PR_GETNSHARE` and `PR_GETSHMASK`, captured
beside the operation, still return ENOSYS; the qualifier explicitly excludes
those fields from parity while retaining their original values in the oracle.

There are 40 explicit PRDA-protection policy cases in the native matrix. IRIX
initializes even after the fixture makes the PRDA read-only or inaccessible;
NetBSD returns EFAULT through checked copy operations, leaving initialization
inactive. The adapter does not bypass UVM protections or recreate the reserved
mapping. After initialization, an unreadable hold terminates with SIGSEGV.

## Verification

| Native run | Lifecycle executions | Records | Asynchronous-signal controls |
| --- | ---: | ---: | ---: |
| LP64 CI, `lp64-ci-2qm8gxav` | 104 | 344 | 12 |
| LP64 ordinary, `lp64-ordinary-yo342ve0` | 104 | 344 | 12 |
| o32 CI, `o32-ci-5uxmp1o9` | 52 | 172 | 8 |

The signal fixtures write their user hold and spin without making another
syscall. A native supervisor uses acknowledged stop/continue barriers to
inspect the actual kernel mask, then sends SIGTERM. The blocking case must
retain a pending signal and remain alive until SIGKILL cleanup; the unblocking
case must terminate from SIGTERM. Native counterparts verify the supervisor.
All 32 observations preserve inherited native SIGINFO/SIGRTMIN mask bits and
verify final process absence.

The matrix also passes 30 native/vendor/descendant-cleanup controls, 32 native
page-zero controls, 32 native-PRDA-absence controls and 20 invalid-PRDA fork
controls. All three guests halt cleanly. The comparison checks exact records
after PID normalization and the documented policy adjustments.

Twelve additional initialized foreign-to-native exec controls pass on the
LP64 and o32 kernels (`lp64-3t_740d4`, `o32-40is4oxx`). The native target checks
that the foreign SIGUSR1 hold and inherited native SIGINFO/SIGRTMIN bits survive,
the PRDA mapping is absent, and native fork/wait returns the child's status.
Both identities and both dispatch forms are covered, with n32 on LP64.
These two guests also halt cleanly.

The main harness received a whitespace-only cleanup after execution. Exact
executed copies remain under each run's `sources/scripts/`; the qualifier
verifies their original hashes and records the source used. Two supplemental
attempts were stopped during boot while correcting the test's native signal
constant. Two later attempts halted cleanly before tests because reboot cleared
the fixtures from `/tmp`; the final harness restages them from hash-checked
media. None of those four diagnostic attempts counts toward the passing matrix.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-init-threads.py \
  --reference .work/irix-reference/init-threads-records-runs/ci-8hf99523 \
  .work/irix-init-threads/runs/lp64-ci-2qm8gxav \
  .work/irix-init-threads/runs/lp64-ordinary-yo342ve0 \
  .work/irix-init-threads/runs/o32-ci-5uxmp1o9 \
  --exec-runs .work/irix-init-threads/exec-runs/lp64-3t_740d4 \
    .work/irix-init-threads/exec-runs/o32-40is4oxx \
  --output docs/results/2026-11-01-irix-init-threads.json
```

IRIS upstream was checked again during this cycle: `upstream/main` remains
`f17b4d3bc1663efd02f93a5e0e4811eebba510c8`, already contained in fork `xiri`
at `13cf2477de9ccbb5e80ecbf5a5de8d85f5df7bf6`. No integration was needed.
These guests retain the qualified emulator revision
`9df1df14334838a989253efefe26f0547e6da592`; the newer fork is not repinned by
this ABI result.

The [original desktop retry](2026-11-01-irix-desktop-init-threads.md) now passes
initialization in all four file/icon launches and reaches session-directory
creation. A rendered Icon Catalog error dialog is diagnostic progress, not a
usable file/icon desktop.
