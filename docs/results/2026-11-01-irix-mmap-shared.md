# Shared mappings and bounded AUTOGROW

The IRIX personality now supports SHARED mappings and accepts AUTOGROW for
the native zero device. This implements the original installer's 1 MiB
READ|WRITE, SHARED|AUTOGROW|AUTORESRV request without modifying its binaries.
The [installer retry](2026-11-01-irix-installer-shared.md) passes the previous
MAP_FAILED crash and reaches a separate process-creation boundary.

The [independent qualification](2026-11-01-irix-mmap-shared.json) checks
**472 original-IRIX records and backing files**, then **1,180 NetBSD records
and backing files plus 44 native/vendor controls**. Every record word and
backing byte is checked against the measured contract or the explicit native
policies below. See the [lab](../../lab/irix-mmap-shared/README.md) and
[decoded reference](../../lab/irix-mmap-shared/reference.json).

## Implementation and observed behavior

NetBSD `xiri` source `7af1404388b9f2db84f97a114c9f003b7c50b094` translates
SHARED/PRIVATE explicitly and delegates mappings to native `sys_mmap`.
AUTOGROW requires a vnode for the native zero character device; aliases work,
while a regular file named `zero` is rejected. A descriptor reference stays
held through the native call to prevent reuse between validation and mapping.
Native UVM supplies shared anonymous memory, fork inheritance, descriptor-close
lifetime and private COW. No new core hook is needed for the eventual
compat_linux-style module.

The reference confirms shared child writes remain visible to the parent,
private child writes stay private, and closing the descriptor does not remove
the mapping. Two independent zero mappings do not alias; two shared mappings
of the same regular file do. Plain shared file writes update exactly the
expected offsets, while private file mappings leave the backing bytes intact.

Regular-file AUTOGROW is deliberately still EINVAL. Its reference behavior is
more extensive than the zero-device request:

| Reference request, initial file size 17 | Immediately after mmap | After access at offset 8192 |
| --- | ---: | --- |
| SHARED\|AUTOGROW, store | 17 | 12288; holes zero, stored byte retained |
| SHARED\|AUTOGROW, read | 17 | 12288; new bytes zero |
| PRIVATE\|AUTOGROW, read or store | 17 | 17; child exits normally |
| SHARED or PRIVATE without AUTOGROW | 17 | 17; child receives SIGBUS |

The older [IRIX mmap manual](https://techpubs.jurassic.nl/manpages_0530/cat2/standard/mmap.html)
describes growth on stores. This measured 6.5.22m installation also extends
on the tested read fault. Pre-extending at mmap would implement neither timing
correctly. The empty-file and regular-file-named-zero cases corroborate the
shared growth behavior.

## Coverage and policies

59 variants cover o32/n32, direct/indirect dispatch, UID0/UID1234, the exact
installer allocation, fork/close behavior, aliases, fixed/local combinations,
file offsets and permissions, protection faults and invalid requests. Native
shared/private memory, close, file visibility, access checks and EOF behavior
run before and after; native o32 and vendor asa/echo execution also pass.
Each child is reaped and the native supervisor verifies no remaining group.

| Kernel / mode | Records and backing files | Controls | Shutdown |
| --- | ---: | ---: | --- |
| LP64 CI, `lp64-ci-f0ux07ei` | 472 | 16 | Clean |
| LP64 ordinary, `lp64-ordinary-f0yfsjg5` | 472 | 16 | Clean |
| o32 CI, `o32-ci-03guecyq` | 236 | 12 | Clean |

Reference `ci-i361kb_a` halts cleanly. Both isolated kernel builds pass,
sequentially with two jobs. Pins retain exact source, kernel and emulator
hashes; older qualified artifacts remain unchanged.

Differences are explicit: regular-file AUTOGROW rejection; native zero-device
acceptance of read-only/write-only descriptors rejected by the original
shared request; native 8 KiB alignment on LP64; stricter unknown-flag rejection;
and native EINVAL for empty/bad-protection requests. No foreign flag bits are
passed through to native mmap. The size-snapshot `lseek` calls remain ENOSYS
(IRIX errno 89) on NetBSD; independently copied backing files establish final
sizes and contents there. This is not a claim of lseek support.

AUTORESRV uses native demand allocation, without promising IRIX logical-swap
accounting, exhaustion signals or mlock semantics. LOCAL still requires one
LWP and an unshared vmspace. Shared-process creation, larger offsets, sustained
memory pressure and physical hardware remain outside this checkpoint.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-mmap-shared.py \
  --reference .work/irix-reference/mmap-shared-records-runs/ci-i361kb_a \
  .work/irix-mmap-shared/runs/lp64-ci-f0ux07ei \
  .work/irix-mmap-shared/runs/lp64-ordinary-f0yfsjg5 \
  .work/irix-mmap-shared/runs/o32-ci-03guecyq \
  --output docs/results/2026-11-01-irix-mmap-shared.json
```

## Retained diagnostics and upstream

The first reference run `ci-n8vn1_u1` completed its cases but timed out exporting
an uncompressed archive. Its interrupted console did not complete shutdown;
it is retained as an unclean diagnostic and is not a seed. Read-only extraction
without recovery could not recover the archive. The qualified repeat starts
from the earlier clean pipe seed and compresses its archive to 97,794 bytes
before export. The reference still emits its documented XFS alerts; these tests
do not qualify its filesystem.

The first native runs `lp64-ci-mat34neh`, `o32-ci-vo_0tdvo` and
`lp64-ordinary-2qev7e02` halted cleanly but failed host result assembly: the
backing archive command ran in the parent shell's directory instead of the
fixture directory. Their syscall logs are retained, but they lack the complete
backing/after-control evidence required for qualification. The corrected
observer repeats all three matrices from the clean seed. See the
[diagnostic metadata](2026-11-01-irix-mmap-shared-diagnostics.json).

IRIS upstream was fetched at this cycle's start: `upstream/main` remains
`f17b4d3bc1663efd02f93a5e0e4811eebba510c8`, already in IRIS `xiri`
`087d250ab25884baaf03cc998377f75711fe5aa4`. No integration or emulator rebuild
was needed. The shared checkout's unrelated performance branch was untouched.
NetBSD guests retain emulator `9df1df14334838a989253efefe26f0547e6da592`;
the reference retains its earlier qualified binary, with both hashes recorded.
