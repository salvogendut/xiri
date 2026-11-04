# Reusable Xiri development image

For routine work, use `./xiri status`, `./xiri doctor`, `./xiri run` and
`./xiri check` from the repository. The [development guide](DEVELOPMENT.md)
explains seed reuse, isolated builds and packaging. These commands read the
selected image manifest; the explicit paths below document this image and
older reproduction checkpoints. Automated checks never promote their result
or replace the manual bundle's NVRAM/overlay state.

The current accelerated xdm bundle is
`.work/images/xiri-netbsd-desktop-20261104-scheduler/`.
`netbsd-xiri.chd` is an 8 GiB NetBSD disk compressed to 496,124,430 bytes
(about 473 MiB). Its SHA256 is
`b6e5c89ef897f441e0c8cfbb5f174a23f082383414c8fb64105500c971992d36`.
The [scheduling update](results/2026-11-04-xorg-scheduling.md) includes the
qualified native CD9660 core correction and selects Xorg's round-robin
scheduler in xdm and the manual launcher. It passes disk round-trip,
full-screen xdm/4Dwm/ctwm, rendering, catalog, native input/query-loop controls,
GNOME Terminal, six Acrobat sequences and clean shutdown. XAA stays enabled.
The preceding [CD mount candidate](results/2026-11-04-system-stability-image.md)
retains its reproduced XTest timeout and was never promoted. The earlier
`20261104-acrobat` manual bundle, overlay and NVRAM remain intact.
The [cumulative application update](results/2026-11-04-irix-acrobat-image.md)
adds the qualified GNOME sockets/PTY/original-shell support, preference saving
and the complete original Acrobat Reader installation with its legacy ELF
loader support. Application checks are separate from disk boot, xdm, both
user desktops, rendering and catalog checks. The previous `20261103-gimp`
image retains the [GIMP checkpoint](results/2026-11-03-irix-gimp.md), and
`20261103-winterm-v2` preserves the
[terminal reliability checkpoint](results/2026-11-03-winterm-reliability.md).
The previous `20261103-xdm-wheel-v2` image retains the [wheel-account qualification](results/2026-11-03-xiri-wheel.md),
including interactive `su -`; the replacement preserves those account files
and checks effective wheel membership inside the native desktop. The previous
`20261103-module` image remains available with its original root launcher. The previous `20261103-newport-xmahjongg`
built-in image remains available as a control, including its manual state.
The earlier `20261102-behavior` software bundle
and `20261102-framed-accel` bundle are preserved for comparison.
The current bundle contains the qualified Xiri kernel, original IRIX
runtimes, installed application/catalog payload, persistent fonts, boot services and
native xdm login, plus a manual fallback launcher. The [desktop service qualification](results/2026-11-02-desktop-services.md)
adds native FAM, catalog contents, toolbar bitmaps and the original Toolchest
menus. The [usability update](results/2026-11-02-desktop-usability.md) adds
graphical automatic boot, console login, both logout menus, window-manager
readiness before client startup, and the native rpcbind loopback fix.
The [icon repair](results/2026-11-02-desktop-icons.md) adds measured locks,
seek offsets and native FAM pathname mapping, with Freeware application and
FileManager folder/document artwork. The [cold-boot record](results/2026-11-02-desktop-behavior-image.json)
verifies the persistent resources, native Xorg/Newport and cleanup. The [import ledger](IRIX-IMPORT.md) records
the source and destination paths; vendor bytes remain outside Git.

The [shell image update](results/2026-11-02-irix-shell-image.md) packages
the high-address library mapping fix, original IRIX `/bin/sh` command support
and native null-device binding. Double-clicking xmahjongg in Icon Catalog's
Freeware page launches it. Winterm still runs NetBSD's shell, now starting
in `/usr/people/xiritest`, as verified with `pwd`. GNOME Terminal now runs
the interactive original IRIX shell; see the
[terminal checks](results/2026-11-04-irix-termios.md). GIMP's former library
mapping failure was cleared;
the current [GIMP check](results/2026-11-03-irix-gimp.md) now qualifies basic
editing, XCF/PNG save and reopen, normal exit and catalog launch. Preference
backups now pass the [preference checks](results/2026-11-04-irix-preferences.md);
wider plug-ins remain unqualified. xosview still
needs IRIX statistics interfaces.

The cumulative image includes 53 GNOME resource paths, the original PTY
helper and 86 Acrobat paths, with per-file provenance and verified ownership,
modes and links. Original user profiles are excluded. GNOME Terminal, gedit
and GIMP preference persistence is qualified separately; first-run setup
remains fresh in this image. Launch `acroread` from Applications and open
`/usr/adobe/Acrobat4.0/Reader/Acrobat.pdf` for its bundled sample. Reader's
catalog launch works, but its icon stays unchanged while running.

The compatibility account file now uses `/usr/people/xiritest` for xiritest
and `/` for the IRIX root convention. Native NetBSD accounts/passwords remain
unchanged, including root's `/root` home and netbsdtest's wheel membership.

The [desktop behavior image](results/2026-11-02-desktop-behavior-image.md)
adds native FAM execution feedback, the granite backdrop and filesystem/home/
Dumpster desktop icons. The source-disk probe verifies xmahjongg changing to
its opened icon while running and returning to the exact closed pixels after
exit. It also verifies filesystem and Dumpster double-clicks opening their
directory views. Full Dumpster operations and launch animation remain open.

## Current xdm image

The core kernel remains byte-identical to NetBSD `xiri` commit
`9390bc04900`, including the [UVM allocation fix](results/2026-11-03-uvm-pglist.md)
found during CHD qualification. The replacement module's sources match commit
`2ca3d76a4384`; it is built against that same kernel. The personality boot-loads
as `exec / filesys` at normal securelevel 1. The [Acrobat build pins](../lab/irix-acrobat/build.json)
retain the original build provenance and committed-source equivalence;
the Xiri fork hooks are still required.

Launch the qualified bundle directly:

```sh
/var/home/salvogendut/Dev/xiri/.work/images/xiri-netbsd-desktop-20261104-scheduler/run-iris.sh
```

It boots automatically to native NetBSD xdm. Use these public development
credentials:

| User | Password | Desktop | HOME |
| --- | --- | --- | --- |
| `xiritest` | `xiritest` | Original IRIX 4Dwm | `/usr/people/xiritest` |
| `netbsdtest` | `netbsdtest` | Standard native NetBSD ctwm | `/home/netbsdtest` |

`netbsdtest` belongs to `wheel`. Run `su -` in its terminal to open a root
login shell; root's password remains empty in this development image.

Xorg explicitly selects the qualified 1280×1024 Newport configuration with
XAA enabled. Original IRIX logout menus return to xdm; system services survive.
Native xdm/PAM and the system Xsession remain unchanged. The IRIX session is
selected only by xiritest's `.xsession`; FAM still serves that one configured
IRIX account. Root has no password and remains available on serial B for
administration. The ttyE0 getty is disabled so xdm owns the graphical keyboard.

The fresh [image qualification](results/2026-11-04-irix-acrobat-image.json) covers three IRIX
logins, a separate native ctwm login, both IRIX logout routes, failed-startup
recovery, catalog launch, full-screen acceleration and clean halt. PNGs show
[4Dwm](results/images/2026-11-04-irix-acrobat-image.png),
[ctwm](results/images/2026-11-04-irix-acrobat-image-native.png), the
[greeter](results/images/2026-11-04-irix-acrobat-image-greeter.png) and
[winterm before any test resize](results/images/2026-11-04-irix-acrobat-image-winterm.png).
Each IRIX login checks untouched terminal geometry and foreground SIGWINCH
delivery; an extra 100×30 terminal preserves its size and closes on typed
`exit`. Terminal defaults select the imported SGI Screen bitmap font with
8×15 cells. The underlying intermittent Type1 font-metric failure remains
open, as does the greeter's Xft Render workaround.
The native logout test ends ctwm from its own terminal;
it does not qualify its Quit menu.

`./xiri check` automatically includes these winterm checks for the selected
bundle. The explicit command is:

```sh
python3 scripts/probe-xiri-xdm.py --bundle .work/images/xiri-netbsd-desktop-20261104-scheduler --winterm
```

For root's manual fallback, stop xdm with `/etc/rc.d/xdm stop`, then run
`xiri-desktop`. User logs are in `~/.xsession-errors` and `~/.xiri/sessions/`;
service logs are `/var/log/xdm.log` and `/var/log/xiri-fam.log`. Use serial B
for `shutdown -h now` before closing the emulator.

## Previous module image with the root launcher

That earlier kernel is source-equivalent to NetBSD `xiri` `d1ce7a96615`, using
`XIRI_IRIX_MODULE` without built-in IRIX support. During boot, NetBSD loads
`compat_irix_o32.kmod` from `/stand/sgimips/11.99.9/modules/`; `/etc/modules.conf`
and `modules=YES` in `/etc/rc.conf` enable it. Both o32 and n32 applications use
this module. Normal securelevel remains 1; manual `modload` is unnecessary.
The kernel and module are a matched pair and still require the Xiri fork.

The image keeps the tested `819c682` IRIS backend, corrected Newport Xorg
driver, original resources and root-launcher/xiritest-session arrangement.
Launch it with:

```sh
/var/home/salvogendut/Dev/xiri/.work/images/xiri-netbsd-desktop-20261103-module/run-iris.sh
```

Log in as `root` (no password), then run `xiri-desktop`.
`modstat | grep compat_irix_o32` should show `exec` and `filesys`. The
[qualification record](results/2026-11-03-irix-module-image.json) and
[PNG](results/images/2026-11-03-irix-module-image.png) cover a fresh CHD boot,
module and resource hashes, accelerated drawing and catalog launching.
The preparation probe also checks graphical login and both logout routes.
Winterm was explicitly resized for input checks; its startup metrics still
need work. Prismatic must use a compatible IRIS backend and a fresh image
state directory. Preserve overlays belonging to the older CHD.

The [service/session runtime](results/2026-11-03-xiri-session.md) and
[xdm integration](results/2026-11-03-xiri-xdm.md) are now packaged in the
current xdm image above. This older module CHD retains its original launcher
and manual state as a regression control.

## Previous accelerated image with the xmahjongg repair

This bundle retains the framed kernel equivalent to NetBSD `a536d8c4da2`
and IRIS `xiri` `819c682`, and replaces the Xorg Newport module with the
[pinned texture correction](../lab/newport-xaa/README.md). XAA and Composite
remain enabled. xmahjongg matches the software control pixel for pixel;
hint/take, undo and resize/restore pass under 4Dwm.

Launch the bundled emulator with this one-liner:

```sh
/var/home/salvogendut/Dev/xiri/.work/images/xiri-netbsd-desktop-20261103-newport-xmahjongg/run-iris.sh
```

Log in as root and run `xiri-desktop`. Use the bundled IRIS backend for the
exact tested behavior. Prismatic requires the corresponding backend rebuild.
This remains a development image: broader 32-bit plane masks, winterm startup
font metrics, additional application compatibility and full gameplay still
need work. The diagnostic checks explicitly resize winterm for input.
The [direct CHD qualification](results/2026-11-03-newport-xmahjongg-image.json)
checks disk boot, the replacement module hash, native Render, catalog launch
and cleanup. Its [PNG](results/images/2026-11-03-newport-xmahjongg-image.png)
shows the launched game. This bundle is preserved as a built-in control;
That cycle selected the module-based image; the current pointer selects the xdm image above.
The inherited opened/closed Icon Catalog pixel check belongs to the
software cycle; catalog launch is checked again from the new CHD.

## Experimental framed-console acceleration image

The separate `.work/images/xiri-netbsd-desktop-20261102-framed-accel/` bundle
uses the requested NetBSD `feature/newport-framed-console` snapshot, equivalent
to commit `a536d8c4da2`, and IRIS `xiri` commit `819c682`. It enables Newport XAA
at 1280×1024 and includes the corrected emulator binaries. The CHD is
480,575,544 bytes; SHA256:
`483560d87b3002a0a8fdae3d170caebcf4fed47c0d6bf87c9de69d1d50d71826`.

Run its bundled backend:

```sh
cd .work/images/xiri-netbsd-desktop-20261102-framed-accel
./run-iris.sh
```

Use the root login and `xiri-desktop` command described below. An existing
Prismatic executable needs the corrected IRIS backend rebuilt into it;
the CHD alone cannot fix accelerated colors in an older emulator.

**This older bundle remains a control:** the RGB24 color and mask checks pass,
but its unpatched Xorg module corrupts xmahjongg artwork with XAA. Winterm can also start with incorrect
vertical font metrics; the automated interaction checks explicitly resize it.
The earlier software-rendered bundle remains a comparison image. The original
icon-state qualification belongs to that software-rendered cycle. Preserve
the manual overlay/NVRAM of this older accelerated bundle.

To compare rendering modes, log out and edit
`/usr/local/share/xiri/xorg.conf` as root: `NoAccel "true"` disables XAA;
`NoAccel "false"` enables it. Restart `xiri-desktop` after changing it.
Keep overlays separate. See the [cycle record](results/2026-11-02-newport-framed-acceleration.md)
for the tests and remaining artwork defect. The [direct CHD observation](results/2026-11-03-newport-framed-image.json)
verifies boot, catalog launch and clean shutdown; its
[PNG](results/images/2026-11-03-newport-framed-image.png) retains the visible
artwork failure.

## Start it in IRIS

Keep `netbsd-xiri.chd`, `iris.toml`, `nvram-graphics.bin` and `nvram.bin` together. Use an Indy
IP24 with an R4400, Newport graphics, 256 MiB RAM and the disk at **SCSI ID
1**. The included configuration selects these settings and CHD overlays.
A compatible IRIS build must include our NetBSD CPU/TLB/device fixes; see
[FORKS.md](FORKS.md). The exact emulator and kernel hashes are recorded in
the bundle's `manifest.json`.

For the standalone emulator, change to the bundle directory and run:

```sh
./run-iris.sh
```

For the GUI, configure a machine with those settings and select the CHD
and supplied NVRAM using absolute paths if they are outside the machine
folder. Select `nvram-graphics.bin` for automatic boot on the display.
Enable SCSI interrupt deferral. The diagnostic serial login uses channel B
at `127.0.0.1:8891` through **Machine → Serial console**.
Monitor and serial A ports are 8898 and 8890. Adjust all three if another
machine already uses them.

The graphical profile starts NetBSD and xdm automatically. Log in as
`xiritest` / `xiritest` for IRIX or `netbsdtest` / `netbsdtest` for native ctwm.
In winterm, `id -un` reports `xiritest`; `echo "$HOME"` and `pwd` both report
`/usr/people/xiritest`. Wait for its `xiritest@xiri$` prompt before typing.
Native `/bin/sh` runs inside winterm through the PTY handoff. A future actual
IRIX root desktop should use HOME `/`; NetBSD root's account remains unchanged.

The IRIX session starts original 4Dwm, Toolchest, winterm, xclock, Icon Catalog,
xmahjongg and desktop icons on xdm's X server. It has no session time limit
by default. The native account uses the unchanged system Xsession and ctwm.
Older images still require root login followed by `xiri-desktop`; use their
bundled README for that historical workflow.

The X screen is 1280×1024; the default PROM timing can leave two extra
framebuffer columns. **Desktop → Open Unix Shell** now opens another xwsh
with NetBSD's shell. Find → Icon Catalog uses the same native launch bridge.
The extra Applications menu is removed at the user’s request. Original
catalog page entries remain in the dynamic Find menu.
The original vendor menu files and IRIX shells are preserved; other original
menu actions still need compatibility work. Each supported menu launch has
its own `launch-APP.*/` log directory inside the current session directory.

The previous `.work/images/xiri-netbsd-desktop-20261102-behavior/`,
`.work/images/xiri-netbsd-desktop-20261102-framed-accel/`,
`.work/images/xiri-netbsd-desktop-20261102-shell/`,
`.work/images/xiri-netbsd-desktop-20261102-icons/`,
`.work/images/xiri-netbsd-desktop-20261102-graphical/`,
`.work/images/xiri-netbsd-desktop-20261102-services/`,
`.work/images/xiri-netbsd-desktop-20261102/` and
`.work/images/xiri-netbsd-desktop-20261101/` bundles are retained.
Use the new CHD in a fresh machine directory/overlay; do not attach an overlay
from the older base image to it.

Choose **Desktop → Log Out** in Toolchest to return to xdm.
For the desktop menu, hold the right mouse button over empty background,
move to **Log Out**, then release. Both routes stop the session's clients;
FAM, rpcbind and xdm remain running. They do not save an IRIX session.
For shutdown, log in as root on serial B and halt NetBSD before stopping IRIS:

```sh
shutdown -h now
```

Wait for the guest's halted message or PROM menu. Keep the CHD's associated
`.diff.chd` overlay with your machine to retain changes. To start another
independent experiment, use a fresh directory containing copies of the
base CHD, configuration and NVRAM. Retain an existing overlay if it contains
work you want to keep; a new directory provides a clean session without
altering it.

## Start it in Prismatic

The [Prismatic boot check](results/2026-11-02-prismatic-xiri.md) reaches
multiuser and observes the installed desktop using the existing release
binary. The [updated desktop check](results/2026-11-02-desktop-launch.md#replacement-image-and-prismatic-confirmation)
additionally covers the larger screen and a menu-created native shell,
with a [Prismatic screenshot](results/images/2026-11-02-prismatic-menu-shell.png).
Those Prismatic observations used earlier images. The current image is
qualified with the pinned standalone IRIS build, including actual Newport
frames and PS/2 console/menu input. Prismatic has not been retested with this
particular CHD and graphical NVRAM; its configuration still uses the same
machine and disk settings.

One earlier serial cold-boot capture was black and was rejected by the
qualifier. The fresh retry produced a valid desktop frame before test input;
its cause remains unresolved. The [usability record](results/2026-11-02-desktop-usability.md)
keeps both observations and the successful graphical-boot checks.

Prismatic embeds IRIS but uses its own configuration format. Use the
included `prismatic.cfg`, not `iris.toml`. The bundle also includes an
independent `prismatic-state/nvram.bin` seeded with the graphical NetBSD boot settings.
From the bundle directory:

```sh
~/Dev/prismatic/target/release/prismatic --config prismatic.cfg --state-dir prismatic-state
```

Press Ctrl+P to start if the frontend is paused, then click the display to
capture input. NetBSD boots to xdm; use `xiritest` / `xiritest` or
`netbsdtest` / `netbsdtest`. Serial B at `127.0.0.1:8891` remains available
for root administration.
Do not attach the same writable CHD/overlay to another running emulator;
make a separate copy when testing simultaneously. Ports 8890, 8891 and
8898 can be changed in `[advanced.expert]` if occupied.

When configuring through **F9**, use Indy IP24, R4400, 256 MiB, Newport and
the CHD at SCSI ID 1. Enable **Tinker** to expose Advanced and retain SCSI
interrupt deferral. An existing Prismatic machine keeps its own NVRAM, so
attaching the CHD does not import the bundle's boot variables. The PROM
commands below fix an existing machine still looking for `sash`.

## PROM settings and fallback

`nvram-graphics.bin` selects `console=g` and `AutoLoad=Yes`; the separate
`nvram.bin` retains the serial PROM profile for automated probes. To change
an existing machine's console profile at the PROM, use:

```text
setenv -f console g
setenv AutoLoad Yes
```

Restart the machine for the console change to take effect. For a diagnostic
serial PROM boot, use `setenv -f console d` and `setenv AutoLoad No` instead.

The verified boot path uses the disk's existing NetBSD volume-header
loader and `/netbsd.boot`, the ELF32 PROM wrapper. `/netbsd` contains the
native ELF64 kernel for kernel metadata/tools. If the PROM reports a missing
`sash`, it is still selecting the IRIX loader. With the existing partition
settings already pointing at SCSI ID 1, the user confirmed this shorter
sequence boots the image in Prismatic:

```text
setenv osloader boot
setenv osloadfilename netbsd.boot
setenv osloadoptions auto
boot
```

For fresh NVRAM or different disk/partition settings, use the full sequence:

```text
setenv systempartition scsi(0)disk(1)rdisk(0)partition(8)
setenv osloadpartition scsi(0)disk(1)rdisk(0)partition(0)
setenv osloadfilename netbsd.boot
setenv osloadoptions auto
setenv osloader boot
boot
```

Save NVRAM in IRIS after setting these variables (`rtc save` in the IRIS
monitor). The bundle also retains `tftp/netbsd-XIRI_INDY` for the lab's
fallback boot route. Normal disk boot does not require TFTP or a source
IRIX image.

## Return to IRIX

Halt NetBSD with `shutdown -h now`, then stop the emulated machine. In the
frontend's media settings, attach the original **IRIX disk at SCSI ID 1**.
Boot to the PROM menu and choose **5) Enter Command Monitor**, then enter:

```text
setenv osloader sash
setenv osloadfilename /unix
setenv osloadoptions auto
boot
```

The supplied installed `irix65.chd` has a volume-header entry named `sash`
and a `/unix` boot-file field, confirmed directly in its ingested raw disk.
Use that loader name for this image. Other IRIX disks may use a different
name, such as `sashARCS`; inspect their volume header or original settings.
If the partition variables were changed, restore them before `boot`:

```text
setenv systempartition scsi(0)disk(1)rdisk(0)partition(8)
setenv osloadpartition scsi(0)disk(1)rdisk(0)partition(0)
```

Both systems use these partition settings with the supplied disks at ID 1;
the loader and kernel filename differ. PROM variables belong to the
machine's NVRAM, not the CHD. Keep separate NetBSD and IRIX machine
configurations/state directories to avoid changing these variables each
time. Prismatic saves NVRAM when its machine stops/quits normally; standalone
IRIS also supports `rtc save` in its monitor.

## Reuse in automated work

Use `./xiri check` for the selected image. It chooses the xdm or legacy
launcher probe from the manifest and never changes the current image pointer.
For the current bundle, the explicit command is:

```sh
python3 scripts/probe-xiri-xdm.py \
  --bundle .work/images/xiri-netbsd-desktop-20261103-xdm
```

This clones the CHD and frozen graphical boot profile under `verification/`,
boots from disk without a TFTP kernel and checks the installed runtime.
Manual NVRAM/overlays remain untouched. Imported payload is reused.

For older harnesses that require a raw disk, materialize a stopped seed
once (the tool reuses the verified extraction when available):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/prepare-xiri-seed.py \
  .work/images/xiri-netbsd-desktop-20261103-module \
  --output-directory .work/xiri-image/prepared-seed-20261103-module
```

This produces `.work/xiri-image/prepared-seed-20261103-module/`. Clone its `disk.raw` for
runs; preserve that seed. Repeating preparation checks its hash and does
not reimport files. Use it with harnesses whose kernel and payload pins match. Keep the older
prepared seeds for historical regression tests; do not substitute a newer
kernel into their pinned runs.

To construct a replacement after qualifying a changed raw seed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-xiri-image.py \
  --seed-run PATH_TO_HALTED_QUALIFIED_RUN \
  --output-directory NEW_BUNDLE_DIRECTORY \
  --baseline lab/irix-module/image-baseline.json \
  --kernel .work/netbsd-module-build/tftp/netbsd-XIRI_INDY \
  --iris-bin-dir .work/images/xiri-netbsd-desktop-20261103-module/emulator
```

The builder runs `chdman verify` and requires a full extracted disk to
match the source SHA-256 exactly. Cold-boot qualification remains a separate
step. Preserve the previous image until its replacement passes.

After the disposable cold-boot run has halted cleanly, qualify its evidence
and promote the bundle's image pointer:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/qualify-xiri-image.py \
  PATH_TO_COLD_BOOT_RUN \
  --output docs/results/NEW_IMAGE_RESULT.json \
  --png docs/results/images/NEW_IMAGE_CAPTURE.png --promote
```

This preserves the build manifest, checks source and payload hashes, verifies
cleanup and framebuffer fidelity, and updates the current local image record.
The previous CHD is retained. Preparing the new raw seed afterward uses the
same `prepare-xiri-seed.py` command above.

## Current scope

The complete desktop is still under development. Icon Catalog discovers 18
pages and lists application names, including all 21 Freeware entries. Native
FAM supplies real directory notifications; FileManager lists native files and
folders. The imported toolbar glyphs render, and the Trusted Path panel is gone.
Boot rc.d owns FAM and rpcbind; they remain running across desktop logouts.
FAM serves the configured IRIX account at UID/GID 1234. Other native accounts
can use the standard NetBSD session.

The [icon repair](results/2026-11-02-desktop-icons.md) restores application-specific
Freeware artwork and FileManager folder/document icons through measured
locks, seek offsets and native FAM pathname mapping. The shell update adds
xmahjongg catalog launches; the behavior update adds opened/closed icon
feedback. Full file operations, broad application compatibility and package
installation remain open. Only
xmahjongg's application-specific data tree was collected completely.
The manual launcher disables 4Dwm session saving. Winterm can log a `gettxt`
warning while reaching the native shell prompt. The winterm cycle fixes the
observed window left open after typed `exit` and propagates terminal resize
to foreground jobs. An earlier repeated desktop start captured an intermittent
xwsh SIGFPE before its window appeared; that failed run and core are retained
in the icon result. The unusually short terminal is now reproduced as a native
Xorg Type1 font-metric failure. Terminal defaults select the existing SGI Screen
bitmap face; the Type1 root cause remains open. Session supervision removes
remaining clients at logout.


## Manual application checks

On 2026-11-03 the user reported that a quick survey of most of the desktop
found many tools and programs working as expected, with others needing tuning.
This supports using the current accelerated image as the development baseline.
It is broad manual feedback, not an application-by-application qualification;
specific application names, actions and failures have not yet been recorded.

Start with the **Freeware** page and inspect the icons, then use Toolchest's
**Open Unix Shell** twice and type commands in each terminal. Close the
xmahjongg launched at desktop startup before trying its catalog entry, so a
new launch can be distinguished from the existing window. Try other catalog
entries individually and record the exact entry/action and any error dialog.
Their presence and artwork do not imply that each application can run.

FileManager can inspect the native test folder
`/usr/people/xiritest/XiriTest`, which contains a directory and text document.
Finish with Toolchest logout, restart the desktop, and try desktop-menu logout.
Keep the overlay and `/var/tmp/xiri-desktop/session.*` logs when reporting a
failure. This lets the next compatibility cycle start from the actual action
and its logs rather than inferring support from the screenshot.
