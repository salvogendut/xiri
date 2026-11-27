<p align="center">
  <a href="xiri-logo.png"><img src="xiri-logo.png" width="320" alt="XiriBSD logo"></a>
</p>

# Xiri

Xiri runs the original SGI IRIX desktop and MIPS applications on NetBSD.
Its goal is to keep SGI workstations useful with a maintained operating system
and the desktop their users know, including 4Dwm, Toolchest, Icon Catalog,
File Manager and winterm.

A boot-loaded NetBSD kernel module implements the IRIX interfaces that the
original binaries expect. NetBSD supplies the drivers, Xorg and xdm login.
Each user can select the IRIX desktop or keep their native NetBSD session.
[Architecture](docs/ARCHITECTURE.md) · [Per-user desktop setup](docs/IRIX-SOFTWARE.md#selecting-the-irix-desktop-for-a-user)

## Try the desktop

When the XiriBSD ISO and CHD images are ready, you can download them from
[www.xiribds.org](https://www.xiribds.org/).

To install NetBSD from the native Indy CD, follow the
[short Prismatic install guide](docs/INSTALL-INDY-PRISMATIC.md).

The SGI Indy is the reference machine. Xiri maintains separate IRIX 6.5.22
and 6.5.30 installations and tests them in IRIS. Start with the Prismatic
launcher for your release if you have a prepared image. To build your own,
import the SGI binaries, fonts and desktop resources from an installed copy
of IRIX made with your own media.
[Build the native Indy ISO](docs/XIRI-INSTALLATION.md#build-the-native-indy-iso) · [Run an Indy desktop image](docs/XIRI-IMAGE.md#clean-indy-audio-images) · [Prepare a donor](docs/XIRI-INSTALLATION.md) · [Install or update Xiri](docs/NATIVE-PACKAGE.md)

## Platform status

All results below are from **IRIS emulation**. Each machine boots NetBSD
to full-screen xdm and runs both the IRIX 4Dwm session and native NetBSD
ctwm with the 6.5.22 and 6.5.30 disk images. Physical testing is still ahead.

| SGI workstation | Tested configuration | What works in emulation |
| --- | --- | --- |
| Indy | R4400 (6.5.22f) or R5000 (6.5.30f), Newport | Reference desktop with accelerated 2D graphics, SGI file playback and Audio Panel controls. [Indy images and audio](docs/XIRI-IMAGE.md#clean-indy-audio-images) |
| Indigo2 | R10000, High IMPACT | Graphical boot console and Xorg desktop with accelerated rectangle fills. [Graphics checks](docs/results/2026-11-22-ip28-2d.md) |
| O2 | R10000, CRIME graphics | Accelerated Xorg desktop, graphical boot console, persistent SCSI storage and MEC Ethernet. [Display](docs/results/2026-11-23-o2-frame.md) · [Disk and networking](docs/results/2026-11-23-o2-io.md) |
| Octane | R10000, Solid IMPACT (6.5.22) or High IMPACT (6.5.30) | Boots from SCSI with a graphical console and full-screen Xorg. Desktop services use loopback. IOC3 Ethernet is still open. [Octane desktop](docs/results/2026-11-23-octane-xdm.md) |

[Indigo2, O2 and Octane launchers and screenshots](docs/results/2026-11-26-platform-v6.md)

## Roadmap

- **Desktop compatibility.** Complete everyday workflows in the original desktop and applications, including file operations, saved sessions and multimedia.
- **Installation and updates.** The workstation build produces a native Indy install CD. `xiriprep` reads your donor image and prepares your account. Installing the shared IRIX desktop directly from that donor is next. [Using xiriprep](docs/XIRIPREP.md) · [Installation plan](docs/XIRI-INSTALLATION.md#donor-preparation-roadmap)
- **Physical workstations.** Qualify the Indy on real hardware, then extend testing to the Indigo2, Octane and O2.

[Full roadmap](docs/ROADMAP.md) · [Development history and test results](docs/HISTORY.md)

## Development

This repository contains the session runtime, installers and test tools.
The kernel lives in the NetBSD-xiri fork (`../NetBSD-xiri`, branch `xiri`).
The main test environment is the IRIS fork (`../iris`, branch `xiri`) with the
Prismatic graphical frontend (`../prismatic`).
[NetBSD-xiri](https://github.com/salvogendut/NetBSD-xiri/tree/xiri) · [IRIS](https://github.com/salvogendut/iris/tree/xiri) · [Prismatic](https://github.com/salvogendut/prismatic) · [Development guide](docs/DEVELOPMENT.md)
