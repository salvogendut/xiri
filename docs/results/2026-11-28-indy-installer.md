# XiriBSD Indy installer, November 28, 2026

The local installer is `.work/images/xiribsd-11.99.11-01-2026-11-28.iso`
(357,124,096 bytes). It boots sysinst on an emulated Indy and installs
NetBSD 11.99.11 with the Xiri compatibility module. Use the same ISO
for either donor release. Supply an installed IRIX disk to `xiriprep` after
booting the installed system. [Prismatic installation guide](../INSTALL-INDY-PRISMATIC.md)

To check your copy, run this command in `.work/images`.

```sh
sha256sum -c xiribsd-11.99.11-01-2026-11-28.iso.sha256
```

Expected SHA256 is `1cf1601db1c2da46a3c5b5195e0ebc98d397f236ed9fb34fd7c0cfe9ed27f07f`.

## Contents

This build reuses the 13 NetBSD and Xorg distribution sets, sysinst kernel
and both PROM loaders from the November 27 operator installer. The two
machine-specific sets were freshly assembled with the following inputs.

| Component | Source |
| --- | --- |
| Installed Indy kernel and PROM-format kernel | NetBSD-xiri `2223c5f0b4b`. [Shared-file-growth kernel](2026-11-27-indy-autogrow.md) |
| IRIX compatibility module | NetBSD-xiri `b187ffa60fd`. [Recording and pollable semaphores](2026-11-28-indy-mediarecorder.md) |
| Optical media service | The qualified [SGI CD Player build](2026-11-28-indy-cdplayer.md). |
| Native desktop runtime and `xiriprep` | Xiri `a79a502`, including the HAL2 audio import plans and the [desktop microphone action](2026-11-28-indy-recorder-overlays.md). |

The ISO contains native code and donor import recipes. SGI applications,
libraries, fonts and artwork come from the owner's separate disk. The build
read back every ISO file and both SGI volume-header loaders. The embedded
`native-media.json` records file digests, the base release sources and the
component revisions under `sources.composition`.

## Blank-disk installations

Both emulated Indys booted the CD at SCSI ID 6, installed all 15 sets on
an empty 6 GiB disk at ID 1 and booted from that disk with the installer
detached. Before import, each guest had `xiriprep` and no `/emul/irix`
directory. The installed kernel, PROM kernel and desktop runtime hashes
matched the ISO.

| Indy | Donor supplied to `xiriprep` after installation | xdm login |
| --- | --- | --- |
| R4400 | Original-media IRIX 6.5.22f Indy CHD | [4Dwm at 1280×1024](2026-11-28-indy-installer-22f.png) and ctwm for the native user |
| R5000 | Original-media IRIX 6.5.30f O2 CHD | [4Dwm at 1280×1024](2026-11-28-indy-installer-30f.png) and ctwm for the native user |

Each import preserved the account's existing X resources and a backup of
its previous session. Repeating preparation kept the group database intact.
The `xiritest` user could shut down after `--allow-shutdown`, and the other
account retained its original permissions. Both desktops showed Toolchest,
Icon Catalog, winterm and xclock. The Qix screen saver ran across a new
login. Both guests powered off cleanly. All 106 host tests passed.
[Checksums and per-release results](2026-11-28-indy-installer.json)
