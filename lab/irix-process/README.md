# Bounded IRIX process interfaces

Later checkpoint: [original winterm now runs a native interactive shell](../../docs/results/2026-11-01-irix-shell.md), with measured descriptor/session/exec interfaces and actual keyboard input.

This lab measures fork, the getpid/getppid register pair, traditional signal
masks and positive-child exit waits against the supplied IRIX 6.5.22m system.
It then observes original winterm/xwsh with the candidate NetBSD kernel.
The [checkpoint report](../../docs/results/2026-11-01-irix-process.md) records
accepted runs and the remaining terminal/session boundary.

The 118 operation variants use o32 and n32, direct and indirect calls, and
root/uid 1234 with empty supplementary groups. That gives 944 original-IRIX
executions. Each mask case emits one guarded 256-byte record; each fork case
emits parent-before, child and parent-after records. The fork records check
both return registers, PID relationships, private memory changes, a shared
file offset, signal-mask inheritance and child-exit consumption. The native
matrix reuses private fixture files: every case reopens the immutable shared
file, and the FIFO empties when the previous, fully reaped group closes it. A FIFO holds
the child alive for deterministic WNOHANG observations. Pointer tests include
NULL, high/wrapped addresses, unaligned and aliased storage, read-only text,
and a range spanning the final mapped page.

`inspect.c` is an independent native supervisor. It holds each process on a
pipe while reading KERN_PROC2 identities and native signal masks, then releases
it and verifies complete process-group cleanup. Native SIGINFO and SIGRTMIN
mask bits deliberately survive foreign mask replacement. `native.c` supplies
independent mask/fork controls before and after each matrix. Existing native
o32, original asa and original echo controls also run before and after.

The adapter maps traditional signals 1–31; checkpoint/realtime masks remain
outside the subset. All four input words are read and all four output words
written, but unsupported mask bits are ignored/reported zero. Native-only
inherited bits are preserved. Signal delivery, handlers, context restoration
and interrupted/restarted calls are not qualified by these mask tests.

`waitsys` accepts positive P_PID with WEXITED and optional WNOHANG/WNOWAIT.
Other selectors/options return EINVAL before consuming a child; non-NULL
resource-usage requests return ENOSYS. NULL info gives EINVAL. Unmapped info
ranges give EFAULT before consumption; a read-only mapped destination faults
during copyout after consumption, matching the measured reference cases.
Exit records contain zero accounting and owned zero padding. The original
system returns undefined bytes in its siginfo padding: those bytes stay private
and are removed from the exported oracle. PIDs are canonicalized only after
checking their relationships. Signal-caused child deaths and accounting are
outside this qualification.

Build fixtures and collect the original oracle:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-process.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-process.py
```

Build the two kernels sequentially, at most two compiler jobs. For LP64:

```sh
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-process-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-process-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-process/XIRI_IRIX_PROCESS" \
XIRI_NETBSD_ARCH=mips64eb XIRI_BUILD_JOBS=2 \
  scripts/build-netbsd-kernel.sh kernel
```

For o32 use mipseb, XIRI_IRIX_PROCESS_O32 and the separate
`.work/netbsd-irix-process-o32-build` output/TFTP directories. Baseline JSON
files pin the clean source revision and all kernel/emulator inputs.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-process.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-process.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-process.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --kernel-abi o32
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-winterm-process.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
```

Repeat the winterm observer with `--mode ordinary`. It retains native PTY,
font/window and ptrace controls. Its new group-owning runner is also checked
with a native program that deliberately leaves a sleeping descendant behind.
Each foreign run must prove the entire owned group is absent afterward.
Before enabling foreign setsid/process-group changes, extend this supervision
to track descendants that leave the inherited group.

`--smoke` is available for initial process/reference diagnosis. Smoke runs
cannot satisfy `qualify-irix-process.py`, which requires the complete matrix,
both LP64 modes, the o32 run, exact source hashes and clean shutdowns. Raw
vendor bytes, disassembly, traces and disks stay in ignored `.work`. Keep at
most four IRIS instances running and stop all owned guests when finished.
