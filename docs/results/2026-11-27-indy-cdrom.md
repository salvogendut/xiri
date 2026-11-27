# The Indy CD-ROM desktop icon

On an original IRIX 6.5.22f Indy, attaching a CD-ROM drive at SCSI ID 6
put a `CDROM` icon on the desktop even with an empty tray. Inserting a
Rock Ridge ISO 9660 disc added a disc and ISO badge to the icon.
`/usr/etc/mediad -n` mounted it read-only at `/CDROM` from
`/dev/rdsk/dks0d6vol`. The SGI desktop's `sabgicons` changed its
`SaRemovableMediaModel` filetype from `cdrom.unloaded` to `cdrom.iso9660`.
Ejecting restored the unloaded filetype and removed the mount.
[Original IRIX empty drive](2026-11-27-cdrom-irix-empty.png) ·
[Original IRIX loaded drive](2026-11-27-cdrom-irix-loaded.png) ·
[SGI removable media guide](https://tech-pubs.net/SGI_Admin/books/IA_Periphrls/sgi_html/ch03.html)

## Xiri desktop

Attach a virtual CD-ROM drive before boot. Prismatic normally uses SCSI ID 6.
Log in through xdm and insert a data disc. The icon changes in the running
session. Double-click it to open the disc in SGI File Manager. To swap
discs, select the icon, hold the right mouse button and choose **Eject
CDROM**. The empty icon returns in the same place. Insert the next disc. The first NetBSD optical drive is `cd0`
regardless of its SCSI ID. [SGI desktop eject instructions](https://pixelbart.net/SGI/IRIX/i/65/18/doc/usr/share/Insight/library/SGI_bookshelves/SGI_EndUser/books/PerSysAdmin/sgi_html/ch02.html)

| Desktop in IRIS | Drive empty | ISO 9660 inserted | Double-click |
| --- | --- | --- | --- |
| 6.5.22f, Indy R4400 | SGI empty-drive artwork | Disc artwork and ISO badge | [File Manager showing README.txt](2026-11-27-cdrom-6.5.22f.png) |
| 6.5.30f, Indy R5000 | Same | Same | [File Manager showing README.txt](2026-11-27-cdrom-6.5.30f.png) |

The native `xiri_cdrom` service checks the drive every three seconds.
It mounts `/dev/cd0a` read-only with the NetBSD `nodev` and `nosuid`
flags. SGI File Manager reads a state file through the user's host-icon
directory and renders the artwork already installed from that user's donor
release. An ordinary local user can browse the disc and request a normal
eject. A busy filesystem stays mounted. The test held a shell in `/CDROM` and confirmed the eject request returned
`Device busy`. After the shell left the disc, the menu ejected it and the
empty icon matched its original pixels. A pre-existing manual mount kept
its mount point and its owner. A nonempty `/CDROM` directory is also preserved. [Xiri desktop eject menu](2026-11-27-cdrom-eject.png)

This check covers one optical drive and ISO 9660 data, including Rock Ridge.
Audio tracks, SGI EFS-format distribution discs and additional drives remain
open. SGI's original desktop can identify audio media and launch CD Player.
[SGI peripheral icons](https://techpubs.jurassic.nl/library/manuals/4000/007-4480-001/sgi_html/ch02.html)

[Per-release measurements and artifact hashes](2026-11-27-indy-cdrom.json)

## Ready-to-boot Prismatic systems

Two standalone XiriBSD disks on the development workstation include the
CD-ROM service, the microphone-capable Indy kernel and its matching module.
Each started from its release's qualified `xiriprep` disk. The launchers
select the NetBSD graphics PROM and attach a read-only sample at SCSI ID 6.

| Desktop | Run from the Xiri checkout |
| --- | --- |
| 6.5.22f, Indy R4400 | `.work/prismatic-indy-cdrom/6.5.22f/run-prismatic.sh` |
| 6.5.30f, Indy R5000 | `.work/prismatic-indy-cdrom/6.5.30f/run-prismatic.sh` |

Press **Ctrl+P** to boot. At xdm, click the display and enter `xiritest`
for both the username and password. Double-click **CDROM** to browse
`README.txt`. To exchange discs, close the disc window, select the drive,
hold the right mouse button and choose **Eject CDROM**. Release the
Prismatic pointer with **Ctrl+Enter**. Under **F9 → Extensions → Storage**,
select target 6 and choose **Storage actions → Insert CD**. The sample is
`.work/prismatic-indy-cdrom/xiri-data.iso`.

Both standalone CHDs passed `chdman verify`. Prismatic 0.1.4
cold-booted a private overlay of each disk, accepted the desktop login and
opened the sample in SGI File Manager. After the File Manager window closed,
`xiritest` ejected the disc and the service reported an empty drive. The
framebuffer showed the microphone alongside the loaded drive. [Prismatic desktop screenshot](2026-11-27-prismatic-cdrom.png)

The project owner also confirmed the CD-ROM feature worked during manual
testing in Prismatic.

## Try it on an existing prepared Indy

The workstation test disc is `.work/images/xiri-cdrom-runtime-test.iso`
(384 KiB, SHA-256 `2ce36cd5c6e22e61e11bcbc6b94232a6975482fb778237660285fe0694d1e967`). It contains four native runtime files. The normal installation
path builds these into the XiriBSD runtime installed by `xiriprep`.

On a copy of a November 27 prepared Indy CHD, log out of 4Dwm, attach the
test ISO at ID 6, and run the following from a NetBSD root shell. The
desktop filetype compiler uses the artwork from the guest's existing donor
installation.

```sh
mount -r -t cd9660 /dev/cd0a /mnt
install -r -m 555 /mnt/daemon /usr/local/libexec/xiri/cdromd
install -r -m 555 /mnt/service /etc/rc.d/xiri_cdrom
install -r -m 555 /mnt/clients /usr/local/libexec/xiri/desktop-clients.sh
install -r -m 444 /mnt/rules /usr/local/share/xiri/applications.ftr
/usr/local/sbin/xiri-update-filetypes
umount /mnt && eject cd0
test -f /etc/rc.conf.d/xiri_cdrom || echo xiri_cdrom=YES >/etc/rc.conf.d/xiri_cdrom
/etc/rc.d/xiri_cdrom start
```

Log in and insert an ISO 9660 data disc. You can reinsert the test ISO
itself. For a shell eject, first leave any directory on the disc, then run
`/usr/local/libexec/xiri/cdromd --eject`.

## Repeat the qualification

Build `cdromd` with the NetBSD/sgimips o32 compiler and matching sysroot
or use the runtime's native `make` target. Run once per qualified Indy
bundle. The checker uses a private disk and generated media, logs in with
xdm, checks the mount and file contents, compares empty/loaded/ejected
pixels and double-clicks the device. The output retains the framebuffers
and window inventory. Temporary disks are removed after guest shutdown.

```sh
python3 lab/native-iso/check-cdrom.py --bundle "$BUNDLE" --emulator "$IRIS_DIR" \
    --daemon "$BUILD_DIR/cdromd" --output "$NEW_RESULT_DIR"
```
