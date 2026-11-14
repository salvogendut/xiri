# IRIS fork cleanup: upstream owns duplicated features

This first cleanup reduces the content difference between IRIS `xiri` and
upstream while preserving the remaining NetBSD fixes and Prismatic interfaces.
It uses forward commits, preserving existing branch history and pinned lab
worktrees. It does not submit an upstream PR or change the manual CHD's emulator.

## Inputs and size

- Upstream checked: `49210388ed5559667d7859dd46103b42b07d3fed`, fetched from
  `https://github.com/techomancer/iris.git`. It is already included; no new merge
  is needed this cycle.
- Fork starting point: `f6be6154eb9928597dfaffdd435c32db751cf681`.
- Result: `7c4552a6aacf5915b7e951c6c60228216b342215`, fast-forwarded into
  `xiri` and pushed to `origin/xiri`.
- Temporary branch: `topic/upstream-delta-cleanup`, isolated from Prismatic's
  normal `../iris` checkout during validation and removed after the push.
- NetBSD `xiri`: `a4a70956805`; unchanged.

Counts compare file contents with the checked upstream revision, including
documentation and tests. They are not counts of independently useful patches.
The machine-readable [ledger](2026-11-14-iris-delta-cleanup.json) records final
counts, commit IDs, validation and cleanup.

| Difference from upstream | Before | After |
| --- | ---: | ---: |
| Changed paths | 104 | 96 |
| Changed paths under `src/` | 60 | 57 |
| Added lines | 4,954 | 4,549 |
| Deleted lines | 373 | 365 |
| Total changed lines | 5,327 | 4,914 |

That removes 413 lines from the content diff (7.8%). Most of the reduction is
obsolete tooling and documentation. Commit ancestry is preserved rather than
squashed to make the ahead count smaller.

## Removed duplication

| Area | Upstream replacement | Cleanup |
| --- | --- | --- |
| NFS MOUNT authentication | `632e0058`, `net: let IRIX 6.5.30 mount the NFS share` | Restore `src/net/nfsudp.rs` exactly to upstream and remove the fork's redundant AUTH_SYS note. Both versions already advertised AUTH_UNIX/AUTH_SYS and AUTH_NULL. Keep the useful NetBSD UDP mount command in `HELP.md`. |
| JIT priority queues | `5d13b02c`, `jitv2: keep compile requests with the machine that made them` | Keep upstream's implementation and queue-isolation regression; remove the overlapping fork stop/drain test. Retain the distinct real-worker test that checks compilation against the correct machine's bus. |
| Embedded firmware | `de2584e2` and the upstream `iris-prom` tool, packed PROM catalog and shared resolver | Remove `tools/embed-prom.py`, which generated obsolete Rust arrays. Correct stale Octane firmware paths, hashes and validation claims. Keep the empty-string embedded-PROM alias used by existing frontends. |
| Incidental differences | Upstream pixel-DMA whitespace and platform-profile assertion | Restore both files exactly, removing two unrelated paths from the patch. |
| Integration journals | Xiri's existing fork workflow and result records | Move the two old integration journals and the original SGIEmu port report into this repository's historical documentation. Keep current feature/API documentation beside the IRIS code. |

The original feature implementations were largely reconciled during earlier
merges. This pass removes their remaining duplication and obsolete material;
it does not claim to remove hundreds of lines of active emulation code.

Historical records remain available:

- [Earlier upstream integration journal](../history/iris/xiri-upstream-integration.md)
- [November 13 integration journal](../history/iris/xiri-upstream-20261113.md)
- [Original SGIEmu port and measurements](../history/iris/sgiemu-register-and-rtc-cache.md)

## Why the remaining fork still exists

| Remaining patch group | Reason to retain it | Possible upstream contribution |
| --- | --- | --- |
| MIPS TLB matching | A 32-bit user access must not alias a 64-bit kernel mapping sharing its low VPN bits. Region/upper-tag matching and snapshot reconstruction still differ upstream. | A focused correctness patch with the o32/extended-entry regression. |
| PS/2 translation | The 8042 translation bit must convert Set 2 input to XT codes, while direct device ports retain their selected set. | Device fix and existing input regressions. |
| MC snapshot restore | Restored MEMCFG registers must republish physical RAM bank mappings outside the controller locks. | Small snapshot fix and the callback regression. |
| Newport RGB24 | Physical plane encoding must be converted for fast-clear colors and write masks in generic, JIT and GPU flat-fill paths. | A renderer patch with the existing cross-path comparisons. |
| Storage and networking | Protected/hashless CHD overlays, Windows sidecar publication, live forward-port reuse and settings across network restarts still add behavior. | Separate storage and network patches, each with its own failure case. |
| Frontend embedding | PCM/serial injection, diagnostics routing, PROM presets, owned remote services, lifecycle/snapshot support and modern-platform buses/counters remain in use by Prismatic. | Several small library-API proposals, not a single desktop-specific PR. |
| Performance preferences | The GPR cache implementation is upstream, but the per-machine opt-in policy is not. The DS1x86 calendar cache also remains local. | Treat policy and RTC optimization separately; removing a duplicate implementation must not silently discard a saved frontend preference. |

The Octane CPU model implementation and common network worker ownership already
use upstream's APIs. Additional fork tests or frontend choices are not themselves
duplicate implementations. Keep useful additional coverage until an upstream
test covers the same behavior.

The smallest correctness patches above are better initial PR candidates than a
PR containing the whole `xiri` branch. Extract them from the current content
difference, with their tests, rather than submitting the historical merge stack.
No upstream PR is opened in this cycle.

## Validation and artifact scope

All 134 focused library tests pass with `jitv2` enabled, using
`nightly-2026-10-28`, locked offline dependencies and two test threads:

| Group | Passed |
| --- | ---: |
| NFS server | 22 |
| JIT queue/pool | 69 |
| PROM resolver | 11 |
| Packed PROM payloads/banners | 2 |
| Platform profiles | 22 |
| Configuration validation | 8 |

No selected test is ignored or failing. Three restored files are byte-identical
to upstream; the only JIT source change removes the redundant test. The
remaining delta passes `git diff --check` against upstream, and relative links
in the edited documentation and archives resolve. Prismatic's API and all
remaining production emulation code are unchanged.

The temporary worktree uses the integration checkout's existing Cargo lockfile
and an isolated build directory. Its first attempt lacked that ignored lockfile;
the successful run used a copy of the existing lockfile without changing
dependencies. These are focused host regressions, not a new guest qualification.

No guest OS or desktop emulator is started for this source cleanup. The selected
manual image remains pinned to qualified IRIS `819c682`; no CHD, snapshot or
user state is regenerated. Temporary source/build output is removed after the
validated changes and concise evidence have been saved.

Cleanup removed 1,002,233,856 allocated bytes (0.93 GiB) of temporary worktree
and build output. The topic branch is deleted, no owned test processes remain,
and compact check logs are retained under `.work/iris-delta-cleanup/`. Existing
pinned worktrees and qualified images are untouched.
