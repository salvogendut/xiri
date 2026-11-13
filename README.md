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

The [current manual CHD](docs/results/2026-11-13-shutdown-sessions.md#manual-image) boots into native
NetBSD xdm. Use **xiritest** / **xiritest** or **xiritest2** / **xiritest2** for
separate IRIX desktops, or **netbsdtest** / **netbsdtest** for standard NetBSD ctwm.
`netbsdtest` belongs to `wheel` and can run `su -` for a root login shell;
root's password is empty in this development image.
These are public development-image credentials. The image's IRIX accounts use
their native identities and HOME/cwd under `/usr/people/<username>`. Native FAM now
identifies each client's native UID and groups; desktop state and session logs
remain private to that user. The
[per-user desktop setup guide](docs/IRIX-SOFTWARE.md#selecting-the-irix-desktop-for-a-user)
explains how any normal account selects the IRIX desktop and how to add users.
The [desktop preferences guide](docs/IRIX-SOFTWARE.md#desktop-preferences)
describes the original Background, Color Schemes and Windows panels and where
each user keeps their settings. Backdrops, colour schemes, focus and window
movement now persist across login and reboot. The [Solid colour picker](docs/results/2026-11-06-desktop-colours.md)
uses its original X11 controls, and SGI colour names resolve through a private
session database. The [saved-session guide](docs/IRIX-SOFTWARE.md#saved-desktop-sessions)
explains **Save Windows & Desks**, automatic and explicit saves, and profile
backups. Xmahjongg has no default autostart entry.
The [File Manager and Dumpster guide](docs/IRIX-FILEMANAGER.md) describes
original file actions, the required hostname setup and per-user storage.
System services start at boot. NetBSD
loads `compat_irix_o32.kmod` during boot and runs the desktop on a kernel
without built-in IRIX support. The [core kernel](lab/native-wait/README.md)
retains the native memory-allocation and CD9660 corrections found during
earlier qualification.
It still requires our NetBSD fork’s core hooks. The [winterm module and shell
handoff](lab/irix-winterm-reliability/README.md) preserve terminal dimensions,
deliver resize notifications to foreground jobs and let winterm close normally
when its shell exits.
Terminal defaults select NetBSD's existing bitmap Courier, restoring
larger winterm text close to IRIX's original appearance.
The [GIMP checkpoint](docs/results/2026-11-03-irix-gimp.md) now demonstrates
original GIMP 1.2.5 editing, XCF/PNG save and reopen, normal exit and catalog
launching as xiritest. Its additional resources and signal-mask module update
are included in the current image; application and desktop-login checks
are recorded separately. The [catalog startup survey](docs/results/2026-11-03-irix-catalog.md)
now records 124 distinct launch attempts in the
[166-entry, tab-by-tab checklist](docs/ICON-CATALOG.md). It distinguishes
windows, errors and busy processes without a window; useful operation still
needs individual checks. Freeware NEdit accepts text but cannot save.

The [GNOME follow-up](docs/results/2026-11-04-irix-gnome.md) now resolves
gedit's busy ORBit startup with pathname Unix stream sockets in the module.
With the additional original resources, gedit edits, saves/reopens and
overwrites a text document and launches through Freeware with running-icon
feedback. Image decoding, help and broader plug-ins remain open.

The [terminal follow-up](docs/results/2026-11-04-irix-terminal.md) adds
socket pairs, legacy descriptor passing and the original GNOME PTY helper.
GNOME Terminal now starts the original IRIX shell, accepts commands in the
correct home directory and closes on `exit`. The subsequent
[interactive-shell checks](docs/results/2026-11-04-irix-termios.md) add measured
terminal attributes and controlling-terminal acquisition to the module.
The unchanged IRIX shell now shows its prompt, recognizes an interactive
terminal, runs foreground commands, survives Ctrl-C and delivers resize
notifications. The [job-control cycle](docs/results/2026-11-05-irix-job-control.md)
adds measured sleep, child-state and process-group interfaces. Both the
original IRIX shell and winterm's native shell pass Ctrl-Z, bg/fg, Ctrl-C,
background reads, explicit waits and logout with active jobs.
It also fixes a shared NetBSD wait-accounting bug exposed by native
multi-child tests; the same test binary fails before the fix and passes after it.
The [tracking follow-up](docs/results/2026-11-05-process-tracking.md) verifies
3,072 native child lifecycles and 16 supervisor cleanup scenarios on old/current
images. Compview cleanup passes in both replays, while its first X query still
times out. The historical tracking failure remains open.
The [deadline investigation](docs/results/2026-11-05-cleanup-deadline.md)
then reproduces five false cleanup failures caused by declaring a timeout
with exit notifications already queued. A final nonblocking event/reap check
corrects them; seven deliberate-delay scenarios pass, including rejection
of a genuinely live child. This does not establish the old compview cause.
The [cleanup candidate CHD](docs/results/2026-11-05-cleanup-image.md) passes
cold desktop, font, shell-job and logout checks, but remains unselected:
96 MiB pressure testing exposes native sleep timeouts on both candidate and
previous images. The [native paging investigation](docs/results/2026-11-05-native-paging.md)
locates long encrypted pageout batches, corrects a big-endian swap-control
sysctl defect, and replaces a racy cleanup postcheck with a single process
query. The full pressure workload, forced encrypted swap readback and cold
desktop checks pass.
The replacement CHD remains unselected after a separate startup kernel crash;
that intermittent fault is recorded for later investigation. The current
bundle retains the preceding native-wait kernel and module.

The [preference cycle](docs/results/2026-11-04-irix-preferences.md) implements
measured IRIX `rename` behavior. GNOME Terminal and gedit settings survive
exit/relaunch, and GIMP saves its settings with an exact `gimprc.old` backup.
The [Acrobat cycle](docs/results/2026-11-04-irix-acrobat.md) imports the complete
original Reader package and supports its older ELF layout. Reader opens PDFs,
changes page and zoom, reopens a document and exits normally. It also launches
from Icon Catalog, although its icon does not change to the running shape.
These application, module and resource updates are packaged in the current
manual image. The multi-user image also includes the maintained cleanup guard;
the paging-kernel candidate remains separate. Earlier images and their manual
state are retained.

Individual application repairs are paused for the
[system-stability cycle](docs/results/2026-11-04-system-stability.md). It adds
repeatable native input, process-cleanup, login/logout and shutdown diagnostics,
and fixes a native NetBSD32 CD mount defect that made CD files unreadable to
ordinary users. The corrected core passes 158 CD ABI checks; the IRIX module
is unchanged. The [Xorg scheduling investigation](docs/results/2026-11-04-xorg-scheduling.md)
then identifies a ready delayed-button release starved by a higher-priority
pointer-query client. Both desktop launchers select the legacy server's
round-robin scheduler while retaining XAA. The scheduler CHD passes 60
native query-loop controls, six complete Acrobat launch/PDF/focus/exit cycles,
GNOME Terminal checks, full-screen xdm, both desktops and clean shutdown.
The separate reduced replay passes 60 capture/focus cycles. The earlier
child-control stalls and catalog-batch halt remain separate open observations.

The [font/menu cycle](docs/results/2026-11-05-newport-text.md) fixes Newport's
software-fallback refresh, restoring disabled Toolchest labels and native
Xft/Render text while preserving acceleration. That image passes
345 text comparisons across the greeter and both desktops, three winterm
starts/resizes, both logout routes, catalog launching and clean shutdown.
A separate replay shows readable labels in all six Toolchest menus and four
cascades. These driver and font settings are retained in the Type1 image below.

The [Type1 follow-up](docs/results/2026-11-05-type1-scaler.md) fixes native
NetBSD MIPS floating-point state loss on signal return, which could turn a
font size into zero. The corrected core passes all 24 native register cases,
200,000 conversions under signals, 560 font operations and 24 IRIX FPU
records. An explicit Type1 winterm passes input, resize and normal exit.
The IRIX module, font libraries and bitmap desktop default are unchanged.
That checkpoint passes its own cold desktop/font qualification and remains
available. The [earlier job-control image](docs/results/2026-11-05-native-wait-image.md)
adds the measured IRIX interfaces and native wait fix, then repeats cold
xdm/4Dwm/ctwm, 345 text comparisons, shell jobs, winterm, catalog launch,
logout/recovery and clean halt. Its separate 22-target replay also completes
with verified cleanup. The current image retains its kernel and
module; earlier bundles and manual state are preserved.

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

Log in at xdm as `xiritest` or `xiritest2`. Log out through Toolchest or 4Dwm
to return to the greeter. To enable the IRIX desktop for another native user,
follow the [per-user desktop setup](docs/IRIX-SOFTWARE.md#selecting-the-irix-desktop-for-a-user):
install the supplied `~/.xsession` template as that user, then log in through
xdm. Root serial login remains available for administration.
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

Compatibility is incomplete. The reproduced Type1 collapse is corrected;
winterm keeps the verified NetBSD bitmap Courier default. Broader graphics operations,
Dumpster actions, other preference panels and broader application restoration
need work. Active sessions now save before X stops when using NetBSD
`shutdown -r now` or `shutdown -h now`; see the
[shutdown-saving result](docs/results/2026-11-13-shutdown-sessions.md).
Backdrop, colour scheme, focus and movement preferences now survive
logout/login and reboot for two users; see the
[desktop-preferences result](docs/results/2026-11-06-desktop-preferences.md). The
[GIMP checkpoint](docs/results/2026-11-03-irix-gimp.md) covers basic editing
and XCF/PNG round trips; large images and the wider
plug-in collection remain open. xosview
still needs IRIX statistics interfaces.
General nested pipelines and layered-terminal revoke remain open; the
qualified job-control subset and its explicit wait-policy differences are
recorded in the [cycle report](docs/results/2026-11-05-irix-job-control.md).
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
