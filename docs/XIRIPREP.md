# Prepare an IRIX desktop account on XiriBSD

Run `/usr/local/sbin/xiriprep` **as root inside XiriBSD**. It identifies an
installed IRIX 6.5.22f or 6.5.30f donor and prepares the named NetBSD account.
On a machine with a matching shared IRIX desktop, it also selects 4Dwm for
that account’s next xdm login. On a fresh native install, installing the
shared desktop payload from the donor is still under development.

## Read a donor from external media

Supply the path to an image **file** as seen by the guest. For a data CD
containing a CHD, attach it at Prismatic’s CD-ROM slot (normally SCSI ID 6).
With one CD drive, run these commands in the native root shell.

```sh
mkdir -p /cdrom
mount -r -t cd9660 /dev/cd0a /cdrom
/usr/local/sbin/xiriprep --check --source '/cdrom/IRIX donor.chd' --user alice
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
writes, export the merged disk before using it as a donor.

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
the separate `xiriprep-indy-tools.iso`, mount it as above, then install the
native tools from the guest root shell.

```sh
(cd / && tar -xzpf /cdrom/xiriprep.tgz)
umount /cdrom
```

You can now insert the donor data CD. The tools CD includes the reader’s
source archive at `/usr/local/share/xiri/xiriprep-source.tgz` after
installation. [Native installation guide](INSTALL-INDY-PRISMATIC.md) ·
[Test results and screenshots](results/2026-11-27-xiriprep.md)
