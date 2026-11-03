# Xiri

Xiri runs original IRIX applications and desktop components on NetBSD and
X.org. The long-term target is a maintained operating system for real SGI
workstations; current development uses an R4400 Indy in the IRIS emulator.
Our reference is **IRIX 6.5.22m**. Other releases and physical hardware need
separate qualification.

The current desktop runs original 4Dwm, Toolchest, Icon Catalog, File Manager,
winterm and xclock. It has SGI fonts, the granite backdrop, desktop icons,
catalog launches and running-icon feedback. Native NetBSD Xorg drives a
1280×1024 accelerated Newport display. It retains the xmahjongg texture
correction qualified by the earlier [rendering and interaction checks](docs/results/2026-11-03-newport-xmahjongg.md).

The [current manual CHD](docs/results/2026-11-03-irix-gimp.md) boots into
native NetBSD xdm. Log in as **xiritest** with password **xiritest** for the
IRIX desktop, or **netbsdtest** / **netbsdtest** for standard NetBSD ctwm.
`netbsdtest` belongs to `wheel` and can run `su -` for a root login shell;
root's password is empty in this development image.
These are public development-image credentials. The IRIX session uses UID
1234 and HOME/cwd `/usr/people/xiritest`; system services start at boot. NetBSD
loads `compat_irix_o32.kmod` during boot and runs the desktop on a kernel
without built-in IRIX support. The retained [core kernel](lab/irix-xdm/README.md)
also fixes a native memory-allocation fault found during CHD qualification.
It still requires our NetBSD fork’s core hooks. The [winterm module and shell
handoff](lab/irix-winterm-reliability/README.md) preserve terminal dimensions,
deliver resize notifications to foreground jobs and let winterm close normally
when its shell exits.
Terminal defaults now select the imported SGI Screen bitmap font, avoiding
the reproduced collapsed metrics from Xorg's scalable IBM Courier face.
The [GIMP checkpoint](docs/results/2026-11-03-irix-gimp.md) now demonstrates
original GIMP 1.2.5 editing, XCF/PNG save and reopen, normal exit and catalog
launching as xiritest. Its additional resources and signal-mask module update
are included in the current image; application and desktop-login checks
are recorded separately. The next pass follows the
[tab-by-tab catalog checklist](docs/ICON-CATALOG.md).

## Related repositories

Xiri development uses these sibling checkouts:

| Repository | Local checkout | Branch | Role |
| --- | --- | --- | --- |
| [NetBSD-xiri](https://github.com/salvogendut/NetBSD-xiri/tree/xiri) | `../NetBSD-xiri` | `xiri` | Our custom NetBSD fork, containing the IRIX compatibility personality and native platform changes. |
| [IRIS](https://github.com/salvogendut/iris/tree/xiri) | `../iris` | `xiri` | Our emulator fork and primary development/testing environment for the emulated SGI Indy. |
| [Prismatic](https://github.com/salvogendut/prismatic) | `../prismatic` | `main` | Our graphical frontend to IRIS, used for interactive emulator and desktop testing. |

This repository holds the native [service/session runtime](runtime/README.md),
Xiri workflow, probes, resource manifests and
documentation. See the [fork workflow](docs/FORKS.md) for integration rules
and the [image guide](docs/XIRI-IMAGE.md) for matching Prismatic's IRIS backend
to a qualified desktop image.

## Run the current image

With the local image bundle and development dependencies already prepared:

```sh
./xiri status
./xiri doctor
./xiri run
```

Log in at xdm as `xiritest`. Log out through Toolchest or 4Dwm to return to
the greeter. Root serial login remains available for administration.
The [manual image guide](docs/XIRI-IMAGE.md) covers PROM settings, Prismatic,
boot troubleshooting and the exact image provenance. `./xiri run` uses the
selected bundle's tested emulator and preserves manual overlays and NVRAM.

Images, imported IRIX files, toolchains and build outputs remain local under
`.work/`; cloning this repository alone does not supply them. The
[import ledger](docs/IRIX-IMPORT.md) records what was copied from the supplied
IRIX image and where it belongs.

## Develop and check

```sh
./xiri check                 # disposable CHD boot, desktop checks and PNG
./xiri seed                  # reusable raw seed for more focused probes
./xiri build kernel --dry-run
./xiri build iris --dry-run
python3 -m unittest discover -s tests -v
```

The [development guide](docs/DEVELOPMENT.md) explains these commands, image
packaging and logs. Defaults live in [config/development.json](config/development.json);
artifact selection comes from the [current image pointer](lab/irix-installed-desktop/image.json).
New builds use separate output directories and do not replace qualified images.
Use the `xiri` integration branches for both forks, following the
[fork workflow](docs/FORKS.md). This lab repository uses `main`.

## Remaining work

Compatibility is incomplete. The underlying Type1 font-metric failure remains
open; winterm's default now uses a verified SGI bitmap face. Broader graphics operations,
Dumpster actions, preferences and session persistence need work. The
[GIMP checkpoint](docs/results/2026-11-03-irix-gimp.md) covers basic editing
and XCF/PNG round trips; preference-backup `rename`, large images and the wider
plug-in collection remain open. xosview
still needs IRIX statistics interfaces.
Continued-child signal behavior and IRIX nanosleep also remain open.
The user's broader desktop survey is encouraging,
but it is not a per-application qualification.

The [module milestone](docs/results/2026-11-03-irix-module.md) follows the
`compat_linux` model. The [qualified service/session runtime](docs/results/2026-11-03-xiri-session.md)
separates boot services from user sessions and follows descendants for logout
cleanup. Native [xdm integration](docs/results/2026-11-03-xiri-xdm.md) now
passes password login, full-screen 4Dwm and ctwm sessions, both IRIX logout
menus and recovery checks. The [xdm image](docs/results/2026-11-03-xiri-xdm-image.md)
packages those changes and passes direct disk boot, both desktop logins and
catalog launching. Original IRIX clogin remains later work. The
[roadmap](docs/ROADMAP.md) defines the dependency and acceptance work.

- [Architecture](docs/ARCHITECTURE.md): kernel, imported runtime, native services and desktop boundaries.
- [IRIX resources](docs/IRIX-RESOURCES.md) and [software/home layout](docs/IRIX-SOFTWARE.md).
- [Newport graphics](docs/NEWPORT.md) and [desktop reference](docs/IRIX-DESKTOP-REFERENCE.md).
- [Emulation setup](docs/EMULATION.md) and [platform feasibility](docs/FEASIBILITY.md).
- [Historical checkpoints](docs/HISTORY.md) and [dated evidence](docs/results/).
