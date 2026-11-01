# IRIS and NetBSD branch consolidation

All existing local and origin branch histories in both forks are now reachable
from their respective published `xiri` branches. The old topic branches and
the local NetBSD trunk backup have been removed. The default branches remain
unchanged. The [machine-readable record](2026-11-01-xiri-branches.json) lists
each retired branch and its original commit, merge parents, retained default
revisions, pinned worktrees and validation log hashes.

| Fork | Published `xiri` revision | Old local branches removed | Old remote branches removed |
| --- | --- | --- | --- |
| [IRIS](https://github.com/salvogendut/iris/tree/xiri) | `43fdfaaf39457223aa7dc2df5cbd565bf3e42cbd` | 4 | 4 |
| [NetBSD](https://github.com/salvogendut/NetBSD-xiri/tree/xiri) | `ee0d7614caa69e25d872ecaf260c603541c4c990` | 28 | 27 |

The local NetBSD checkout is still `../NetBSD-nixbench`; its origin is the
NetBSD-xiri fork. IRIS remains at `../iris`. Both checkouts are clean, on
`xiri`, and track `origin/xiri`. Their only other local/origin branches are
`main` for IRIS and `trunk` for NetBSD. Upstream remote refs were not changed.

## Merged work

IRIS merge `bf4f30078f44bbd69d3fa71e83f8be169ded0411` combines the
`4aff0d90abfb5c60d7e05011ffa9691f5c012cea` frontend/Newport history with
the `9df1df14334838a989253efefe26f0547e6da592` extended TLB-tag fix.
This includes the earlier NFS and snapshot fixes, upstream changes and
frontend APIs. The merge was conflict-free. The TLB implementation matches
the TLB branch exactly, while the merged tests retain the newer CPU setup API.
Follow-up `43fdfaaf39457223aa7dc2df5cbd565bf3e42cbd` gives one regression
test an explicit thread stack, as described below.

NetBSD starts with the complete IRIX compatibility chain through
`6761f8e288701cec1a5760e3d3606ff6bbe67a90`, including the PRDA and working
4Dwm/winterm session records. Merge `3d69fc2298b` adds XFS history through
`7261c6ae9885e71084807ef28e39c02be9c11aab`; merge `ee0d7614caa` adds the
already existing trunk updates through `b6720166b89087e7fbf2dcafc79cb17cdba6d603`.
Both merges were conflict-free. The IRIX, MIPS and sgimips source subtrees
match the PRDA branch exactly; XFS and libpuffs match the XFS branch exactly.
Inherited whitespace in imported/upstream files was left unchanged.

## History and worktree preservation

Before deleting branches, ancestry checks verified all 11 recorded IRIS refs
and all 58 recorded NetBSD refs against their integration heads. These counts
include local/origin duplicates and origin's symbolic HEAD. Temporary
`xiri-integration` branches were published and verified first, because the old
`xiri/...` refs prevented Git from creating a branch named `xiri`.

Remote deletion used exact expected commit leases. Local deletion used
`git branch -d` after verifying ancestry and detaching the pinned worktrees.
The canonical `xiri` branches were then published and verified, and the
temporary integration branches removed. Final checks confirmed every recorded
old branch tip remains an ancestor of the published `xiri` tip.

These worktrees remain clean and detached at their original commits:

| Worktree | Preserved revision |
| --- | --- |
| `.work/iris-netbsd64` | `9df1df14334838a989253efefe26f0547e6da592` |
| `.work/netbsd-irix-src` | `6abdd05eca298e29af07d6176ea453e696de90a3` |
| `.work/netbsd-irix64-src` | `6761f8e288701cec1a5760e3d3606ff6bbe67a90` |
| `.work/netbsd64-src` | `40d3a490765b8babc8c9cd2aa03a80fa26567320` |

## Validation

IRIS passed all 26 selected TLB tests using the existing Toolbox, locked
dependencies, Rust `nightly-2026-10-28`, two build jobs and two test threads:

```sh
cargo +nightly-2026-10-28 test --locked --offline --lib tlb -- --test-threads=2
```

The first run overflowed the default test-thread stack in
`test_o32_cannot_alias_extended_tlb_entries`, which constructs multiple TLBs
containing inline virtual maps. The follow-up commit wraps that test in a
thread with an explicit 8 MiB stack, following the neighboring snapshot tests.
Its original assertions are unchanged. The repeat passed without a global
test-stack override. Both attempt logs are retained locally under
`.work/branch-consolidation/`, with hashes in the JSON record.

All eight XFS host test suites passed via
`env PYTHONDONTWRITEBYTECODE=1 sh external/gpl2/xfs/tests/run.sh` in Toolbox:

| Suite | Reported checks/cases |
| --- | --- |
| Superblock | 1,070 |
| Allocation groups | 1,600, plus I/O bounds and failure checks |
| Inode, allocation, bmap and reads | 8,879 |
| Directory, lookup and remote symlinks | 33,342 |
| Journal | 1,734, plus clean-guard and argument checks |
| Inline attributes and mount policy | 1,272 |
| External attributes | 1,146 |
| POSIX ACLs | 329,048 |

No guest runtime was requalified during this consolidation. Existing kernel,
emulator, disk and resource pins are unchanged, including the successful
[4Dwm session baseline](2026-11-01-irix-4dwm.md). A combined build and runtime
qualification is required before adopting the integrated tips as lab baselines.
No IRIS guest instances were launched for the branch work.

## Continuing work

Use the [fork workflow](../FORKS.md): routine changes go on `xiri`; temporary
topic branches, when needed, merge back into the respective `xiri` at the end
of the cycle and are removed after publication. Historical branch labels in
qualification JSON remain intact. Reproduction commands now fetch `xiri` and
check out the original exact commit. `scripts/build-iris.sh` clones `xiri`
before selecting its unchanged pinned revision, and historical branch links
now resolve to immutable commits.
