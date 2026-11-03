# Fork development

Use `xiri` as the integration branch in each fork:

| Project | Remote | Local development checkout | Default branch |
| --- | --- | --- | --- |
| IRIS | [salvogendut/iris, xiri](https://github.com/salvogendut/iris/tree/xiri) | `../iris` | `main` |
| NetBSD | [salvogendut/NetBSD-xiri, xiri](https://github.com/salvogendut/NetBSD-xiri/tree/xiri) | `../NetBSD-xiri` | `trunk` |

The NetBSD checkout is now `../NetBSD-xiri`; `../NetBSD-nixbench` is a
compatibility symlink to it, preserving older reproduction commands.
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
git -C ../NetBSD-xiri switch xiri
git -C ../NetBSD-xiri pull --ff-only origin xiri
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

The 2026-11-03 catalog survey fetched upstream at
`28fa516684c54e00e35b258c65e5dcac3a36165c`, already contained in IRIS
`xiri` `ae62114344a1d435152b8ae7e48c599974b4aec7`. No merge or emulator
rebuild was needed. The survey retains the qualified GIMP CHD and its
`819c682` emulator; both fork integration checkouts started clean.
The active-day check after midnight in Europe/Rome on 2026-11-04 fetched
the same upstream revision and reconfirmed ancestry; no integration or
additional emulator build was required.

The 2026-11-03 GIMP cycle fetched upstream again at
`28fa516684c54e00e35b258c65e5dcac3a36165c`. It is already an ancestor of
IRIS `xiri` `ae62114344a1d435152b8ae7e48c599974b4aec7`; no merge or rebuild
is required. The application diagnostic retains the current winterm CHD's
qualified `819c682` emulator. Both fork checkouts started clean on `xiri`.

NetBSD `xiri` now contains and has pushed the full-action-mask/NODEFER fix
`7b7794b0c07` and its documentation follow-up `675a3ac19e5`. The isolated
`.work/netbsd-gimp-build` module retains the unchanged `9390bc04900` N64
core. The [build record](../lab/irix-gimp/build.json) verifies source
equivalence; [paired signal records](results/2026-11-03-irix-gimp-signals.json)
and [application observations](results/2026-11-03-irix-gimp.json) record the
passed checks and clean shutdown. Pinned worktrees and the winterm manual
image remain intact.

The 2026-11-03 winterm reliability cycle fetched upstream at
`28fa516684c54e00e35b258c65e5dcac3a36165c`, already contained in the current
IRIS `xiri` tip `ae62114344a1d435152b8ae7e48c599974b4aec7`. There were no new
upstream commits to integrate. Diagnostics retain the current CHD's qualified
`819c682` emulator; the independent COW persistence changes in the integration
checkout do not repin that artifact.

The corresponding NetBSD module changes are committed on `xiri` as
`4f3d8a183ea`: PTY window-size translation and SIGCHLD SA_NOCLDSTOP support.
The [source-equivalence record](../lab/irix-winterm-reliability/source-equivalence.json)
checks every module-build source against that commit. The N64 core kernel
remains byte-identical to `9390bc04900`; only the compatibility module is
rebuilt in the separate `.work/netbsd-winterm-build` directory. The
[cycle report](results/2026-11-03-winterm-reliability.md) records validation.

The 2026-11-03 wheel-account image update fetched upstream again at
`28fa516684c54e00e35b258c65e5dcac3a36165c`, already contained in IRIS `xiri`
`1aed0dfc842a427e32a53ad083e1be0a9d46a613`. No merge or fork build was needed;
the update changes native account membership and image metadata only.

The 2026-11-03 xdm-image cycle fetched upstream at
`28fa516684c54e00e35b258c65e5dcac3a36165c`, already contained in IRIS `xiri`
`1aed0dfc842a427e32a53ad083e1be0a9d46a613`; no upstream merge was needed.
The first CHD login exposed a native UVM allocator lower-bound fault. NetBSD
`xiri` commit `9390bc04900a0d04796d494aca5b00651f12954d` fixes it; the
[allocator record](results/2026-11-03-uvm-pglist.md) preserves the failed run
and exact regression. A fresh kernel/module build uses the integration
checkout and `.work/netbsd-xdm-build`. The image retains the qualified
`819c682` emulator; the [image record](results/2026-11-03-xiri-xdm-image.md)
tracks replacement validation. Older detached builds and manual images
remain unchanged.

The 2026-11-03 xdm cycle fetched upstream again at
`28fa516684c54e00e35b258c65e5dcac3a36165c`, already contained in IRIS `xiri`
`1aed0dfc842a427e32a53ad083e1be0a9d46a613`. No merge or affected emulator
rebuild was needed. Both fork checkouts were clean; NetBSD `xiri` remains
`1c248bf932f369c3271239b8c20bc3efd55bca44`. This cycle changes native Xiri
userspace only and retains the module image's qualified kernel/module and
`819c682` emulator. Pinned reproductions and the previous manual image remain
untouched. The [xdm qualification](results/2026-11-03-xiri-xdm.md) covers
three IRIX sessions, a separate native ctwm account, full-screen acceleration,
logout/recovery and clean guest shutdown.

The 2026-11-03 service/session cycle fetched upstream again at
`28fa516684c54e00e35b258c65e5dcac3a36165c`, already contained in IRIS `xiri`
`1aed0dfc842a427e32a53ad083e1be0a9d46a613`. There were no new commits to
integrate and no emulator build changes. This cycle changes native userspace
integration in Xiri. Independent console-artwork work advanced NetBSD `xiri`
to `1c248bf932f369c3271239b8c20bc3efd55bca44` during the cycle; those changes
were left untouched. Guest qualification retains the module image's tested
`819c682` emulator and the kernel/module from `d1ce7a96615`.
The [qualification](results/2026-11-03-xiri-session.md) passes native descendant
checks, four desktop sessions and service lifecycle checks. Detached
reproduction worktrees and the selected manual image are preserved.

The 2026-11-03 module-image cycle checked upstream again at
`28fa516684c54e00e35b258c65e5dcac3a36165c`. It is already contained in
`xiri` `1aed0df`; no integration or fork source changes were needed.
The image uses the previously qualified `819c682` emulator and the matching
kernel/module artifacts from NetBSD `d1ce7a96615`. Image boot and desktop
checks are recorded separately from source-build qualification.

The module cycle merged and pushed NetBSD commits `c46d4e9a931` and
`d1ce7a96615` to `xiri`. The completed `topic/compat-irix-module` branch was
removed after the push; its source worktree is detached at `d1ce7a96615`.
They build the o32/n32 personality as an N64 module and repair a diagnostic
receive assertion exposed by the desktop test. The [cycle record](results/2026-11-03-irix-module.md)
contains lifecycle, boot, desktop and regression evidence. Its isolated
`.work/netbsd-module-src` source and `.work/netbsd-module-build` artifacts
preserve the tested input; the older detached lab worktrees stay pinned.

The 2026-11-03 kernel-module cycle fetched upstream
`28fa516684c54e00e35b258c65e5dcac3a36165c` and integrated it as
`1aed0dfc842a427e32a53ad083e1be0a9d46a613` on IRIS `xiri`, then pushed it.
The sole new upstream commit corrects the Octane CPU in a virtio-serial
validation test. Our previous integration already contains that correction
and an O2 rejection assertion. Resolving the overlapping test hunk preserved
our version; `git diff --cached --exit-code HEAD` verified an identical tree
before the merge commit, and `git diff --check` passed. No executable or test
code changed in this integration. Guest module qualification retains the
qualified `819c682` emulator bundled with the current desktop image.

The 2026-11-03 workflow-cleanup cycle fetched upstream
`68f4e4a6d56d85e109ef3d4363854df1cd39cfda` and merged/pushed it as
`c84757d2f812412581253352c9947c1058e9cf3a`, integrating its storage,
configuration-validation, serial, virtio-serial, idle-parking and NFS updates.
The fork's embedded O2/Octane firmware selection is preserved, including
strict explicit-path errors. See the [cycle record](results/2026-11-03-workflow-cleanup.md)
for the integration commit and validation. The manual desktop bundle retains
its tested `819c682` emulator; integration does not repin that artifact.

This merge was made in `.work/iris-upstream-sproc`. Subsequent independent
performance integration advanced `xiri` to `3b854a8` and returned its ownership
to `../iris`; the temporary worktree is now detached at `26771f9`. The new tip
contains `c84757d`. Its additional changes belong to that separate cycle.
`./xiri status` finds the actual branch owner; `./xiri build iris` builds there
without switching a shared checkout. NetBSD development uses `../NetBSD-xiri` on `xiri`.
See the [maintained commands](DEVELOPMENT.md).

The November 3 xmahjongg cycle checked upstream again: `2eb811f` is still
already contained in IRIS `xiri` `819c682`; no integration was needed.
NetBSD `xiri` is now `5f094bc6ab9` after the separate runtime-theme merge.
The rendering investigation keeps its existing framed-kernel pin for a
controlled comparison. All three project checkouts were clean and pushed
before starting the investigation.

The xmahjongg repair changes the Xorg driver in **NetBSD xsrc**, which is a
separate repository from the NetBSD kernel fork. The reproducible
[source pin and patch](../lab/newport-xaa/README.md) currently live in Xiri;
neither fork needs another code change for this correction. Native builds
of the original and patched module isolate the change against the same
Xorg headers. The existing kernel and IRIS integration pins remain intact.

The framed-console/acceleration trial rechecked upstream on 2026-11-02
and again on 2026-11-03 (Europe/Rome, 23:00 UTC on November 2):
`upstream/main` remains `2eb811f43a69a9dec7f0ceb50cb439b7e088845c`, already
contained in `xiri` at `e0493739955391c1a344655fd0361d4997e51372`
and still contained after the color correction at `819c682`.
No merge was needed. A separate release build in `.work/target-newport-accel`
is used for this trial; the older qualified emulator binaries remain intact.
At the user's explicit request, its NetBSD source comes from a snapshot of
`feature/newport-framed-console`. Those frame changes were subsequently
committed by their owning task as `a536d8c4da2`; all twelve changed files
match the build snapshot byte-for-byte. See
[the trial inputs](../lab/newport-accel/README.md).

IRIS `xiri` commit `819c6825504d40ad9f9aa00554249affd2da9446` corrects
RGB24 fast-clear colors and physical write masks using the REX3/RB2 layout
catalogued in `../sgi`. The new expected-value regressions fail on the
previous renderer; 183 Newport tests pass after the correction, including
generic and Cranelift paths. Guest qualification uses a separate build of
this commit, preserving the earlier binaries and disk images. The shared
IRIS/Prismatic performance checkouts remain untouched.

The [desktop behavior cycle](results/2026-11-02-irix-desktop-behavior.md)
reviewed upstream `2eb811f43a69a9dec7f0ceb50cb439b7e088845c` and merged/pushed it
as IRIS `xiri` commit `e0493739955391c1a344655fd0361d4997e51372`. Only the Octane
halt-request document and its index link changed. Whitespace and link checks
passed; executable code and the qualified 9df1df1 emulator pin are unchanged.

The [original-shell cycle](results/2026-11-02-iris-upstream-vendor-shell.md)
integrates upstream `4c1c87f5161c13b323d9b5d57a93779d355729b5` through
`xiri` merge `f38cfa1c5e62def9fbefa5244e07adf285f02d3b`. Workspace tests
pass 2,618 checks and JIT/idle library tests pass 2,956. Existing guest
emulator pins remain unchanged.

The [shell-image packaging cycle](results/2026-11-02-irix-shell-image.md)
rechecked upstream on 2026-11-02: it remains at `4c1c87f5161c13b323d9b5d57a93779d355729b5`.
No merge or emulator rebuild was needed. Image checks retain the qualified
`9df1df14334838a989253efefe26f0547e6da592` emulator pin.

The same cycle adds NetBSD shell support at
`849755450135c6734bb61c4973d687d0c8060739`. Concurrent work switched the
shared checkout to `feature/wscons-decor` before the compatibility-only
commit; that commit was then fast-forwarded into `xiri` from the isolated
`.work/netbsd-vendor-shell-src` checkout and pushed. The active feature
branch and its uncommitted Newport edits were preserved. Final qualification
uses the clean committed tree, not the shared checkout's work in progress.

The [2026-11-02 desktop cycle](results/2026-11-02-iris-upstream-desktop.md)
integrates upstream `43e525a847ceeb9453af5d685dd8d353bea133e1` into `xiri`,
with 2,578 workspace and 2,921 JIT/idle library tests passing. The existing
integration worktree owns `xiri`; the shared performance checkout and pinned
guest binaries remain unchanged.

The [desktop usability cycle](results/2026-11-02-desktop-usability.md)
rechecked the same upstream revision later on 2026-11-02; there were no new
commits to integrate. Native rpcbind's duplicate-loopback fix is NetBSD
`xiri` commit `d3a316bd7e1`; it does not repin or rebuild the guest kernel.

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

The desktop filesystem/RPC cycle qualifies NetBSD `xiri` source
`9c8bd4e328f` with 6,500 records and 32 controls across LP64 CI/ordinary and
o32 CI guests. Separate desktop build directories preserve the signal kernel
and qualified CHD. See the [result](results/2026-11-02-irix-desktop-fs.md).

The 2026-11-02 icon/file-locking cycle fetched IRIS upstream again at
`43e525a847ceeb9453af5d685dd8d353bea133e1`, already contained in integration
`xiri` at `a4a1659d0b3180713f988d73b7b7da204048ae6a`. No merge or emulator
rebuild was needed. NetBSD `xiri` adds measured o32/n32 record-lock translation
at `3e154cdc37c`; separate filelocks build directories preserve the previous
kernels and images. See the [locking/artwork record](results/2026-11-02-irix-filelocks.md)
for reference measurements and validation.

The same icon cycle adds measured o32/n32 seek offsets at NetBSD `xiri`
`57430add71d693d33ba2048f4543e74d16ea315e`. Clean builds are pinned in
`lab/irix-filetypes/{baseline,o32-baseline}.json`; the lock-only builds remain
preserved. Both NetBSD commits are pushed. Native FAM pathname mapping is
maintained in this repository; no IRIS source changes were required.

The 2026-11-02 catalog/application cycle fetched eight new IRIS commits through
`3cba53ad50c500f73c4e0d97cb4cb13e7662c820` and merged them without conflicts
into `xiri` at `c0eb0b27f30dceddfad53fc1895bf2576be0c6da`, now pushed. The
changes cover JIT worker shutdown, weak lock ownership, Octane cleanup,
ISP1040 completion interrupts, sparse disk-copy fallback, CI shell markers and
Windows memory remapping. Offline locked workspace tests passed (2,589 tests,
33 ignored); the `jitv2,idle-pause` library suite passed (2,927 tests,
32 ignored). These Linux tests do not validate the Windows-specific backend.
The integration used `.work/iris-upstream-sproc` and nightly 2026-10-28 in the
existing Toolbox. Logs are `.work/catalog-actions/iris-{workspace,jit-idle}.log`.
The pinned guest emulator and detached reproduction worktrees remain unchanged.

The same application cycle qualifies NetBSD `xiri` commit
`ac4423d4657c4664898dfcab44b9f19c66f46f3b`, now pushed, for high preferred
library addresses. Separate elfmap-high builds preserve the icons kernel.
The [result](results/2026-11-02-irix-elfmap-high.md) records 700 mapping checks,
32 controls and the original IRIX comparison. The existing manual CHD is
unchanged.
