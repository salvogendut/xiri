# Initial IRIX TCP client lab

This checkpoint adds IPv4 stream socket creation, connect, TCP_NODELAY,
SO_KEEPALIVE and sginap to the shared o32/n32 personality. SGI_SYSCONF's
_SC_CLK_TCK query returns 100, the unit used by the foreign sleep interface.
See the [results](../../docs/results/2026-10-30-irix-tcp.md) for the exact
qualified behavior and remaining desktop boundary.

## Build

This checkpoint was developed on NetBSD topic branch `xiri/irix-tcp`. The existing
`.work/netbsd-irix64-src` worktree now uses this branch; the earlier
`xiri/irix-lp64` revision and kernel artifacts remain available. The
[LP64 pin](baseline.json) and [o32 pin](o32-baseline.json) identify the source,
configurations, kernels, original runtime files and unchanged IRIS build.

```sh
git -C ../NetBSD-nixbench fetch origin xiri
# Inspect existing worktrees before adding another checkout.
git -C ../NetBSD-nixbench worktree add --detach "$PWD/.work/netbsd-irix64-src" \
  "$(python3 -c 'import json; print(json.load(open("lab/irix-tcp/baseline.json"))["source_revision"])')"

XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-tcp-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-tcp-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-tcp/XIRI_IRIX_TCP" \
XIRI_NETBSD_ARCH=mips64eb ./scripts/build-netbsd-kernel.sh all
```

The qualified local outputs are `.work/netbsd-irix-tcp-build` and
`.work/netbsd-irix-tcp-o32-build`. They use the previous matching cross-tools
with separate object/output directories. Fresh builders should build tools
in their own directory. Source paths are bound to each build directory;
never reuse one with a different source path or target architecture.
For the 32-bit variant, use `XIRI_IRIX_TCP_O32`, `mipseb`, and another build
and TFTP directory. Kernel timestamps affect hashes: inspect and repin an
intentional rebuild before qualification. Both the PROM boot wrapper and
the native `/netbsd` file must match their pin.

Build the original assembly fixtures using the existing mips64 cross-tools:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-tcp.py
```

The builder invokes one Toolbox session and emits 184 test programs plus
an original IRIX-only echo server under `.work/irix-tcp/probes`. The source
contains no vendor code. The manifest records source/tool hashes and exact
fixture bytes. Negative sginap requests and tests using native inherited
sockets are local policy/effect tests, excluded from the original reference.

## Qualify

Prepare the immutable disk/NVRAM seed, asa/echo/runtime extraction, desktop
library closure, and native controls from the [LP64](../irix-lp64/README.md)
and [desktop](../irix-desktop/README.md) labs first.

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/probe-irix-tcp.py --mode ci --x11
python3 scripts/probe-irix-tcp.py --mode ordinary --x11
python3 scripts/probe-irix-tcp.py --mode ci --kernel-abi o32
python3 scripts/probe-irix-reference-tcp.py
```

Every run starts from private disk/NVRAM copies. The native parent independently
captures output, exec errors, exit/signal status and elapsed guest time, with
a 30-second child deadline. Direct/indirect forms cover both foreign ABIs;
the 32-bit kernel runs the o32 subset. Tests check valid operations, bad
file descriptors, malformed lengths/families/options, null/high/wrapping
pointers, o32 stack spill failures, preserved n32 registers and delay slots.
The guest remains usable after the tests and must halt cleanly.

A native NetBSD loopback peer on port 6111 validates the exact eight-byte
payload in both directions. An independent native parent also initializes
an inherited socket option to the opposite value, runs a foreign setter,
and reads the actual option with native getsockopt. These effect tests run
as root and UID 1234/GID 5678. One- and 101-tick sleeps have minimum-duration
checks. Negative durations are explicitly rejected with EINVAL; signal
interruption and the maximum-duration sleep remain unqualified.

Toolchest's closed-display tests use `127.0.0.1:99`; no server listens on
6099. User syscall/return/path traces distinguish genuine ECONNREFUSED from
an unsupported-call display error. The 4Dwm mapping blocker is retained as
a separate regression. Asa, echo and native controls surround the workload.

`--x11` verifies the pinned NetBSD 11.0 X sets, installs them only in that
run's private guest, and starts native Xvfb on display 98. Native xdpyinfo
must complete a TCP connection before and after the foreign clients. The
isolated test display uses no authentication and does not represent a
qualified desktop session. It exercises the client transport independently
of Newport drawing/input. The server stops before shutdown.

`desktop.json` and `desktop-x11.json` pin reviewed startup boundaries,
including exact outputs, termination, console diagnostics, ordered foreign
calls, selected return values and paths. Missing pins yield observations,
not a qualification pass. Raw logs and original vendor bytes remain private.

The original IRIX harness freezes and checks every uploaded fixture, starts
the supplied original-assembly peer, and checks 168 paired cases. It uses
`reference.json` rather than assuming the bounded NetBSD policy matches all
IRIX behavior. A reference delay-slot syscall terminates with shell status
140 (SIGSYS); NetBSD's dispatcher preserves its supported delay-slot behavior.

## Preserve earlier behavior

Run the existing LP64 workload against the new pinned kernel:

```sh
for mode in ci ordinary; do
  python3 scripts/probe-irix-lp64.py --mode "$mode" \
    --pin lab/irix-tcp/baseline.json \
    --build-directory .work/netbsd-irix-tcp-build
done

export XIRI_IRIS_BIN_DIR="$PWD/.work/target-netbsd64/release"
python3 scripts/probe-irix-runtime.py --suite dispatch --mode ci \
  --pin lab/irix-tcp/o32-regression.json \
  --kernel-directory .work/netbsd-irix-tcp-o32-build/tftp
python3 scripts/probe-irix-experiment.py --suite dispatch-regressions \
  --expect compat --mode ci \
  --kernel-directory .work/netbsd-irix-tcp-o32-build/tftp \
  --ident XIRI_IRIX_TCP_O32_20261030
unset XIRI_IRIS_BIN_DIR
```

These are the existing loader, dispatch, heap, native and vendor regressions,
with their expectations preserved. The old harness defaults still select
their previous checkpoints. Build products, firmware, original binaries,
libraries, disk overlays and raw traces stay outside Git.

## Subsequent checkpoint

The [getsockname lab](../irix-sockname/README.md) extends this exact fixture
set and retains separate kernel outputs. Shared probe scripts select it with
`--checkpoint sockname`; the default still reproduces this TCP checkpoint.
Toolchest's later boundary is getpeername (1093).

The [legacy recvmsg checkpoint](../irix-recvmsg/README.md) retains this coverage
and adds received-data, fault-consumption and header-output comparisons. The
latest [Toolchest session diagnosis](../irix-toolchest/README.md) identifies its
later empty-environment crash and the remaining select/xstat boundaries, using
that unchanged kernel. This lab keeps its historical kernel and expectations.

Active development now uses the consolidated [`xiri` branches](../../docs/FORKS.md).
The former topic names in this lab are historical labels; fetch `xiri` and
check out the exact pinned commit to reproduce this checkpoint.
