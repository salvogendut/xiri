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
| `./xiri check` | Boot a disposable CHD copy, check desktop behavior, render pixels, home directory, catalog launching and cleanup, then write a qualification JSON and PNG. |
| `./xiri seed [--output PATH]` | Extract or reuse a raw automation seed without repeating the import. A mismatched existing disk is rejected. Changed manual graphical NVRAM is preserved and excluded from a new frozen seed. |
| `./xiri build kernel` | Build tools and the configured mips64eb kernel from the NetBSD `xiri` worktree, with at most two build jobs. |
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
cleanup and RPC warning detection across log rotation. Guest behavior is checked separately with `./xiri check`.
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

## IRIX module development

The [module lab](../lab/irix-module/README.md) provides the separate
`XIRI_IRIX_MODULE` configuration and `scripts/build-irix-module.py`.
It builds a kernel without `COMPAT_IRIX_O32`, then links the same personality
as a filesystem-loaded module. `scripts/probe-irix-module.py --desktop`
checks lifecycle, normal boot loading and the Newport desktop on a disposable
seed. `scripts/probe-irix-module-regressions.py --seed <passed-module-run>`
replays the measured signal, sproc and receive cases with the boot-loaded module.

The ordinary `./xiri build kernel` and current manual-image pointer retain
their existing configuration. Module work has isolated source/tool/object
paths and the same pinned emulator as the manual desktop. See the
[cycle evidence](results/2026-11-03-irix-module.md) for its exact inputs and
remaining stock-kernel dependencies.
