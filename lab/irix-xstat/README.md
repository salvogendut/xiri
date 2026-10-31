# IRIX xstat lab

This checkpoint measures syscall 1158 on the user's IRIX 6.5.22m installation,
then implements its bounded o32/n32 pathname-stat contract in the NetBSD fork.
The [result](../../docs/results/2026-10-31-irix-xstat.md) records qualification
and its historical Toolchest boundary. The [fxstat follow-up](../irix-fxstat/README.md)
shares the serializer, regresses this matrix on its newer kernel, and advances
Toolchest past the allocator fault. No proprietary source is used.

[abi.json](abi.json) specifies offsets and measured semantics. Version 2 writes
136 bytes for o32 and 152 bytes for n32; version 3 writes 152 bytes for either.
The layout definitions derive from BSD-licensed historical NetBSD code at
`5aca2679d78276864d2980a08314887b2058fb2c`, corrected using the reference records.
The historical version-2 selection and o32 large-file conversion alone were
insufficient: IRIX uses the wide n32 layout and saturates small sizes at
`INT32_MAX`.

The 81 fixture variants cover both ABIs, direct and indirect dispatch, versions,
file types, hard/symbolic links, sparse large files, permissions, path lengths,
unaligned output, inaccessible/read-only pointers, validation order and page
boundary copies. Each static executable writes a 576-byte record containing its
return registers, identity, normal output guards and end-of-page snapshot.
Both root and uid/gid 1234 run the identical executable bytes on original IRIX
and NetBSD. There are 648 reference executions; an o32 kernel runs the o32 half.

`native-stat.c` independently records native filesystem metadata. The host
comparator translates these named values to the measured foreign layout and
checks every byte, including untouched guards, partial copies and zero padding.
Filesystem identities, allocation and timestamps are therefore checked against
the actual native file, rather than ignored or compared to an unrelated XFS
inode. The filesystem string is explicitly `unknown`, and project ID is zero.
These are compatibility limits, not an XFS emulation claim. Other unqualified
ranges and interfaces are listed in `abi.json`.

The namespace cases create distinct native and `/emul/irix` shadow files, and a
native-only fallback file. They verify the existing emulation-root policy.
A native observer follows the selected real path. The fixtures also check that
unreadable files remain stat-able and inaccessible parent directories fail for
the ordinary user.

Build and measure original IRIX:

```sh
python3 scripts/build-irix-xstat.py
python3 scripts/probe-irix-reference-xstat.py
```

Original runtimes, media and raw vendor traces stay in ignored `.work` paths.
Only original probe source, synthetic records, hashes and findings are public.
The reference harness batches tar additions by fixture prefix to stay below
IRIX's argument limit. It synchronizes the console before shutdown and waits
for the power-off message. Never archive the whole fixture tree: it contains a
sparse file larger than 2 GiB.

Build each kernel with at most two jobs, sequentially:

```sh
XIRI_BUILD_JOBS=2 \
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-irix64-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-irix-xstat-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-irix-xstat-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-xstat/XIRI_IRIX_XSTAT" \
XIRI_NETBSD_ARCH=mips64eb scripts/build-netbsd-kernel.sh kernel
```

For o32 use `netbsd-irix-xstat-o32-build`, `XIRI_IRIX_XSTAT_O32` and `mipseb`.
The baseline JSON files pin clean source revisions and all kernel hashes.
The focused lab requires a stopped, qualified recvmsg LP64 X11 seed containing
only desktop libraries, such as the private run below:

```sh
python3 scripts/probe-irix-xstat.py \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-xstat.py --mode ordinary \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
python3 scripts/probe-irix-xstat.py --kernel-abi o32 \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
```

Each run copies the stopped disk, cold-boots the pinned kernel, verifies its
inherited inputs, and loads original helpers through a read-only virtual CD.
Native/asa/echo controls bracket the tests. LP64 runs also start native Xvfb,
launch HOME-configured Toolchest three times per identity before and after
installing the supplied menu/app-defaults/locale indexes, and collect foreign
syscall traces plus an X window-tree observation while the bounded child runs.
A successful xstat call alone does not qualify a window or event loop.

Regression commands:

```sh
python3 scripts/probe-irix-tcp.py --checkpoint recvmsg --kernel-checkpoint xstat \
  --desktop-expectations lab/irix-xstat/desktop.json
python3 scripts/probe-irix-tcp.py --checkpoint recvmsg --kernel-checkpoint xstat --kernel-abi o32
python3 scripts/probe-irix-select.py --kernel-checkpoint xstat --fixtures-only \
  --seed-directory .work/irix-recvmsg/runs/lp64-ci-nw5d95pw
```

Run harnesses from the host: they use the host `genisoimage` and launch IRIS in
the existing `xiri-iris` toolbox. Up to four independent IRIS guests may run at
once under the user's current limit. Track each run and finish its clean guest
shutdown and host process cleanup before considering it complete.

The closed-display Toolchest trace changes when xstat succeeds. The explicit
`desktop.json` preserves reviewed expectations for this kernel without changing
the historical transport results. The fault follow-up accepts a stopped LP64
xstat run with resources installed:

```sh
python3 scripts/probe-irix-xstat-fault.py --seed-directory <completed-xstat-run>
```

It first checks the native exec PC and labelled null-load control, then captures
the later Toolchest stop twice as root. Non-root untraced launches remain in
the focused matrix; the native tracer rejects that credential transition at
`PT_TRACE_ME` (child exit 124), so no non-root fault PC is claimed. Raw instructions, registers and
stack data stay private. The tracer deliberately kills and reaps a stopped
child after capture; its final SIGKILL is cleanup, not the original fault.

Recheck the three completed focused runs, two transport runs and select run
with `scripts/qualify-irix-xstat.py`. Pass the three focused directories as
positional arguments, `--transport-runs <lp64-run> <o32-run>`,
`--select-run <select-run>` and `--output <report.json>`. The qualifier checks
complete reference/NetBSD records, current helper sources, raw trace decoding,
expected diagnostic outcomes, regression status and clean shutdowns.
