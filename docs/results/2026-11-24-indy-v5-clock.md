# Indy v5 desktops with SGI Clock

Run one command from the Xiri repository. Each bundle uses its own writable
overlay. At xdm, the test password matches the account name. Log in as
`xiritest` for 4Dwm or `netbsdtest` for ctwm.

| IRIX userland | Indy | Launch command | SGI Clock |
| --- | --- | --- | --- |
| 6.5.22f | R4400, Newport, 256 MiB | `.work/images/xiri-clean-indy-6.5.22f-v5-20261124/run-iris.sh` | [Screenshot](2026-11-24-indy-v5-clock-6.5.22f.png) |
| 6.5.30f | R5000, shadow cache, Newport, 256 MiB | `.work/images/xiri-clean-indy-6.5.30f-v5-20261124/run-iris.sh` | [Screenshot](2026-11-24-indy-v5-clock-6.5.30f.png) |

Open **Icon Catalog → DesktopTools → clock** or run
`/emul/irix/usr/sbin/clock` in winterm. The ordinary session also starts
`xclock`. The SGI application owns a separate window with X class `Clock`.

## Installation and upgrade

Both CDs use the rebuilt sgimips Xorg and GLX module and the existing v4
kernel, Xiri module and accelerated Newport driver. The vendor payload for
each release combines its verified donor import with its own Overlay 1
font map and three Iris bitmap fonts. The host generates and verifies
their index. Rebuilding each ISO reproduced every file listed in its
checksum table. [Display fix](2026-11-24-indy-glx.md) ·
[Package and upgrade commands](../NATIVE-PACKAGE.md#clean-installation-on-an-emulated-indy)

The install tests started with a fresh copy of the stock-to-modular NetBSD
bootstrap. Each installer resumed following interruption and an administrator
file conflict, then passed repeat installation. The image builder checked
each halted disk against its CHD data hash. Cold boot with the installer CD
detached reached full-screen 4Dwm and native ctwm through xdm. The original
SGI Clock mapped under `xiritest`; equal-sized window dumps taken three
seconds apart had different checksums. Both users logged out to the greeter.

The upgrade tests used private copies of the published v4 CHDs. Both
updaters refused to replace a running display server. After xdm stopped,
each updater installed the new pair and fonts, accepted a second run, then
restored the original v4 receipt, display files and modes on rollback.
The tests verified that the password database, xdm settings and user
preferences retained their contents. The R5000 test also covered an older
installation without the created-file ledger.

The separate Background colour chooser still uses its X11 path on these
256 MiB Indys. The GL colour chooser exhausted guest memory in the earlier
rendering tests. [Memory measurements](2026-11-24-indy-glx.md)

The release-specific CDs and guest logs are in
`.work/installers/indy-11.99.11/glx-v5/`. The record includes the CHD
hashes, package receipts, mode-checked rollback and Clock samples.
[Qualification record](2026-11-24-indy-v5-clock.json)
