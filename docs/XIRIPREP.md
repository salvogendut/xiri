# Prepare an IRIX desktop account on XiriBSD

Run `/usr/local/sbin/xiriprep` **as root inside XiriBSD**. The first run installs the shared
desktop from your own installed IRIX 6.5.22f or 6.5.30f disk image. The
machine uses one donor release. The examples select `xiritest`. Substitute
your ordinary NetBSD login, or repeat the command to prepare another user.

If you installed `xiribsd-indy-xiriprep-11.99.11.iso`, the command is
already available. [Continue to the donor import](#read-a-donor-from-external-media)

## Use the tools CD on an existing Indy

If you installed the earlier `xiribsd-indy-native-11.99.11.iso`, boot your
existing system disk at SCSI ID 1. In Prismatic, attach
`.work/images/xiriprep-indy-desktop-tools.iso` at **F9 → Media → SCSI ID 6 → CD-ROM**.
In a root shell on the guest, mount the CD, install the tools and unmount it.

```sh
mkdir -p /cdrom
mount -r -t cd9660 /dev/cd0a /cdrom
(cd / && tar -xzpf /cdrom/xiriprep.tgz)
umount /cdrom
```

Eject the tools CD. You can now attach your donor media to the same Indy.

## Read a donor from external media

Supply the path to an image **file** as seen by the guest. Use a standalone
export of an installed IRIX system. If the emulator stores changes in an overlay,
stop it and export the merged disk first. The raw base can be several GiB yet
have an empty SGI volume header when the installed system lives in its overlay.
[Exporting a donor](../profiles/README.md)

### CHD on a data CD

On your **workstation**, place the donor CHD inside a data ISO. Choose a new
output filename and substitute the path to your standalone CHD on the right
of the equals sign. The file on the CD will be named `IRIX donor.chd`.

```sh
genisoimage -R -V OWNER_DONOR -o irix-donor.iso -graft-points \
  'IRIX donor.chd=/absolute/path/to/standalone.chd'
```

Attach `irix-donor.iso` to Prismatic’s CD-ROM slot (normally SCSI ID 6).
In the **guest root shell**, mount it read-only. The optional `--check` identifies
the release and reports the account status. Run the next command to install.

```sh
mkdir -p /cdrom
mount -r -t cd9660 /dev/cd0a /cdrom
/usr/local/sbin/xiriprep --check --source '/cdrom/IRIX donor.chd' --user xiritest
/usr/local/sbin/xiriprep --source '/cdrom/IRIX donor.chd' --user xiritest
```

Once `xiriprep` reports that the desktop is selected, run `umount /cdrom`
and eject the CD.

### Raw image on a second disk

The tested setup used a second disk at SCSI ID 2 with an FFS filesystem on
`/dev/sd1c` containing the exported IRIX disk as a regular file. Use the
device and filename that match your disk. In the **guest root shell**, run

```sh
mkdir -p /mnt/donors
mount -r -t ffs /dev/sd1c /mnt/donors
/usr/local/sbin/xiriprep --check --source '/mnt/donors/IRIX backup.img' --user xiritest
/usr/local/sbin/xiriprep --source '/mnt/donors/IRIX backup.img' --user xiritest
```

After a successful import, run `umount /mnt/donors`. The reader detects the
format by content, so either medium can hold a CHD or a raw whole-disk image.
It reads the mounted file directly, including compressed CHD data.

## Check the first login

Run `shutdown -r now` as root and boot from the installed disk. At xdm, use
the selected account’s usual credentials. On both tested Indys, 4Dwm opened
at 1280×1024 with Toolchest, Icon Catalog, winterm and xclock. To check the
Screen Saver, open its control panel, select Qix and click **Demo**. Press
Space to return. Logging in as a user who kept the default XiriBSD session
opens ctwm. [Results and screenshots for both releases](results/2026-11-27-xiriprep-desktop.md) ·
[Start a tested Indy image](XIRI-IMAGE.md#indy-images-created-with-xiriprep)

## What gets installed

The reader locates the SGI volume’s root XFS filesystem and identifies the
release from its shell and 4Dwm. It verifies the executables, shared libraries, fonts,
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

## Rebuild the tools CD

To make the tools CD again from a current installer on the workstation, run
`python3 scripts/package-xiriprep-tools.py installer.iso tools.iso`. Both
images contain only native components and the release inventories. The installed
reader’s source archive is at `/usr/local/share/xiri/xiriprep-source.tgz`.
