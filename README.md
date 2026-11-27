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

## Install Xiri

The standard way to create a Xiri system is to **install XiriBSD, then run
`xiriprep` as root on the installed machine**. The Indy is the reference platform.
The installer ISO contains NetBSD, native Xiri tools and donor profiles.
All IRIX executables, libraries, fonts and desktop artwork come from your own donor disk.

1. On a fresh Indy, install from the native XiriBSD ISO and boot from disk. If you already installed the earlier native ISO, add the tools CD to your existing system. [Fresh install in Prismatic](docs/INSTALL-INDY-PRISMATIC.md) · [Tools CD for an existing Indy](docs/XIRIPREP.md#use-the-tools-cd-on-an-existing-indy)
2. Mount the media containing your installed IRIX disk image. The reference
   releases are 6.5.22f and 6.5.30f. The installer also recognizes the
   independently distributed SuperIRIX Indy 6.5.22m.
   Give `xiriprep` the path to the CHD or raw file and the NetBSD login to prepare. [Using xiriprep](docs/XIRIPREP.md)

On the first import, `xiriprep` installs the shared 4Dwm desktop, fonts and
native services. Reboot and log in through xdm as the selected user. Other
users keep their own desktop. [Build the native Indy ISO](docs/XIRI-INSTALLATION.md#build-the-native-indy-iso) · [Try a tested desktop image](docs/XIRI-IMAGE.md#indy-images-created-with-xiriprep)

When the XiriBSD ISO and CHD images are ready, you can download them from
[www.xiribds.org](https://www.xiribds.org/).

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
- **Installation and updates.** Keep reproducible original-media installs for both releases and test independently supplied disks. Extend update and recovery coverage on installed desktops. [Installation plan](docs/XIRI-INSTALLATION.md#donor-preparation-roadmap)
- **Physical workstations.** Qualify the Indy on real hardware, then extend testing to the Indigo2, Octane and O2.

[Full roadmap](docs/ROADMAP.md) · [Development history and test results](docs/HISTORY.md)

## Development

This repository contains the session runtime, installers and test tools.
The kernel lives in the NetBSD-xiri fork (`../NetBSD-xiri`, branch `xiri`).
The main test environment is the IRIS fork (`../iris`, branch `xiri`) with the
Prismatic graphical frontend (`../prismatic`).
[NetBSD-xiri](https://github.com/salvogendut/NetBSD-xiri/tree/xiri) · [IRIS](https://github.com/salvogendut/iris/tree/xiri) · [Prismatic](https://github.com/salvogendut/prismatic) · [Development guide](docs/DEVELOPMENT.md)
