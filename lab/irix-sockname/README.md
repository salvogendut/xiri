# IRIX getsockname lab

This checkpoint extends the [TCP client lab](../irix-tcp/README.md) with
trap 1094 in the shared o32/n32 dispatcher. It translates the native IPv4
socket address into the foreign 16-byte layout and qualifies output lengths,
copyout errors and independently observed connected addresses.

See the [results](../../docs/results/2026-10-31-irix-sockname.md) for the
measured contract and the subsequent Toolchest startup boundary.

## Build

NetBSD source is on `xiri/irix-sockname` in the user's fork. The local
`.work/netbsd-irix64-src` worktree uses this branch; previous TCP and LP64
branches and their separate kernel outputs remain available. The
[LP64 pin](baseline.json) and [o32 pin](o32-baseline.json) identify the exact
source, kernel configuration, emulator, seed and vendor runtime inputs.

After preparing the existing TCP lab's tools and inputs:

```sh
git -C ../NetBSD-nixbench fetch origin xiri/irix-sockname
# Inspect the existing worktree and use a clean checkout of the pinned source.
git -C .work/netbsd-irix64-src status --short
git -C .work/netbsd-irix64-src switch --detach \
  "$(python3 -c 'import json; print(json.load(open("lab/irix-sockname/baseline.json"))["source_revision"])')"
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-sockname-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-sockname-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-sockname/XIRI_IRIX_SOCKNAME" \
XIRI_NETBSD_ARCH=mips64eb ./scripts/build-netbsd-kernel.sh all

PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-tcp.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-sockname.py
```

Fresh builds should use their own tools directory. The qualified local build
reuses matching cross-tools with a separate object directory. For the o32
kernel use `XIRI_IRIX_SOCKNAME_O32`, `mipseb`, and the separate
`.work/netbsd-irix-sockname-o32-build` build/TFTP directories. Rebuilt kernel
timestamps affect hashes; review and repin both native and boot images before
qualification.

The fixture builder verifies and copies the existing 184 TCP probes without
changing their bytes, then adds 140 original getsockname probes and an
IRIX-only address peer. All generated objects, binaries and manifests remain
under ignored `.work/irix-sockname/probes`.

## Qualify

Prepare the private vendor inputs, desktop library closure and pinned native
X sets as described by the TCP lab. The shared harness retains `tcp` as its
default; explicitly select this checkpoint:

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/probe-irix-reference-tcp.py --checkpoint sockname
python3 scripts/probe-irix-tcp.py --checkpoint sockname --mode ci --x11
python3 scripts/probe-irix-tcp.py --checkpoint sockname --mode ordinary --x11
python3 scripts/probe-irix-tcp.py --checkpoint sockname --mode ci --kernel-abi o32
```

Each run uses a disposable guest and requires clean shutdown. The TCP echo
peer stays on loopback port 6111. A separate address peer on port 6112 sends
the client's address returned by native accept. Connected foreign probes
compare the returned family, port and address with that independent observation
before normalizing the ephemeral port in their records. Getsockname padding
and guards remain in the record and are checked separately. Both peers must
finish the expected number of requests successfully. On IRIX, each peer’s
wrapper saves its actual exit code atomically because the shell can lose
background wait statuses during a large suite. Directory archiving avoids
the reference system’s small command-line size limit.

The new records contain the usual 32-byte result header and 64 bytes of
output memory initialized with guards. Cases cover capacities 0 through 32,
INT_MAX and -1; invalid, closed and non-socket descriptors; null, high,
wrapping and read-only pointers; unaligned and overlapping outputs; unusable
stacks; delay slots; unbound and connected sockets. Both direct/indirect
traps and o32/n32 argument layouts are exercised. Selected cases also run
as UID 1234/GID 5678.

The native runner bounds each child. Native file/swap controls, vendor
asa/echo and the existing TCP tests remain in each applicable run. The X
route verifies native clients before and after Toolchest. Authentication is
disabled only on this disposable guest's Xvfb display.

Only original test source, interface observations and hashes are committed.
Vendor binaries, headers, media and raw traces remain private ignored inputs.

The subsequent [getpeername lab](../irix-peername/README.md) qualifies the peer-address query and its connection-state/error ordering. Toolchest passes both address queries and next encounters hostname, descriptor-control and message-transfer requirements. This lab retains its historical boundary pins.
