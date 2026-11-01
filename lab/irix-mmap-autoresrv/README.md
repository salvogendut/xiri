# Private AUTORESRV mappings

Original fm, bgicons and Icon Catalog reach a pthread-table allocation request
with address 0, length `0x160000`, protection READ|WRITE, flags `0x102` and an
O_RDWR `/dev/zero` descriptor. This lab adds IRIX `MAP_AUTORESRV` (`0x100`) to
the existing private mapping subset and checks the original applications
separately from the mapping contract.

[SGI's programming manual](https://techpubs.jurassic.nl/library/manuals/2000/007-2478-007/pdf/007-2478-007.pdf)
describes delayed swap reservation. The older [IRIX mmap manual](https://techpubs.jurassic.nl/manpages_0530/cat2/standard/mmap.html)
specifies reservation on the first store and SIGBUS if logical swap is then
exhausted. These are related but distinct from merely creating an address range.

NetBSD UVM private mappings already use demand allocation and copy-on-write,
without reserving swap for the complete extent at mmap time. The adapter
accepts the foreign flag and calls native mmap; native descriptor, protection,
resource-limit, range and page-alignment checks still apply. It does not pass
IRIX bits through as native flags. Native `MAP_NORESERVE` is documented as
unimplemented in [NetBSD's mmap manual](https://man.netbsd.org/mmap.2), so adding
that flag would not establish a separate policy.

This subset does not reproduce IRIX logical-swap accounting, fault-time
exhaustion signals or mlock interactions. Native memory-pressure behavior
remains in force. Shared mappings, AUTOGROW, ANYADDR and unknown flags remain
outside the adapter. LOCAL still requires one LWP and an unshared vmspace.
Signed 32-bit offsets and native page sizes retain the previous restrictions.

## Fixtures

There are 58 variants, each built for o32/n32 and direct/indirect dispatch,
then run as root and UID1234. The 33 prior private/fixed/local variants are
retained; their former AUTORESRV rejection now becomes an accepted mapping.
The 25 additional variants cover:

- The actual 1.375 MiB O_RDWR request, reading the entire zero-filled extent
  and writing its first and last bytes after closing the descriptor.
- Fixed/local combinations, replacement and preservation on invalid input,
  one-byte rounding, regular-file contents and offsets, and invalid descriptors.
- Read-only store faults, mprotect to read-only, NONE-to-RW restoration, and
  private fork inheritance with child writes isolated from the parent.
- Empty, unaligned and half-page requests, invalid flag combinations and
  unsupported shared/autogrow behavior.

The write-only regular-file fixture uses a separate mode-0666 file so ordinary
users can open the descriptor before mmap rejects its access mode. The normal
file remains mode 0444. Native runs hash both files before/after to verify
private mappings have not modified either backing file.

Records are 64 big-endian words. Besides the existing request, return,
identity and payload fields, words 26/27 identify fork/protection cases;
28–31 record the verified child exit and unchanged parent bytes; 40–45 hold
protection-change returns. Child PID and waitinfo are checked inside the
fixture before recording success. Deliberate protection faults occur only
after the complete record has been written.

Native/vendor controls, native page-zero checks before/after foreign-to-native
exec, descendant-supervisor controls and guest shutdown accompany the matrix.
The independent qualifier compares every record against original IRIX, with
explicit native-policy adjustments inherited from the fixed/local checkpoint.

## Reproduce

Build the LP64 and o32 kernels sequentially with at most two jobs in
`.work/netbsd-irix-mmap-autoresrv-build` and its `-o32-build` counterpart.
Use the configs here, `mips64eb`/`mipseb` respectively, and the source revision
in the pins. A verified matching toolchain may be reused through a `tools`
symlink after recording `build-arch`; preserve all previous qualified outputs.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-mmap-autoresrv.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/pin-irix-mmap-autoresrv.py --kernel-abi o32
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-mmap-autoresrv.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-mmap-autoresrv.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-mmap-autoresrv.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-mmap-autoresrv.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-mmap-autoresrv.py \
  --seed-directory .work/irix-x11-fonts/runs/ci-_6m3l41w --kernel-abi o32
```

`qualify-irix-mmap-autoresrv.py --reference REFERENCE RUN... --output REPORT`
requires the complete LP64 CI/ordinary and o32 CI set. The initial
`--export-reference` records decoded reference words here; subsequent checks
require that same reference record. It does not certify swap-exhaustion behavior.

`probe-irix-desktop-autoresrv.py` and `--mode ordinary` repeat the bounded
file/icon session using these kernels. They preserve the previous kernel and
observations, and retain the working winterm and native window checks.
Original binaries, disks and raw traces remain under ignored `.work`.

The [qualified result](../../docs/results/2026-11-01-irix-mmap-autoresrv.md)
records 464 original-IRIX observations, 1,160 native mapping cases, 30 controls
and 32 native page-zero controls. The [desktop follow-up](../../docs/results/2026-11-01-irix-desktop-autoresrv.md)
records successful table/fixed mappings and the next PR_INIT_THREADS boundary.
