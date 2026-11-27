# Prepare an IRIX desktop account on XiriBSD

Run `/usr/local/sbin/xiriprep` **as root inside XiriBSD**. The first run installs the shared
desktop from an installed IRIX disk. The supported profiles include our
6.5.22f and 6.5.30f installations and the independently distributed
SuperIRIX Indy 6.5.22m. The
machine uses one donor release. The examples select `xiritest`. Substitute
your ordinary NetBSD login, or repeat the command to prepare another user.

The current `xiribsd-indy-donor-profiles-11.99.11.iso` includes the tool and
all five desktop profiles. [Continue to the donor import](#read-a-donor-from-external-media)

## Use the tools CD on an existing Indy

If you installed the earlier native or xiriprep ISO, boot your existing
system disk at SCSI ID 1. In Prismatic, attach
`.work/images/xiriprep-indy-donor-profiles-tools.iso` at **F9 → Media → SCSI ID 6 → CD-ROM**.
In a root shell on the guest, mount the CD, install the tools and unmount it.

```sh
mkdir -p /cdrom
mount -r -t cd9660 /dev/cd0a /cdrom
(cd / && tar -xzpf /cdrom/xiriprep.tgz)
umount /cdrom
```

Eject the tools CD. You can now attach your donor media to the same Indy.

### Revert the tools update

On an Indy that previously used `xiriprep-indy-desktop-tools.iso`, reattach
that previous CD and repeat the mount and extraction above. If you customized
any installed tools, restore those files from your own pre-update backup.
The update also adds three profiles. Check their shipped hashes before removing
them on rollback. The commands below run on the guest as root.

```sh
cd /usr/local/share/xiri/plans
test "$(sha256 -q 6.5.22f-ip28.plan)" = 9a0a4f901784bec6b68e75074c5b1f9ab05493f4ae30d6395c222d3d3547202a && rm 6.5.22f-ip28.plan
test "$(sha256 -q 6.5.30f-ip30.plan)" = 108da12f14bf458cb738b0b6c91a3cfff9da5deea42efafaf80ebee2ddf2aa93 && rm 6.5.30f-ip30.plan
test "$(sha256 -q 6.5.22m.plan)" = a9ded07a99015783363bda8c4726831179d2f5b995ceb00755f7415798ca0c7b && rm 6.5.22m.plan
```

This procedure was tested on systems prepared with each original reference
donor. The existing 4Dwm account and its preferences survived the round trip.

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
the release, reports the selected profile and checks any installed release
receipt. The install command verifies every selected file before publishing
the shared desktop.

```sh
mkdir -p /cdrom
mount -r -t cd9660 /dev/cd0a /cdrom
/usr/local/sbin/xiriprep --check --source '/cdrom/IRIX donor.chd' --user xiritest
/usr/local/sbin/xiriprep --source '/cdrom/IRIX donor.chd' --user xiritest
```

Once `xiriprep` reports that the desktop is selected, run `umount /cdrom`
and eject the CD.

### CHD or raw image on a second disk

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

For the **SuperIRIX 6.5.22m Indy**, extract `irix65.chd` from
`irix65_chd.rar` and put the CHD on the second disk. Its 5.3 GiB file
exceeds the single-file limit of the data-CD command above. If the file is
at the root of the mounted disk, use the following commands before unmounting.

```sh
/usr/local/sbin/xiriprep --check --source /mnt/donors/irix65.chd --user xiritest
/usr/local/sbin/xiriprep --source /mnt/donors/irix65.chd --user xiritest
```

Look for `Identified IRIX 6.5.22m` and `Desktop profile: 6.5.22m.plan`.
Select the operating-system CHD from the archive. The second, Freeware CHD
supplies optional package media. [Archive checksums and provenance](IRIX-RESOURCES.md#provenance-of-the-downloads-images)

To make a second disk for Prismatic on the workstation, give NetBSD’s
`nbmakefs` a directory containing only the CHD. Run the commands below from
the Xiri checkout with a new work directory and output file.

```sh
mkdir .work/superirix-media
cp --reflink=auto "$HOME/Downloads/irix65_chd/irix65.chd" .work/superirix-media/
.work/netbsd-irix-build/tools/bin/nbmakefs -t ffs -B be -o version=2 \
  .work/superirix-donor.ffs .work/superirix-media
```

Attach `.work/superirix-donor.ffs` as a **hard disk at SCSI ID 2** and mount
it read-only as above. Only the standalone base file is copied in this example.
To import your own changes from a writable emulator overlay, export the
stopped donor first.

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
release and profile from the combined fingerprints of its shell, 4Dwm and
Toolchest. The shell and 4Dwm alone are identical on the tested 6.5.22f and
6.5.22m disks. Independently installed systems can have different libraries
or optional components. [Donor comparison](results/2026-11-27-owner-donors.md)

The reader verifies the executables, shared libraries, fonts,
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
