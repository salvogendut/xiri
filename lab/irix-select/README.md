# IRIX select lab

Follow-up: the [xstat checkpoint](../../docs/results/2026-10-31-irix-xstat.md) implements the next pathname-stat contract. This lab retains the historical select-kernel results. Use `--kernel-checkpoint xstat --fixtures-only` to check its guarded select matrix on the newer kernel.

This follows the [Toolchest session diagnosis](../irix-toolchest/README.md).
The new adapter implements trap 1100 for both o32 and n32, with explicit 32-bit
arguments/timeval fields and native scan/wait machinery on owned fd-set storage.
The [ABI notes](abi.json) describe the measured rules and two explicit limits.
Xiri helper/probe sources and metadata are public; vendor inputs and raw guest
artifacts remain in `.work`.

The original-IRIX oracle has 276 fixtures (69 cases in four ABI/dispatch forms).
Each reports 512 bytes: return registers, guarded sets, the original timeval,
and a post-wakeup data/EOF observation where relevant. Tests cover bits 31, 32
and 63; unique descriptor counts across sets; aliasing; invalid, unaligned and
read-only pointers; validation/copyout order; timeouts; and delayed TCP data/EOF.
The peer performs an explicit handshake before a 300 ms delay, or keeps a stream
idle for timeout/writable checks. Original IRIX and NetBSD have independent
peers whose case/mode logs are checked.

IRIX counts distinct descriptors rather than ready bits. It still copies later
sets after a copyout error. Forwarding directly to native `select` would miss
both rules. A small kernel-storage entry point in `sys_select.c` reuses the
native wait/notification protocol; the IRIX adapter owns marshalling, final-word
preservation, unique counting and copyout behavior. Native select/poll entry
points retain their existing behavior.

Two cases intentionally differ from IRIX: positive nfds above 1024 returns
EINVAL, and selecting an invalid descriptor within the requested range returns
EBADF even where IRIX ignores the tested high bit. The latter suggests internal
scan-range truncation; this lab does not infer a complete IRIX fd-table allocator.
Negative nfds follows the measured zero-descriptor behavior. Signal delivery and
concurrent fd/set changes remain outside qualification.

## Qualification

The [result report](../../docs/results/2026-10-31-irix-select.md) and
[evidence](../../docs/results/2026-10-31-irix-select.json) record 1,380 guarded
select executions, 28 additional syscall-timed executions, 24 staged Toolchest
launches and 1,925 unchanged transport/control regressions. All six final
NetBSD guests halted cleanly. Toolchest now gets past select and stops at
unsupported version-2 xstat; no window or event loop is qualified.

## Reproduce

The user's NetBSD fork branch is `xiri/irix-select`. [baseline.json](baseline.json)
and [o32-baseline.json](o32-baseline.json) pin its source, kernels and emulator.
Use separate output directories and at most two build jobs. Reusing the matching
cross-tools requires preserving their `build-arch` marker in the new directory.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/build-irix-select.py
python3 scripts/probe-irix-reference-select.py
XIRI_BUILD_JOBS=2 \
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-select-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-select-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-select/XIRI_IRIX_SELECT" \
XIRI_NETBSD_ARCH=mips64eb ./scripts/build-netbsd-kernel.sh kernel
```

Build o32 separately using `XIRI_IRIX_SELECT_O32`, `mipseb`, and the
`.work/netbsd-irix-select-o32-build` build/TFTP directories. Rebuilds change
kernel timestamps; review and repin matching boot/native images together.

Run every emulator suite to completion before starting the next:

```sh
python3 scripts/probe-irix-select.py --mode ci \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-select.py --mode ordinary \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-select.py --mode ci --kernel-abi o32 \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-tcp.py --checkpoint recvmsg --kernel-checkpoint select --mode ci
python3 scripts/probe-irix-tcp.py --checkpoint recvmsg --kernel-checkpoint select --mode ci --kernel-abi o32
python3 scripts/probe-irix-select-timing.py \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-v4xcbcmn
```

The focused harness requires a clean qualified recvmsg LP64 X11 seed, copies its
disk/NVRAM, verifies inherited binaries/libraries, and installs the matching
native kernel from a read-only ISO. Every select fixture runs under root and
non-root IDs. Native o32 and vendor asa/echo controls bracket the run (n32 is
omitted on the o32 kernel). Socket delays and timeouts have independent minimum
elapsed-time checks; the native parent enforces a five-second child deadline.
Those parent times include launch and post-select draining. A separate timing
harness uses a clean passed LP64 transport-regression seed (replace the example
path above with your own run). It compares 28 unchanged guarded fixtures and
pairs timestamped kernel entry/return records to isolate time inside select.
The installed o32 `kdump` reads only the zero high half of the LP64 nanoseconds
word. Timing therefore decodes the [binary header layout](trace-layout.json)
explicitly; its offsets and field widths were checked against the pinned kernel
DWARF. Raw trace files remain private.
It checks delayed data/EOF and null-time waits against a 150 ms lower bound,
and 100 ms idle timeouts against a 90 ms lower bound; immediate ready/empty
calls provide comparison measurements. It uses the same independent peer and
brackets the run with native controls. These are bounded wait checks, not a
precision timer or signal-interruption qualification.

LP64 also repeats Toolchest twelve times with an explicit HOME, at normal
priority, first with libraries alone and then with the supplied menu,
app-defaults and locale indexes. Native TCP X controls bracket those launches.
The expected next boundary is the unsupported version-2 xstat configuration
check. Each trace is compressed on the guest and transferred as hex through the
existing serial console; the original raw text is restored and retained on the
host. This changes evidence transport, not the observed program.

The legacy harness's `--kernel-checkpoint select` option runs unchanged recvmsg
fixtures and expectations against the new kernel. Its default still reproduces
the historical kernel. Results include source/fixture hashes and clean-shutdown
status. Review all observations before promoting a run to qualified, and check
that no `iris` or `iris-ci` processes remain.
