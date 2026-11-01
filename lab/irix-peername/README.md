# IRIX getpeername lab

This checkpoint adds trap 1093 to the shared o32/n32 personality and reuses
the qualified IPv4 output conversion from getsockname. The [results](../../docs/results/2026-10-31-irix-peername.md)
record the measured interface and the next unchanged Toolchest boundary.

The subsequent [X-client startup checkpoint](../irix-xconnect/README.md)
adds measured hostname, descriptor-control, message-transfer and shutdown
interfaces while retaining this checkpoint's fixture programs unchanged.

## Build

This checkpoint was developed on NetBSD topic branch `xiri/irix-peername`. The local
`.work/netbsd-irix64-src` worktree uses that branch. Earlier TCP and
getsockname branches and kernel outputs remain separate. The [LP64 pin](baseline.json)
and [o32 pin](o32-baseline.json) identify the exact source and inputs.

After preparing the [getsockname lab](../irix-sockname/README.md):

```sh
git -C ../NetBSD-nixbench fetch origin xiri
# Inspect the worktree and use a clean checkout of the pinned source.
git -C .work/netbsd-irix64-src status --short
git -C .work/netbsd-irix64-src switch --detach \
  "$(python3 -c 'import json; print(json.load(open("lab/irix-peername/baseline.json"))["source_revision"])')"
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-peername-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-peername-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-peername/XIRI_IRIX_PEERNAME" \
XIRI_NETBSD_ARCH=mips64eb ./scripts/build-netbsd-kernel.sh all

PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-tcp.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-sockname.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-peername.py
```

Fresh builds use their own tools directory. The qualified local build reuses
the matching cross-tools with separate object/output directories. For o32,
use `XIRI_IRIX_PEERNAME_O32`, `mipseb`, and separate
`.work/netbsd-irix-peername-o32-build` build/TFTP directories. Intentional
rebuilds change kernel timestamps; review and repin both boot and native images.

The builder verifies and freezes all 324 previous fixtures unchanged, then
adds 156 original getpeername probes and an IRIX-only server-address peer.
Its manifest records source hashes, tools and binary hashes under ignored
`.work/irix-peername/probes`.

## Qualify

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/probe-irix-reference-tcp.py --checkpoint peername
python3 scripts/probe-irix-tcp.py --checkpoint peername --mode ci --x11
python3 scripts/probe-irix-tcp.py --checkpoint peername --mode ordinary --x11
python3 scripts/probe-irix-tcp.py --checkpoint peername --mode ci --kernel-abi o32
```

Repeat the established loader, runtime and static regressions with these
kernels and the LP64-capable emulator build:

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/probe-irix-lp64.py --mode ci \
  --pin lab/irix-peername/baseline.json \
  --build-directory .work/netbsd-irix-peername-build
XIRI_IRIS_BIN_DIR="$PWD/.work/target-netbsd64/release" \
  python3 scripts/probe-irix-runtime.py --suite dispatch --mode ci \
  --pin lab/irix-peername/o32-regression.json \
  --kernel-directory .work/netbsd-irix-peername-o32-build/tftp
XIRI_IRIS_BIN_DIR="$PWD/.work/target-netbsd64/release" \
  python3 scripts/probe-irix-experiment.py --suite dispatch-regressions \
  --expect compat --mode ci \
  --kernel-directory .work/netbsd-irix-peername-o32-build/tftp \
  --ident XIRI_IRIX_PEERNAME_O32_20261031
```

The existing echo and local-address peers retain loopback ports 6111 and
6112. The new server on 6113 reports its accepted socket's own address,
using native getsockname on NetBSD and original getsockname on IRIX. Clients
verify that endpoint against the configured port/address before testing
getpeername. The peer keeps each connection open until the client closes it.
All peers must complete their expected requests and exit successfully.

Tests cover connected, never-connected and connection-refused sockets;
zero, truncated, exact, oversized and negative capacities; invalid and
read-only output pointers; bad/closed/non-socket descriptors; output aliasing
and alignment; unusable stacks and delay slots. Direct/indirect o32/n32
forms preserve the full-width n32 saved register. Each 96-byte record
contains return values and 64 guarded output bytes. Selected cases repeat
as UID 1234/GID 5678.

Each run uses a disposable guest and requires clean shutdown. Native file,
swap and vendor asa/echo controls remain in the suite. Native X clients must
work before and after Toolchest on the controlled Xvfb display. Its disabled
authentication applies only inside that disposable guest.

Run emulator suites sequentially to keep host load manageable. After each
batch, check for leftover `iris`/`iris-ci` processes and terminate unused test
instances. The harness normally shuts down the guest and exits its emulator.

The reference harness splits checksum arguments into bounded groups and
archives the directory to avoid IRIX's small command-line limit. Each
background peer saves its actual exit status atomically; the host reads
those files directly because IRIX sh can discard background wait status
and does not support modern command substitution syntax.

Only original probes, interface observations and metadata are committed.
Vendor binaries, media, headers and raw traces remain private ignored inputs.

The [legacy recvmsg checkpoint](../irix-recvmsg/README.md) retains this coverage
and adds received-data, fault-consumption and header-output comparisons. The
latest [Toolchest session diagnosis](../irix-toolchest/README.md) identifies its
later empty-environment crash and the remaining select/xstat boundaries, using
that unchanged kernel. This lab keeps its historical kernel and expectations.

Active development now uses the consolidated [`xiri` branches](../../docs/FORKS.md).
The former topic names in this lab are historical labels; fetch `xiri` and
check out the exact pinned commit to reproduce this checkpoint.
