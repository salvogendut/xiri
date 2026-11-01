# Reusable Xiri development image

The local bundle is `.work/images/xiri-netbsd-desktop-20261101/`.
`netbsd-xiri.chd` is an 8 GiB NetBSD disk compressed to 479,911,028 bytes
(about 458 MiB). It contains the qualified Xiri kernel, original IRIX
runtimes, installed application/catalog payload, persistent fonts and a
manual desktop launcher. [Cold-boot qualification](results/2026-11-02-xiri-image.md)
verifies disk boot and visible windows on native Xorg/Newport. The [import ledger](IRIX-IMPORT.md) records the
source and destination paths; vendor bytes remain outside Git.

## Start it in IRIS

Keep `netbsd-xiri.chd`, `iris.toml` and `nvram.bin` together. Use an Indy
IP24 with an R4400, Newport graphics, 256 MiB RAM and the disk at **SCSI ID
1**. The included configuration selects these settings and CHD overlays.
A compatible IRIS build must include our NetBSD CPU/TLB/device fixes; see
[FORKS.md](FORKS.md). The exact emulator and kernel hashes are recorded in
the bundle's `manifest.json`.

For the standalone emulator, change to the bundle directory and run:

```sh
/path/to/iris --config iris.toml
```

For the GUI, configure a machine with those settings and select the CHD
and supplied NVRAM using absolute paths if they are outside the machine
folder. Enable SCSI interrupt deferral. Open **Machine → Serial console**;
the supplied configuration uses serial channel B at `127.0.0.1:8891`.
Monitor and serial A ports are 8898 and 8890. Adjust all three if another
machine already uses them.

Select **Start System**, or enter `boot` at the PROM command monitor.
Log into NetBSD as `root` (the development guest has no root password),
then start the desktop from that serial console:

```sh
/usr/local/bin/xiri-desktop
```

The launcher starts native Xorg/Newport and original 4Dwm, Toolchest,
winterm, xclock, Icon Catalog and xmahjongg. It uses the reserved ordinary
UID 1234 and `HOME=/usr/people/xiritest` for clients. Native `/bin/sh` runs
inside winterm through the existing PTY handoff. The launcher has no
session time limit by default. Logs are under `/var/tmp/xiri-desktop/`.

Press Ctrl-C in the serial console running the launcher to end the session.
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
binary. Catalog communication and display repaint issues remain follow-ups.

Prismatic embeds IRIS but uses its own configuration format. Use the
included `prismatic.cfg`, not `iris.toml`. The bundle also includes an
independent `prismatic-state/nvram.bin` seeded with the NetBSD boot settings.
From the bundle directory:

```sh
~/Dev/prismatic/target/release/prismatic --config prismatic.cfg --state-dir prismatic-state
```

Press Ctrl+P to start if the frontend is paused. Use the serial console at
`127.0.0.1:8891` for NetBSD login with the provided serial-console NVRAM.
Do not attach the same writable CHD/overlay to another running emulator;
make a separate copy when testing simultaneously. Ports 8890, 8891 and
8898 can be changed in `[advanced.expert]` if occupied.

When configuring through **F9**, use Indy IP24, R4400, 256 MiB, Newport and
the CHD at SCSI ID 1. Enable **Tinker** to expose Advanced and retain SCSI
interrupt deferral. An existing Prismatic machine keeps its own NVRAM, so
attaching the CHD does not import the bundle's boot variables. The PROM
commands below fix an existing machine still looking for `sash`.

## PROM settings and fallback

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
  .work/images/xiri-netbsd-desktop-20261101
```

For older harnesses that require a raw disk, materialize a stopped seed
once (the tool reuses the verified extraction when available):

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/prepare-xiri-seed.py \
  .work/images/xiri-netbsd-desktop-20261101
```

This produces `.work/xiri-image/prepared-seed/`. Clone its `disk.raw` for
runs; preserve that seed. Repeating preparation checks its hash and does
not reimport files. The installed-image probe accepts this directory as
`--staged-seed` when its kernel and payload manifests still match.

To construct a replacement after qualifying a changed raw seed:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-xiri-image.py \
  --seed-run PATH_TO_HALTED_QUALIFIED_RUN \
  --output-directory NEW_BUNDLE_DIRECTORY
```

The builder runs `chdman verify` and requires a full extracted disk to
match the source SHA-256 exactly. Cold-boot qualification remains a separate
step. Preserve the previous image until its replacement passes.

## Current scope

The complete desktop is still under development. The populated catalog
files are installed, but Icon Catalog still showed its Blank fallback in
the imported-payload test. FileManager actions, catalog launching, broad
application compatibility and package installation remain open. Only
xmahjongg's application-specific data tree was collected completely.
The manual launcher disables 4Dwm session saving and may show its existing
Trusted Path warning. The winterm launcher also logs a `gettxt` execution
warning while still reaching the native shell prompt. These limits accompany the image; copying the
original resources does not establish full desktop compatibility.
