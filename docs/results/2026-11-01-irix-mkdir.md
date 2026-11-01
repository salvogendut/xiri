# Measured IRIX directory creation

The IRIX personality now translates `mkdir` (trap1080) through native NetBSD
filesystem creation. It preserves native authorization, effective credentials,
umask and filesystem ownership policy, with measured IRIX pathname handling.
The [lab](../../lab/irix-mkdir/README.md) retains fixtures and reproduction
commands; the [reference oracle](../../lab/irix-mkdir/reference.json) contains
1,280 original-IRIX records.

## Reference behavior

The cleanly halted reference run `ci-xilnl6o7` executes eight original fixtures
under five real/effective credential combinations. Each execution checks 32
pathname/mode cases. Both o32/n32 and direct/indirect traps are covered, with
inherited umasks022 and077. The two mixed-UID identities distinguish effective
permission checks from the real-ID behavior of `access`.

Successful creation returns zero, leaves V1 unchanged, and creates a directory
with masked ordinary permission bits and the effective UID/GID in this
reference fixture. Extra type/high/special mode bits do not appear in the
created directory's tested mode. Existing directories, regular files, final
symlinks and dangling final symlinks return EEXIST. Parent symlinks are followed;
missing/non-directory parents, loops, bad pointers and overlong names return
the observed errors. A terminated string ending at the mapped page boundary
works; an unterminated string reaching the unmapped page returns EFAULT.

IRIX returns EEXIST for `mkdir("data/file/",0755)`. The adapter therefore checks
the original bounded pathname before removing trailing slashes, then invokes
native `do_sys_mkdir` with the copied path. The native CREATE lookup retains
TRYEMULROOT behavior: use an existing emulation parent, otherwise fall back to
the native path. The ordinary native filesystem performs the operation.

## Native filesystem policy and independent checks

FFS parent-group ownership remains native policy. The original
reference's tested children carry effective GID and no inherited setgid bit;
the group field is explicitly adjusted in comparisons, with every
changed record retained. This is not a claim of identical XFS/FFS ownership
semantics, ACL behavior or supplementary-group conformance.

Each native execution also records independent `find`/`stat` snapshots before
and after the foreign process. The qualifier requires all preexisting
pathnames to retain their type, mode and UID/GID, and permits only the expected
new directories. It verifies each new directory's effective owner, masked
permissions, parent group and absence of special mode bits. A separately owned
emulation parent proves that absolute creation selects that namespace while
leaving the corresponding native path untouched.

Native-only controls create a directory despite an inaccessible emulation
shadow, check duplicate creation and removal, and verify that the read-only CD
cannot be modified. Root must receive EROFS; an ordinary user may encounter
EACCES or EROFS in the measured native controls. The exact returned error is captured.
Original asa/echo and native o32 execution remain before/after controls.

## Qualification

The [independent native qualification](2026-11-01-irix-mkdir.json) passes
**100 executions / 3,200 records**, with **1,540 created directories** verified
by independent native snapshots and **44 before/after controls**. There are
960 explicit parent-group policy records. Return registers, error precedence,
UIDs, modes and all other recorded fields match the reference without further
normalization. Source is NetBSD `xiri`
`1690de11a095134b6eee4d7f85a8b046b1a86c47`.

| Native run | Executions | Records |
| --- | ---: | ---: |
| LP64 CI, `lp64-ci-ap565xms` | 40 | 1,280 |
| LP64 ordinary, `lp64-ordinary-o9990rsx` | 40 | 1,280 |
| o32 CI, `o32-ci-legkevsx` | 20 | 640 |

All three guests halt cleanly. The report binds source evidence, build pins,
fixtures, serial logs and filesystem observations. The native read-only
control observes EACCES for UID1234 on LP64 and EROFS on o32; root receives
EROFS on both. Both paths deny the write and leave native execution intact.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-mkdir.py \
  --reference .work/irix-reference/mkdir-records-runs/ci-xilnl6o7 \
  .work/irix-mkdir/runs/lp64-ci-ap565xms \
  .work/irix-mkdir/runs/lp64-ordinary-o9990rsx \
  .work/irix-mkdir/runs/o32-ci-legkevsx \
  --output docs/results/2026-11-01-irix-mkdir.json
```

## Development diagnostics

The [earlier candidates](2026-11-01-irix-mkdir-diagnostics.json) are retained
separately from qualification. Two LP64
attempts halted at the native read-only test's overly narrow EROFS expectation;
they never reached the foreign matrix. The o32 candidate collected 640 records
but exposed a missing explicit dispatch-allowlist entry: mkdir still returned
ENOSYS. The handler, name table and allowlist are all present in the corrected
source. An obsolete desktop attempt was interrupted through its harness and
halted cleanly. A build-time missing VFS declaration was also corrected before
any accepted build. These attempts are not passing application evidence.

## Upstream and scope

IRIS upstream was checked at cycle start. `upstream/main` remains
`f17b4d3bc1663efd02f93a5e0e4811eebba510c8`, already contained in fork `xiri`
at `087d250ab25884baaf03cc998377f75711fe5aa4`; no integration was needed.
Guest qualification retains emulator `9df1df14334838a989253efefe26f0547e6da592`.
The new adapter uses an existing native VFS helper and adds no core hook.
The eventual `compat_linux`-style module target remains in the roadmap.

The [desktop follow-up](2026-11-01-irix-desktop-mkdir.md) now renders Icon Catalog’s
empty fallback page and observes bgicons exit zero. Both file-manager launches
advance to SIGSEGV after unsupported pipe/sgikopt calls.

At cycle end, the shared IRIS checkout had moved to `perf/sgiemu-port` with
unrelated local edits. This cycle made no IRIS changes and leaves that work
untouched; the qualified emulator artifacts and `xiri` integration reference
above remain pinned.
