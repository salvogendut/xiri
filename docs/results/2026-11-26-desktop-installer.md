# Installing a game from the IRIX desktop

On the v6 Indy, the original **DesktopTools → SoftwareManager** icon opens a NetBSD authentication terminal. The installed Toolchest resource names the same executable in **System → Software Manager**. Once an administrator authenticates and selects a mounted distribution, SGI Software Manager 4.1 opens on the user's display. It installs under `/emul/irix` and records the selection in the SGI installation history.

The graphical qualification starts with the clean v6 disk for each release, initializes the original SGI history from its matching Foundation and overlay media and registers the desktop entry twice. It uses a real Catalog double-click as `xiritest`, authorizes with the development `netbsdtest` wheel account, selects `fw_xmahjongg` from the complete May 2004 Freeware CD 4, and uses **Customize Installation → Start**. A new login tests the game's Freeware icon. Software Manager then removes the game through the same authorization route.

The preservation checks compare the original desktop filetype table, vendor installer, Mozilla executable and user's session selection byte for byte. All 94 non-Freeware Catalog links on 6.5.22f and all 82 on 6.5.30f matched their starting state. Both desktops retained the Freeware release notes and reopened the local Mozilla welcome page from Applications. Both guests returned to xdm and halted cleanly. These checks cover xmahjongg; individual Freeware products can have additional library and device requirements.

| IRIX release | Software Manager | Game launched from Freeware | Surviving Applications entry |
| --- | --- | --- | --- |
| 6.5.22f, R4400 | [Install selection](2026-11-26-desktop-installer-6.5.22f-install-selection.png) | [xmahjongg](2026-11-26-desktop-installer-6.5.22f-game.png) | [Mozilla](2026-11-26-desktop-installer-6.5.22f-preserved-browser.png) |
| 6.5.30f, R5000 | [Install selection](2026-11-26-desktop-installer-6.5.30f-install-selection.png) | [xmahjongg](2026-11-26-desktop-installer-6.5.30f-game.png) | [Mozilla](2026-11-26-desktop-installer-6.5.30f-preserved-browser.png) |

[Manual setup and authorization](../../lab/irix-installer/README.md#open-software-manager-from-the-indy-desktop) · [Release-specific hashes, history and preserved links](2026-11-26-desktop-installer.json) · [Graphical test](../../lab/native-package/check-desktop-installer.py).
