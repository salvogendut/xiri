# Indy frontend and full Screen Saver installers

IRIS `xiri` at `46c116ee` incorporates upstream `d8cf7e91`. Prismatic
`910997e` adapts saved machine configurations to IRIS's device slots and
accepts its new framebuffer interface. The release binary uses
`pcap,idle-pause,jitv2`. Instigator was built separately at
`4acffdef6802`.

## Frontend verification

On private copies of the previous Screen Saver disks, both Indys accepted
an xdm login as `xiritest` and opened 4Dwm, Toolchest, Icon Catalog and
winterm. With the saved Qix preference, the test shortened the live
inactivity timeout from 600 to 60 seconds. Two Prismatic captures two
seconds apart showed moving lines. Space restored the desktop. The tester
opened **Toolchest → System → Shut Down System**, clicked **Shut Down** in
the confirmation dialog and observed the emulator's soft power-off.

| Guest | SGI `sfplay` left / right, measured at host | Changed Qix pixels in sampled area |
| --- | --- | ---: |
| 6.5.22f, R4400 Indy | 440.2 / 730.1 Hz | 40,626 |
| 6.5.30f, R5000 Indy | 440.2 / 730.1 Hz | 37,842 |

The IRIS device suite passed 3,575 tests (40 ignored). Prismatic passed
208 tests on the fork (7 ignored) and 175 on an isolated checkout of the
fork's `main` at `878bc6da` (5 ignored). Its two native Instigator BOOTP/TFTP
tests passed separately, as did formatting, Clippy, the SDL dummy display
and the diskless PROM framebuffer check.

## Full installer contents

The two release ISOs use one native package. Its installed files differ
from audio-v8 in two places. The Xorg extension module implements the SGI
screen saver protocol. The desktop session script starts the selected IRIX
saver on the next login. The package preserves a verified stock copy of the
Xorg module for rollback. Each ISO carries its donor's 16 saver files,
including xlock, its libraries and 11 presets. Each release rejected the
other release's saver CD during assembly.

## Clean installs and manual disks

A stock NetBSD 11.0/sgimips bootstrap installed the X sets and booted
the matching 11.99.11 kernel and module at securelevel 1. Each release
started on its own copy with no desktop or vendor tree. On the accelerated
IRIS packaging baseline (`0bc52567`), `install.sh --mozilla` succeeded twice
from the release's one CD. Both machines halted cleanly. Each CHD passed
`chdman verify` and matched its source raw disk's logical SHA-1.

Starting from the resulting CHDs, the test selected Qix in the original
ControlPanels app, ran Demo, woke the desktop, and observed idle activation.
After logging out to xdm and back in, the saved commands were byte-identical
and the timeout returned to 600 seconds. The test temporarily shortened it
to eight seconds and captured three frames. On both releases Space restored
the desktop and disabling the saver reset the timeout to zero.

| Release | Changed pixels between successive frames after relogin | Test launcher from the Xiri checkout |
| --- | --- | --- |
| 6.5.22f | 54,355 and 60,990 | `.work/prismatic-indy-saver-v9/6.5.22f/run-prismatic.sh` |
| 6.5.30f | 63,794 and 34,221 | `.work/prismatic-indy-saver-v9/6.5.30f/run-prismatic.sh` |

The final Prismatic executable cold-booted both new disks on separate overlays.
It captured audio at 439.8 / 729.8 Hz and 440.0 / 730.1 Hz respectively.
After inactivity, Qix changed 37,341 and 55,547 pixels between two frames.
Space restored 4Dwm and the original Toolchest menu powered off each guest.
[Toolchest confirmation on 6.5.22f](2026-11-27-indy-saver-v9-toolchest.png).

The private full ISOs, checksums and compact qualification archive are in
`.work/installers/indy-11.99.11/saver-v9/`. Each image directory contains its
own CHD, PROM state and checksums. The GUI tests used private overlays.
[Hashes and guest results](2026-11-27-indy-saver-install.json) ·
[Manual login](../XIRI-IMAGE.md#clean-indy-audio-images) ·
[Build the installer](../NATIVE-PACKAGE.md#build-a-full-indy-installer-with-screen-saver).
