# Native NetBSD on Indigo2 IP28

The original fixture qualifies the first native IP28/R10000 kernel: ARCS64 startup,
1 GiB RAM, serial console, interrupts/timers, HPC3 SCSI/FFS, Ethernet and
clean halt. It does not qualify an IMPACT framebuffer, Xorg or an IP28 IRIX
compatibility module. See the [result](../../docs/results/2026-11-22-ip28-kernel.md).

The subsequent `XIRI_IP28` configuration adds `MODULAR`, IMPACT `genfb`/Xorg
`wsfb`, and PS/2 keyboard/mouse. Keep the original `GENERIC64_IP28` checkpoint
separate. This is firmware-initialized **High IMPACT at 1280×1024**, using a
24-bit RGB shadow in 32-bit RAM pixels and programmed transfers. It does not
add DMA/3D acceleration. The original checkpoint uses serial B; the graphical
console work below adds visible boot and debugger output.
See the [module/IMPACT result](../../docs/results/2026-11-22-ip28-impact.md).

## Measuring IMPACT display updates

Add `display-bench.c` to the Xorg fixture ISO and regenerate its SHA256
manifest. Run `check.py` with `--xorg --display-bench --fixture-media ISO`.
Use a new output directory and private overlay for each run. For a disk
baseline select `--kernel netbsd.ip28`. For a candidate add
`--tftp BUILD_DIRECTORY/kernel --kernel netbsd`. Run the same pair
sequentially on each release. The kernel and module installation and full
graphical-console/xdm checks are separate from the timed single-user runs.

The Xlib client alternates two colours in a 640×480 X window. The first
workload fills the window. The second copies a checkerboard from a prepared
pixmap, exercising patterned uploads through wsfb. After a warm-up frame,
the host times five updates from the serial drawing request until a pixel
near the bottom right changes on the emulator display. This includes serial
delivery, guest scheduling, Xorg, the framebuffer worker and monitor polling.
The client moves the mouse clear of the sampled region. The test compares
all 307,200 displayed pixels in the final frame of each workload and retains
the samples, medians and PNGs. Use `scanout.py RUN_DIRECTORY/xorg.png` to check
the independent colour swatches and odd-width atlas from the Xorg probe.

## Graphical boot console

The console kernel selects native IMPACT text output when the PROM uses
`console=g`. Firmware displays the loader, then a static RAM framebuffer and
synchronous transfers provide early NetBSD text. `genfb` takes over at device
attachment; Xorg continues to use the standard 1280×1024 `wsfb` interface.
Console text and DDB output do not depend on the framebuffer update thread.
Serial B remains available for a root login once the system reaches multiuser.

Build the matching kernel/module pair as below. On a private overlay, boot
single-user through serial and run `prepare-console.sh` from verified media
containing `netbsd`, `compat_irix_o32.kmod` and `SHA256`. This removes the
explicit screen-0 allocation from `/etc/wscons.conf`: the graphical console
already supplies it. It retains the existing xdm accounts and serial getty.

Set the PROM to `console=g`, `OSLoadFilename=netbsd.ip28`,
`OSLoadOptions=auto` and `AutoLoad=Yes`, then reset for the console selection
to take effect. The new bundles retain those settings. Both the kernel and
firmware must match the graphical-console setup; older serial-only kernels
are not a substitute.

The qualification command uses a prepared overlay and saved firmware:

```sh
python3 lab/ip28-kernel/check.py --iris IRIS_BINARY --disk RELEASE_BASE_CHD \
  --overlay-dir PREPARED_OVERLAY --output RUN_DIRECTORY \
  --firmware-dir SAVED_FIRMWARE --kernel netbsd.ip28 \
  --autoboot --graphical-console --console-check --xdm full \
  --fixture-media TEST_ISO --command-timeout 300
```

`TEST_ISO` contains `type-ready.c` and a `SHA256` manifest. The probe captures
boot text, exercises a temporary root console login with PS/2 keys, enters
DDB with Ctrl-Alt-Esc, evaluates a constant and continues, then runs the normal
IRIX/native/IRIX xdm session checks. It stops its own IRIS instance afterward.
For graphical shutdown, it checks sustained return to PROM code and retains
the PROM-menu PNG; boot/shutdown text is no longer expected on serial B.

For serial recovery, select `console=d` and reset. If Xorg is needed in that
mode, create its screen from the serial root shell with `wsconscfg 0` before
starting xdm. Restore `console=g` for normal graphical boot. No extra X server
should run while xdm owns the display.

## Matching module and IMPACT checks

Build the kernel and module from the same NetBSD source checkout, using the
same tools and an isolated output directory:

```sh
sh lab/ip28-kernel/build.sh NETBSD_SOURCE NETBSD_TOOLS BUILD_DIRECTORY \
  NETBSD_SOURCE/sys/arch/sgimips/conf/XIRI_IP28
sh lab/ip28-kernel/build-module.sh NETBSD_SOURCE NETBSD_TOOLS BUILD_DIRECTORY
```

The module is `BUILD_DIRECTORY/module/compat_irix_o32.kmod`. Dependency
generation explicitly selects the N64 ABI; module compilation uses NetBSD's
full-width addresses and long calls. Neither script changes shared toolchain
wrappers. `XIRI_IP28` selects `sd0a` even when bootstrapped by TFTP.

For qualification, add these files to the read-only installation ISO:

- `compat_irix_o32.kmod` from the matching build;
- `check-module.sh`, `check-xorg.sh`, `check-desktop.sh`, `xiri-ip28-desktop`, `framebuffer.c`,
  and `xorg.conf` from this directory;
- `runner.c` from `lab/irix-lp64/`, `lifecycle.c` from `lab/irix-module/`,
  `probe.c` from `lab/indy-netbsd/x11/`, and `type-ready.c` from `lab/irix-4dwm/`;
- the locally retained, manifest-verified IRIX `asa` fixture as `vendor-asa`.

Regenerate the ISO's `SHA256` manifest. Run separately for each vendor line:

```sh
python3 lab/ip28-kernel/check.py \
  --iris IRIS_BINARY --disk RELEASE_BASE_CHD \
  --tftp BUILD_DIRECTORY/kernel --media QUALIFICATION_ISO --output RUN_DIRECTORY \
  --check-command 'mount -t cd9660 -o ro /dev/cd0a /cdrom && sh /cdrom/check-module.sh' \
  --xorg --desktop --command-timeout 300
python3 lab/ip28-kernel/scanout.py RUN_DIRECTORY/xorg.png
```

The module test checks rejected foreign exec before/after loading, exact
fixture output, the release image's vendor shell/echo, busy-unload `EBUSY`,
unload and reload. The common o32 `asa` fixture comes from 6.5.22; each guest
uses its own release's interpreters/libraries and installed shell/echo.

The graphics checks cover framebuffer dimensions and mapping bounds, Xlib
fills/copies/masks/odd-width images, actual PS/2 keyboard/release events and all
three mouse buttons, full-size PNG capture, and clean Xorg termination.
`scanout.py` requires Pillow and compares 8,944 displayed pixels, including the
whole 96×93 final atlas, independently of Xorg's shadow-buffer readback.
The test image's Xorg allocates `0xfe` primary-colour components.

`--desktop` exercises the installed service/session runtime as `xiritest`,
with the existing fonts/resources and `wsfb` replacing `newport` in the private
image's Xorg configuration. It types into winterm, checks home/UID, captures
the desktop and requests supervised logout. These single-user fixtures do not
qualify xdm login, early graphics-console boot or physical R10000 DMA caches.
The separate xdm checks below cover normal authenticated login.

The desktop test waits for the native shell handoff before typing and tolerates
windows disappearing during XQueryTree/XFetchName. It also initializes loopback
and the PTY namespace omitted by a single-user boot. These are test/startup
preconditions, not changes to the IRIX ABI.

## Manual IMPACT desktop

The separate graphical bundles are
`.work/native/xiri-ip28-impact-6.5.22-20261122/` and
`.work/native/xiri-ip28-impact-6.5.30-20261122/`. Each has a standalone CHD,
saved PROM state, `run-iris.sh`, and complete serial/boot instructions in
`README.txt`. Run the launcher, connect to serial B, choose PROM option 5,
enter `boot`, and press Return for the root shell. Then run:

```sh
/usr/local/sbin/xiri-ip28-desktop
```

This starts a full-screen native Xorg server and the existing desktop runtime
as `xiritest` with home `/usr/people/xiritest`. It loads the matching module and
prepares the services skipped by single-user boot. Log out through Toolchest,
then `/sbin/halt` before closing IRIS. Early boot stays on serial B; normal
xdm boot uses the separate bundles and checks below.

## Native xdm startup

The existing runtime also supports normal IP28 boot into native NetBSD xdm.
The platform-specific requirement is a wsdisplay screen before Xorg starts:
with serial B as the console, the kernel does not allocate screen 0. The
manual desktop wrapper creates it itself; xdm needs `wscons=YES` and
`screen 0 - vt100` in `/etc/wscons.conf`. Native `wscons` runs before LOGIN.

`prepare-xdm.sh` applies that configuration to a private copy of a qualified
IP28 IMPACT image. It retains the serial getty, disables the ttyE0 getty,
uses the existing `wsfb` Xorg configuration, and checks that the matching
module and existing per-user sessions are installed. It does not set passwords
or replace native PAM/Xsession. Preserve the original image while qualifying
the candidate.

For reproducible checks, create a Rock Ridge ISO containing `prepare-xdm.sh`,
`lab/irix-4dwm/type-ready.c` and a NetBSD-format `SHA256` manifest. Prepare a
private overlay, then boot it through the normal rc.d sequence:

```sh
python3 lab/ip28-kernel/check.py \
  --iris IRIS_BINARY --disk QUALIFIED_IP28_CHD --kernel netbsd.ip28 \
  --fixture-media XDM_FIXTURE_ISO --output PREPARATION_DIRECTORY \
  --check-command 'sh /cdrom/prepare-xdm.sh'
python3 lab/ip28-kernel/check.py \
  --iris IRIS_BINARY --disk QUALIFIED_IP28_CHD --kernel netbsd.ip28 \
  --fixture-media XDM_FIXTURE_ISO --overlay-dir PREPARATION_DIRECTORY \
  --output XDM_RUN_DIRECTORY --xdm full --command-timeout 300
```

`--fixture-media` mounts and verifies test files without replacing the kernel
or bootloader. `--xdm full` checks automatic module/service startup at
securelevel 1, the full-size greeter, authenticated IRIX and native desktops,
home/UID/groups/X authority, logout/relogin, stable system services and orderly
`shutdown -h now`. Native ctwm logout is exercised by ending the user's window
manager from its terminal. These tests use the image's public lab credentials.

After flattening a halted overlay and verifying its CHD, copy the successful
run's `nvram.bin` and `nveeprom.bin` into the candidate bundle. Run a separate
cold boot with `--xdm greeter --autoboot --firmware-dir CANDIDATE_BUNDLE`.
That check issues no PROM boot commands and needs no qualification CD. The
saved values are `OSLoader=boot`, `OSLoadFilename=netbsd.ip28`,
`OSLoadOptions=auto`, `AutoLoad=Yes`, with serial `console=d`.

The xdm bundles are `.work/native/xiri-ip28-xdm-6.5.22-20261122/` and
`.work/native/xiri-ip28-xdm-6.5.30-20261122/`. Run either `run-iris.sh`; if
paused, press Ctrl-P. Firmware boots NetBSD automatically and the graphical
greeter appears when startup finishes. Log in as `xiritest` / `xiritest` for
4Dwm, or `netbsdtest` / `netbsdtest` for native ctwm. These are the existing
public development-image credentials. The native user retains wheel membership.
Each bundle's `README.txt` gives serial administration and recovery settings.
Use `shutdown -h now` and wait for the PROM before closing IRIS.

## Build

Use the NetBSD fork's `xiri` branch containing `GENERIC64_IP28`. The script
uses an existing cross-toolchain without rewriting its shared wrappers.
All outputs go into the supplied directory; compilation uses two jobs.
Run this in the existing build container where the tools execute:

```sh
lab/ip28-kernel/build.sh NETBSD_SOURCE NETBSD_TOOLS BUILD_DIRECTORY
```

The kernel is `BUILD_DIRECTORY/kernel/netbsd`, an ELF64 image linked at
`0xa800000020080000`. An optional fourth argument selects another kernel
configuration for regression builds. The standalone loader is built with
[the boot64 fixture](../ip28-boot64/README.md); its load address is
`0xa800000020003000`.

## Prepare an isolated disk

Keep the two release lines separate. Use the respective qualified
6.5.22 or 6.5.30 Xiri base CHD; the native checks do not run its vendor desktop.
Create a Rock Ridge ISO containing `netbsd`, `ip28boot` and a NetBSD-format
`SHA256` manifest, then run:

```sh
python3 lab/ip28-kernel/check.py \
  --iris IRIS_BINARY --disk BASE_CHD --tftp BUILD_DIRECTORY/kernel \
  --media INSTALL_ISO --output PREPARATION_DIRECTORY
```

The script uses a private copy-on-write overlay, fresh firmware state and
private control ports. It selects `sd0a` during the initial TFTP boot, checks
native commands and installs `/netbsd.ip28` and `/usr/mdec/ip28boot`. It writes
`ip28boot` as `boot` in that overlay's volume header. The existing `/netbsd`
and IRIX module are retained, but are not qualified as an IP28 pair.

Then cold-boot through the installed loader:

```sh
python3 lab/ip28-kernel/check.py \
  --iris IRIS_BINARY --disk BASE_CHD --kernel netbsd.ip28 \
  --overlay-dir PREPARATION_DIRECTORY --output DISK_BOOT_DIRECTORY
```

A pass requires the expected machine identity, native shell, FFS write/read
comparison, process execution, timer commands, Ethernet replies, and an actual
`halting...` followed by the PROM menu. `halt: halted by root` alone is not
shutdown evidence. Address readiness is awaited with `ifconfig -w 20` before
pinging the local IRIS NAT gateway. Tests stop their own emulator on completion
or failure, and verify that the supplied base CHD is unchanged.

Package a successful, halted overlay without a large raw intermediate:

```sh
chdman copy -i OVERLAY_CHD -ip BASE_CHD -o CANDIDATE_CHD -c zlib -np 2
chdman verify -i CANDIDATE_CHD
python3 lab/ip28-kernel/check.py \
  --iris IRIS_BINARY --disk CANDIDATE_CHD --kernel netbsd.ip28 \
  --kernel-sha256 EXPECTED_KERNEL_SHA256 --output PACKAGED_BOOT_DIRECTORY
```

Use `--firmware-dir BUNDLE_DIRECTORY` for a further cold boot using its saved
`nvram.bin` and `nveeprom.bin` without issuing any `setenv` commands.

Only a separately cold-booted packaged CHD is a retained candidate. Preserve
both previous qualified Indy images. Remove disposable overlays and build
objects after saving the source, logs and qualified replacements.

## Indy regression

Build `lab/irix-module/XIRI_IRIX_MODULE` with the same source/toolchain in a
separate output directory. Boot its `netbsd.elf32` using
`--machine indy-r4400` for the 6.5.22 base or `--machine indy-r5000` for 6.5.30,
`--tftp REGRESSION_BUILD/kernel --kernel netbsd.elf32`, and:

```text
--irix-module /stand/sgimips/11.99.9/modules/compat_irix_o32/compat_irix_o32.kmod
```

This additionally loads the existing module and runs the original IRIX shell.
It checks shared-kernel regression coverage, not a new graphical qualification.

## Manual serial boot

The retained bundles are:

- `.work/native/xiri-ip28-6.5.22-20261122/`
- `.work/native/xiri-ip28-6.5.30-20261122/`

Run their `run-iris.sh` from any directory. They select IP28/R10000, High
IMPACT and 1 GiB RAM, with `console=d`; the graphical window does not contain
the NetBSD console. Connect a second terminal to the serial port listed in the
bundle's `README.txt`. If execution is paused, type `start` at the IRIS monitor.
Choose PROM option 5, then `boot`; press Return for `/bin/sh`.

The saved settings use compact firmware paths:

```text
setenv console d
setenv SystemPartition dksc(0,1,8)
setenv OSLoader boot
setenv OSLoadPartition dksc(0,1,0)
setenv OSLoadFilename netbsd.ip28
setenv OSLoadOptions single
boot
```

Use `mount -u -w /` for writes and `/sbin/halt` before closing IRIS. The
bundles keep manual changes in their own overlays. These original serial-only
bundles intentionally remain at their earlier kernel checkpoint; use the
separate IMPACT desktop bundles above for graphics. The native IRIX IMPACT disk and the qualified
Indy desktop bundles are separate and unchanged.
