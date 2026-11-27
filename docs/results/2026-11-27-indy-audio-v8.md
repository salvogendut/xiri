# Indy audio-v8 installers, updates and test disks

| IRIX desktop | Emulated Indy | Fresh installer SHA-256 | CHD SHA-256 |
| --- | --- | --- | --- |
| 6.5.22f | R4400, Newport | `12c3cc0adb4e49ac226f0a25f9640d16d6a3a64956fa0efd79fce372d541f349` | `746f613d574a7245f503ad15a5cb338455f98eeddf0c64c25a99e95ac01978e9` |
| 6.5.30f | R5000, Newport | `4ae2c0b5f0c27f5fae0a6e4c0ddc5583d5b7f012c74555e5ae247ccfab050723` | `69727d570e8579ac155d320b247c6a2d3d01d7b16d35bfd8623b7f574189679c` |

Run the release's Prismatic launcher under `.work/prismatic-indy-audio-v8/`.
The full installer ISOs are in `.work/installers/indy-11.99.11/audio-v8/`
and the update ISOs in its sibling `v7-to-audio-v8/`. Each ISO directory and each release’s launcher directory
contains a `SHA256` file. Run `sha256sum -c SHA256` there before the first
launch, while the graphical PROM state still has its delivered contents.
[Launch and login](../XIRI-IMAGE.md#clean-indy-audio-images) ·
[Install, update and roll back](../NATIVE-PACKAGE.md#upgrade-an-installed-indy-from-audio-v7-to-audio-v8) ·
[Build inputs, hashes and guest results](2026-11-27-indy-audio-v8.json).

## Fresh installations

The [Screen Saver follow-up](2026-11-27-indy-saver-repair.md) supplies
updated images and a repair CD for installations made from these ISOs.

The bootstrap started with NetBSD 11.0/sgimips and its X sets. It booted
the matched 11.99.11 kernel and loaded `compat_irix_o32` at securelevel 1.
Each release was installed twice with `install.sh --mozilla` on its own
clean clone. Each halted disk was compressed with zlib, verified with
`chdman verify` and checked against the source disk's uncompressed SHA-1.
The launchers use the same Prismatic executable and release-specific
graphical PROM settings as audio-v7. Writable test overlays were separate
from the delivered images.

## Graphical cold boots in Prismatic

On each CHD, the logo on the live xdm form matched the reference artwork
pixel for pixel. The form measured 690×304. Xorg reported a 1280×1024
desktop and Prismatic captured the Newport scanout at 1282×1024.
`xiritest` logged in to 4Dwm with its home and working directory at
`/usr/people/xiritest`. The session opened Toolchest, Icon Catalog,
winterm and xclock. The native `netbsdtest` login opened ctwm and xterm.

With the original SGI Audio Panel open, each release played one continuous
stereo WAV throughout seven observations. Native writes changed the visible
Mute box. Panel clicks changed the native mixer. All muted intervals
contained digital zero. Unmuting restored the 440 Hz left and 730 Hz
right channels with peaks of 4016 and 8031 at the saved levels of 64,128.
[6.5.22f desktop and Audio Panel](2026-11-27-indy-audio-v8-6.5.22f.png) ·
[6.5.30f desktop and Audio Panel](2026-11-27-indy-audio-v8-6.5.30f.png).

## Updating existing desktops

The update CD checks both full installers against their release receipts.
The SGI desktop and Mozilla archives are identical across v7 and v8 for
each release. The six native files that differ are the kernel, boot wrapper, module,
active xdm resources, example resources and logo pixmap.

On each v7 disk the test saved a user's backdrop, document and session
selection, the account and group databases, and custom speaker settings.
The R4400 used levels 80,96 and the R5000 used 96,112, both muted. After
upgrading, each machine booted to xdm, loaded the new module and restored
those levels and mute. Rollback booted the original kernel, loaded its
module and restored the original boot-file and receipt hashes. Repeating
either operation succeeded. Both directions preserved the saved file hashes.

The R4400 started with stock xdm resources. The upgrade selected the logo
and rollback removed the added pixmap. The R5000 started with a locally
edited xdm resource file and preinstalled logo. Both survived the round trip.

Two additional v7 guests installed their own Mozilla component before the
update. Both kept the executable and a saved file in the user's Mozilla
profile across upgrade and rollback. Each direction checked the four
desktop receipts, the browser's enabled state and its component receipt.
