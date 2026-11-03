# Reusable Xiri development image

The current accelerated development bundle is
`.work/images/xiri-netbsd-desktop-20261103-newport-xmahjongg/`.
`netbsd-xiri.chd` is an 8 GiB NetBSD disk compressed to 480,615,682 bytes
(about 458 MiB). Its SHA256 is
`1fa5c92ffac3706680e16acd1270df4707928106529cf94084152f9dfac14ab5`.
The [texture-repair cycle](results/2026-11-03-newport-xmahjongg.md) records its
source and rendering checks. The earlier `20261102-behavior` software bundle
and `20261102-framed-accel` bundle are preserved for comparison.
It contains the qualified Xiri kernel, original IRIX
runtimes, installed application/catalog payload, persistent fonts and a
manual desktop launcher. The [desktop service qualification](results/2026-11-02-desktop-services.md)
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
in `/usr/people/xiritest`, as verified with `pwd`. Interactive original-shell
use remains unqualified. GIMP gets past its
former library mapping failure but fails signal registration; xosview still
needs IRIX statistics interfaces.

The [desktop behavior image](results/2026-11-02-desktop-behavior-image.md)
adds native FAM execution feedback, the granite backdrop and filesystem/home/
Dumpster desktop icons. The source-disk probe verifies xmahjongg changing to
its opened icon while running and returning to the exact closed pixels after
exit. It also verifies filesystem and Dumpster double-clicks opening their
directory views. Full Dumpster operations and launch animation remain open.

## Accelerated image with the xmahjongg repair

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
shows the launched game. `lab/irix-installed-desktop/image.json` selects this
bundle. The inherited opened/closed Icon Catalog pixel check belongs to the
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

The graphical profile starts NetBSD automatically. Log into NetBSD on the
display as `root` (the development guest has no root password), then start
the desktop:

```sh
/usr/local/bin/xiri-desktop
```

Root is the service launcher. The desktop itself runs as **xiritest, UID
1234**, so `/usr/people/xiritest` is its home. In winterm, `id -un` should
report `xiritest`, and `echo "$HOME"` and `pwd` should both show that path.
The user chose to retain this arrangement for the new test image. Direct
xiritest login is deferred because the current supervisor reserves the
whole UID for cleanup. A future actual IRIX root desktop should use HOME
`/`; NetBSD root's own account remains unchanged.
Wait for winterm's `xiritest@xiri$` prompt before typing: its window can appear
before the shell has finished starting.

The launcher starts native Xorg/Newport and original 4Dwm, Toolchest,
winterm, xclock, Icon Catalog and xmahjongg. It uses the reserved ordinary
UID 1234 and `HOME=/usr/people/xiritest` for clients. Native `/bin/sh` runs
inside winterm through the existing PTY handoff. The launcher has no
session time limit by default. Logs are under `/var/tmp/xiri-desktop/`.

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

Choose **Desktop → Log Out** in Toolchest to return to the launching shell.
For the desktop menu, hold the right mouse button over empty background,
move to **Log Out**, then release. Both routes stop the owned clients and
services. They do not save an IRIX session. Ctrl-C in a serial console
running the launcher remains an alternative.
Then shut down NetBSD before stopping IRIS:

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
capture input. NetBSD boots on the display; log in as `root` and run
`xiri-desktop`. Serial B at `127.0.0.1:8891` remains available for diagnostics.
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

Use the prepared image for routine desktop work. Inventory/extraction is
only necessary when deliberately changing the imported payload. This
probe clones the CHD, boots directly from disk and uses its installed
launcher without importing applications again:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-xiri-image.py \
  .work/images/xiri-netbsd-desktop-20261103-newport-xmahjongg \
  --iris-bin-dir .work/images/xiri-netbsd-desktop-20261103-newport-xmahjongg/emulator \
  --arrange-winterm
```

For older harnesses that require a raw disk, materialize a stopped seed
once (the tool reuses the verified extraction when available):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/prepare-xiri-seed.py \
  .work/images/xiri-netbsd-desktop-20261103-newport-xmahjongg \
  --output-directory .work/xiri-image/prepared-seed-20261103-newport-xmahjongg
```

This produces `.work/xiri-image/prepared-seed-20261103-newport-xmahjongg/`. Clone its `disk.raw` for
runs; preserve that seed. Repeating preparation checks its hash and does
not reimport files. Use it with harnesses whose kernel and payload pins match. Keep the older
prepared seeds for historical regression tests; do not substitute a newer
kernel into their pinned runs.

To construct a replacement after qualifying a changed raw seed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-xiri-image.py \
  --seed-run PATH_TO_HALTED_QUALIFIED_RUN \
  --output-directory NEW_BUNDLE_DIRECTORY \
  --baseline lab/newport-accel/corrected-baseline.json \
  --kernel .work/netbsd-newport-frame-build/tftp/netbsd-XIRI_INDY \
  --iris-bin-dir .work/target-newport-accel/release
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
The launcher owns FAM and any rpcbind it starts, then removes them on exit.
This remains a single-user development service at UID/GID 1234.

The [icon repair](results/2026-11-02-desktop-icons.md) restores application-specific
Freeware artwork and FileManager folder/document icons through measured
locks, seek offsets and native FAM pathname mapping. The shell update adds
xmahjongg catalog launches; the behavior update adds opened/closed icon
feedback. Full file operations, broad application compatibility and package
installation remain open. Only
xmahjongg's application-specific data tree was collected completely.
The manual launcher disables 4Dwm session saving. Winterm can log a `gettxt`
warning while reaching the native shell prompt; typing `exit` can leave its
xwsh window open. A repeated desktop start also captured an intermittent
xwsh SIGFPE before its window appeared; that failed run and core are retained
in the icon result. A direct-CHD diagnostic also produced an unusually short
terminal window with incorrect vertical font metrics; resizing restored input.
Initial sizing still needs investigation. Stopping `xiri-desktop` removes
remaining clients.


## Manual application checks

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
