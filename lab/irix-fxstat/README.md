# IRIX fxstat lab

This checkpoint measures descriptor-based syscall 1160 on the user's IRIX
6.5.22m installation and implements its bounded o32/n32 contract in the NetBSD
fork. The [result](../../docs/results/2026-10-31-irix-fxstat.md) and
[machine-readable qualification](../../docs/results/2026-10-31-irix-fxstat.json)
record the passing subset and remaining Toolchest boundary. [abi.json](abi.json) records the measured layouts, validation order and
limits. No proprietary source is used.

There are 65 fixture variants, each built for o32/n32 and direct/indirect
syscall dispatch. Root and uid/gid 1234 execute the same 260 ELF files on
original IRIX and NetBSD: 520 guarded records per LP64 run and 260 on o32.
Cases cover regular files, an empty file, directory, FIFO, `/dev/null`, sparse
large files, open modes, closed/reused/invalid descriptors, version selection,
unaligned and inaccessible output, and partial page-boundary copies. An
inherited descriptor for a mode-0000 file remains valid after dropping
credentials. Each 576-byte record contains registers, primary identity, output guards
and an end-of-page snapshot. The reference does not normalize supplementary
groups; final fixtures use permissions that make this irrelevant to descriptor
setup. The earlier mode-0751 directory setup is excluded for that reason.

The native `fstat` observer independently records metadata for each descriptor
class and identity. The host comparator packs these named values into the
measured foreign layout and checks every record byte. Native filesystem
identity, sizes, times and allocation are therefore checked, not ignored.
Filesystem type is explicitly `unknown`; project ID is zero. Version 2 uses
136 bytes on o32 and 152 on n32; version 3 uses 152 for either ABI. The shared
serializer preserves the qualified xstat contract, which is regressed on both
kernels and both LP64 emulator modes.

Build and measure the original reference:

```sh
python3 scripts/build-irix-fxstat.py
python3 scripts/probe-irix-reference-fxstat.py
```

Only original helpers, synthetic records, input hashes and findings are public.
Vendor binaries, disk images, framebuffer captures and raw vendor traces stay
in ignored `.work` directories. Never archive the whole synthetic fixture tree:
it includes a sparse file larger than 2 GiB. The reference harness batches tar
additions and waits for clean power-off.

Build the kernels sequentially with at most two compiler jobs:

```sh
XIRI_BUILD_JOBS=2 \
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-fxstat-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-fxstat-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-fxstat/XIRI_IRIX_FXSTAT" \
XIRI_NETBSD_ARCH=mips64eb scripts/build-netbsd-kernel.sh kernel
```

For o32 use `netbsd-irix-fxstat-o32-build`, `XIRI_IRIX_FXSTAT_O32` and `mipseb`.
Baseline JSON files pin clean source, configs, emulator and kernel hashes.

Focused runs require a stopped, qualified recvmsg LP64 X11 seed containing only
desktop libraries. Each run makes an independent disk copy:

```sh
python3 scripts/probe-irix-fxstat.py \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-fxstat.py --mode ordinary \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-fxstat.py --kernel-abi o32 \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
```

Native/asa/echo controls bracket the workload. LP64 runs launch HOME-configured
Toolchest three times per identity with libraries alone, then with the supplied
menu, app-defaults and locale indexes installed. Each attempt captures syscall
traces, a window tree and a root framebuffer while the bounded child runs.
Native X checks bracket these attempts. Metadata success alone does not qualify
a usable window or event loop.

Regression commands:

```sh
python3 scripts/probe-irix-xstat.py --kernel-checkpoint fxstat --fixtures-only \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-xstat.py --kernel-checkpoint fxstat --fixtures-only \
  --mode ordinary --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-xstat.py --kernel-checkpoint fxstat --fixtures-only \
  --kernel-abi o32 --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-select.py --kernel-checkpoint fxstat --fixtures-only \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-tcp.py --checkpoint recvmsg --kernel-checkpoint fxstat \
  --desktop-expectations lab/irix-fxstat/desktop.json
python3 scripts/probe-irix-tcp.py --checkpoint recvmsg --kernel-checkpoint fxstat \
  --kernel-abi o32
```

Run harnesses on the host; they use host `genisoimage` and launch IRIS through
the existing toolbox wrapper. The current user-authorized limit is four IRIS
instances total. Track each guest through clean shutdown and host process exit.
Kernel builds remain sequential with two jobs.

`scripts/qualify-irix-fxstat.py` rechecks complete focused and xstat records,
current helper sources, raw Toolchest trace decoding, reviewed outcomes,
regression status and clean shutdowns. Supply three focused run directories,
`--xstat-runs` with three regression directories, `--select-run`,
`--transport-runs` with LP64 and o32 directories, and `--output`.
