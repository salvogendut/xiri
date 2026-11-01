# Initial IRIX pthread state

The original file/icon desktop clients previously stopped at
`prctl(PR_INIT_THREADS=20)` after allocating their pthread table. This lab
measures that operation on the user-supplied IRIX 6.5.22m installation and
qualifies a bounded NetBSD adapter. The [result](../../docs/results/2026-11-01-irix-init-threads.md)
passes 260 executions / 860 records, 32 asynchronous-signal checks and 12
initialized foreign-to-native exec controls.

## Measured contract

The 104 reference executions cover o32/n32, direct/indirect traps, root and
UID1234. Thirteen variants check initial and repeated initialization, unused
argument registers, preexisting signal masks, fork, exec, preservation of
unrelated PRDA data/flags, forged/cleared validity bits, user-written masks,
syscall-written masks and PRDA page protections.

Initialization enables a kernel-tracked state, copies the current signal hold
to PRDA `0x200e70` and sets bit 0 at `0x200e6c`, preserving other flags.
Both ABIs use the same big-endian 64-bit hold on this reference kernel, with
traditional signals in the second word. Repeating initialization succeeds
without resetting a user-written mask or restoring a cleared validity bit.
Setting that bit before initialization does not activate the user mask.

Fork inherits the effective native mask and PRDA contents, updates the child
PID, and clears the child's validity bit and initialized state. The child can
initialize independently. Exec creates fresh PRDA contents and resets the
initialization state while retaining the effective signal mask.

## Adapter and limits

The adapter uses per-process emulation data with exec/fork/exit hooks. It
imports the PRDA hold before foreign syscalls, traps and pending-signal
delivery, and updates the hold after a supported `sigprocmask` change.
Native signal machinery strips unmaskable signals and owns pending queues and
delivery. Native-only mask bits survive foreign replacement.

The new optional `emul.e_sigmask` callback in `lwp_userret` runs in the current
LWP context without process/LWP locks held. It handles a PRDA change followed
by asynchronous signal delivery without another syscall. This is an added
core-kernel dependency to resolve for the final loadable-module target, along
with the existing select helper.

This implements initialization for one native LWP and an unshared vmspace.
Thread creation/scheduling, foreign signal handlers, and realtime signals are
separate work. Only the existing traditional signal mapping (1–31) is used.
The accompanying `PR_GETNSHARE` and `PR_GETSHMASK` queries remain unsupported;
their original returns are recorded and excluded from parity comparisons.

PRDA protections remain authoritative on NetBSD: initialization with a
read-only or inaccessible hold returns EFAULT, whereas the reference succeeds.
After initialization, an unreadable hold causes SIGSEGV. Automatic recreation
or privileged writes to the reserved PRDA page are not implemented.

## Independent controls

`signal-spin.c` changes its PRDA hold and spins without making a syscall.
The native supervisor uses acknowledged stop/continue barriers to inspect the
actual native mask, then sends SIGTERM. Blocking must retain a pending signal
until SIGKILL cleanup; unblocking must permit SIGTERM termination. Native
counterparts check the supervisor, and inherited SIGINFO/SIGRTMIN mask bits
check preservation outside the foreign mapping. Both identities and ABIs are
covered. Other controls retain native/vendor execution, descendant cleanup,
PRDA removal on native exec, page-zero policy and invalid-PRDA fork behavior.

## Reproduce

Build LP64 and o32 kernels sequentially with at most two jobs using the configs
here and isolated `.work/netbsd-irix-init-threads[-o32]-build` directories.
Use `scripts/build-netbsd-kernel.sh`, the `xiri` NetBSD checkout and matching
toolchains as described in the preceding AUTORESRV lab.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-init-threads.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-init-threads.py --kernel-abi o32
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-init-threads.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-init-threads-controls.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-init-threads.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-init-threads.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-init-threads.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-init-threads.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --kernel-abi o32
```

The reference harness can clone a previously observed, cleanly halted
reference run with `--seed-directory`; it records that seed's result hash.
`qualify-irix-init-threads.py --reference REF RUN... --output REPORT` requires
the complete three-run native matrix. `--export-reference` records decoded
observations; later qualification must match the recorded reference exactly.

`probe-irix-desktop-init-threads.py` repeats the bounded desktop session with
the new kernel. Runtime binaries, disk clones and raw traces stay in `.work`.

`probe-irix-init-threads-exec.py --seed-directory RUN` clones a stopped full
native run, restages the existing KIND=4 fixtures, and adds the native
`exec-launch.c` / `after-init.c` helpers. Run once for LP64 and once for o32;
pass their directories to `qualify-irix-init-threads.py --exec-runs LP64 O32`.
The native target verifies inherited mask bits, PRDA removal and native
fork/wait after initialized foreign exec.

For the desktop evidence, use
`qualify-irix-desktop-init-threads.py RUN... --png PNG --output REPORT`.
It retains shell/window failures and distinguishes a rendered fatal dialog
from desktop success. See the [desktop report](../../docs/results/2026-11-01-irix-desktop-init-threads.md).

The following [directory-creation lab](../irix-mkdir/README.md) clears mkdir
and advances the original desktop clients beyond their session-directory error.
