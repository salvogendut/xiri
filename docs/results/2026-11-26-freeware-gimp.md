# GIMP 1.2.5 from the May 2004 Freeware CDs

SGI Software Manager 4.1 installs GIMP on the clean Xiri Indy desktops for
IRIX 6.5.22f and 6.5.30f. Each run starts from a private overlay with no
GIMP executable or SGI installation history. The installer uses each
desktop’s release-specific Foundation and overlay prerequisites.
[Install GIMP on an Indy](../../lab/irix-installer/README.md#install-gimp-125-from-the-freeware-cds).

## What the installation needs

| May 2004 disc | Products supplying the selected subsystems |
| --- | --- |
| 1 | aalib, bzip2 |
| 2 | GIMP, gettext, GLib, GTK+, gzip |
| 3 | libjpeg, libpng, libXpm, zlib, OpenSSL |
| 4 | TIFF, wget |

The media builder copies the original product descriptions, installation
databases and data streams. It verifies all 43 files against the
[disc inventory](../../lab/irix-installer/gimp-cd.json).
SGI’s installer reported no conflicts for the 19 selected Freeware
subsystems on either release. The GIMP selection includes its runtime,
base data, base plug-ins and scripts. [Software Manager selection](2026-11-26-freeware-gimp-6.5.22f-installation.png).

The original catalog hook adds
`gimp → /usr/freeware/bin/gimp` to the Freeware page. Its filetype hook
compiles the SGI rules and the helper merges them into the desktop table.

On both clean installations the first launch failed at `libgtk-1.2.so.1`.
The CD installs eight selected n32 shared libraries with mode 0644.
Xiri's ELF mapper checks execute permission on these files. The helper now
sets the eight regular files to 0555 after Software Manager records a
successful installation. The same binary then reports `GIMP version 1.2.5`
and opens the first-run wizard. The [earlier imported GIMP test](2026-11-03-irix-gimp.md)
used a donor tree with executable library modes already applied.

## Desktop check

The first xdm session creates the normal user's GIMP profile, opens a white
192 × 160 PPM, paints two strokes and saves through the PNM plug-in.
After quitting GIMP and logging out, the user logs in again, double-clicks
**gimp** in the Freeware tab and opens the saved file with Ctrl+O.
The check verifies the file owner, compares its bytes across logins and
compares the brush strokes in the reopened window against the decoded
file. All 30,020 interior RGB pixels matched exactly on each release. The
comparison excludes the one-pixel border where GIMP draws the layer boundary.

| Indy | Freeware tab | Reopened image |
| --- | --- | --- |
| 6.5.22f, R4400 | [Catalog](2026-11-26-freeware-gimp-6.5.22f-catalog.png) | [GIMP window](2026-11-26-freeware-gimp-6.5.22f-reopened.png) |
| 6.5.30f, R5000 | [Catalog](2026-11-26-freeware-gimp-6.5.30f-catalog.png) | [GIMP window](2026-11-26-freeware-gimp-6.5.30f-reopened.png) |

The [per-release results](2026-11-26-freeware-gimp.json) record the selected
subsystems, executable and filetype hashes, image checks and clean shutdowns.
The [follow-up maintenance check](2026-11-26-gimp-removal.md) covers shared
library conflicts, removal and reinstallation. Printing and GNOME plug-ins
remain open.
