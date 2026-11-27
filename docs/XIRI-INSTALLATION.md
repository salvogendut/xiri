# Reproducible Xiri installation

## Standard installation

1. Install the native XiriBSD ISO on a blank disk and boot the installed
   system. The same native ISO serves both IRIX release lines. [Indy install guide](INSTALL-INDY-PRISMATIC.md)
2. Mount the media containing your installed IRIX donor image. As root on
   XiriBSD, run `/usr/local/sbin/xiriprep --source /mnt/donors/irix.chd --user alice`,
   substituting the actual CHD or raw image path and intended NetBSD login.
   If the account is missing, the tool offers to create it. [Donor and account instructions](XIRIPREP.md)

The first import installs the shared desktop and fonts, prepares the native
services and selects the named account. Reboot before that account’s first
4Dwm login. The donor can be removed after the import.
[Reference donor checks](results/2026-11-27-xiriprep-desktop.md) ·
[Independently installed donors and tools update](results/2026-11-27-owner-donors.md)

The earlier full desktop CDs and prepared CHDs provide working desktops for
comparison and recovery. [Reference media and test results](results/2026-11-27-indy-saver-install.md)

Both Indy releases use stock NetBSD/sgimips userland with a MIPS64 kernel and
matching `compat_irix_o32` module built from the `xiri` branch of NetBSD-xiri.
The tested configuration uses native Xorg and accelerated Newport on IRIS.
The installer saves the stock kernel for native NetBSD recovery.
[Installation and rollback instructions](NATIVE-PACKAGE.md#switching-between-the-stock-and-xiri-kernels)

The optional [Indy Screen Saver update and rollback](results/2026-11-26-sgi-screen-saver.md#update-an-existing-v6-disk) adds the original Qix Demo to an installed v6 desktop. The separate [Indy HDSP update and rollback](results/2026-11-26-indy-hdsp.md#manual-test-on-either-indy-v6-disk) installs the Indy kernel, its PROM image, the HDSP compatibility module and its device links. Both updates work with the existing v6 disks.

## Planned workstation build and `xiriprep`

### Build the native Indy ISO

Use a Linux workstation with Python 3.11 or later, Git 2.38 or later,
`genisoimage`, `isoinfo`, C and C++ compilers, and the NetBSD cross-build
prerequisites. The build environment also needs CMake 3.19 or later for
the native donor reader and access to the pinned libchdr, FAM and pkgsrc sources. On Fedora add `--toolbox xiri-iris` to compile in the
existing Toolbox while the workstation assembles and reads back the media.
Run the build from the Xiri checkout.

```sh
scripts/build-xiribsd-iso.py --work .work/native-indy \
    --output .work/images/xiribsd-indy-native.iso
```

The builder resolves the three remote branches once, writes their commit IDs,
the two prepared Git tree IDs and the recipe hashes to
`.work/native-indy/sources.json`, and reuses that lock on retry. Use
`--prepare-only` to stop after checking the sources. For another build, use a
new work directory and pass `--lock /path/to/sources.json` from the recorded
Xiri revision. A complete local fork checkout supplied with
`--src-reference ../NetBSD-xiri` saves a download. Keep the reference checkout
while the build directory is in use. `-j` selects the number of build jobs.
The default builds both toolchains. Developers can pass `--tools64` to reuse
an existing NetBSD mips64eb toolchain for the kernel and module.

To rebuild the current Indy installer, use the
[five-profile installer lock](../lab/native-iso/indy-owner-donors-20261127.json)
with the Xiri recipe revision in its `xiri` field and pass that file to
`--lock`. The [earlier desktop installer lock](../lab/native-iso/indy-xiriprep-20261127.json)
reproduces the version with the two original profiles.

To reproduce the original November 27 ISO, use Xiri revision `ebdce50`
(which includes its source lock and original recipe) and add
`--lock lab/native-iso/indy-20261127.json` to the command above.
[Recorded sources and build inputs](../lab/native-iso/indy-20261127.json).

The Indy uses a 32-bit native userland and Xorg, a 64-bit kernel, and an
ELF32 copy of that kernel for the PROM loader. The CD contains NetBSD install
sets and native Xiri components. Its `native-media.json` identifies the source
trees, installed Xiri files, and SHA256 of every set and the installer kernel.
Archive `sources.json` with the ISO. The build directory can be removed once
the image has been tested.

To boot the CD, install all 15 sets and reach the graphical login, follow
the [Prismatic Indy install guide](INSTALL-INDY-PRISMATIC.md). It uses
Prismatic's usual CD-ROM slot at SCSI ID 6 and a blank disk at ID 1.
The stock 32-bit recovery kernel is `netbsd.stock`.

### Donor preparation roadmap

The first target is an Indy. One native XiriBSD ISO should support two
separately tested installations, one using a 6.5.22f donor and one using
a 6.5.30f donor. Build both project donors from original media. Also test
the same ISO with an installed disk from outside the project, retaining
that disk's stream and provenance. An owner can build the ISO before obtaining
or attaching a donor. The existing private desktop CDs and CHDs include
imported SGI files. They serve as references for the finished desktop.

The workstation builder supplies the kernel, module, userland, patched Xorg,
native xdm, desktop services and the on-target donor installer. The original November 27
ISO predates that command. An installed Indy can add it from the tools CD.
[Run xiriprep on the Indy](XIRIPREP.md).
[NetBSD and Xorg source changes](NETBSD-UPSTREAM.md#display-xfs-and-session-work-have-separate-destinations).

Root runs `xiriprep --source /path/to/irix.chd --user alice` on XiriBSD.
It opens a CHD or raw image on any mounted filesystem, identifies the
release, uses the existing account or offers to create it, verifies and imports
the release’s base desktop and fonts, and selects the session. The first run
records the release, runtime and import plan in `/var/db/xiri-install`.
[Current importer](../scripts/xiri_lab/irix_import.py) ·
[Existing per-user session](IRIX-SOFTWARE.md#selecting-the-irix-desktop-for-a-user).

The workstation importer uses `chdman` and `guestfish` and pins a whole-disk
hash. The on-target reader identifies the SGI root partition and matches
the shell, 4Dwm and Toolchest together to a release and desktop import plan.
The plans cover the original two donors, an additional Indigo2 6.5.22f
and Octane 6.5.30f installation, and the independently distributed
SuperIRIX Indy 6.5.22m. A newly encountered combination of libraries
or optional components needs its own audit. The full import verifies each
file in the selected plan. [Donor comparison](results/2026-11-27-owner-donors.md)

The fork already supplies a read-only PUFFS `mount_xfs` with IRIX journal
support. It accepts an extracted XFS partition in a regular file and requires
a clean unmount record. The donor reader reuses its XFS routines and reads
the partition directly inside the raw file or CHD. [Fork mount_xfs manual](https://github.com/salvogendut/NetBSD-xiri/blob/xiri/external/gpl2/xfs/puffs/mount_xfs.8).

Reading the SGI label and XFS superblock on the workstation gave these
sizes for the two reference CHDs. Both labels passed their checksums and
identified partition 0 as root. Its first sector is 266,240 on both disks.
Both filesystems use XFS v4 and 4,096-byte blocks.

| Donor | Root partition length (512-byte sectors) | Bytes to stage as an extracted partition |
| --- | ---: | ---: |
| 6.5.22f | 8,122,368 | 4,158,652,416 |
| 6.5.30f | 16,510,976 | 8,453,619,712 |

These sizes make a reader that can address a partition within a donor
particularly valuable on an Indy. Discover the partition from each donor's
label. The shared starting sector is specific to these two installations.

**Acceptance.** Boot the ISO on an emulated Indy with a blank disk and no
donor attached. Install, eject the ISO, reboot and log in to native ctwm.
Repeat from that base separately for each donor release. Run `xiriprep`
for an ordinary account, log in to full-screen 4Dwm, and exercise winterm,
Icon Catalog and the saved Screen Saver. Confirm a second account still
gets ctwm and a repeat import preserves the first user's preferences. Keep
each release's test CHD and results separate.

## Our original-media installation

The November 14 audit found a completed installation in
`~/Downloads/IRIX media/Installed/Indy-R4400-6.5.22/`. Its `README.txt`,
`INSTALL-NOTES.txt`, `installation.cfg`, console log and `desktop.png` record:

| Input or result | Recorded value |
| --- | --- |
| Frontend and emulator | Prismatic `99914900`, IRIS `xiri` at `fb24628e` |
| Installation server | Native Instigator v0.5.1, private BOOTP/TFTP/RSH network |
| Machine | Indy IP24, R4400, 128 MB, Newport 24-bit |
| Target disk | New 4 GiB raw disk at SCSI ID 1, XFS with 4096-byte blocks |
| Software selection | Feature stream, `keep *`, `install standard` |
| Installed release | `uname -R` reports **6.5 6.5.22f** |
| Recorded validation | Successful installation, then graphical login and 4Dwm after a cold disk boot with no CD and the helper disabled |

The original media remain under `~/Downloads/IRIX media/`:

```text
common/IRIX 6.5 Foundation 1.iso
common/IRIX 6.5 Foundation 2.iso
6.5.22/IRIX 6.5.22 Overlay 1 of 3.iso
6.5.22/IRIX 6.5.22 Overlay 2 of 3.iso
6.5.22/IRIX 6.5.22 Overlay 3 of 3.iso
6.5.22/IRIX 6.5.22 Applications November-2003.iso
```

All six match the installation server's staged copies by size and SHA256.
The [audit ledger](results/2026-11-14-irix-donor-audit.json) records those hashes,
full emulator/frontend revisions and hashes of the saved evidence. The saved
notes identify Instigator's version, but not its exact commit; the frontend's
current build metadata describes a later build. This audit did not boot the
guest again or qualify its files under Xiri.

### Reuse the existing installation workflow

Prismatic's [installation guide](../../prismatic/docs/installing-irix.md) and
[6.5.22 Instigator template](../../prismatic/packaging/install-server/instigator-6.5.22.example.yaml)
describe the maintained procedure. Instigator reads the original CD images and
serves five distributions: Overlay 1, Overlay 2, Overlay 3, merged Foundations,
and Applications. The saved setup is
`../prismatic/target/install-server/irix6522/setup/instigator.yaml`; a reproducible
setup should live outside `target/` so build cleanup cannot remove it.

The completed install used Overlay 1 CD to copy the miniroot, then the private
network for the kernel and packages. A separate fresh-disk check verified a
fully network-based bootstrap through the filesystem-creation prompt:

```text
setenv tapedevice bootp():/6.5.22/dist/sa
boot -f $tapedevice(sashARCS) --m
```

Follow the guide's preceding `fx` partitioning and PROM environment setup;
these two commands alone are not a complete install recipe. Clear installed-OS
boot overrides while installing, retain graphics hardware even when using the
serial console, and keep idle parking disabled for the recorded serial `fx`
workaround. The saved full install resolved optional Java/Inventor dependency
conflicts and reached **No conflicts** before `go`.

IRIS also supplies a direct CD-changer workflow in
[its installation guide](../../iris/clanker/irix/irix-install.md), with
[`iris-irix65.toml`](../../iris/iris-irix65.toml) and `iris-ci` helpers. That
is a separate route using an empty CHD and the same six CD roles. The older
`irix-install/iris-install.toml` is a Windows/June-1998-media example; it is not
the configuration used for our Prismatic 6.5.22 installation.

### Export and qualify a donor CHD

The saved installation consists of **all three** files:
`irix6522.img`, `irix6522.img.overlay`, and `irix6522.img.overlay.dirty`.
The base is an empty sparse disk; installation writes are in the overlay and
its sector map. Converting the base alone would produce an empty donor.

This export is now complete: the [donor qualification](results/2026-11-14-irix-donor.md)
records the read-only merged export, verified CHD/raw round trip, filesystem
inventory, graphical cold boot and clean guest power-off. Original disk files
and PROM state are preserved. The 505.4 MiB CHD, source hashes, launcher and PNG
are retained in `.work/donors/irix-6.5.22f-original-media/`.

This donor is **6.5.22f**; Xiri's selected manual-test CHD remains **6.5.22m**.
The separate import profile now passes resource comparison and NetBSD desktop
checks, without replacing that reference. A standard CD install
does not establish the presence of the old donor's additional GIMP, Acrobat,
GNOME or freeware payloads. Keep those components optional with their own
provenance and missing-component checks.

The completed static comparison finds all 42 selected core paths: 20 have
identical full-file hashes, and the 22 differing core ELFs have identical code
sections. The imported 55-path bitmap set and granite backdrop match. Acrobat
resources are present; GIMP, GNOME and xmahjongg need additional payloads.
The versioned [6.5.22f import profile](../profiles/README.md) now builds the
vendor payload independently of our prepared NetBSD image. Its
[qualification record](results/2026-11-14-irix-import.md) covers reproducibility,
imported file hashes, the desktop, shell, File Manager, logout/relogin and native
ctwm.

### Starting from stock NetBSD

The [clean bootstrap fixture](../lab/native-package/README.md#bootstrapping-a-stock-target)
uses the original NetBSD 11.0 Indy install. It adds the release X sets, saves
the stock kernel, and installs the matching Xiri kernel, boot wrapper and
module on a private disk. The PROM boots `netbsd.boot` and NetBSD loads
`compat_irix_o32` through `/etc/modules.conf`. The [bootstrap
record](results/2026-11-23-clean-bootstrap.json) identifies the exact disk,
kernels, module and emulator for that first 11.99.9 run. The
[11.99.11 installer](NATIVE-PACKAGE.md#clean-installation-on-an-emulated-indy)
combines a new native package with each release's verified vendor payload. It
installs on a fresh clone of the stock bootstrap and preserves existing user
and site configuration across a repeat installation. The modular boot
reproduces the earlier `savecore` warning about the missing `_dumpdev` symbol.
Crash-dump collection remains open. [Earlier modular boot](results/2026-11-03-irix-module-image.md)

The v5 Indy installer can also include the release-matched SGI Mozilla
browser. Select it with `install.sh --mozilla` on a fresh or existing v5
desktop, then reboot. [Media inputs, upgrade and removal](NATIVE-PACKAGE.md#install-or-remove-mozilla-on-the-indy).

### Build the vendor payload

```sh
./xiri import \
  --source .work/donors/irix-6.5.22f-original-media/irix-donor.chd \
  --output .work/imports/irix-6.5.22f-v1 \
  --component acrobat
```

The default profile pins the qualified donor's exact CHD/raw hashes. Desktop
and fonts are included by default; Acrobat is optional. GIMP, GNOME and
xmahjongg report missing source components before extraction. An independent
installation needs its own audited source pin, even if its release matches.

`payload.tar.gz` contains the vendor files and screen fonts; `manifest.json`
records every source/destination, source type, canonical path, mode, hash,
dependency and omitted catalog link. Two independent donor builds produced
identical payloads and manifests. The [profile guide](../profiles/README.md)
documents reproducibility, the read-only extraction boundary, required native
components and disposable NetBSD qualification. The separate clean installation
procedure above consumes this payload.

## Separate IRIX 6.5.30 workflow

**Release policy:** always maintain two deliverables, one for IRIX 6.5.22 and
one for IRIX 6.5.30. Each has its own donor, import profile, qualification record
and manual-test CHD; neither replaces the other. Native NetBSD components may
be shared only where validated with both releases. Qualify the first 6.5.30
payload after the native-package milestone; a planned second version is not
yet a qualified image.

Maintain a separate original-media installation and Xiri qualification process
for **IRIX 6.5.30**, as requested on November 14. Reuse common tooling, with
release-specific media manifests, installation recipes, import profiles, donor
CHDs and test results. Keep the 6.5.22 workflow available independently.

Prismatic already records successful **6.5.30f** installations and graphical
disk boots on O2 R5000 and Octane R10000. Use those
[installation records](../../prismatic/docs/installation.md) and the
[6.5.30 Instigator template](../../prismatic/packaging/install-server/instigator.example.yaml)
as the starting point. That setup uses the 6.5.30 overlays, Applications August
2006, and Foundation 1 and 2. The O2 and Octane recipes retain their own PROM,
miniroot and graphics settings; 6.5.30 does not support the Indy donor machine.

The separate process must pin and check its media, package selection, release
stream, tool revisions and exported disk contents, then inventory its required
desktop resources. This stage is now complete for the O2 donor: the
[6.5.30 result](results/2026-11-14-irix-6.5.30.md) records media pins, verified
CHD/raw round trip, fresh native IRIX serial boot/shutdown, resource/ELF
inventory and two byte-identical imports. Use
[`profiles/irix-6.5.30f-v1.json`](../profiles/irix-6.5.30f-v1.json) explicitly.
This donor includes desktop/fonts but no Acrobat, GIMP, GNOME or xmahjongg.
Its n32 libraries include MIPS IV code; retain the R4400/6.5.22 reference and
use a MIPS IV CPU for this qualification. The
[Indy/R5000 retry](results/2026-11-14-r5000-6.5.30.md) now boots the existing
NetBSD kernel through native login and full-screen xdm. Its core desktop,
shell, File Manager, logout/relogin and native ctwm checks now pass with shadow
cache mode and the MIPS IV-aware compatibility module. This runs imported 6.5.30 applications on
NetBSD, not a 6.5.30 IRIX kernel on unsupported Indy hardware.

On the emulated O2/R10000, the IP32 N64 kernel boots from an 8 GiB SCSI disk
using NetBSD's `ip3xboot` in the SGI volume header and the ELF32-wrapped
kernel in FFS. Both Xiri release disks run the vendor shell and open full-screen
xdm on the CRIME display. Log in as `xiritest` for 4Dwm or `netbsdtest` for ctwm.
[O2 launchers and greeter update](results/2026-11-23-o2-greeter.md) ·
[O2 boot results](results/2026-11-23-o2-r10000-boot.md) ·
[O2 disk and Ethernet checks](results/2026-11-23-o2-io.md)

For manual Indy testing, use the [clean v5 Xiri CHDs and launch
commands](results/2026-11-24-indy-v5-clock.md). Each release has its own
NetBSD installation and writable overlay. The [November 15 preview
images](results/2026-11-15-irix-previews.md) document the earlier prepared
disks. The separate native IRIX donor CHDs remain available for donor boot
testing.

The emulated Octane/R10000 boots its IP30 kernel and brings up full-screen
xdm and 4Dwm on Solid IMPACT and High IMPACT. Its disk layout requires the
ELF64 `ip30boot` loader. [Octane boot results and launchers](results/2026-11-23-octane-frame.md)

## Existing reference and external background

The [SGI installation guide](https://sgi.neocities.org/installguide) describes
installing IRIX 6.5.22 into a MAME disk from Foundations, Overlays and Applications
media, with NFS and demos as optional additions. This is useful for preparing a
donor installation and understanding its package composition.

Its [home page](https://sgi.neocities.org/) links to
[irix-6.5.22m-MAME.tar.xz](http://usftp.irixnet.org/sgi-mame/irix-6.5.22m-MAME.tar.xz)
as an installed IRIX disk and describes using `irix65.chd`. The page was checked;
the download host was inaccessible through the browsing tool, and this archive
has not been downloaded or inspected. It is background information, not a
required download for the original-media workflow.

Our existing donor is separately identified in
[the reference manifest](../lab/irix-reference/manifest.json): IRIX 6.5.22m,
`irix65.chd`, SHA256
`f0615ce71308026c1366c289be8de8a640a0ca83ca7b808139acb71f3482a659`.
The local RAR matches the uploader’s manifest. The TAR archive above remains
unverified. [RAR archive provenance](IRIX-RESOURCES.md#provenance-of-the-downloads-images)

The two disks have distinct roles: the IRIX image supplies original programs,
libraries and resources; the target runs NetBSD, the compatibility module and
native services. The guide's IRIX disk-formatting, boot-loader and Xsgi commands
are not target installation instructions. No MAME setup is required merely to
import files from a readable donor image.

## Installation stages

1. **Inspect the source.** Accept an explicit CHD or raw disk path. Identify the
   SGI partition layout, filesystem and release; inventory required files before
   producing an installation package. Mount the donor read-only with XFS recovery
   disabled. Record hashes and available components, and report missing inputs.
   An archive is first unpacked to obtain the disk; archive recognition must not
   depend on a particular filename. A base with outstanding emulator overlays
   requires a verified merged export; never silently inventory the base alone.
2. **Build the import payload.** Consolidate the current copy ledgers and later
   resource additions into one versioned profile. Preserve required library,
   catalog and resource relationships, with explicit file modes and symlinks.
   Keep the base desktop independent of optional GIMP, Acrobat, GNOME and freeware
   payloads. Report absent optional components without describing them as working
   applications. Produce a deterministic archive and source-to-destination ledger.
3. **Assemble the native package.** Supply the matching kernel/module provenance,
   native FAM, session helpers, rc.d services, Xorg/Newport requirements and
   configuration templates. Record build inputs and hashes. A bundle must include
   or explicitly require every dependency that earlier prepared images inherited.
4. **Install and configure.** Check target architecture, kernel/module compatibility,
   required native tools, payload integrity and disk space before changing files.
   Install the IRIX payload under `/emul/irix`, native helpers under the maintained
   runtime prefixes, and boot/service configuration through defined install steps.
   Preserve existing administrator configuration and user homes. Record owned files
   and backups so retry, upgrade and removal have defined behavior.
5. **Enable a user's session and verify it.** Select the existing Xiri `.xsession`
   template for an ordinary native account. Generate IRIX account lookup tables
   from native identities. New IRIX-style homes may use `/usr/people/<name>`;
   preserve an existing user's actual HOME, and retain `/` for an IRIX root session.
   Verify boot-loaded module, services, full-screen xdm, desktop launch, logout and
   saved preferences. Native users must retain their standard desktop option.

Installer configuration should expose source, destination, component selection,
desktop account and display choice. Lab run directories, fixed test UIDs,
test passwords and probe histories must not be installation prerequisites.

## Existing pieces and the work needed

| Component | Available now | Work for the supported installer |
| --- | --- | --- |
| Read-only donor access | `./xiri import` takes explicit source/output paths, pins the donor, mounts XFS with `ro,norecovery`, reports missing files and cleans temporary extraction state. | Broader release/partition discovery and separately audited donor profiles. |
| Resource provenance | Versioned 6.5.22f desktop/fonts/Acrobat profile, dependency closure, conflict checks and missing-component errors. | Separate sources and profiles for GIMP, GNOME and freeware absent from this donor. |
| Payload archive | Independent builds produce identical archives and manifests. NetBSD pax extraction passes all file hashes. The installer can resume after a full font target on a separate filesystem. [Recovery procedure](NATIVE-PACKAGE.md#recover-from-a-full-target-filesystem) | Exercise additional component selections. |
| Native runtime | The [native packager](NATIVE-PACKAGE.md) builds from pinned sets. The [desktop removal procedure](NATIVE-PACKAGE.md#remove-the-desktop-and-return-to-native-netbsd) preserves homes and supports same-release reinstall. The [helper update](NATIVE-PACKAGE.md#upgrade-native-helpers-on-an-installed-indy) handles replacements, additions and retirements. The [v4 update](NATIVE-PACKAGE.md#configure-the-fam-service-log-with-v4) replaces the FAM startup script and its example while preserving active configuration. | Extend migration coverage to other services and defaults as they change. |
| Kernel/module | Both Indy images can boot the saved NetBSD 11.0 kernel and return to 11.99.11 with the matching Xiri module and user homes intact. [Rollback procedure](NATIVE-PACKAGE.md#switching-between-the-stock-and-xiri-kernels) | Repeat the boot and rollback checks on physical Indy hardware. |
| Display and native services | Native package includes the pinned Newport driver, corrected Xorg/GLX pair, Xorg configuration and patched FAM/rpcbind; stock X libraries and tools are explicit prerequisites. | Repeat deployment on physical Indy hardware. |
| Desktop validation | Both clean Indy releases cold-boot to xdm, run 4Dwm with the original shell and native ctwm with UXTerm, and return to xdm. | Extend clean-target coverage to preferences and additional applications. |
| Reusable CHD | [Clean v5 Indy bundles](results/2026-11-24-indy-v5-clock.md) are built from the halted per-release installations, verified against raw bytes and booted from private overlays. | Repeat this installer qualification on additional platforms. |

The initial 1,990-record ledger alone was insufficient. The new profile includes
later vendor resources available in this donor. The original qualification used a prepared native image. The clean Indy test
now exercises native installation and both vendor releases on stock userland.

## Reference desktop installer checks

These checks cover the earlier full desktop media. The standard workflow has
its own [fresh-install acceptance criteria](#donor-preparation-roadmap).

- Build the same payload twice from the same source/profile and obtain matching
  file inventories and archive hashes. **Passed for the 6.5.22f profile.**
- Complete an installation on a clean, compatible NetBSD target without copying
  a prepared Xiri desktop filesystem or relying on historical probe directories.
  **Passed on both emulated Indy targets.** [Results and screenshots](results/2026-11-23-clean-indy-desktops.md)
- Verify required bytes, types, modes and symlinks, and demonstrate useful errors
  for a missing component, wrong kernel/module pair or insufficient space. The
  [v4 recovery checks](results/2026-11-24-indy-v4-recovery.md) cover actual
  failed writes during payload copy, service configuration and native update.
- Repeat installation without overwriting user preferences or administrator
  configuration; recover from an interrupted install using its recorded state.
- Remove the desktop, verify native ctwm through xdm on the stock kernel and
  reinstall the same release with saved preferences. The [dual-release
  recovery test](results/2026-11-24-indy-desktop-removal.md) also interrupts
  removal and checks that pre-existing native files and links survive.
- Upgrade an installed native helper, resume an interrupted change and roll back
  with the same release-specific CD. [Dual-release checks](results/2026-11-24-indy-native-upgrade.md)
- Boot to full-screen xdm, enter an ordinary IRIX desktop, exercise catalog launch,
  winterm and File Manager, save preferences, log out/in and reboot. Check a second
  IRIX account and a separate native desktop account.
- Preserve the donor image and qualified manual CHD. Remove owned scratch disks,
  extraction caches and test instances after saving the results. Retain only the
  selected package/image and compact provenance needed to reproduce it.

Original IRIX `inst`/Software Manager support remains a separate milestone for
ongoing application installation, upgrades and removal. This importer bootstraps
the desktop; copying files does not establish IRIX package installation history.
See [software installation](IRIX-SOFTWARE.md) and the [roadmap](ROADMAP.md).
