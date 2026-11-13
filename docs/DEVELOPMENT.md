# Maintained development workflow

Use `./xiri` from this repository (Python 3.11 or newer, standard library only).
It resolves paths from its own location, so it also works from another directory.
The entry point covers routine work against the selected image; the older
`scripts/` and `lab/` experiments remain available for reproduction.

## Commands

| Command | Effect |
| --- | --- |
| `./xiri status [--json]` | Show the selected image, its kernel/emulator pins and current integration worktree revisions/status. Source tips can be newer than the tested image. |
| `./xiri doctor` | Hash-check immutable image inputs and the qualification record; check host tools and Toolbox. It does not boot a guest. |
| `./xiri run` | Open the bundle's pinned IRIS launcher for manual testing. NVRAM, overlays and snapshots retain normal manual-session behavior. |
| `./xiri check` | Boot a disposable CHD copy and select checks for its manifest: xdm login/4Dwm/ctwm, including both IRIX accounts when present, or the manual launcher for older images. Check rendering, home directory, catalog launching and cleanup, then write qualification JSON and PNGs. |
| `./xiri seed [--output PATH]` | Extract or reuse a raw automation seed without repeating the import. A mismatched existing disk is rejected. Changed manual graphical NVRAM is preserved and excluded from a new frozen seed. |
| `./xiri build kernel` | Build tools and the configured modular mips64eb kernel from the NetBSD `xiri` worktree, with at most two build jobs. Build its matching personality with the command below. |
| `./xiri build iris` | Build the IRIS `xiri` worktree with the pinned Rust toolchain, locked offline dependencies and two jobs. |
| `./xiri image --seed-run RUN --output NEW_BUNDLE` | Package a halted, qualified raw run as a new CHD bundle. Uses selected-image pins unless matching replacements are explicitly supplied. |

`run`, `check`, `seed`, `build` and `image` accept `--dry-run`. Commands that
execute helpers record their arguments, exit status and output under
`.work/workflows/`. `check` writes `qualification.json` and `desktop.png`
there. It never promotes the new observation or overwrites the selected
bundle. In a terminal, Ctrl-C requests the child probe's normal cleanup and
waits for it; do not kill its supervisor while that cleanup is in progress.
The existing probe remains the owner of its emulator and container processes.
Manual `run` transfers control directly to IRIS.

Images qualified with shell jobs retain `job_control_checks` in their
manifest. `./xiri check` then requests `--jobs` automatically, covering native
winterm and the original IRIX shell, foreground/background control, child
waiting and logout with active jobs. The [job-control lab](../lab/irix-job-control/README.md)
documents the raw ABI fixtures and original-shell prompt behavior.

The [configuration](../config/development.json) defines fork locations,
integration branch, build jobs, toolchain and kernel configuration. Image
selection is separate: [image.json](../lab/irix-installed-desktop/image.json)
points to a local bundle whose manifest supplies exact tested artifacts.
NVRAM digests describe the prepared state; later manual changes are expected.
`doctor` deliberately does not reset or reject those changes.

## Source builds versus qualified artifacts

Builds go to `.work/builds/netbsd` and `.work/builds/iris`. They do not update
the selected image, its emulator, historical detached trees or pinned build
outputs. Both fork commands find the worktree that owns `xiri`, without
switching a shared checkout. Inspect `./xiri status` before building: it shows
uncommitted source changes as well as revisions. Temporary topic work still
follows [FORKS.md](FORKS.md); use explicit underlying build commands and separate
outputs when testing a topic before integration.

During cleanup, IRIS `xiri` belonged to `.work/iris-upstream-sproc`. Separate
performance work subsequently returned ownership to `../iris` and advanced
`xiri` to `3b854a8`, which contains this cycle's `c84757d` merge. The command
discovers the owner each time. The NetBSD checkout is `../NetBSD-xiri`.
Keep older detached lab worktrees pinned. The historical `scripts/build-iris.sh`
reproduces an older baseline and is not the current integration builder.

A new source build requires its own baseline and guest qualification before
use in a replacement image. For packaging, supply matching `--baseline`,
`--kernel` and `--iris-bin-dir` when moving beyond the selected image's pins.
`image` refuses an existing output directory. Follow the
[image qualification/promotion procedure](XIRI-IMAGE.md) after packaging;
creating a CHD alone does not make it the current manual image.

## Prerequisites and checks

The local environment includes Toolbox container `xiri-iris`, the pinned
Rust toolchain/dependency cache, NetBSD source, guest images and imported
resources. `doctor` checks host `git`, `toolbox`, `genisoimage`, `magick` and
`cp`, plus container `chdman` and `Xvfb`. It is an image/workflow readiness
check, not a complete compiler or hardware qualification. See
[emulation setup](EMULATION.md) for initial provisioning.

Run the host regression checks with:

```sh
python3 -m unittest discover -s tests -v
```

They cover artifact mismatch/missing-file rejection, mutable NVRAM,
worktree selection, binary guest transfers, monitor errors, interruption
cleanup, RPC warning detection across log rotation and runtime installation
without overwriting local configuration. Guest behavior is checked separately with `./xiri check`.
The two maintained desktop probes share `scripts/xiri_lab/guest.py` for
UART writes paced at 20 ms per byte, compressed output, monitor captures and bounded waits;
the established `probe-netbsd.py` still owns boot and teardown. Result files
record hashes for these shared sources as well as each probe.

The xdm probe also saves `checkpoint.json` after each captured screen and
completed login/logout phase. This preserves partial observations if the
host supervisor disappears. A checkpoint cannot qualify an image: promotion
still requires the final `result.json`, verified halt and unchanged base CHD.

For changes to graphical console login, both logout routes, or xmahjongg
interaction, also run the explicit prepared-disk probe documented in the
[xmahjongg evidence](results/2026-11-03-newport-xmahjongg.md#full-desktop-replay).
This more specialized probe requires a matching kernel build with symbols and
the native driver artifact. Its older defaults are historical; pass all
current paths explicitly. Do not rewrite old experiment defaults or delete
qualified artifacts as part of routine cleanup.

For application startup surveys, use the
[catalog lab](../lab/irix-catalog/README.md) and retain the
[per-tab checklist](ICON-CATALOG.md). Its runner creates disposable guests
from the historical GIMP bundle by default, records bounded process/window observations
and verifies cleanup. Use `--limit` and `--after-case` for small fresh batches;
keep interrupted queries and failed halts as diagnostics. The qualifier checks
inventory coverage and raw evidence before the renderer updates the checklist.
Startup observations remain separate from useful operation and normal exit.

Pass `--bundle .work/images/xiri-netbsd-desktop-20261104-acrobat` to exercise
the new cumulative image; retain the old default for reproducing the survey.
`--seed` overlays must belong to that same base CHD. The
[preference lab](../lab/irix-pathops/README.md) and
[Acrobat lab](../lab/irix-acrobat/README.md) cover the new paired pathname and
legacy-loader fixtures. Their application checks use fresh disposable homes
and keep diagnostic settings out of the manual image.

`prepare-xiri-xdm-image.py` accepts `--gnome-resources`, `--terminal-resources`
and `--acrobat-resources` directories produced by the respective stagers.
It validates archive membership, original bytes, ownership, modes and links,
preserves inherited GIMP provenance, and migrates only the synthetic IRIX
account lookup file. Native accounts/passwords stay unchanged with
`--keep-accounts`. The builder verifies the prepared runtime snapshot; current
runtime code must still match, while its README may advance independently.
The bundle retains the exact source hashes actually prepared in the guest.
`--refresh-xservers` explicitly adopts the maintained Xorg launch command in
the disposable image and records the old/new configuration hashes. Use it
when preparing an image for a server-command change such as `-dumbSched`;
the general runtime installer continues to preserve administrator settings.

The [terminal lab](../lab/irix-terminal/README.md) supplies paired socketpair,
legacy descriptor-transfer, PTY-master, termios and tty-session fixtures.
The interactive-shell cycle uses the separate `.work/netbsd-termios-build`
module output, with its source hashes retained beside the fixtures. The catalog harness's
`--pty-setup` option installs a candidate device script before graphical
login; it records the source hash and requires setup to succeed. Use a clean
seed and the module matching its unchanged core. The terminal qualifier
requires a clean final halt and distinguishes measured IRIX parity from
explicitly unsupported shapes and native-peer cleanup controls. Kernel-ring
shutdown polling retains its last observation in `shutdown-dmesg.txt` and
allows 300 seconds with ten-second intervals between reads, since each read
pauses the guest.

## Desktop preference checks

Desktop preference changes have a separate
[two-user check](../lab/irix-desktop-behavior/README.md#desktop-preference-checks):
select settings in the original panels, log out/in, reboot, then compare
saved files, visible backdrops and actual focus/drag behavior. The fixture
checks both click/opaque and pointer/outline policies. Keep those test profiles
in disposable overlays. The normal desktop no longer autostarts xmahjongg;
catalog regression probes start their own initial instance explicitly.
The [preference evidence](results/2026-11-06-desktop-preferences.md) records
the original resource mechanism. The [colour follow-up](results/2026-11-06-desktop-colours.md)
adds SGI name lookup and the Solid picker in X11 mode. `./xiri check` selects
`--colours` for images containing this support; the probe runs from the actual
users' winterm environments and compares every SGI alias with its original
RGB value and a numeric allocation control.

Saved-session changes also require the [session checks](results/2026-11-06-desktop-sessions.md):
use the original Windows panel to exercise continuous and explicit saves,
close an application, restore multiple terminals and their geometry, then
repeat with another native user and a normal logout before reboot. Keep the
users' saved files and before/after screenshots in the disposable run.
The [shutdown extension](results/2026-11-13-shutdown-sessions.md) also checks
an active continuous session with `shutdown -r now`, and an explicit snapshot
with `shutdown -h now` followed by a cold boot. Verify the save acknowledgment
before xdm stops, restored geometry, separate users' state and bounded cleanup
when a save stalls. Direct `reboot`, `halt` and `poweroff` bypass rc.shutdown.
For images containing `save-session`, the maintained xdm probe automatically
checks fresh versus restored launches, duplicate clients, stable winterm
restart commands and the save acknowledgment at logout. The native
[supervisor suite](../lab/irix-session/README.md) also checks stalled saves and
isolation of the desktop save hook from nested application supervisors.
Direct reboot while logged in remains a recorded shutdown-ordering limit.

## IRIX module development

The [module lab](../lab/irix-module/README.md) provides the separate
`XIRI_IRIX_MODULE` configuration and `scripts/build-irix-module.py`.
It builds a kernel without `COMPAT_IRIX_O32`, then links the same personality
as a filesystem-loaded module. `scripts/probe-irix-module.py --desktop`
checks lifecycle, normal boot loading and the Newport desktop on a disposable
seed. `scripts/probe-irix-module-regressions.py --seed <passed-module-run>`
replays the measured signal, sproc and receive cases with the boot-loaded module.

The ordinary `./xiri build kernel` now selects `XIRI_IRIX_MODULE`. Complete
that new source build with its matching personality:

```sh
./xiri build kernel
python3 scripts/build-irix-module.py --build .work/builds/netbsd
```

The second command audits imports, relocations and the absence of a built-in
IRIX personality, and writes `.work/builds/netbsd/module.json`. Keep these
two artifacts together. Neither command replaces the qualified manual image
or the retained `.work/netbsd-module-build` outputs. The previous built-in
configuration remains available as `lab/newport-accel/XIRI_NEWPORT_FRAME`
for explicit comparison builds in separate output directories. See the
[module cycle evidence](results/2026-11-03-irix-module.md) for exact inputs
and remaining stock-kernel dependencies, and the
[image preparation recipe](../lab/irix-module/README.md#prepare-a-manual-image)
for boot configuration and manual-image acceptance.

## Native service/session runtime

[`runtime/`](../runtime/README.md) is the maintained deployment source for
rc.d services, configuration, manual/user launchers and native session helpers.
The older lab copies remain pinned to their original experiments. Native build
and install commands, prerequisites and ownership are in the runtime guide.

Run the focused guest qualifier with:

```sh
python3 scripts/probe-xiri-session.py --seed .work/xiri-image/prepared-seed-20261103-module
```

It clones the seed, verifies staged source hashes, builds and installs the
runtime, reboots with services enabled, and exercises accelerated Newport
desktop sessions. The result, source snapshot, logs and PNGs stay under
`.work/irix-session/runs/ordinary-*`. `--guard-only` limits the run to native
descendant lifecycle checks; `--services-only` checks daemon stop/start,
restart, RPC unregistration and external-owner refusal. `--debug-failure`
keeps a failed guest available
for a bounded local command queue; normal teardown still owns that emulator.
The [cycle record](results/2026-11-03-xiri-session.md) pins the desktop and
service lifecycle runs, source coverage and screenshots. The probe does not
change the current CHD or image pointer.

For native xdm integration, run:

```sh
python3 scripts/probe-xiri-xdm.py
```

This separately clones the same seed, installs the opt-in xdm configuration,
selects the user's `.xsession` and reboots. It tests native password rejection
and acceptance, full-screen X geometry, readable greeter text, desktop input,
both logout menus, failed startup/retry and unrelated-login/service survival.
A separate native account without `.xsession` must retain NetBSD's standard
ctwm desktop, then permit another xiritest/4Dwm login.
For the current image prepared with `--multiuser`, run the cold probe with
`--bundle BUNDLE --multiuser --winterm --fonts --colours`. It adds concurrent per-user FAM watches, credential and
home isolation, and an xdm login as `xiritest2`. `./xiri check` selects this
additional gate automatically when the image manifest contains that account.
Prepare this image with `--fam-build .work/native-fam-multiuser --multiuser`
after building the [multi-user native FAM](../lab/native-fam/README.md).
Results, the frozen harness/runtime and GL scanout PNGs stay under
`.work/irix-xdm/runs/ordinary-*`. `--debug-failure` provides the same bounded
command queue; SIGTERM requests cleanup instead of leaving the guest running.
The [integration record](results/2026-11-03-xiri-xdm.md) describes evidence and
remaining boundaries. To prepare an image, use
`python3 scripts/prepare-xiri-xdm-image.py`, then package its halted run with
`./xiri image`. The [image cycle](results/2026-11-03-xiri-xdm-image.md) records
the recipe and result. The full payload hash check can take more than five
minutes in the emulator; it has a bounded 30-minute allowance.
For a replacement kernel/module pair, pass `--kernel-build BUILD --baseline
BASELINE` to the preparer, then the same baseline and boot kernel to
`./xiri image`. The preparer verifies the old inventory before installing
the new pair and checks its normal boot loading after graphical reboot.
The [native allocator regression](results/2026-11-03-uvm-pglist.md) runs with
`python3 scripts/test-uvm-pglist.py` against the fork's actual source.

`python3 scripts/probe-xiri-xdm.py --bundle NEW_BUNDLE` cold-boots the CHD using
its graphical AutoLoad NVRAM and tests the installed runtime. It supplies no
TFTP boot kernel and does not reinstall runtime files or reset the accounts'
passwords. The native account must already exist. A frozen profile under
`verification/` lets tests keep working after manual NVRAM changes. Use the standard
`qualify-xiri-image.py` command for validation/promotion; it recognizes the
xdm record and requires both login paths. The bundle's build PROM profiles and
manual overlays remain intact. `./xiri check` performs the same dispatch from
the selected manifest and never promotes an observation by itself.

For the [font/menu driver update](../lab/newport-text/README.md), prepare
the pinned xsrc source and build the driver natively against the image's Xorg
SDK. Pass `--newport-driver PATH --refresh-font-resources --keep-accounts`
to image preparation. It verifies the existing payload, stops Xorg before
installing the driver and explicitly adopts the matching Courier/xdm resources;
normal runtime installation still preserves administrator files. This imports
no additional IRIX fonts. Build into a new bundle and run
`probe-xiri-xdm.py --bundle NEW_BUNDLE --winterm --fonts` before promotion.
The font gate checks native core/Xft pixels and Courier metrics at the greeter,
three IRIX logins and native ctwm. Review the saved Toolchest menus separately
for visual completeness; a capture alone does not establish a working action.
`./xiri check` selects these additional checks from the new font-profile metadata.

The [Type1/FPU fixtures](../lab/type1-scaler/README.md) exercise the native
kernel separately from bitmap desktop acceptance. They compare all native
o32 floating-point registers across signals, run arithmetic under SIGALRM,
trace fresh Type1 sizes in Xvfb and measure actual pixmap glyphs. The known
baseline register failure must be observed before accepting the corrected
core. `qualify-type1-scaler.py` revalidates the retained comparison and
original-IRIX/winterm controls. Its source-equivalence ledger preserves the
actual pre-commit build revision and patch. Use `lab/type1-scaler/baseline.json`
with `.work/netbsd-fpu-build` when preparing that kernel's replacement image.

The [native paging lab](../lab/native-paging/README.md) separates native
sleep/observer timing, swap-encryption settings and paged-data readback from
the complete desktop workload. Preserve failed whole-run results even when
their individual controls pass: a resident memory readback does not prove
swap-in, and a narrower sleep pass does not qualify the X input sequence.
`probe-native-sleep.py` retains the input bundle pin, replacement artifact
hashes, exact media/harness, native traces and clean-halt evidence. Large
diagnostic archives use a bounded loopback transfer with a guest/host digest
check. Use `--trace-native` on the system runner only for diagnosis; keep
the normal watchdog and exact process counts for the final pressure gate.

Check filesystem headroom before another image/build cycle. Rust `debug/incremental`
caches can grow by several GiB across the emulator targets; they are regenerable
when no compiler is using them. Preserve final executables, kernel/module/debug
artifacts, guest evidence and manual overlays. The native-paging packaging record
documents independent CHD decoding in temporary memory storage and a verified
reflink for the persistent raw cache, avoiding another fully allocated 8 GiB copy.
Cargo's `debug/build` and `release/build` directories are also regenerable
dependency build caches. Old `verification/roundtrip.raw` files can be removed
after checking their hashes and the retained CHD against the bundle manifest;
`prepare-xiri-seed.py` automatically decodes the CHD when this cache is absent.
The [cleanup ledger](results/2026-11-05-workspace-cleanup.json) lists the exact
removed caches, retained CHDs and restoration commands.

The [November 8 cleanup report](results/2026-11-08-workspace-cleanup.md)
records the retirement of historical automated guest disks, overlays and
build caches. Keep compressed, qualified image bundles and their manifests,
manual overlays/NVRAM, source worktrees, final build artifacts and extracted
test evidence. Keep one raw seed for the selected image; after qualification
and packaging, retire redundant decoded copies and disposable run disks.
Preserve failed-run reports, logs and traces before retiring their disks.

Stop a guest through its owning harness, wait for the final result, then
verify that its recorded process group has exited before removing disks.
A shutdown log from before a reset does not establish that the current guest
is halted. Read process state in the same host/container namespace as the
owner; a sandboxed `ps` may not see an escalated emulator. Keep an interrupted
run's status explicit and use a fresh run for final qualification.
Directory sizes can count shared Btrfs extents repeatedly; use the change in
filesystem available space to report actual recovery.
The [November 13 cycle cleanup](results/2026-11-13-shutdown-sessions.md#cleanup)
retired its temporary emulator/frontend builds and completed guest disks,
then replaced the raw seed only after the new CHD passed qualification.

Historical result paths describe the original run and may now name retired
disk caches. Use `./xiri seed` for the selected image, or materialize an older
qualified bundle only when needed:

```sh
python3 scripts/prepare-xiri-seed.py .work/images/BUNDLE --output-directory .work/xiri-image/SEED
```

This restores the bundle's frozen disk, not a retired test's transient guest
state. Rerun that experiment with its retained harness when that state is
needed. Remove the extra seed after the investigation. Original IRIX media
paths and the deferred freeware inspection cache are documented in the
cleanup report; the workspace CHD paths now link to the verified originals
in `~/Downloads`.
