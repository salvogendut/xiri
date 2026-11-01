# IRIX terminal to native shell

This checkpoint measures descriptor duplication, descriptor bounds, session
creation and 32-bit exec argument/environment vectors on original IRIX, then
exercises their NetBSD implementation. Both foreign ABIs use four-byte pointer
vectors even on the LP64 kernel. Native exec owns lookup, permissions, limits
and the transition to the executable's native personality.

The kernel subset adds `dup` (1041), `execve` (1059), the descriptor-limit query
`ulimit(4)` (1063), `SGI_SETSID` (20) and `SGI_FDHI` (109). FDHI returns one past
the highest currently open descriptor. Misaligned vectors return EFAULT.
Native RLIMIT_NOFILE remains policy; null argv returns native EINVAL, whereas
the original reference shell terminates with status 139. Other ulimit selectors
remain EINVAL. No vendor source is used.

The 19 fixture variants cover o32/n32, direct/indirect traps and root/uid1234:
152 executions on IRIX or LP64 NetBSD, 76 on the o32 kernel. Descriptor records
include holes, closing the highest descriptor, EBADF, first/repeated setsid,
and the getpid/getppid register pair. Exec tests include exact argv/environment
content, empty arguments, null environment, inaccessible paths, invalid and
page-boundary pointers, and unaligned pointer vectors. All bytes of each record
are compared after explicit PID/limit normalization; native EINVAL for null
argv is checked as a separate policy.

## Native session integration

`handoff.c` is an explicit native helper installed as `/usr/libexec/xiri-shell`
inside disposable guests. It receives xwsh's three PTY descriptors, verifies
they refer to the same character device, reopens that device through native
`/dev/pts`, replaces the inherited descriptors, and acquires
the native controlling terminal, sets the foreground process group and an
80x24 window size, records that state, then execs NetBSD `/bin/sh -i`. It does
not implement foreign termios or caught-signal frames. Reopening the native
vnode avoids the observed panic when shell exit revokes a controlling terminal
through the nullfs compatibility view. The captured path is
`exit1 -> VOP_REVOKE -> layer_revoke -> vrelel`, with a reclaimed terminal
vnode retaining writecount 1. General layered-tty teardown remains open.

`ctty-control.c` independently tests native session teardown after master
closure, both directly and after reopening a compatibility alias. The child
receives native SIGHUP; the parent reaps it. Mode 1 is a diagnostic alias-only
variant and is not part of the accepted matrix.

`guard.c` reserves UID1234 for one job, verifies that it is initially unused,
then drops real/effective/saved credentials and supplementary groups before
forking. It follows the reserved identity through native KERN_PROC2 snapshots,
including children that create sessions or outlive the original launcher.
Unprivileged native broadcast SIGKILL checks every target's credentials and
excludes the guard itself; cleanup verifies the reserved identity is absent.
`escape-control.c` independently tests a session descendant that outlives its
launcher. This policy is for fresh, isolated test guests, not a shared login.

`type.c` sends actual XTest keyboard events to a named terminal. The typed
command prints a unique marker, runs native `uname` and `id`, and writes a
marker file. The harness checks that file's exact bytes and owner, records
native tty/session state, and captures the real X framebuffer. Native xterm,
direct original xwsh, and the unchanged winterm launcher are separate cases.
The launcher runs under native `/bin/sh` with explicit WINTERM, PATH and HOME.

## Reproduction

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-shell.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-shell.py

XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-shell-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-shell-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-shell/XIRI_IRIX_SHELL" \
XIRI_NETBSD_ARCH=mips64eb XIRI_BUILD_JOBS=2 \
  scripts/build-netbsd-kernel.sh kernel

PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-shell.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
```

Repeat with `--mode ordinary`. The o32 regression uses the matching
`XIRI_IRIX_SHELL_O32` configuration, `mipseb`, isolated
`.work/netbsd-irix-shell-o32-build` outputs and `--kernel-abi o32 --scope interfaces`.
Builds run sequentially with two compiler jobs. At most four tracked IRIS
instances run concurrently, and each guest shuts down after its observations.
Pins bind the kernels, clean fork revision, emulator and original runtime hashes.

The accepted captures are the original reference `ci-wxmdrkn_`, LP64
`lp64-ci-1fjbm6rb` and `lp64-ordinary-g6g5ohv2`, and the interface-only o32
`o32-ci-6orv7kae`. Independently qualify them and convert the captured winterm
framebuffer to PNG with:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-shell.py \
  --reference .work/irix-reference/shell-records-runs/ci-wxmdrkn_ \
  .work/irix-shell/runs/lp64-ci-1fjbm6rb \
  .work/irix-shell/runs/lp64-ordinary-g6g5ohv2 \
  .work/irix-shell/runs/o32-ci-6orv7kae \
  --output docs/results/2026-11-01-irix-shell.json \
  --png docs/results/images/2026-11-01-irix-winterm-shell.png
```

The o32 interface capture predates the app-only environment, keyboard and
handoff corrections. Its fixture, runner, supervisor and kernel hashes remain
unchanged; it does not execute the app handoff. The qualifier preserves those
historical source hashes while checking its complete interface observations.
See the [result report](../../docs/results/2026-11-01-irix-shell.md) for the
accepted matrix, screenshot and remaining limitations. The kernel pins identify
the clean implementation revision `98f7de3f343`; later documentation commits
do not change the tested binaries.

`--smoke` is bring-up only and excluded from qualification. Raw vendor bytes,
full traces and guest disks stay under ignored `.work`. The bounded trace view
uses raw `kdump -x` and the existing process trace filter because the installed
o32 kdump cannot safely format native LP64 msghdr records. The complete binary
and text traces remain on each stopped guest disk.

The later [4Dwm session](../../docs/results/2026-11-01-irix-4dwm.md) preserves
this native handoff and typed-command proof alongside original Toolchest and
4Dwm on the PRDA kernel. Session saving is disabled; terminal signal, resize,
gettxt and normal-exit limitations remain unchanged.
