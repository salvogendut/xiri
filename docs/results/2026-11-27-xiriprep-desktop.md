# Install 4Dwm directly from an IRIX donor on XiriBSD

On the emulated Indy, a blank-disk XiriBSD install can import the original
IRIX desktop on the target. The same native installer ISO serves both IRIX
releases. The owner supplies the donor after sysinst, and can eject it after
`xiriprep` finishes. [Installation guide](../INSTALL-INDY-PRISMATIC.md) ·
[Donor and user setup](../XIRIPREP.md)

## Installer media

| Local artifact in `.work/images/` | Bytes | SHA256 |
| --- | ---: | --- |
| `xiribsd-indy-xiriprep-11.99.11.iso` | 356857856 | `a90cca14c5d2c482e06fdbff1b21c383f21434b92ae91027b5f684a0247604e0` |
| `xiriprep-indy-desktop-tools.iso` | 2459648 | `d3cf59f0474b6030de5903b9f28369faaf035a6af183aec329d76faadbffd0e8` |

The installer reuses the verified November 27 NetBSD sets, kernel, module
and Xorg. The workstation cross-built the donor reader and desktop runtime
and assembled the CD with the native ISO recipe at `a06d856`. ISO readback
checked the sets and SGI boot loaders. The small tools CD carries the same
native tools for owners of the earlier installation. Neither CD includes an
IRIX executable, font or donor filesystem.
[Build inputs](../../lab/native-iso/indy-xiriprep-20261127.json) ·
[Original NetBSD build](2026-11-27-native-indy-iso.md)

## Two blank-disk imports

Each Indy installed all 15 sets onto its own 6 GiB disk. After reboot,
`xiriprep` read the reference CHD from a read-only data CD at SCSI ID 6.
The root shell selected `xiritest`, an ordinary NetBSD account with its own
`/usr/people/xiritest` home. The second login, `native`, kept its native
session configuration.

| Donor | Indy CPU | Verified plan entries | Desktop |
| --- | --- | ---: | --- |
| IRIX 6.5.22f | R4400 | 1668 | [Screenshot](2026-11-27-xiriprep-desktop-22.png) |
| IRIX 6.5.30f | R5000 | 1606 | [Screenshot](2026-11-27-xiriprep-desktop-30.png) |

Each guest first ran a negative test. One expected file digest was changed
in the disposable guest's plan. Import stopped at the mismatch before
publishing either shared directory or changing the user's session. Restoring
the plan allowed a successful retry. A further run preserved the user's
X resources and original session backup. The installed receipt matched both
published trees.

After power-off and removal of the donor CD, each Indy booted the installed
system, registered FAM with rpcbind, and logged into 4Dwm at 1280×1024.
The checks looked for Toolchest, Icon Catalog, xclock and winterm, including
its native shell handoff. [Repeat the blank-disk regression](../../lab/native-iso/check-desktop.py)

The Screen Saver control panel ran Qix in Demo, on idle and on idle after a
second xdm login. Frame comparisons detected animation in all three runs.
Space returned to the catalog. Disabling the saver and logging out returned
both guests to xdm. Each then admitted the second account to native ctwm.
The host regression suite also passed all 106 tests.

## Existing installations and raw donors

A separate pair of Indys installed the original native ISO and loaded
`xiriprep.tgz` from the new tools CD. Each mounted a second FFS disk
read-only at `/mnt/donors` and imported its release from a regular raw
image file. The installed receipts matched the CHD import on both releases.
The raw files were verified 4 GiB and 8 GiB exports of the reference disks.

An initial test supplied the original emulators' raw base files alone.
Both had zero-filled SGI volume headers because the installations lived in
the overlays. The reader rejected them before installing any desktop files.
Using the merged standalone exports resolved the error.

## Retained desktops

Both powered-off system disks were compressed to CHD. `chdman verify` and
a SHA1 comparison against the source disk passed for each. A fresh emulator
then booted a copy of each CHD, logged in through xdm, opened 4Dwm, Toolchest,
Icon Catalog and winterm, and powered off. The screenshots above are from
these direct CHD boots. [Launch instructions](../XIRI-IMAGE.md#indy-images-created-with-xiriprep)

| Local image directory under `.work/images/` | SHA256 of `netbsd-xiri.chd` | Evidence |
| --- | --- | --- |
| `xiribsd-indy-6.5.22f-xiriprep-20261127` | `6bb36f074e9548c40a3891215b423b0e459ea1a8756e206121c4287210fb922b` | [R4400 record](2026-11-27-xiriprep-desktop-22.json) |
| `xiribsd-indy-6.5.30f-xiriprep-20261127` | `0fb59a29c3f2c381e0c89a46541e633e2d14c36b64d3e7de3e22248b707c7714` | [R5000 record](2026-11-27-xiriprep-desktop-30.json) |

## Coverage

The plans cover the base desktop, its linked libraries, screen fonts, catalog
links and Screen Saver. Additional proprietary software, supplemental packages
and compatibility with independently installed donor layouts require separate
qualification. Physical SGI hardware was outside this run.
