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
