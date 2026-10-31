# IRIX legacy recvmsg lab

Follow-up: the [Toolchest session diagnosis](../../docs/results/2026-10-31-irix-toolchest-session.md) identifies the later SIGSEGV as an empty-environment `HOME` null dereference. Supplying `HOME` exposed unsupported `select` and configuration `xstat` calls. The later [select adapter](../../docs/results/2026-10-31-irix-select.md) implements the measured readiness/timeout subset; `xstat` remains next. The historical observations below are preserved.

This checkpoint measures trap 1099 after the [X-client startup checkpoint](../irix-xconnect/README.md)
let Toolchest complete X setup. It retains all 844 earlier fixture programs
and adds 276 guarded receive probes (1,120 programs in total) for direct/indirect o32 and n32 calls.
The [results](../../docs/results/2026-10-31-irix-recvmsg.md) describe the
qualified subset, differences from original IRIX and the next desktop boundary.

## Build

Use the user's NetBSD fork branch `xiri/irix-recvmsg`, with the exact revision
and kernel hashes recorded in [baseline.json](baseline.json) and
[o32-baseline.json](o32-baseline.json). The local source worktree is
`.work/netbsd-irix64-src`; older branches and build outputs remain separate.

After preparing the preceding lab:

```sh
export PYTHONDONTWRITEBYTECODE=1
git -C ../NetBSD-nixbench fetch origin xiri/irix-recvmsg
git -C .work/netbsd-irix64-src status --short
# Use a clean checkout of the pinned revision.
git -C .work/netbsd-irix64-src switch --detach \
  "$(python3 -c 'import json; print(json.load(open("lab/irix-recvmsg/baseline.json"))["source_revision"])')"
python3 scripts/build-irix-recvmsg.py
XIRI_BUILD_JOBS=2 \
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-recvmsg-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-recvmsg-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-recvmsg/XIRI_IRIX_RECVMSG" \
XIRI_NETBSD_ARCH=mips64eb ./scripts/build-netbsd-kernel.sh all
```

For o32 use `XIRI_IRIX_RECVMSG_O32`, `mipseb`, and separate
`.work/netbsd-irix-recvmsg-o32-build` build/TFTP directories. The local builds
reuse the matching cross-tools with separate object directories. Intentional
rebuilds change timestamps; review and repin boot and native kernel images together.

## Qualification

Run each emulator suite to completion before starting the next:

```sh
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/probe-irix-reference-tcp.py --checkpoint recvmsg
python3 scripts/probe-irix-tcp.py --checkpoint recvmsg --mode ci --x11
python3 scripts/probe-irix-tcp.py --checkpoint recvmsg --mode ordinary --x11
python3 scripts/probe-irix-tcp.py --checkpoint recvmsg --mode ci --kernel-abi o32
```

The original peers retain loopback ports 6111–6114. A new source peer on
6115 sends a readiness byte followed by eight known bytes and a write-half
shutdown. EOF-only cases omit the payload; empty nonblocking cases keep the
peer's write half open until the client closes. Each client waits for readiness
before the tested call. The peer records the fixture ID, mode and transmitted
payload length, and accepts EOF or a TCP reset when the client closes.

Each new 192-byte fixture record contains return registers, guarded payload
and name buffers, the full legacy header after the call, and a follow-up drain
of the remaining queued data. Static fixture addresses keep the header
snapshot comparable across the two operating systems. Input vectors are
checked for unexpected mutation. The 1,072 paired cases include 272 new
receive cases; four additional receive programs test explicit flag rejection.
The [ABI notes](abi.json) record field offsets and the measured contract.
Read-only header length-copyout faults are deliberately ignored, matching IRIX. The records distinguish an error before
receiving from a copyout failure after data has already been consumed.

The previous socket cases run first to preserve their peers' original alarm
deadlines. Every peer must finish successfully. Native file/swap and unchanged
asa/echo controls remain in the suite. The LP64 X route requires native clients
before and after Toolchest on a disposable Xvfb display. Raw `kdump -x` output
avoids interpreting LP64 kernel message structures with the guest's o32 decoder.

Check for leftover `iris`/`iris-ci` processes after the batch. Original media,
headers, vendor binaries and raw traces stay in ignored `.work`; Git contains
original probes, interface metadata and evidence summaries. The full desktop
acceptance plan remains in the [roadmap](../../docs/ROADMAP.md#milestone-3-original-desktop-proof).


The [SIOCNREAD checkpoint](../irix-siocnread/README.md) regresses this transport
suite using `--kernel-checkpoint siocnread` on LP64 and o32. For LP64, pass
`--desktop-expectations lab/irix-fxstat/desktop.json` to retain the already
reviewed metadata-related trace changes on the unused display. This is separate
from the active-X Toolchest rendering checks in the SIOCNREAD lab.
