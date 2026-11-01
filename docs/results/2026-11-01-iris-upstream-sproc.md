# IRIS upstream update during the sproc cycle

IRIS `xiri` now includes upstream
[`4ad1b1d435dc115697433f091b10dfa8c48aa7ed`](https://github.com/techomancer/iris/commit/4ad1b1d435dc115697433f091b10dfa8c48aa7ed)
through published merge `045d69245609d186907a20e0b002e2b60be9a1ac`.
The fetch found 19 commits after the previously checked `f17b4d3`.
The [evidence record](2026-11-01-iris-upstream-sproc.json) contains their full
revisions, commands, lockfile identity and validation log hashes.

The changes add an overlay sector journal, disk flushing on exit signals,
MC DMA wake/stop fixes, Ethernet receive overflow handling and bounded receive
holding, breakpoint publication ordering, idle/reset cycle accounting, JIT
deferred-compilation accounting and more reliable test synchronization.

The merge from our `087d250` required no conflict resolutions. All 59 fork-only
files outside the upstream change set have identical Git blobs before and after
the merge. Overlapping changes retain the fork's CHD handling, memory-controller
snapshot restoration, TLB fixes and embedded machine lifecycle support. New
disk-persistence tests exercise the journal and signal-flush behavior.

Validation used the existing Fedora Toolbox, Rust `nightly-2026-10-28`, locked
offline dependencies, two build jobs, two test threads, Xvfb and software GL:

| Suite | Passed | Failed | Ignored |
| --- | ---: | ---: | ---: |
| Complete workspace | 2,161 | 0 | 29 |
| Core library with `jitv2,idle-pause` | 2,504 | 0 | 28 |

The workspace total includes 2,062 core, 92 GUI, three hostcall, two binary /
integration and two documentation tests. A nested child-process result is
excluded from the total to avoid counting it twice. Initial launcher attempts
failed before running tests because the isolated worktree needed the explicit
Cargo path/environment and existing ignored lockfile; these logs are retained.
No source change was needed to make the suites pass.

Integration used `.work/iris-upstream-sproc` on `xiri`. The shared `../iris`
checkout's unrelated `perf/sgiemu-port` work was left untouched. There was no
temporary topic branch to remove. Qualified detached worktrees, release
binaries and guest pins remain unchanged: these host checks do not establish
a new NetBSD or IRIX guest baseline.
