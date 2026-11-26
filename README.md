# Xiri

Xiri runs original IRIX applications and desktop components on NetBSD and
X.org. Both release lines use the kernel and matching boot-loaded IRIX module
from the `xiri` branch of our NetBSD-xiri fork. The long-term target is a
maintained operating system for real SGI workstations. The qualified reference
uses an R4400 Indy in the IRIS emulator.
Our current manual reference is **IRIX 6.5.22m**. We maintain separate release
lines for **6.5.22 and 6.5.30**, each with its own profiles, qualification and
CHD. The separate [6.5.30f donor and import](docs/results/2026-11-14-irix-6.5.30.md)
are reproducible. The [Indy/R5000 retry](docs/results/2026-11-14-r5000-6.5.30.md)
now passes native boot and the 6.5.30f core desktop, shell, File Manager and
login/logout checks with IRIS shadow cache mode. For manual testing, use the
[clean 6.5.22f and 6.5.30f Indy v6 CHDs](docs/results/2026-11-26-indy-v6.md).
Each has a launcher, an IRIX desktop and a native NetBSD login.
The [Indy ControlPanels results](docs/results/2026-11-26-indy-controlpanels.md)
cover Screen Saver, Display, Sounds, Audio Panel and the native HAL2 mixer.
The [Screen Saver update](docs/results/2026-11-26-sgi-screen-saver.md) enables
the original Qix Demo and idle animation on both Indy desktops. The [HDSP audio update](docs/results/2026-11-26-indy-hdsp.md) connects the SGI sound controls to the native Indy mixer. The [general playback update](docs/XIRI-IMAGE.md#general-irix-audio-playback-on-indy) runs the original SGI `sfplay` on both releases.
On the Indy, the original Display panel reports the active Newport timing. The desktop can play the donor’s named sound effects through Prismatic. [Manual test images and controls](docs/XIRI-IMAGE.md#indy-display-and-desktop-sounds).
The emulated O2/R10000 shows NetBSD boot messages in the Indy console frame before opening full-screen xdm.
Both the IRIX 6.5.22 and 6.5.30 disks run 4Dwm and native ctwm.
[O2 framed console and boot screenshots](docs/results/2026-11-23-o2-frame.md) ·
[O2 greeter and redraw timings](docs/results/2026-11-23-o2-greeter.md) ·
[O2 SCSI boot results](docs/results/2026-11-23-o2-r10000-boot.md) ·
[O2 disk persistence, Ethernet and DHCP setup](docs/results/2026-11-23-o2-io.md)
The [Indigo2, Octane and O2 kernel update guide](docs/results/2026-11-26-platform-v6.md) includes the current standalone CHD launchers for both IRIX releases, the matching kernel and module, and rollback instructions.
Physical hardware needs separate qualification.
The emulated Octane boots from its own SCSI disk, shows NetBSD startup
messages in the Indy console frame and opens a 1280×1024 xdm greeter.
Log in as `xiritest` for the IRIX 4Dwm desktop or `netbsdtest` for NetBSD
ctwm. The 6.5.22 disk uses Solid IMPACT and the 6.5.30 disk uses High IMPACT.
The Octane launchers use the IRIS R10000 JIT for faster window redraws.
[Octane framed console and boot screenshots](docs/results/2026-11-23-octane-frame.md) ·
[Octane redraw measurements](docs/results/2026-11-23-octane-redraw.md) ·
[Octane disk build instructions](docs/results/2026-11-23-octane-xdm.md)

The current desktop runs original 4Dwm, Toolchest, Icon Catalog, File Manager,
winterm, xclock and Desks Overview. It has SGI fonts, the granite backdrop,
desktop icons, catalog launches and running-icon feedback. Native NetBSD Xorg drives a
1280×1024 accelerated Newport display. It retains the xmahjongg texture
correction qualified by the earlier [rendering and interaction checks](docs/results/2026-11-03-newport-xmahjongg.md).

The [current manual CHD](docs/results/2026-11-14-desktop-controls.md#manual-image) boots into native
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
describes the original Background, Color Schemes, Windows, Desktop, Icon Views,
Keyboard, Mouse and Screen Saver panels and where each user keeps their settings.
Backdrops, colour schemes, focus and window
movement now persist across login and reboot. The [Solid colour picker](docs/results/2026-11-06-desktop-colours.md)
uses its original X11 controls, and SGI colour names resolve through a private
session database. The [saved-session guide](docs/IRIX-SOFTWARE.md#saved-desktop-sessions)
explains **Save Windows & Desks**, automatic and explicit saves, and profile
backups. Xmahjongg has no default autostart entry.
The [window and desk guide](docs/IRIX-WINDOWS.md) covers original window
controls, click-to-focus keyboard navigation and **Desktop → Extra Desks**.
The [windows/desks checks](docs/results/2026-11-13-desks.md) pass separate users,
saved geometry and active-desktop reboot on the new CHD.
The [desktop controls follow-up](docs/results/2026-11-14-desktop-controls.md)
adds desk rename/copy/delete and preference restoration through the original
panels. Keyboard's repeat toggle works; its SGI-specific timing sliders remain
disabled. Icon Views' hidden-file defaults are checked with fresh folders under
both users.
The [File Manager cycle](docs/results/2026-11-13-file-manager.md) adds local
create, rename, copy, move, discard, recovery and emptying under both users.
That module passed 720 paired filesystem checks against IRIX. The
[filesystem follow-up](docs/results/2026-11-14-file-manager.md) adds symlink
and timestamp support, with 328 further ABI checks and a fresh two-user
GUI run covering cross-filesystem moves, collisions and permission failures. The
[dialog investigation](docs/results/2026-11-14-desktop-controls.md) confirms that
Escape left a real collision popup open; clicking Cancel/Overwrite dismisses it.
The [File Manager and Dumpster guide](docs/IRIX-FILEMANAGER.md) explains the
original actions, hostname setup and per-user storage.
The [clipboard guide](docs/IRIX-CLIPBOARD.md) explains mouse-selection paste
between native and IRIX terminals, gedit Copy/Paste, native xterm's CLIPBOARD
mode and the current encoding/lifetime limits.
The [cold-image checks](docs/results/2026-11-13-clipboard.md) pass 19 exact
payload comparisons and clipboard reset across both IRIX users and native ctwm.
The [document guide](docs/IRIX-DOCUMENTS.md) explains per-user editor/viewer
choices, native application icons and the separate document/drop paths.
The [document checks](docs/results/2026-11-13-documents.md) pass saved editor
isolation and native icon drops under both IRIX accounts. The
[drag-and-drop update](docs/results/2026-11-13-dragdrop.md) fixes gedit's icon
action and adds file drops into running gedit and GIMP. Both users' gedit
checks, cancellation and unchanged source contents pass. GIMP still needs
its icon or File → Open for filenames requiring URI escapes. The new CHD
also passes 345 native text comparisons and three winterm checks.
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
needs individual checks. Freeware NEdit could not save in that survey;
it has not been retested with the later filesystem module.

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
bundle retains the preceding native-wait kernel, with the later filesystem module.

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
with verified cleanup. The current image retains that core kernel and updates
the filesystem module; earlier bundles and manual state are preserved.

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
to a qualified desktop image. The [IRIS delta audit](docs/results/2026-11-14-iris-delta-cleanup.md)
tracks upstream replacements and the remaining candidates for focused upstream PRs.
The [2026-11-22 IRIS refresh](docs/results/2026-11-22-iris-upstream.md)
records the current integration, fresh binaries, desktop checks and launch commands.
The [Indigo2 R10000 / High IMPACT investigation](docs/results/2026-11-22-indigo2-impact.md)
explains the corrected GPU regression test and records the native IP28 checks.
The [IP28 BSD bootloader checkpoint](docs/results/2026-11-22-ip28-boot64.md)
provides a tested 64-bit loader. The [native IP28 kernel result](docs/results/2026-11-22-ip28-kernel.md)
records working serial boot, storage and Ethernet on both release-line disks,
with [build and manual-test instructions](lab/ip28-kernel/README.md).
The [IP28 module and IMPACT/Xorg checkpoint](docs/results/2026-11-22-ip28-impact.md)
adds a matching loadable IRIX personality, native 1280×1024 `wsfb` graphics
and PS/2 input. Both vendor desktops pass shell/logout checks, with separate
bootable CHDs and [manual instructions](lab/ip28-kernel/README.md#manual-impact-desktop).
The [IP28 xdm checkpoint](docs/results/2026-11-22-ip28-xdm.md) adds normal
boot into a full-screen greeter, authenticated IRIX and native ctwm sessions,
and separate automatic-boot images for both release lines.
The [IP28 graphical-console checkpoint](docs/results/2026-11-22-ip28-console.md)
adds visible boot text and a native debugger console before Xorg starts,
with separate graphical-console images and serial recovery instructions.
The [High IMPACT 2D update](docs/results/2026-11-22-ip28-2d.md) adds hardware
rectangle fills and batched pixel uploads, with measured display latency and
manual test images for both releases.
The [framed IP28 console](docs/results/2026-11-22-ip28-frame.md) uses the Indy's
artwork for boot messages and debugger output. The report includes screenshots
and launch commands for the 6.5.22 and 6.5.30 images.
The [desktop latency measurements](docs/results/2026-11-22-desktop-latency.md)
compare held 4Dwm window moves and winterm scrolling on Indy and Indigo2.
The [High IMPACT window-copy investigation](docs/results/2026-11-22-impact-window-copy.md)
traces native Xsgi and compares Xorg readback, framebuffer RAM and scanout.

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

The [versioned importer](profiles/README.md) now builds a reproducible vendor
payload from our own original-media IRIX 6.5.22f installation. Its
[NetBSD desktop checks](docs/results/2026-11-14-irix-import.md) cover full-screen
xdm, the IRIX desktop and shell, File Manager, logout/relogin and native ctwm.
The existing manual-test CHD remains the 6.5.22m reference, with its additional
applications. The [native package](docs/NATIVE-PACKAGE.md) now assembles the
matching kernel/module, native services, display driver and cross-built session
runtime without reading a prepared image. Its [6.5.22f qualification](docs/results/2026-11-14-native-package.md)
passes installation/reinstallation, desktop/shell, logout/relogin and native ctwm.
The separate 6.5.30 version now has a verified donor and reproducible payload.
Its core desktop checks now pass on Indy/R5000 with shadow cache mode and a
MIPS IV-aware module. Both original-media release lines now have
[clean v5 Indy test CHDs, launch commands and Clock screenshots](docs/results/2026-11-24-indy-v5-clock.md).
They start from stock NetBSD 11.0 userland, boot the 11.99.11 modular kernel,
and run accelerated 4Dwm or native ctwm according to the user's xdm session.
The [everyday desktop checks](docs/results/2026-11-24-indy-v4-use.md) cover Catalog launches,
File Manager moves and per-user session restoration after a cold boot.
On either clean Mozilla Indy, install or remove xmahjongg from May 2004
Freeware CD 4 using SGI Software Manager or the terminal installer. After
reboot, double-click the game in Icon Catalog’s **Freeware** tab.
[Desktop Software Manager](lab/irix-installer/README.md#open-software-manager-from-the-indy-desktop)
· [Terminal instructions](lab/irix-installer/README.md#use-the-complete-freeware-cd-4-with-a-clean-mozilla-indy)
· [Desktop install and removal on both Indys](docs/results/2026-11-26-desktop-installer.md).
The same installer can add xosview’s CPU and memory meters and upgrade
SGI Freeware UnZip 5.40 to 5.50 in place. [Manual instructions](lab/irix-installer/README.md#install-xosview-and-upgrade-unzip-in-software-manager)
· [Upgrade results](docs/results/2026-11-26-freeware-upgrade.md).
To use xmahjongg and UnZip on the same desktop, use the
[shared package helpers](lab/irix-installer/README.md#install-xmahjongg-and-unzip-together).
Software Manager can install, remove and reinstall GIMP 1.2.5 from the May 2004
Freeware CDs. Removing GIMP keeps shared libraries and the user's images and settings.
[Install and launch GIMP](lab/irix-installer/README.md#install-gimp-125-from-the-freeware-cds) · [Remove or reinstall it](lab/irix-installer/README.md#remove-and-reinstall-gimp).
Both clean Indy v6 desktops include the module that preserves HTTP timestamps for SGI Freeware wget. Boot the release-matched CHD or update an existing v5 installation in place. [6.5.22f and 6.5.30f launchers](docs/results/2026-11-26-indy-v6.md) · [Installer and rollback](docs/NATIVE-PACKAGE.md#install-or-update-an-indy-to-v6).
Both vendor timezone compilers can now create hard-linked aliases with the
updated module. The same two Indys were used to trace SGI Clock and
Freeware xosview. [Hard-link and application results](docs/results/2026-11-24-indy-link-clock-xosview.md)
Both v5 installers ship the corrected NetBSD Xorg/GLX pair and each release’s
indexed Iris fonts. SGI Clock draws and advances on both Indys. [Rendering results and screenshots](docs/results/2026-11-24-indy-glx.md)
The [installer guide](docs/NATIVE-PACKAGE.md#clean-installation-on-an-emulated-indy)
covers building per-release media and repeat installation. It also explains
how to [boot the saved stock kernel and return to Xiri](docs/NATIVE-PACKAGE.md#switching-between-the-stock-and-xiri-kernels)
on the same disk. The [desktop removal and reinstall guide](docs/NATIVE-PACKAGE.md#remove-the-desktop-and-return-to-native-netbsd)
covers native ctwm recovery, the stock Newport driver and preservation of
user homes and local configuration. [Test results and screenshots for both releases](docs/results/2026-11-24-indy-desktop-removal.md)

The [native helper update guide](docs/NATIVE-PACKAGE.md#upgrade-native-helpers-on-an-installed-indy) covers updating an installed Indy and rolling back from the same release-specific CD. The [v3 account update](docs/NATIVE-PACKAGE.md#add-or-retire-helpers-with-the-v3-account-update) also handles added and retired commands.
The [v4 FAM service update](docs/NATIVE-PACKAGE.md#configure-the-fam-service-log-with-v4)
lets administrators choose the file-monitor log in `/etc/rc.conf.d/xiri_famd`.
The [disk-full recovery guide](docs/NATIVE-PACKAGE.md#recover-from-a-full-target-filesystem)
explains how to resume an install or update after freeing space.

Compatibility is incomplete. The reproduced Type1 collapse is corrected;
winterm keeps the verified NetBSD bitmap Courier default. Broader graphics operations,
remote filesystems, full-disk failures, other preference panels and broader
application restoration need work. Active sessions now save before X stops when using NetBSD
`shutdown -r now` or `shutdown -h now`; see the
[shutdown-saving result](docs/results/2026-11-13-shutdown-sessions.md).
Backdrop, colour scheme, focus and movement preferences now survive
logout/login and reboot for two users; see the
[desktop-preferences result](docs/results/2026-11-06-desktop-preferences.md). The
[GIMP checkpoint](docs/results/2026-11-03-irix-gimp.md) covers basic editing
and XCF/PNG round trips; large images and the wider
plug-in collection remain open. The SGI Freeware xosview CPU and memory
meters run on both Indys with the updated compatibility module.
[Meter measurements and screenshots](docs/results/2026-11-24-indy-xosview.md).
The [Applications tab survey](docs/results/2026-11-24-indy-applications.md)
covers every visible launcher on the two original-media Indy desktops.
The [stock-profile startup retest](docs/results/2026-11-25-applications-recheck.md) lists each icon on the two Mozilla test images.
Both v5 Indy installers support Mozilla as an optional component. Use
`install.sh --mozilla` at installation time or on an existing v5 desktop.
[Clean CHDs and screenshots](docs/results/2026-11-25-mozilla-installer.md#boot-the-clean-test-images) ·
[Installation and rollback](docs/NATIVE-PACKAGE.md#install-or-remove-mozilla-on-the-indy).
IRIX Mozilla can browse public HTTP pages on both Indys. The November 25 HTTP
images and the in-place upgrade for the earlier input disks include the IRIX
socket and hostname fixes. [Launch commands, screenshots and upgrade instructions](docs/results/2026-11-25-mozilla-http.md).

The Mozilla test CHDs for the 6.5.22f R4400 and 6.5.30f R5000 include the
event-worker fix. Launch either Indy and test the File menu and address bar
from the Applications tab. [Ready-to-boot images and login](docs/results/2026-11-25-mozilla-input.md#ready-to-boot-indy-images).
Freeware xosview needs a separate installation on these images.
[Manual test results and xosview CD instructions](docs/results/2026-11-25-indy-interaction.md).
Both Indy releases can create and join a worker using SGI's n32 libpthread
on the matching development kernel and module. Both vendor Mozilla
versions can render a local page from the Applications catalog on the
separate Mozilla test images. The optional browser imports now include an offline
homepage installer for new profiles. On 6.5.22f a per-user WebJumper setting opens
the original About document and the Mozilla Mail account wizard from the catalog. [Setup and screenshots](docs/results/2026-11-25-webjumper-homepage.md) ·
[Showcase graphics requirements](docs/results/2026-11-25-showcase-graphics.md) ·
[Test images](docs/results/2026-11-25-mozilla-sigpoll.md#launch-the-test-images).
[Mozilla imports](docs/results/2026-11-24-indy-mozilla.md) ·
[Worker qualification](docs/results/2026-11-25-nsproc.md) ·
[Threaded library loading](docs/results/2026-11-25-threaded-elfmap.md) ·
[Threaded heap](docs/results/2026-11-25-threaded-break.md) ·
[Mozilla event workers and stack guards](docs/results/2026-11-25-irix-event-workers.md) ·
[Private libc locks](docs/results/2026-11-25-irix-usync.md) ·
[Thread stack guards](docs/results/2026-11-25-irix-stack-guard.md) ·
[Mozilla startup, signal waits and local X connections on both Indys](docs/results/2026-11-25-mozilla-event-diagnosis.md).
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
- [NetBSD upstreaming](docs/NETBSD-UPSTREAM.md): required core interfaces, exact source files, native fixes, module packaging and upstream acceptance work.
- [IRIX resources](docs/IRIX-RESOURCES.md) and [software/home layout](docs/IRIX-SOFTWARE.md).
- [Newport graphics](docs/NEWPORT.md) and [desktop reference](docs/IRIX-DESKTOP-REFERENCE.md).
- [Emulation setup](docs/EMULATION.md) and [platform feasibility](docs/FEASIBILITY.md).
- [Historical checkpoints](docs/HISTORY.md) and [dated evidence](docs/results/).
