# IRIX PTY allocation

This lab measures the interfaces used by original libc `_getpty`, then checks
winterm/xwsh on the candidate NetBSD kernel. The checkpoint separates allocator
success from a working terminal: `fork`, signal masks, terminal attributes,
shell execution and interactive input still need qualification.

The adapter accepts legacy `O_NDELAY` and `O_NOCTTY`, translates metadata only
for actual native PTY character devices in the first 400 slots, supplies native
`chmod`/`chown` with explicit 32-bit arguments, and recognizes the exact
`I_STR/UNLKPT` request emitted by libc. Native vnode authorization remains in
charge. In particular, NetBSD rejects unprivileged file giveaways that this
IRIX installation permits. Nonblocking status uses the native canonical `O_NONBLOCK` representation;
this does not reproduce IRIX's separate legacy nonblocking semantics.

`setup.sh` is for a fresh disposable guest, before any PTYs are open. It mounts
native ptyfs with group 0/mode 0600, shares that filesystem under the emulation
root using nullfs, creates a native ptm clone node, and supplies the 400 q/r
slave aliases recognized by the first IRIX device bank. This is an experimental
namespace, not a production session installer. It imports no original device
nodes or account state. The native clone grants the slave to the real UID;
UNLKPT does not grant ownership or bypass permissions. NetBSD has no matching
slave-lock state, so unlock only validates the native master and exact request.

The [qualified report](../../docs/results/2026-10-31-irix-pty.md) retains accepted
runs, exact counts, policy differences and reproduction commands.

## Measurements

- `native.c`: repeated native allocation, raw data in both directions,
  nonblocking empty reads, closure and reuse; root and uid 1234.
- `fixture.c`: original test source built with the supplied IRIX GCC 3.3 and
  linked to its libc. The n32 executable is private and pinned in
  `libc-fixture.json`. The installed o32 compiler attempts failed; the separate
  libc-free probes cover that ABI without requiring the old compiler.
- `probe.c`/`start.S`: fixed 84-byte records, 58 operation variants for each of
  o32/n32 and direct/indirect dispatch, two identities with no supplementary
  groups. Records preserve call results, flags, selected metadata, IDs,
  stat-buffer guards and the input unlock request. Path failures, malformed
  pointers, permission denials and unsupported selectors are included.
- The original libc observer checks allocation and slave opening; the winterm
  observer retains native PTY, ptrace and font controls and records exact
  original-app trace boundaries and window trees.

Build the libc-free fixtures, then collect the original reference:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-pty.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-pty-records.py
```

The optional original-IRIX survey and compiler measurement use
`probe-irix-reference-pty.py` and its `--measure` option. Binary bytes,
disassembly, raw traces and disposable disks stay under ignored `.work`.

Build `XIRI_IRIX_PTY` and `XIRI_IRIX_PTY_O32` sequentially with two compiler jobs
at most, using the authorized NetBSD worktree and separate build/TFTP outputs.
The baseline JSON files pin source, emulator and kernel hashes. For the LP64
kernel, with the cross tools already prepared:

```sh
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-pty-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-pty-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-pty/XIRI_IRIX_PTY" \
XIRI_NETBSD_ARCH=mips64eb XIRI_BUILD_JOBS=2 \
  scripts/build-netbsd-kernel.sh kernel
```

For o32 use `mipseb`, `XIRI_IRIX_PTY_O32`, and the separate
`.work/netbsd-irix-pty-o32-build` output/TFTP directories. Run host-side
harnesses with the stopped font/locale seed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-pty-records.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-pty-records.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-pty-records.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --kernel-abi o32
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-pty-libc.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-winterm-pty.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
```

Repeat the last two with `--mode ordinary`. Each harness owns and halts its
guest. Keep at most four instances alive, including the original oracle.
Capture-only results remain uncompared until `qualify-irix-pty.py` checks every
record against the oracle and explicit policy. `qualify-irix-winterm-pty.py`
checks both modes of original libc and winterm observations against native
controls. Accepted paths and commands belong in the checkpoint report.
