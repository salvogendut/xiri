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
