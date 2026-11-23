# Clean Indy desktop installation

Both release disks start from the same stock NetBSD 11.0/sgimips installation.
The shared bootstrap installs `xbase`, `xetc`, `xfont` and `xserver`,
saves the stock kernel and cold-boots the Indy kernel and boot wrapper from
the 11.99.11 integration build. NetBSD loads `compat_irix_o32` from the
filesystem at boot and reaches securelevel 1. The bootstrap checked the stock
disk and PROM hashes before and after the test. [Kernel build](2026-11-23-netbsd-current.md)

| Local manual bundle | Emulated configuration | Donor payload |
| --- | --- | --- |
| `.work/images/xiri-clean-indy-6.5.22f-20261123` | Indy R4400, 256 MiB, Newport | Original-media 6.5.22f desktop, fonts and Acrobat |
| `.work/images/xiri-clean-indy-6.5.30f-20261123` | Indy R5000, shadow cache, 256 MiB, Newport | Original-media 6.5.30f desktop and fonts |

Run `./run-iris.sh` in either bundle. Log in at xdm as `xiritest` with
password `xiritest` for 4Dwm, or as `netbsdtest` with password
`netbsdtest` for native ctwm. These are disposable test-image credentials.
The launcher gives each release its own writable CHD overlay.

## Installation checks

- Each target started without a vendor tree, Xiri services or desktop accounts.
  The qualification fixture created the two test accounts and selected Xiri
  only for xiritest. The installer itself leaves user accounts and homes under
  native administration.
- A TERM interrupted installation after it recorded the input archives. A retry
  encountered a deliberately conflicting administrator file at
  `/usr/lib/desktop` after publishing the verified vendor trees. It preserved
  that file. Removing the fixture conflict and rerunning the installer completed
  the installation. Another full run checked the same receipt and file hashes.
- Native account databases, tty and rc policy, host lookup, module policy,
  a user X resource and site configuration retained their recorded hashes.
  The repeat install also preserved the selected home `.xsession` and xdm service
  configuration. A 6.5.22f manifest paired with a 6.5.30f archive was rejected
  by the host media builder.
- On a stock system, the Xorg Newport driver name is a symlink to
  `newport_drv.so.0`. The installer backs up the link, retains the stock
  versioned file and publishes the pinned accelerated driver at the Xorg lookup
  path. The first graphical trials exposed a missing Toolchest menu file on
  both releases. The native profile now supplies the menu used by the session.
- Both disks halted cleanly before packaging. `chdman verify` passed on both
  CHDs, and each data SHA-1 matched its complete 8 GiB raw disk.

## Graphical qualification

Each CHD cold-booted in its own disposable overlay with the graphical PROM.
The Xorg log confirms Newport XAA acceleration. At xdm, xiritest entered
4Dwm at 1280×1024 with Toolchest, Icon Catalog, winterm and xclock. The
session recorded the expected home and working directory, winterm acquired a
native controlling PTY, and the original IRIX `/bin/sh` executed as xiritest.
After logout, netbsdtest entered stock ctwm with a mapped UXTerm. Ending that
session returned to xdm. Both guests recorded a clean unmount and halt.

| Release | Screenshots |
| --- | --- |
| IRIX 6.5.22f | [4Dwm](2026-11-23-clean-indy-6.5.22f-desktop.png) · [ctwm](2026-11-23-clean-indy-6.5.22f-ctwm.png) |
| IRIX 6.5.30f | [4Dwm](2026-11-23-clean-indy-6.5.30f-desktop.png) · [ctwm](2026-11-23-clean-indy-6.5.30f-ctwm.png) |

The native check matches the user's ctwm command line and queries the X
window tree for UXTerm. An earlier exact-name process check timed out while
the native desktop and terminal were visible. The full host suite passed
84 tests. [Qualification records and artifact hashes](2026-11-23-clean-indy-desktops.json)

The native package is retained in `.work/packages/netbsd-sgimips-indy-11.99.11-v1`.
The two local installer CDs and compressed qualification logs are in
`.work/installers/indy-11.99.11`. See the [install
instructions](../NATIVE-PACKAGE.md#clean-installation-on-an-emulated-indy) and
[reproduction commands](../../lab/native-package/README.md#bootstrapping-a-stock-target).
The subsequent [stock kernel round trip](2026-11-23-indy-kernel-rollback.md)
covers both Indy images. Physical Indy hardware, cross-version upgrades,
removal and recovery from a power cut during writes remain open.
