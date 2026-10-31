# IRIX X-client startup interfaces

This checkpoint extends the qualified socket-address queries with gethostname,
fcntl, sendmsg and shutdown. It retains the earlier fixture bytes and uses
original probes to compare the next interfaces with the supplied IRIX image.
The [results](../../docs/results/2026-10-31-irix-xconnect.md) describe the measured
contract, its limits and the subsequent Toolchest behavior.

## Build

Use the user's NetBSD fork branch `xiri/irix-xconnect`. The local worktree is
`.work/netbsd-irix64-src`; the exact source and inputs are recorded in
[baseline.json](baseline.json) and [o32-baseline.json](o32-baseline.json).
Earlier checkpoint branches and build outputs remain available.

After preparing the [peername lab](../irix-peername/README.md):

```sh
export PYTHONDONTWRITEBYTECODE=1
git -C ../NetBSD-nixbench fetch origin xiri/irix-xconnect
# Inspect the worktree and use a clean checkout of the pinned source.
git -C .work/netbsd-irix64-src status --short
git -C .work/netbsd-irix64-src switch --detach \
  "$(python3 -c 'import json; print(json.load(open("lab/irix-xconnect/baseline.json"))["source_revision"])')"
python3 scripts/build-irix-xconnect.py
XIRI_BUILD_JOBS=2 \
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-xconnect-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-xconnect-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-xconnect/XIRI_IRIX_XCONNECT" \
XIRI_NETBSD_ARCH=mips64eb ./scripts/build-netbsd-kernel.sh all
```

For o32, use `XIRI_IRIX_XCONNECT_O32`, `mipseb`, and separate
`.work/netbsd-irix-xconnect-o32-build` build/TFTP paths. The local builds reuse
the matching cross-tools, with separate object directories. Rebuilding changes
kernel timestamps: review and repin the boot and native kernel images together.

## Qualification

Run emulator suites sequentially, waiting for each clean shutdown:

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/probe-irix-reference-tcp.py --checkpoint xconnect
python3 scripts/probe-irix-tcp.py --checkpoint xconnect --mode ci --x11
python3 scripts/probe-irix-tcp.py --checkpoint xconnect --mode ordinary --x11
python3 scripts/probe-irix-tcp.py --checkpoint xconnect --mode ci --kernel-abi o32
```

The original echo, local-address and peer-address helpers retain ports
6111–6113. The new helper on loopback port 6114 records the actual bytes
received from each message/shutdown probe. Its fixed records include the
fixture ID, byte count and a padded 16-byte payload. Selected write-shutdown
cases require an acknowledgment after the peer receives EOF, before the
client closes its read side. Each helper must complete and exit successfully.
The harness finishes the earlier socket cases before the new startup cases,
so the older peers retain their original alarm deadlines. Desktop traces use
`kdump -x`: the guest decoder is o32 and cannot safely interpret native LP64
message-header records as its own structures. The host decodes the raw
foreign call/return records and still compares the traced path names.

A native parent also observes file-status changes made by selected foreign
fcntl children on a shared socket. This checks that flag changes affect the
native descriptor. Descriptor close-on-exec bits are queried directly; an
IRIX exec transition remains outside this checkpoint.

The NetBSD guest's hostname is set to `IRIX` for paired guarded-output tests,
matching the reference installation. This changes only the disposable guest;
the wrapper reads the current native hostname rather than a fixed string.

Native file/swap controls and unchanged vendor asa/echo remain in the socket
suite. The X route requires native clients before and after Toolchest against
a disposable Xvfb display with authentication disabled. Check that no unused
`iris` or `iris-ci` processes remain after the batch.

Only original probes, interface metadata and evidence summaries enter Git.
Vendor media, headers, libraries, applications and raw traces stay under
ignored `.work`. The eventual full desktop on NetBSD/X.org follows the
[desktop acceptance plan](../../docs/ROADMAP.md#milestone-3-original-desktop-proof)
and the supplied SGI interface guidelines after IRIX X applications work.
