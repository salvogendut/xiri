# IRIX filetype database locking

The missing Icon Catalog/FileManager artwork investigation reaches
`/usr/lib/filetype/desktop.otr`, then fails IRIX `fcntl` selector 13
(`F_SETBSDLKW`). The imported filetype tables and icon resources are already
present. This cycle implements and qualifies locking before reassessing the
artwork; kernel support alone is not evidence that icons render.

## Original-system measurements

The reference is the supplied installed **IRIX 6.5.22m** image. No leaked
source is used. The raw fixtures run unchanged on both systems, with direct
and indirect dispatch, o32 and n32, as root and UID/GID 1234.

- 728 guarded ABI executions: `.work/irix-reference/filelocks-runs/ci-i1dk7lpa`.
- 104 cross-process executions: `.work/irix-reference/lock-behavior-runs/ci-0nti9yc5`.
- Both reference guests shut down cleanly. Raw records, fixture hashes,
  identity and provenance are retained in `lab/irix-filelocks/*reference.json`.
- The initial diagnostic `.work/irix-reference/filelocks-runs/ci-fz5hr3tc`
  established that n32 requires a different layout; its intentionally
  superseded fixtures are retained under `.work/irix-filelocks/initial-layout`.

The o32 lock record is 36 bytes. The n32 record is 48 bytes, with signed
64-bit start and length at offsets 8 and 16, and PID at 28. Guard pages show
that the full record must be readable. Unaligned records work. Set operations
accept read-only input; queries require writable output. Invalid descriptors
are rejected before a null record pointer is examined.

Selectors 6/7 are nonblocking/blocking record locks; 12/13 are their older BSD
variants; 14 queries conflicts. The older variants permit a write lock on a
read-only descriptor and a read lock on a write-only descriptor, while 6/7
return EBADF. This is measured release-specific behavior, not an assumption
from later documentation. Negative lengths are rejected; the raw reference
records retain the boundary-specific EINVAL/EOVERFLOW distinction.

Locks are process-owned byte ranges. Shared readers coexist, overlapping
writers fail with IRIX EACCES, disjoint ranges coexist, blocking requests
wait, and partial unlocks preserve the remaining range. Closing either a
duplicate descriptor or another open descriptor for that file releases the
process's locks. Closing the child's inherited descriptor does not release
the parent's locks. Child exit releases the child's locks. The BSD and
regular selectors participate in the same lock state.

## Implementation and qualification

NetBSD source `3e154cdc37c` on `xiri`, isolated build
`.work/netbsd-irix-filelocks-build`, configuration
`lab/irix-filelocks/XIRI_IRIX_FILELOCKS`. The previously qualified graphical
image and kernel remain unchanged. The adapter uses native vnode locks with
explicit foreign selector, layout, type and error translation.

[The paired qualification](2026-11-02-irix-filelocks.json) passes **1,248 lock
records, 12 native/foreign interoperability executions and 20 native/vendor
controls**. The final LP64 ordinary run is
`.work/irix-filelocks/runs/lp64-ordinary-tadj913n`; the o32 CI run is
`.work/irix-filelocks/runs/o32-ci-e4e57ddd`. Both halt cleanly. The original
raw runner marked directory setup reads as differences; the separate
qualifier verifies the full records with the explicit read distinction below.
No lock-result bytes are ignored. Source and emulator hashes are in the lab
pins and the qualification report.

The first graphical run restored generic catalog and FileManager folder/
document icons. The [completed icon repair](2026-11-02-desktop-icons.md) adds
seek offsets and native FAM pathname mapping to restore application-specific
artwork. Locking alone did not resolve those remaining failures.

The native/foreign interoperability peer tests the same vnode in both
personalities: the IRIX query reports the native parent's lock range and PID,
its overlapping lock fails, releasing the native lock allows the IRIX lock,
and a native query reports the IRIX child's range/PID. Native acquisition then
fails until the foreign child exits. The query uses SEEK_CUR after reading
64 bytes, checking nonzero relative offsets.

The guarded probe also reads 64 bytes to establish its current offset.
NetBSD permits this setup read on a directory; IRIX returns EISDIR. The
comparator checks that specific existing read difference, while comparing
all lock results and every remaining record byte against the reference.
This is not a locking failure or a change to the read adapter. The first
prototype instead used the unimplemented legacy lseek selector 19; that
setup was replaced and the complete original reference rerun.

IRIS upstream was checked at the start of this cycle on 2026-11-02:
`43e525a847ceeb9453af5d685dd8d353bea133e1` remains the latest fetched
`upstream/main`; integration `xiri` remains
`a4a1659d0b3180713f988d73b7b7da204048ae6a`. No merge or emulator rebuild was
needed. The guests use the already pinned emulator recorded in the lab pins.

## Reproduce

Build the cross-compiled peers with `scripts/build-irix-filelocks.py`,
`scripts/build-irix-lock-behavior.py`, and
`scripts/build-irix-lock-interop.py`. The first two paired reference runners
are `scripts/probe-irix-reference-filelocks.py` and
`scripts/probe-irix-reference-lock-behavior.py`; both accept a clean reference
`--seed-directory` and retain checksummed fixtures and raw stdout records.

With the pinned kernel builds and prepared graphical seed, run:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-filelocks.py --mode ordinary
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-filelocks.py --mode ci --kernel-abi o32
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-xiri-desktop-icons.py
```

The retained first-comparator harness is
`.work/irix-filelocks/probe-initial-comparator.py`. Pass it through
`qualify-irix-filelocks.py --original-harness` when rechecking the two raw
runs above; the current runner uses the documented comparator directly.

Scope: selectors 6, 7, 12, 13 and 14 only. Separate explicit large-file
selectors, network lock managers, deadlock/signal-interruption cases and
unmeasured error-order combinations remain outside this qualification.
The n32 layout supports 64-bit ranges for these selectors. Legacy lseek
selector 19 is covered by the subsequent [seek qualification](2026-11-02-irix-lseek.json);
the directory-read difference remains separate work. No additional IRIX
image resources were needed for these fixes.
