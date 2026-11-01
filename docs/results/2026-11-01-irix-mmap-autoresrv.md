# Private AUTORESRV mappings

The NetBSD `xiri` branch now accepts private IRIX `MAP_AUTORESRV` mappings.
Original pthread-table allocation passes, and the file/icon clients proceed
to a later `PR_INIT_THREADS` failure. The [application result](2026-11-01-irix-desktop-autoresrv.md)
records that boundary separately from this mapping qualification.

The [lab](../../lab/irix-mmap-autoresrv/README.md),
[decoded original records](../../lab/irix-mmap-autoresrv/reference.json) and
[qualification report](2026-11-01-irix-mmap-autoresrv.json) bind the source,
fixtures, three native runs and original IRIX 6.5.22m reference. Kernel code
is pinned at `c11c9f16fad11837a169a3cd566582bebea2c029`; both kernels were built
from clean source in separate outputs, sequentially with two jobs. Previous
qualified kernels and emulator pins are preserved.
The fork's `xiri` branch is pushed through documentation commit
`def129feb38`, with the tested code remaining pinned at the revision above.

## Implemented behavior

The adapter accepts foreign AUTORESRV (`0x100`) alongside PRIVATE, optionally
FIXED and LOCAL, then performs a real native mmap. It retains all previous
descriptor, protection, page-alignment, range and resource-limit checks.
Shared mappings, AUTOGROW, ANYADDR and unknown bits remain rejected. LOCAL
still requires one LWP and an unshared vmspace; file offsets remain signed
32-bit values. No original application or library is patched.

[SGI's programming manual](https://techpubs.jurassic.nl/library/manuals/2000/007-2478-007/pdf/007-2478-007.pdf)
describes AUTORESRV as delaying swap reservation. The older
[IRIX mmap manual](https://techpubs.jurassic.nl/manpages_0530/cat2/standard/mmap.html)
specifies first-store reservation and SIGBUS if logical swap is exhausted.
Inspection of the pinned UVM mapping, anonymous-page and page-daemon sources
shows native private mappings use demand allocation/COW without reserving
swap for the entire extent at map creation. The report records those source
hashes. No additional native flag is required; [NetBSD documents MAP_NORESERVE
as unimplemented](https://man.netbsd.org/mmap.2).

This translation preserves native memory-pressure policy. It does not claim
identical IRIX logical-swap accounting, exhaustion signals, locking behavior
or general pthread support. The tests establish accessible mappings and the
listed lifecycle/error behavior under the tested resource conditions.

## Verification

| Environment / run | Mapping records | Controls | Native page-zero controls |
| --- | --- | --- | --- |
| Original IRIX, `ci-pix8rhaj` | 464 | Identity and exit/fault checks in each fixture | — |
| LP64 CI, `lp64-ci-4fwco0gr` | 464 | 10 | 12 |
| LP64 ordinary, `lp64-ordinary-qn5sp0mh` | 464 | 10 | 12 |
| o32 CI, `o32-ci-rvwh45gf` | 232 | 10 | 8 |

All 1,160 native mapping cases, 30 controls and 32 native page-zero controls
pass. Of the mapping records, 852 match the original oracle after checking
and normalizing non-fixed placement/page size; 308 use explicitly listed
native-policy expectations. These include native page alignment, empty/bad
requests, unsupported flags and the previously documented write-only
`/dev/zero` difference. They are not presented as exact IRIX policy matches.

There are 58 variants across both foreign ABIs, direct/indirect dispatch and
root/UID1234. They retain all 33 prior fixed/local variants and add 25 cases
for AUTORESRV. The previous AUTORESRV case now succeeds. New coverage verifies:

- The actual 1.375 MiB, READ|WRITE, PRIVATE|AUTORESRV, O_RDWR `/dev/zero`
  request, including zero contents across the full extent and first/last writes.
- Descriptor-close survival, private regular-file writes without changing
  backing files, aligned offsets, fixed replacement and untouched neighbors.
- EBADF for invalid/closed descriptors, EACCES for a write-only regular-file
  descriptor, and invalid type/alignment/length/flag combinations.
- Read-only stores faulting, mprotect removing write permission, NONE-to-RW
  restoration, and fork inheritance with child writes isolated from the parent.

Original IRIX accepts the high unknown flag used here and AUTOGROW; the
bounded native adapter continues to reject them. Original empty mappings
return ENXIO while the adapter returns EINVAL. LP64 requires 8 KiB alignment
where original IRIX and the o32 kernel use 4 KiB. The existing write-only
`/dev/zero` native allowance remains explicit; the new regular-file check
returns EACCES on both systems. None of these differences is hidden by
normalizing the output.

The qualifier checks all 64 words of each record, successful payload checks,
fault status, identities, fixture/source hashes, kernel pins, mode coverage,
native/vendor controls and clean shutdown. Both backing files are unchanged
after every native matrix. Native page-zero protection is checked directly
and after foreign-to-native exec. All completed qualification guests halt
cleanly.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-mmap-autoresrv.py \
  --reference .work/irix-reference/mmap-autoresrv-records-runs/ci-pix8rhaj \
  .work/irix-mmap-autoresrv/runs/lp64-ci-4fwco0gr \
  .work/irix-mmap-autoresrv/runs/lp64-ordinary-qn5sp0mh \
  .work/irix-mmap-autoresrv/runs/o32-ci-rvwh45gf \
  --output docs/results/2026-11-01-irix-mmap-autoresrv.json
```

## Retained setup attempts and workflow

The first fixture setup used the mode-0444 normal file for the write-only
descriptor case. UID1234 would fail at open, before exercising mmap. This was
caught during review; the three mapping harnesses were interrupted and the
fixture corrected to use a separate mode-0666 file. The final run above is
the only accepted reference/matrix. These earlier attempts remain private:

| Run | Disposition |
| --- | --- |
| Original IRIX `ci-23tm5k9x` | Interrupted; clean guest shutdown; excluded |
| LP64 CI `lp64-ci-g4vl9csx` | Interrupted during staging; clean shutdown; excluded |
| LP64 ordinary `lp64-ordinary-8de_rpt5` | Interrupted before login; emulator terminated without a clean guest halt; excluded |

Frozen harness, builder and probe copies preserve the setup used by those
attempts. The independent desktop run did not use that fixture and was
unaffected. Original binaries, raw traces and disks remain under `.work`.
The final host process inspection found no remaining IRIS instances.

IRIS upstream was checked at cycle start: `upstream/main`
`f17b4d3bc1663efd02f93a5e0e4811eebba510c8` was already contained in fork `xiri`
`d3d8a99dd4eba49f20ca748bbf78b030fb207a89`. No integration was needed.
NetBSD guest qualification still uses emulator
`9df1df14334838a989253efefe26f0547e6da592`, not the newer fork tip.
