# Prepare an IRIX desktop account on XiriBSD

Run `/usr/local/sbin/xiriprep` **as root inside XiriBSD**. The first run installs the shared
desktop from your own installed IRIX 6.5.22f or 6.5.30f disk image. The
machine uses one donor release. You can select additional NetBSD users
independently by running the same command with a different login.

## Read a donor from external media

Supply the path to an image **file** as seen by the guest. For a data CD
containing a CHD, attach it at Prismatic’s CD-ROM slot (normally SCSI ID 6).
With one CD drive, run these commands in the native root shell.

```sh
mkdir -p /cdrom
mount -r -t cd9660 /dev/cd0a /cdrom
/usr/local/sbin/xiriprep --check --source '/cdrom/IRIX donor.chd' --user alice
```

To install after checking, run the command without `--check`. When it reports
that the desktop is selected, eject the donor CD and reboot. Choose the
named user at xdm. The installed desktop runs from the system disk.

```sh
/usr/local/sbin/xiriprep --source '/cdrom/IRIX donor.chd' --user alice
umount /cdrom
shutdown -r now
```

For a raw image on a second disk already mounted at `/mnt/donors`, use
the same command with its path.

```sh
/usr/local/sbin/xiriprep --source '/mnt/donors/IRIX 6.5.30.img' --user alice
```

Change the filenames and login to your own. The reader detects CHD by its
contents and also accepts a standalone raw SGI whole-disk image. It reads
the volume label, locates root XFS and verifies the shell and 4Dwm against
the release profiles. Reads go directly to the mounted file. A CHD needs
no expanded copy on the system disk. If the emulator has pending overlay
writes, export the merged disk before using it as a donor. A raw base file
can be several GiB yet have an empty SGI volume header when the installation
lives in its overlay. Copy the standalone export onto the external media.
[Exporting a donor](../profiles/README.md)

## What gets installed

The reader verifies the selected release’s executables, shared libraries, fonts,
desktop resources and original catalog links inside private staging directories.
The published trees are `/emul/irix` and `/usr/local/share/xiri/fonts`. Allow
192 MiB free on the filesystem containing `/var/db`, 184 MiB on the destination
filesystem for `/emul`, and 8 MiB under `/usr/local/share/xiri`. On a typical
single-filesystem Indy install, the staging tree is renamed into place.

XiriBSD supplies the session launcher, native FAM daemon and service scripts.
The first import builds the font index and filetypes, synchronizes account
lookups and sets up rpcbind, desktop devices, session shutdown and xdm for
the next boot. If verification fails, correct the donor or free the requested
space and rerun. A matching installation is reused for later logins. Use a
separate system disk for the other IRIX release. Optional browser, freeware
and audio packages have separate installation procedures.
[Desktop software](IRIX-SOFTWARE.md)

## Account and session behavior

- **Inspect first.** `--check` identifies the donor and reports whether
  the account exists. It does not write to the donor, account or session.
- **Existing account.** Omit `--check` to prepare the user. Their native
  home and password are preserved. When the matching shared desktop is
  installed, xiriprep writes the session as the user and saves a previous
  `~/.xsession` as `~/.xsession.before-xiriprep`. Repeating the command
  preserves that backup. Restore it to return to the previous session.
  Other logins retain their current desktops.
- **Missing account.** After the donor is identified, xiriprep asks whether
  to create the user. Enter accepts the default **No**. If you answer **Yes**,
  NetBSD creates an ordinary user with home `/usr/people/<login>` and
  prompts for a password. In a non-interactive run, create the account first.

## Add the command to the original native Indy ISO installation

The original `xiribsd-indy-native-11.99.11.iso` predates xiriprep. Attach
the separate `.work/images/xiriprep-indy-desktop-tools.iso`, mount it as
above, then install the native tools from the guest root shell.

```sh
(cd / && tar -xzpf /cdrom/xiriprep.tgz)
umount /cdrom
```

You can now insert the donor data CD. The tools CD includes the reader’s
source archive at `/usr/local/share/xiri/xiriprep-source.tgz` after
installation. [Native installation guide](INSTALL-INDY-PRISMATIC.md) ·
[Fresh-install results and screenshots](results/2026-11-27-xiriprep-desktop.md)

To make the tools CD again from a current installer on the workstation, run
`python3 scripts/package-xiriprep-tools.py installer.iso tools.iso`. Both
images contain only native components and the release inventories.
