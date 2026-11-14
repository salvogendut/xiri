# Reproducible Xiri installation

Status: vendor import and desktop smoke checks qualified, 2026-11-14. The first import source is an
**installed IRIX 6.5.22 image built from the user's original installation media**.
Our existing Prismatic installation now provides a
[verified donor CHD](results/2026-11-14-irix-donor.md) and a tested recipe;
the importer need not depend on a website hosting a preinstalled disk. The
supported end-to-end Xiri installer described here does not exist yet. Existing
import, runtime-install and CHD preparation tools provide its components.

The first target is the tested NetBSD/sgimips configuration on IRIS, with our
matching MIPS64 kernel and `compat_irix_o32` module, native Xorg and accelerated
Newport. Stock-kernel installation remains dependent on the three interfaces
described in [NetBSD upstreaming](NETBSD-UPSTREAM.md). Physical hardware is a
separate qualification target.

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
ctwm. Native packaging and clean-target installation remain separate stages.

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
components and disposable NetBSD qualification. No complete stock-NetBSD
installer or IRIX 6.5.30 qualification is implied by this import step.

## Separate IRIX 6.5.30 workflow

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
desktop resources. Validate imported ELF ABI/instruction-set requirements
against the NetBSD target and run the desktop/service/session acceptance checks
with the corresponding profile. Xiri support for 6.5.30 remains unqualified;
the existing IRIX boots are donor-installation evidence only. This is follow-up
work alongside the initial 6.5.22 packaging effort, not an additional completed
installer.

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
It came from the supplied RAR archive. Do not assume it is byte-identical to the
linked TAR archive or that another installation includes the same freeware.

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
| Payload archive | Normalized modes and metadata; two builds produce identical archives/manifests. NetBSD pax extraction passes all file hashes. | Managed installation with target-side type/mode/link verification, backup and retry semantics. |
| Native runtime | `runtime/Makefile`, `runtime/install.sh`, services and account synchronization. | Package its prerequisites as well as integration files; add complete preflight and managed-install records. |
| Kernel/module | Qualified builds and matching artifact manifests. | Package or identify the exact compatible pair; separate kernel installation/reboot from desktop activation. |
| Display and native services | Qualified Newport driver, Xorg configuration and patched FAM. | Reproducible build/package inputs independent of a populated desktop seed. |
| Desktop validation | Imported 6.5.22f desktop/shell/File Manager, logout/relogin and native ctwm smoke checks on a qualified native base. | Run the broader image/multi-user/preferences checks on a clean installation, including reinstall and failure recovery. |
| Reusable CHD | Current `build-xiri-image.py` verifies a prepared guest and its CHD round trip. | Make CHD production consume the same installation workflow rather than a chain of previously modified desktop images. |

The initial 1,990-record ledger alone was insufficient. The new profile includes
later vendor resources available in this donor. Native fixes and configuration
are still inherited by the qualification image, so a fresh installation also
requires the native packaging and managed-install stages.

## Acceptance for the first supported workflow

- Build the same payload twice from the same source/profile and obtain matching
  file inventories and archive hashes. **Passed for the 6.5.22f profile.**
- Complete an installation on a clean, compatible NetBSD target without copying
  a prepared Xiri desktop filesystem or relying on historical probe directories.
- Verify required bytes, types, modes and symlinks, and demonstrate useful errors
  for a missing component, wrong kernel/module pair or insufficient space.
- Repeat installation without overwriting user preferences or administrator
  configuration; recover from an interrupted install using its recorded state.
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
