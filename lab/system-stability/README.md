# Native system stability

This cycle precedes further per-application repairs. Its starting evidence is
the two native child-control stalls in the catalog bootstrap exclusions, the
catalog batch's failed halt, and the transient ten-second native XTest timeout
during the Acrobat image checks. None yet establishes a shared cause.

The fixture setup also exposed lost CD9660 ownership/mask fields in native
NetBSD32 mount translation. `cd9660.c` exercises the real mount system call,
modern and legacy sizes, zero-length legacy calls, ownership/masks, unprivileged
reads, legacy updates, guarded buffers, truncated arguments and copy faults.
`cd9660_mount.h` is the original NetBSD header retained with its license because
the guest's installed development headers do not include it. Baseline images
record the known CD regression failures separately from stability coverage;
a candidate core must pass every CD check.

Run the maintained probe with an explicit qualified bundle:

```sh
python3 scripts/probe-system-stability.py \
  --bundle .work/images/xiri-netbsd-desktop-20261104-acrobat
```

The default is three sequential cold boots, two xiritest sessions per boot,
100 input iterations per transport/desktop and 20 pairs of native detached-child
tests per greeter/IRIX session. It uses ordinary graphical IRIS, a host virtual
display, the bundle's exact emulator and immutable qualification NVRAM, and a
disposable disk overlay. It does not alter the manual image or runtime.

`--kernel-build .work/netbsd-stability-build` verifies and installs that build's
core, boot wrapper and matching module into the clone, halts and reboots it,
then runs the tests. `--seed RUN` can instead clone a cleanly halted candidate
run with exactly matching kernel/module artifacts. The source result and disk
overlay are hashed; the original seed remains unchanged. A cleanly halted
diagnostic failure is a valid starting state, not a qualification pass. The
candidate must still complete all checks after the new cold boot.

`xinput.c` opens a private native event-receiver window. Each iteration opens a
new X connection, moves the pointer, sends press/release with the original
helper's timing, checks both received events, and closes the sender. Every
blocking phase has BEGIN/END monotonic timestamps. An independent alarm emits
`XINPUT_TIMEOUT` and exits 124; Xlib is never called from the signal handler.
Local Unix and loopback TCP transports run at the greeter, under 4Dwm as
xiritest and under standard ctwm as netbsdtest. A deliberately held X server
first verifies timeout detection and recovery; that expected failure is
reported separately.

`guard-loop.sh` repeats the survey's native orphan controls with strict status,
completion-marker and descendant-cleanup checks. The original adversarial
session tests additionally cover double-fork/setsid, child bursts, failed exec,
leader failure, signals and logout while preserving an independent process
of the same user. The catalog's observer variant and installed session guard
remain distinct. No UID-wide termination is used.
The live-burst fixture waits for all 25 intended processes before teardown;
a fixed startup timer can stop it early when paging slows native forks. Its
exact ownership-count check remains mandatory. The completion burst retains
its 49-process check with a bounded minute to finish under load.

Every boot must return both users to the full-size xdm greeter and finish with
the kernel's clean-unmount and halt markers. `--halt-active` logs into 4Dwm
again before shutdown to exercise the service shutdown hooks with active
desktop clients as well. A successful run records bounded
coverage; it does not by itself explain earlier intermittent failures.
`--pressure-mib 96` holds a bounded native allocation with dirty pages across
the session tests. Before/during VM counters record the actual memory load;
there is no assumption that requesting memory necessarily forces paging.
This covers process creation under pressure and, with `--halt-active`, shutdown
with an independent native job still alive. The fixture responds to TERM and
has a separate 30-minute lifetime limit. Without active shutdown the probe
explicitly releases and waits for it before halting.
Results, source hashes, guest logs, screenshots and CPU/kernel diagnostics
are retained in `.work/system-stability/boot-*`. `--debug-failure` exposes the
same bounded request-file diagnostic interface as the catalog probe before
cleanup. All owned emulators are stopped even on failure.

The [first cycle report](../../docs/results/2026-11-04-system-stability.md)
separates primary qualification, diagnostic failures and manual continuations.
Each run retains its exact harness and media. The maintained runner's installed
artifact fields contain only verified hashes; the input bundle pin and candidate
build ledger remain separate to avoid attributing the replacement core to the
input image's source revision.
