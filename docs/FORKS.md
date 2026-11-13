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

The document-launching cycle fetched upstream on 2026-11-13 through
`9605704cf2a0b204fddc920e6236a3b8050f9e38` and integrated seven commits as
`84125cacb985f974c8f9d81150560150267fb194` on IRIS `xiri`.
The sole conflict was the documentation index; all fork and upstream entries
are retained. The feature workspace passes 5,539 library tests (60 ignored),
the default library passes 4,852 (51 ignored), both normal CLI binaries build,
and all 32 optional idle-parking tests pass with `jitv2` enabled.
The [integration ledger](results/2026-11-13-documents-upstream.json) retains
exact inputs and log hashes. NetBSD and the qualified manual-image emulator
remain unchanged; pinned detached worktrees are preserved.

The clipboard cycle fetched upstream on 2026-11-13 through
`74e265540ae1baf247608e0044defacca6b475c9` and integrated 15 commits.
IRIS `xiri` is pushed at `2dc6fa9132233d3aa9fd96bdaa1c5c556675cf6b`.
The documentation index retains both sides' entries; the frontend serial
extension uses upstream's new constructor and refused-byte tracking.
The feature-enabled workspace passes 5,530 library tests (59 ignored), the
default library passes 4,843 (50 ignored), and both normal CLI binaries build.
The [integration ledger](results/2026-11-13-clipboard-upstream.json) records
commands, hashes and scope. The selected CHD and frontend bundle retain their
qualified emulator pins. NetBSD remains unchanged at `8bf86af`.

The same November 13 File Manager cycle adds filesystem statistics and
removal to NetBSD `xiri` at `8bf86afce2afede752c0eae37852e2f2472d91cb`, pushed
to origin. The module passes 384 statvfs-family and 336 unlink/rmdir records
against original IRIX 6.5.22m. Its
[build manifest](../lab/irix-pathops/filemanager-build.json) and
[committed equivalence](../lab/irix-pathops/source-equivalence.json) explicitly
separate the new module from the unchanged native-wait core at
`e9ff76a58affee773b767d334f98075bf86daf7e`. The manual image retains its
qualified emulator `819c6825504d40ad9f9aa00554249affd2da9446`.

The File Manager/Dumpster cycle fetched upstream on 2026-11-13 through
`a6503d006c6dee03878919d58b52470f0a855125`. The two incoming commits merge
cleanly as `993d8400f50c81edd8b853323458c0484908c866`, pushed on IRIS `xiri`.
The updated CI feature set passes all 14 REX replay corpus tests (two ignored).
The refused-GPU-submission regression also passes with real Mesa Lavapipe
Vulkan execution. The changes concern CI features and optional GPU error
reporting; the desktop image and retained frontend binaries keep their
previously qualified pins. The isolated 1.21 GiB build directory was removed
once the merge and logs were saved; the [check ledger](results/2026-11-13-file-manager-upstream.json)
retains exact revisions, feature sets, log hashes and cleanup size.

The shutdown/session cycle fetched `https://github.com/techomancer/iris.git`
on 2026-11-13 through `f0914a0b73d086f4b7a58cb8e362e2ce8973617a` and
integrated all 645 incoming commits. Merge
`36858ff4e8694756502fa1e84b1190e6997d6e0d` is pushed on IRIS `xiri`.
CPU part models, packed firmware and network ownership use the new
upstream APIs; the fork retains NetBSD TLB matching, Newport RGB24 planes,
frontend embedding hooks and opt-in GPR/RTC caching. Prismatic adaptation
`3a5e48d7269f2145b5c571da1c3c78b82d88e827` is pushed on its `main` branch.

Validation passes the full IRIS workspace suite (5,482 library tests), the
R4400 bare-metal named-failure baseline, 180 Prismatic tests, formatter/clippy,
isolated upstream-main compilation/clippy, dummy SDL and graphical PROM
smokes, and the rebuilt Instigator's BOOTP/TFTP over Unix and TCP streams.
The merged core also boots NetBSD/Xorg and restores two winterms and xclock
at their saved positions after an active-desktop reboot; clean halt and the
base-image hash pass. The [integration ledger](results/2026-11-13-iris-upstream.json)
records exact sources, binaries and local evidence.

NetBSD source is unchanged on `xiri`. The new shutdown-saving image retains
its independently qualified `819c682` emulator, kernel/module and Newport
driver pins. The merged emulator is separately qualified; pinned lab worktrees
and existing manual images/state are preserved.

The saved-desktop-session cycle checked upstream on 2026-11-06 at 12:31 UTC.
`280f3eb22e74057d506fed082f527b92320fabd7` is still an ancestor of IRIS `xiri`
at `b23f674c235b37c3ac83808085d28ac128bb79c4`, with no incoming commits.
No merge or rebuild was required. Both fork worktrees were clean; NetBSD
remains on `xiri` at `0febc6eb24ad889d12a3b2afaa12558c9781859d`.
This cycle changes the native session runtime and imports the original
`tellwm` helper, retaining the qualified kernel/module and emulator pins.

The desktop-colour cycle fetched `https://github.com/techomancer/iris.git`
on 2026-11-06 at 10:42 UTC. Upstream remains
`280f3eb22e74057d506fed082f527b92320fabd7`, already contained in IRIS `xiri`
at `b23f674c235b37c3ac83808085d28ac128bb79c4`; the incoming log is empty and
`merge-base --is-ancestor` passes. No merge or rebuild is needed. Both fork
worktrees are clean; NetBSD remains on `xiri` at
`0febc6eb24ad889d12a3b2afaa12558c9781859d`. Colour fixes use session resources;
the previously qualified emulator, kernel, module and Newport driver remain
pinned. See the [colour result](results/2026-11-06-desktop-colours.md).

The desktop-preferences cycle fetched upstream on 2026-11-06 through
`280f3eb22e74057d506fed082f527b92320fabd7`. Merge
`b23f674c235b37c3ac83808085d28ac128bb79c4` is pushed on IRIS `xiri`.
The five commits add opt-in Newport partial framebuffer uploads and their
documentation, correct Perfetto event references, and document MIPSpro
installation. The merge needs no conflict resolution. The default Linux
release build passes; regression results are 123 default Newport tests,
132 with `rex-dirty-upload,gputrace`, ten upload-planner tests, five display
tests and five UI tests. Four Newport tests remain ignored in each build.
The compositor filter selects no tests and is not counted as validation.
Logs and build provenance are under `.work/desktop-preferences/iris-*` and
`.work/workflows/build-x39ei456`. The optional upload feature stays disabled
by default. Desktop tests retain the qualified `819c682` emulator and the
existing kernel/module; no NetBSD source changes are needed for preferences.

The multi-user desktop cycle fetched upstream at its start on 2026-11-05
and again after midnight on 2026-11-06 (23:00 UTC on November 5).
`c382cdcc25389769b5ae3a436ae1ff73ae42e964` is already an ancestor of IRIS
`xiri` at `fb24628e1bf97a4f379309c79e808d82929672b7`; the incoming commit
list is empty. No integration or emulator rebuild is needed. NetBSD remains
on `xiri` at `0febc6eb24ad889d12a3b2afaa12558c9781859d` without source
changes for this feature. Multi-user FAM uses the existing native TCP owner
lookup. Tests retain the selected wait image's kernel/module and pinned
`819c6825504d40ad9f9aa00554249affd2da9446` emulator. The
[multi-user qualification](results/2026-11-05-multiuser.md) passes with these
unchanged pins; only the lab/runtime repository needs a feature commit.

The 2026-11-05 native-sleep investigation fetched upstream at 19:40 UTC.
`c382cdcc25389769b5ae3a436ae1ff73ae42e964` was already included in IRIS
`xiri` at `fb24628e1bf97a4f379309c79e808d82929672b7`; no additional
integration or emulator rebuild was needed. Diagnostic guests retain
the qualified `819c682` emulator and their original kernel/module hashes.
The local check ledger is `.work/native-sleep/setup.json`.

The 2026-11-05 cleanup-deadline cycle fetched upstream at 17:00:05 UTC through
`c382cdcc25389769b5ae3a436ae1ff73ae42e964`. Merge
`fb24628e1bf97a4f379309c79e808d82929672b7` is pushed on IRIS `xiri`.
The seven commits cover pixel transfer scale/bias, sphere-map coordinates,
separate specular lighting, graphics tests/constants/documentation, and
Windows directory-fsync handling. The sole source conflict in `cow_disk.rs`
preserves our Windows `MoveFileExW` replacement with write-through while
adding upstream's contextual I/O errors; Unix rename and directory fsync
remain in place.
The isolated Linux release build passes, as do 358 Odyssey, 16 GL, six COW,
four CHD and 47 block-node tests (431 total; four Odyssey tests ignored).
Windows execution was not tested. Local logs are under
`.work/cleanup-deadline/iris-{build,test-*}.log`; build provenance is
`.work/workflows/build-xyih1ztn/build.json`.
The [runtime correction](results/2026-11-05-cleanup-deadline.md) changes no
NetBSD source. NetBSD remains at `e9ff76a58affee773b767d334f98075bf86daf7e`;
the replacement image and diagnostic guests retain qualified emulator
`819c682`, and all pinned reproduction worktrees remain unchanged.

The 2026-11-05 process-tracking cycle fetched upstream through
`54ea8c05afa2996c192768cc72bbe6fcb3c01f5f`. Merge
`e67e3cc3731c17de1a0c226dbd2d4448d07ec80f` is pushed on IRIS `xiri`.
The three commits cover Odyssey reads/lighting, IRIX 6.5.30 NFS negotiation,
and irix-sh timeout/line-length handling. The sole source conflict combines
our existing NetBSD AUTH_SYS mount fix with upstream's equivalent AUTH_UNIX
name, retaining AUTH_NULL as the second accepted flavour.
The isolated release build, 356 Odyssey tests (four ignored), and 158 network
tests pass. Host controls also check irix-sh's timeout reset and 255/256-byte
command/text-line boundaries without opening a guest connection. These checks
do not qualify a live IRIX 6.5.30 mount or telnet session. Logs and hashes are
indexed in the [process-tracking record](results/2026-11-05-process-tracking.json).
NetBSD remains at `e9ff76a58affee773b767d334f98075bf86daf7e`; no kernel change
is inferred from an unreproduced tracking failure. The manual image and
diagnostic guests retain pinned emulator `819c682`, and detached reproduction
worktrees remain unchanged.

The 2026-11-05 process/job-control cycle fetched upstream at 09:55 UTC and
found `436847c55cd0` and `61fcc816ef62`, covering the Odyssey/VPro memory and
fragment pipeline plus graphics configuration defaults. Merge `4c53dfc303c4`
on IRIS `xiri` preserves both sets of changelog notes after the sole manual
conflict; source files merge automatically. The isolated release build passes,
as do 354 Odyssey tests (four ignored) and 54 configuration tests. The merge
is pushed to `origin/xiri`. The
current manual image and ABI comparisons retain their pinned `819c682`
emulator; no qualified artifact or detached lab worktree is replaced.

NetBSD `xiri` commits `ded40d74024a79922c33f56c4b7c342cc39aa9f9` and
`e9ff76a58affee773b767d334f98075bf86daf7e` are pushed. They add the measured
IRIX sleep/child-state/group interfaces and fix a separate native multi-child
wait-accounting defect. The [cycle report](results/2026-11-05-irix-job-control.md)
records the native before/after tests, full ABI and regression checks, and
real shell jobs. Build/source-equivalence ledgers preserve both the v3
module checkpoint and the later native-core fix.

The 2026-11-05 Type1 scaler investigation fetched upstream again at 07:08 UTC.
Revision `3bcde9f702f0b52fdb296eeda4fe10b26555f3da` remains contained in
IRIS `xiri` at `bd67e65ff159748635dd484adf7fac94a591f84b`.
There are no new commits to integrate or affected emulator changes to build.
Diagnostics use private copies of the qualified fonts image and the preserved
2026-11-03 failure snapshot, retaining each artifact's pinned emulator.
NetBSD `xiri` commit `3b25e6cf2251f180c89027d00b33ee1c29933517` corrects
native MIPS FPU validity across signal/context restoration. The
[Type1 qualification](results/2026-11-05-type1-scaler.md) passes native
register/arithmetic/font controls, original IRIX FPU records and Type1
winterm input/resize/exit. The independent system run passes CD, native
input, both desktops, cleanup and active-desktop halt. The IRIX module is
unchanged; [source equivalence](../lab/type1-scaler/source-equivalence.json)
ties the exact pre-commit build and patch to the clean fork commit. The
[new CHD](results/2026-11-05-type1-image.md) passes cold xdm/4Dwm/ctwm,
winterm, fonts, catalog and clean shutdown before selection; older images
and pinned worktrees remain intact.

The 2026-11-05 fonts/Toolchest cycle fetched upstream again at 23:33 UTC
on 2026-11-04. Revision `3bcde9f702f0b52fdb296eeda4fe10b26555f3da`
remains contained in IRIS `xiri` at
`bd67e65ff159748635dd484adf7fac94a591f84b`; no integration or affected
emulator rebuild is required. Diagnostics start from a disposable clone of
the qualified scheduler image, retaining its `819c682` emulator and NetBSD
`xiri` source `0cd56e7a286c4cd3d67ab7cc971b233a83ac1655`.
The [qualified replacement image](results/2026-11-05-newport-text.md) retains
those kernel/module and emulator pins. Its change is in the xsrc userspace
Newport driver, tracked under `lab/newport-text`; no fork source was changed.
Native controls, cold xdm/4Dwm/ctwm, menu review and clean shutdown pass.

The 2026-11-04 XTest investigation fetched
`https://github.com/techomancer/iris.git` at 21:45 UTC. Upstream remains
`3bcde9f702f0b52fdb296eeda4fe10b26555f3da`, already contained in IRIS `xiri`
`bd67e65ff159748635dd484adf7fac94a591f84b`. There is no new merge or affected
emulator build to validate. Diagnostic guests retain the image's pinned
`819c682` emulator and use disposable overlays; the preceding Acrobat image
and its manual state remain intact. The [scheduler image](results/2026-11-04-xorg-scheduling.md)
is selected after fresh native/application, both-user session and clean-halt
acceptance. Neither fork changes in this cycle.
The active-day recheck after local midnight on 2026-11-05 (2026-11-04
23:00 UTC) fetched the same upstream revision. Both fork `xiri` branches
remain clean and match their origin tracking refs; no integration or emulator
rebuild is needed. The scheduling candidate changes only Xiri runtime launch
configuration and retains the tested kernel/module/emulator artifacts.

The 2026-11-04 replacement-image cycle fetched
`https://github.com/techomancer/iris.git` at 19:50 UTC. Upstream remains
`3bcde9f702f0b52fdb296eeda4fe10b26555f3da`, already integrated in IRIS `xiri`
`bd67e65ff159748635dd484adf7fac94a591f84b`; no merge or affected emulator
rebuild is needed. Image work uses NetBSD `xiri` commit
`0cd56e7a286c4cd3d67ab7cc971b233a83ac1655`, its qualified native core and
unchanged IRIX module. The [new image pin](../lab/system-stability/baseline.json)
retains the tested `819c682` emulator and records the replacement core's
source/build provenance explicitly. The [replacement-image record](results/2026-11-04-system-stability-image.md)
qualifies CHD round-trip, disk boot and both-user xdm behavior, but holds
promotion after reproducing a native XTest timeout. Neither fork changes in
this image cycle; the previous manual bundle/state and pinned lab worktrees
remain unchanged.

The 2026-11-04 system-stability cycle fetched
`https://github.com/techomancer/iris.git` again at 18:15 UTC. Upstream remains
`3bcde9f702f0b52fdb296eeda4fe10b26555f3da`, already integrated in IRIS `xiri`
`bd67e65ff159748635dd484adf7fac94a591f84b`. There are no new commits to merge
or affected emulator changes to rebuild. The
[system-stability cycle](results/2026-11-04-system-stability.md) retains the
qualified image's pinned emulator and uses disposable CHD overlays. NetBSD
`xiri` commit `0cd56e7a286c4cd3d67ab7cc971b233a83ac1655` is pushed; it fixes
native NetBSD32 CD9660 ownership/mask translation. The separate
`.work/netbsd-stability-build` core passes 158 CD checks and a complete loaded
desktop/login/logout/active-shutdown run. The original GIMP image passes the
separate baseline stability run while retaining its known CD failures. The
[build ledger](../lab/system-stability/build.json) records matching committed
source bytes and the unchanged IRIX module. The manual CHD and pinned lab
worktrees remain unchanged pending separate image qualification.

The 2026-11-04 preferences/Acrobat cycle again fetched
`https://github.com/techomancer/iris.git`. Upstream remains
`3bcde9f702f0b52fdb296eeda4fe10b26555f3da`, already integrated in IRIS `xiri`
`bd67e65ff159748635dd484adf7fac94a591f84b`; no production changes or affected
emulator checks were required. The qualified emulator artifacts remain pinned.
NetBSD `xiri` commits `d35accbc0f8919a7b37debc17de117e0086e52bd` (rename)
and `2ca3d76a4384cd73dbef1bd09b9cace12afadf41` (legacy Acrobat ELF) are pushed.
The separate `.work/netbsd-preferences-build` and `.work/netbsd-acrobat-build`
outputs preserve the prior termios build and unchanged core kernel. The
[pathname](../lab/irix-pathops/build.json) and [Acrobat](../lab/irix-acrobat/build.json)
ledgers tie the tested modules to exact equivalent committed source bytes.


The 2026-11-04 interactive-shell cycle fetched
`https://github.com/techomancer/iris.git` again and confirmed upstream
`3bcde9f702f0b52fdb296eeda4fe10b26555f3da` is already contained in IRIS
`xiri` `bd67e65ff159748635dd484adf7fac94a591f84b`. There were no new commits
to integrate or affected emulator changes to rebuild; the preceding cycle's
eight stream tests remain the validation for that integration. The outstanding
NetBSD push through `4cf85855f1ee` also completed. New terminal-attribute work
uses NetBSD `xiri` and `.work/netbsd-termios-build`, preserving the qualified
core, pinned lab worktrees and manual CHD. The
[termios report](results/2026-11-04-irix-termios.md) records its application
checks and [module provenance](../lab/irix-terminal/termios-build.json).
NetBSD `xiri` commit `89b8a71e1e4bf8a6e7d3ef3962b40adca08c1e2a` is pushed
and matches every recorded source hash. Its 928 new paired observations,
896 existing regressions, original-shell/catalog checks and both-user xdm
sequence pass; all test guests halt cleanly.

The 2026-11-04 GNOME Terminal cycle fetched upstream
`3bcde9f702f0b52fdb296eeda4fe10b26555f3da` and merged it into IRIS `xiri`
as `bd67e65ff159748635dd484adf7fac94a591f84b`, then pushed the merge.
The sole new commit changes the network redial timing test; production code
is unchanged. All eight `net::stream::tests` passed using the pinned nightly
compiler and a separate `.work/iris-terminal-target` output directory.
The first invocation could not find Cargo inside the toolbox; the explicit
Cargo-path retry is the successful validation. The qualified guest emulator
and manual CHD remain pinned. NetBSD module work uses `xiri` and the separate
`.work/netbsd-terminal-build` output.

NetBSD `xiri` commit `4cf85855f1ee` adds the terminal interfaces. All source
inputs match the [recorded module build](../lab/irix-terminal/build.json)
byte for byte. The [cycle report](results/2026-11-04-irix-terminal.md) records
392 new terminal/descriptor checks, 136 Unix-stream and 368 IPv4 regressions,
original-shell commands/catalog launching, a native foreground resize check
and native/IRIX login regression coverage. The core, pinned lab worktrees
and published manual CHD remain unchanged.


The 2026-11-04 GNOME startup cycle fetched upstream
`28fa516684c54e00e35b258c65e5dcac3a36165c` and verified that it remains an
ancestor of IRIS `xiri` `ae62114344a1d435152b8ae7e48c599974b4aec7`.
There were no new commits to merge or emulator changes to rebuild. Both fork
checkouts started clean. Socket compatibility work uses NetBSD's `xiri`
checkout and the separate `.work/netbsd-gnome-build` module output; the
qualified GIMP module, core kernel, emulator and manual CHD are preserved.

NetBSD `xiri` commit `0b2e08f1c0b` adds pathname Unix stream sockets and is
pushed. All recorded module/core inputs match the tested build byte for byte.
The [GNOME cycle](results/2026-11-04-irix-gnome.md) records 136 Unix socket
observations, 368 existing IPv4 regressions, gedit's document/catalog checks
and the follow-up application survey. The source/artifact pins are retained
in [the build record](../lab/irix-gnome/build.json); pinned worktrees and the
published GIMP CHD remain unchanged.

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
