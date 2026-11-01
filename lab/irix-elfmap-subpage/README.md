# ELF data segments at 4 KiB boundaries

This lab extends the shell kernel toward original 4Dwm. Its libimdUtil and
libXpm data segments have 4 KiB boundaries, with matching native-page offsets.
The LP64 kernel has 8 KiB pages. The mapper accepts aligned, congruent data
segments by normalizing an owned header copy to the native page boundary.
Caller headers remain unchanged; native virtual code/data pages stay separate.

Nonempty data includes the preceding file bytes. Pure BSS receives zero-filled
padding. Native private mappings keep overlapping file-page aliases independent:
a write through a data alias must not modify code or the underlying file. The
normalization precedes address-space limits, collision selection and rollback
journaling. Placement and accounting use full native pages. Logical file
segment overlap, native-page incongruence, code/data virtual-page sharing and
byte-aligned segment starts remain rejected. Native o32 uses 4 KiB pages and
therefore admits some layouts rejected by LP64; those differences are explicit.

The new fixture set retains all 57 relocation cases and adds 17 subpage cases.
Both foreign ABIs and both identities run on IRIX and LP64; o32 kernel regression
runs the o32 ABI. The additional actions check data, BSS, native prefix contents,
code/data COW aliases, collisions, repeated maps, RX/gap faults, upper bounds and
invalid layouts. Native input hashes are checked before and after every case.
A page-size query gates prefix checks: no preceding half-page exists on IRIX or
the o32 kernel. Native RLIMIT_AS cases accompany each ABI/identity pair.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-elfmap-subpage.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-elfmap-subpage.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-elfmap-subpage.py \
  --seed-directory .work/irix-xclock/runs/ci-0xaicapn
# Repeat with --mode ordinary and separately --kernel-abi o32.
```

Build the two configs sequentially using `scripts/build-netbsd-kernel.sh`,
`XIRI_BUILD_JOBS=2`, the existing `.work/netbsd-irix64-src` worktree and separate
`.work/netbsd-irix-elfmap-subpage{,-o32}-build` directories. Use `mips64eb` for
`XIRI_IRIX_ELFMAP_SUBPAGE`, `mipseb` for `XIRI_IRIX_ELFMAP_SUBPAGE_O32`, and each
build's own `tftp` subdirectory. The baseline JSON files pin exact inputs.
The implementation is on NetBSD branch `xiri/irix-elfmap-subpage`.

All runs use private disk/NVRAM copies and halt on completion. Keep at most four
IRIS instances. Raw reference files, application bytes, dumps and disks remain
under ignored `.work`. The previous relocation and shell labs remain unchanged.

Qualification passes [740 mapping cases and 10 limit checks](../../docs/results/2026-11-01-irix-elfmap-subpage.md), plus 32 native/vendor controls:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-irix-elfmap-subpage.py \
  --reference .work/irix-reference/elfmap-subpage-runs/ci-h5ffn_3j \
  .work/irix-elfmap-subpage/runs/lp64-ci-1slll0pa \
  .work/irix-elfmap-subpage/runs/lp64-ordinary-2af0n1nx \
  .work/irix-elfmap-subpage/runs/o32-ci-532cq5jw \
  --output docs/results/2026-11-01-irix-elfmap-subpage.json
```

The implementation pin is the clean code revision `c819dd1c090`. Later
README changes do not alter those tested binaries. The optional `--xclock`
probe mode is inherited from the relocation harness; this matrix does not
invoke or claim its graphical checks.
