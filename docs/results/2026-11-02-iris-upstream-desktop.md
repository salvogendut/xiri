# IRIS upstream integration during desktop repair

IRIS `xiri` includes 27 new upstream commits through
`43e525a847ceeb9453af5d685dd8d353bea133e1`. The published merge and exact
commit list are in the [qualification record](2026-11-02-iris-upstream-desktop.json).
Changes include Odyssey/VPro graphics, O2 rendering, headless Octane snapshots,
stream Ethernet and test/trace path defaults.

The merge preserves the fork's network worker ownership and shutdown joins,
embedded firmware loading, powered-off reset handling and peripheral restart.
Conflicts in the changelog, storage guide and agent index retain both sets of
documentation. The Octane power-on body includes upstream VPro reset state.
An initial compile failure exposed an upstream diagnostic's assumption that
firmware came from a named path; the message now describes the loaded PROM.

Validation used Rust `nightly-2026-10-28`, locked offline dependencies, two
build jobs, two test threads, Xvfb and software GL in the existing Toolbox:

| Suite | Passed | Failed | Ignored |
| --- | ---: | ---: | ---: |
| Workspace | 2,578 | 0 | 33 |
| Library with `jitv2,idle-pause` | 2,921 | 0 | 32 |

Nested child test reports are excluded from these totals. The initial failure
and successful rerun logs are retained privately and hashed in the record.
Fork-only files outside the upstream change set retain identical Git blobs.
The only edit after these tests removed an upstream extra newline at EOF,
alongside documentation additions.

The integration worktree is `.work/iris-upstream-sproc` on `xiri`. Unrelated
`../iris` performance work, detached reproductions and qualified guest binaries
remain unchanged. Host tests alone do not qualify a replacement guest emulator.
