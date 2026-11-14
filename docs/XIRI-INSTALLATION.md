# Reproducible Xiri installation

Status: implementation plan, 2026-11-14. The user selected an **already-installed
IRIX 6.5.22 image** as the first import source. The supported end-to-end installer
described here does not exist yet. Existing import, runtime-install and CHD
preparation tools provide its components.

The first target is the tested NetBSD/sgimips configuration on IRIS, with our
matching MIPS64 kernel and `compat_irix_o32` module, native Xorg and accelerated
Newport. Stock-kernel installation remains dependent on the three interfaces
described in [NetBSD upstreaming](NETBSD-UPSTREAM.md). Physical hardware is a
separate qualification target.

## Source image and the supplied guide

The [SGI installation guide](https://sgi.neocities.org/installguide) describes
installing IRIX 6.5.22 into a MAME disk from Foundations, Overlays and Applications
media, with NFS and demos as optional additions. This is useful for preparing a
donor installation and understanding its package composition.

Its [home page](https://sgi.neocities.org/) links to
[irix-6.5.22m-MAME.tar.xz](http://usftp.irixnet.org/sgi-mame/irix-6.5.22m-MAME.tar.xz)
as an installed IRIX disk and describes using `irix65.chd`. The page was checked;
the download host was inaccessible through the browsing tool, and this archive
has not been downloaded or inspected. Its filename is not a qualification pin.

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
   depend on a particular filename.
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
| Read-only donor access | `inventory-irix-installed-desktop.py` and later resource stagers use guestfish with `ro,norecovery`. | Explicit source/output arguments, shared source ownership and cleanup, release/partition discovery, useful missing-file errors. |
| Resource provenance | Initial copy ledger plus font, bitmap, backdrop, GIMP, GNOME, shell, document, session, File Manager and Overview ledgers. | One consolidated profile, conflict checks and explicit optional components. |
| Payload archive | `stage-irix-installed-desktop.py` preserves file hashes and catalog link text. | Reproducible archive metadata, final installed permission rules and inclusion of later additions. |
| Native runtime | `runtime/Makefile`, `runtime/install.sh`, services and account synchronization. | Package its prerequisites as well as integration files; add complete preflight and managed-install records. |
| Kernel/module | Qualified builds and matching artifact manifests. | Package or identify the exact compatible pair; separate kernel installation/reboot from desktop activation. |
| Display and native services | Qualified Newport driver, Xorg configuration and patched FAM. | Reproducible build/package inputs independent of a populated desktop seed. |
| Desktop validation | Existing image, xdm, multi-user, session, font and application checks. | Run them against an installation created by the new workflow, including reinstall and failure recovery. |
| Reusable CHD | Current `build-xiri-image.py` verifies a prepared guest and its CHD round trip. | Make CHD production consume the same installation workflow rather than a chain of previously modified desktop images. |

The initial 1,990-record ledger alone is insufficient. Later qualified cycles
added resources and native fixes, and the current image builder starts from a
prepared seed. Merely exposing its existing command line would preserve that
hidden dependency instead of producing a fresh installation.

## Acceptance for the first supported workflow

- Build the same payload twice from the same source/profile and obtain matching
  file inventories and archive hashes.
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
