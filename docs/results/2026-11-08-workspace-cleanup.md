# Workspace cleanup — November 8, 2026

Recovered approximately **250.6 GiB (269 GB) of filesystem space** by retiring
obsolete automated guest disks and regenerable caches. The
[machine-readable report](2026-11-08-workspace-cleanup.json) records exact byte
measurements, retained artifact hashes and local audit-ledger hashes.

| Measurement | Before | After |
| --- | ---: | ---: |
| Available space on `/var` | 13.1 GiB | 263.7 GiB |
| `.work`, as reported by `du` | 2.68 TiB | 101.4 GiB |

The directory totals count shared Btrfs extents repeatedly. Their reduction
is **not** the physical recovery; the change in filesystem available space
is the recovery reported above. These are host-wide measurements taken
during the cleanup, rather than an exclusive extent accounting calculation.

Removed:

- 683 historical raw guest disks and 140 disposable test CHDs.
- 166 automated test overlays, 22 decoded round-trip verification copies,
  and 17 aliases to retired disks.
- 109 temporary transfer disks and one obsolete recovery disk; extracted
  results, traces, logs and screenshots remain.
- 436 generated probe ISOs whose source `media/` directories remain.
- 427,365 NetBSD compiler object/dependency files, Cargo dependency build
  caches, an unused libguestfs appliance cache and old snapshot memory caches.
- The decoded freeware inspection disk. Its original CHD and recorded raw
  digest remain available for reconstruction.
- Two byte-identical local source-media copies, replaced with symlinks to
  the verified originals in `~/Downloads`. The original files are unchanged.

The exact removal records are under `.work/cleanup-20261108/`:
`disk-removals.jsonl`, `cache-removals.jsonl.gz` and
`media-reclamation.json`. Historical run directories also retain a
`disk-cache-removal-20261108.json` notice. Transient guest filesystem state
from retired runs was intentionally discarded; the retained evidence is
not a promise of byte-identical reconstruction of that transient state.

## Preserved and verified

SHA-256 checks passed for 31 canonical compressed images, 153 manual-state
files and 719 final kernel/module/debug/executable artifacts. The selected
sessions image, its manual overlay and graphical NVRAM are unchanged,
including the user's saved desktop settings. The selected raw automation
seed also matches its recorded digest. Nine source checkout/worktree HEADs
remain pinned; both integration forks remain clean on `xiri`.

`./xiri doctor` passes all 17 immutable-artifact checks and its host/Toolbox
checks. No guest boot or application retest was needed: source and runtime
behavior did not change. No IRIS or Prismatic instances were running at the
final activity check.

The remaining workspace contains qualified image bundles and user state,
the current raw seed, pinned source worktrees, final binaries/debug symbols,
build tools, offline dependencies, original imported resources and compact
test evidence. Baseline bootstrap disks and manual Prismatic state remain.

## Reconstruct only when needed

Use `./xiri seed` for the current image. For a historical qualified image:

```sh
python3 scripts/prepare-xiri-seed.py .work/images/BUNDLE --output-directory .work/xiri-image/SEED
```

The helper validates the CHD and decodes it when its raw cache is absent.
For a retired generated `probe.iso`, run `genisoimage -quiet -R -J -o
probe.iso media` in that run directory. Compiler objects and dependency
caches regenerate through the corresponding build commands; qualified final
artifacts remain in their original locations.

Source-media paths now resolve as follows:

| Workspace path | Retained original |
| --- | --- |
| `.work/irix-reference/media/irix65.chd` | `~/Downloads/irix65_chd/irix65.chd` |
| `.work/irix-freeware/media/base.chd` | `~/Downloads/irix-sgi-freeware-cdroms-chd/irix-sgi-freeware-cdroms.chd` |

Keep those originals available. The decoded installed-IRIX reference remains
at `.work/irix-reference/media/irix65.raw`. If freeware-media inspection is
resumed, reconstruct its sparse raw cache from the retained CHD:

```sh
set -o pipefail
.work/target-netbsd64/release/chd-extract .work/irix-freeware/media/base.chd /dev/stdout |
  python3 .work/irix-freeware/sparse-stream.py .work/irix-freeware/media/freeware.raw
```

The expected raw SHA-256 is
`4854f25ccca842e36ad2626f750a3a5f9cb57db4d0e6b9f331b48c91515feb18`.
This is a deferred inspection cache, not an input needed to run the current
desktop. The development guide now describes retaining one current raw seed
and retiring disposable disks after evidence extraction and qualification.
