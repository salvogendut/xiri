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
| `./xiri check` | Boot a disposable CHD copy and select checks for its manifest: xdm login/4Dwm/ctwm for xdm images, or the manual launcher for older images. Check rendering, home directory, catalog launching and cleanup, then write qualification JSON and PNGs. |
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
