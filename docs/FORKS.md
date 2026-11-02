# Fork development

Use `xiri` as the integration branch in each fork:

| Project | Remote | Local development checkout | Default branch |
| --- | --- | --- | --- |
| IRIS | [salvogendut/iris, xiri](https://github.com/salvogendut/iris/tree/xiri) | `../iris` | `main` |
| NetBSD | [salvogendut/NetBSD-xiri, xiri](https://github.com/salvogendut/NetBSD-xiri/tree/xiri) | `../NetBSD-nixbench` | `trunk` |

The local NetBSD directory retains its older name; its origin points to
NetBSD-xiri. There is currently no separate `../NetBSD-xiri` checkout.
The [consolidation record](results/2026-11-01-xiri-branches.md) records the
merged histories, removed branch names and verification. Work includes both
the IRIX compatibility chain and XFS in NetBSD, and all NetBSD/frontend/TLB
changes in IRIS. The default branches remain available for upstream tracking.

## Continue development

Inspect `git worktree list` before switching branches. If another active
worktree owns `xiri`, leave it unchanged and create a topic from the latest
`origin/xiri` for independent work. Publish the validated integration with a
normal fast-forward push; the owning task can advance its checkout when ready.

```sh
git -C ../iris switch xiri
git -C ../iris pull --ff-only origin xiri
git -C ../NetBSD-nixbench switch xiri
git -C ../NetBSD-nixbench pull --ff-only origin xiri
```

Make routine changes on `xiri`. When a topic branch is needed, create it from
that project's `xiri`, merge it back into `xiri` at the end of the work cycle,
and remove the completed topic branch after the merge is pushed. Use a prefix
such as `topic/`: Git cannot keep `xiri` and `xiri/<name>` branches together.
Within these two forks, the default branches are not development targets for
Xiri changes. The separate `salvogendut/xiri` lab/documentation repository
continues on `main`; it is not one of the two forks in this table.

Use separate build output paths for a new source tree or architecture, and
keep kernel builds sequential with at most two jobs. Branch consolidation does
not repin qualified kernels, emulator binaries, runtime resources or guest disks.

## IRIS upstream updates

Check [techomancer/iris](https://github.com/techomancer/iris) at the start of each
development cycle and once per active day during longer cycles. This is part
of active repository work; no unattended scheduler is installed.

```sh
git -C ../iris fetch --no-tags upstream main
git -C ../iris log --oneline xiri..upstream/main
git -C ../iris diff --stat xiri...upstream/main
```

Review and merge new upstream commits into `xiri`, using a temporary
`topic/upstream-<date>` branch when needed. Resolve conflicts while preserving
the fork's NetBSD and frontend changes. Run the affected build and regression
checks, record the exact upstream revision and results, then finish the usual
merge/push/topic-cleanup cycle. Diagnose failed checks before publishing;
record any unresolved blocker instead of presenting an untested merge as ready.
Existing guest pins remain unchanged until a separate runtime qualification
accepts a replacement.

The [2026-11-01 upstream integration record](results/2026-11-01-iris-upstream.md)
tracks the first check under this workflow.

The updated offscreen GL path needs an EGL runtime, which was absent from the
original Fedora build Toolbox. Install it there before the workspace tests:

```sh
toolbox run -c xiri-iris sudo dnf install -y mesa-libEGL libglvnd-egl
```

An isolated `xvfb-run -a` display with `LIBGL_ALWAYS_SOFTWARE=1` can exercise
the GL context test without depending on the host desktop's graphics setup.
Keep the test enabled so a missing runtime is not mistaken for a successful
GL check.

## Reproduce an earlier checkpoint

Historical topic branch names in result JSON and old prose describe where the
work was developed. Those branch names have been retired; their commits remain
reachable through the consolidated history. Fetch `xiri`, then create or use a
detached worktree at the exact `source_revision`/`emulator_revision` from the
chosen lab's pin. Existing pinned worktrees keep their original commits and
files. Their detached state is intentional.

```sh
git -C ../NetBSD-nixbench fetch origin xiri
git -C ../iris fetch origin xiri
```

The established worktrees are `.work/netbsd-irix-src`,
`.work/netbsd-irix64-src`, `.work/netbsd64-src` and `.work/iris-netbsd64`.
Inspect `git worktree list` before creating another. Keep the matching build
and TFTP directories with their lab. Do not replace a pinned checkout with the
latest branch and reuse its old qualification record.

`scripts/build-iris.sh` now clones `xiri`, then fetches and checks out its
unchanged qualified revision. Existing historical build commands likewise
fetch the consolidated branch and retain their explicit detached commit.
A new combined runtime qualification is required before adopting the integrated
fork tips as new lab baselines; host regression tests alone do not replace it.

The 2026-11-01 pipe/installer cycle rechecked upstream at
`f17b4d3bc1663efd02f93a5e0e4811eebba510c8`, already in IRIS `xiri`
`087d250ab25884baaf03cc998377f75711fe5aa4`. No integration or new emulator
build was needed. The pinned guest emulator remains `9df1df14334838a989253efefe26f0547e6da592`;
[pipe qualification](results/2026-11-01-irix-pipe.md) records the affected
kernel builds and guest checks. Unrelated shared-checkout performance work
was left untouched.

The subsequent 2026-11-01 shared-mapping/installer cycle fetched the same
upstream revision and found no new commits to integrate. NetBSD code is on
`xiri` at `7af1404388b9f2db84f97a114c9f003b7c50b094`; the isolated LP64/o32
builds and [paired mapping matrices](results/2026-11-01-irix-mmap-shared.md)
qualify it. No emulator change was needed, and the unrelated shared-checkout
performance work and detached reproductions were preserved. The
[installer retry](results/2026-11-01-irix-installer-shared.md) records the
next `sproc` boundary independently of kernel mapping qualification.

The 2026-11-01 sproc cycle found 19 new upstream commits through
`4ad1b1d435dc115697433f091b10dfa8c48aa7ed` and published merge
`045d69245609d186907a20e0b002e2b60be9a1ac` to IRIS `xiri`. The isolated
`.work/iris-upstream-sproc` worktree owns that branch; the shared checkout's
`perf/sgiemu-port` work remains untouched. The [integration record](results/2026-11-01-iris-upstream-sproc.md)
reports 2,161 workspace and 2,504 JIT/idle library tests passing. Existing
qualified guest binaries and detached worktrees remain pinned.

At the start of the subsequent native sproc implementation cycle, a fresh
fetch still reported upstream `4ad1b1d435dc115697433f091b10dfa8c48aa7ed`, already
contained in IRIS `xiri` at `045d69245609d186907a20e0b002e2b60be9a1ac`.
No further merge or emulator build was needed. The new kernel work is on
NetBSD `xiri`; separate `.work/netbsd-irix-sproc-build` and
`.work/netbsd-irix-sproc-o32-build` directories preserve the earlier mapping
checkpoint. The pinned guest emulator and detached reproductions are unchanged.

Native sproc kernel code is pinned at NetBSD `xiri`
`f32cbf59a52b951f9792b2af74125ad2bbedae44`. The
[qualification record](results/2026-11-01-irix-sproc.md) covers both kernel
builds, LP64 CI/ordinary and o32 CI, plus mapping regressions; the
[installer follow-up](results/2026-11-01-irix-installer-sproc.md) records the
new descriptor boundary. Later documentation-only commits do not change
these qualified binaries or their recorded source revision.


The 2026-11-01 F_DUPFD cycle fetched IRIS upstream again at
`4ad1b1d435dc115697433f091b10dfa8c48aa7ed`, already integrated in IRIS `xiri`
`045d69245609d186907a20e0b002e2b60be9a1ac`. No merge or emulator rebuild was
needed. NetBSD kernel code is on `xiri` at
`572dcb832cb3a42f7c728115db241cae88fc5d8c`, with separate
`.work/netbsd-irix-dupfd-build` and `.work/netbsd-irix-dupfd-o32-build` outputs.
The [F_DUPFD qualification](results/2026-11-01-irix-dupfd.md) records both builds,
the original/native matrices and regressions. Later documentation commits do
not change those artifacts; detached reproductions and unrelated IRIS
performance work remain untouched.


The time/gettimeofday continuation retains the same checked upstream revision
and IRIS integration state. NetBSD `xiri` source
`76de548ab644cb471f4c5b97ec89671c1d385c5b` builds in separate
`.work/netbsd-irix-time-build` and `.work/netbsd-irix-time-o32-build` directories.
The [time qualification](results/2026-11-01-irix-time.md) records both clean
builds, original/native ABI matrices and xclock updates. The
[installer retry](results/2026-11-01-irix-installer-time.md) retains its remaining
helper boundary. Later documentation commits do not change the pinned source
or binaries; no IRIS source change or upstream merge was needed.

At the start of the installer-helper cycle, all three repositories were
verified clean and pushed (Xiri `640a039`, NetBSD `xiri` `1532f82a003`, IRIS
`xiri` `045d692`). A fresh fetch again found upstream
`4ad1b1d435dc115697433f091b10dfa8c48aa7ed` already contained in IRIS `xiri`.
No integration or affected emulator rebuild was needed. The
[helper qualification](results/2026-11-01-irix-installer-helpers.md) uses the
existing time kernel and qualified emulator in fresh disposable guests;
detached reproductions and the unrelated IRIS performance branch remain
untouched. Only Xiri lab tooling and documentation change in this cycle.

The 2026-11-01 signal-reference cycle starts from Xiri `dd4c1f4`, NetBSD
`xiri` `1532f82a003` and IRIS `xiri` `045d692`. A fresh fetch from
`https://github.com/techomancer/iris.git` again finds upstream
`4ad1b1d435dc115697433f091b10dfa8c48aa7ed` already contained in the IRIS
integration branch. There are no new commits to merge or emulator changes
to rebuild. The [480-execution reference](results/2026-11-01-irix-signal-reference.md)
uses the pinned original-IRIX emulator; NetBSD runtime source remains
`76de548ab644cb471f4c5b97ec89671c1d385c5b`. Both fork integration worktrees
remain clean and detached reproductions remain pinned.


The signal implementation/import cycle again fetched IRIS upstream at
`4ad1b1d435dc115697433f091b10dfa8c48aa7ed`, already an ancestor of IRIS `xiri`
`045d69245609d186907a20e0b002e2b60be9a1ac`. No new commits, merge or emulator
rebuild was needed. The integration worktree remains `.work/iris-upstream-sproc`;
the unrelated main-checkout performance branch and detached labs are untouched.
NetBSD `xiri` signal code is pinned at
`4680cd61b625a5eaa393a0deaea73f4b9f7ed7bc` in the separate signal build
folders. The [qualification](results/2026-11-01-irix-signal.md) records
1,216 final native records, 76 controls and exact earlier regression pins.
Documentation-only commits do not change the qualified binaries. Installed
application import is Xiri lab work and does not modify the source image.

At the 2026-11-02 Europe/Rome day boundary, the image cycle fetched IRIS
`upstream/main` again from `https://github.com/techomancer/iris.git`. It remains
`4ad1b1d435dc115697433f091b10dfa8c48aa7ed`, already an ancestor of integration
`xiri` at `045d69245609d186907a20e0b002e2b60be9a1ac`. No merge or affected
emulator rebuild was required. NetBSD `xiri` is pushed through documentation
commit `d267235cc0d`; the image retains qualified signal kernel source
`4680cd61b625a5eaa393a0deaea73f4b9f7ed7bc`. Both integration worktrees remain
clean, and detached reproductions retain their original pins.

The 2026-11-02 Prismatic boot cycle fetched IRIS upstream again: revision
`4ad1b1d435dc115697433f091b10dfa8c48aa7ed` remains contained in `xiri`
`045d69245609d186907a20e0b002e2b60be9a1ac`; no merge or rebuild was needed.
The [Prismatic test](results/2026-11-02-prismatic-xiri.md) exercised its
existing release binary and preserved its separate performance checkout.
This was frontend validation, with no development changes on that branch.

The 2026-11-02 desktop display/menu cycle fetched upstream again and found
`4ad1b1d435dc115697433f091b10dfa8c48aa7ed` already contained in IRIS `xiri`
`045d69245609d186907a20e0b002e2b60be9a1ac`. No merge or affected emulator
rebuild was needed. The work changes Xiri's native Xorg configuration and
desktop launch integration; the NetBSD signal kernel and both fork source
branches remain unchanged. The performance checkout and pinned lab worktrees
are preserved.
