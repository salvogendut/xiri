# Screen Saver on the audio-v8 Indy desktop

The original 6.5.22f and 6.5.30f audio-v8 images omitted the vendor's
`xlock`, its presets and the SGI `SCREEN-SAVER` extension for NetBSD Xorg.
The panel could enable the native X timeout, but the selected animation
had nothing to run. Installing the previous saver CD fixed Demo and idle
animation in the current session. After logging out and back in,
`panelsession.err` identified a second failure.

```text
/usr/bin/X11/xlock: not found
```

The panel had saved the correct command for IRIX. Xiri now translates its
executable to `/emul/irix/usr/bin/X11/xlock` when replaying that user's
settings. The original `~/.desktop-<hostname>/panelsession` keeps the
vendor paths. The release-specific repair CD installs the corrected
launcher, all 16 vendor files and the NetBSD Xorg extension.

## Try the repaired desktop

| IRIX release | Prismatic launcher, relative to the Xiri checkout | Qix after a fresh login |
| --- | --- | --- |
| 6.5.22f, R4400 Indy | `.work/prismatic-indy-saver-v8/6.5.22f/run-prismatic.sh` | [Screenshot](2026-11-27-indy-saver-6.5.22f.png) |
| 6.5.30f, R5000 Indy | `.work/prismatic-indy-saver-v8/6.5.30f/run-prismatic.sh` | [Screenshot](2026-11-27-indy-saver-6.5.30f.png) |

Press **Ctrl+P**, log in as `xiritest` (password `xiritest`), and open
**Icon Catalog → ControlPanels → screensaver**. Check **Screen Saver On**,
select **Qix**, leave **Lock Screen** off and click **Demo**. Press **Space**
to wake, then **Close**. Qix also starts on inactivity with the panel
closed. The initial delay is ten minutes. [Screen Saver panel](2026-11-27-indy-saver-panel.png).

To keep an existing audio-v8 machine and its overlay, use the repair CD
for the installed release. Each new launcher has its own base disk and
state directory. [In-place repair and rollback](../NATIVE-PACKAGE.md#add-screen-saver-to-an-audio-v8-indy).

## Verification

On a disposable copy of each original audio-v8 image, the test installed
the CD, restored the original launcher and Xorg module, then installed the
repair twice. From the actual Catalog panel it enabled Qix, ran Demo,
woke the desktop, and let Xorg's inactivity timer activate Qix. It then
logged out to xdm and back in as the same user. The saved commands matched
byte for byte and the X server restored the 600-second timeout. The test
temporarily shortened that timeout to eight seconds to measure animation.
In all three cases, three sampled frames showed moving lines and Space
restored the desktop. Disabling the saver set the timeout to zero.

Each delivered CHD was built separately from a clean audio-v8 base and
verified with `chdman verify` and the uncompressed disk SHA-1. Both
cold-booted in Prismatic to a visible xdm greeter, reported the SGI and
MIT saver extensions, listed 11 presets and completed guest soft power-off.
On another copy of each delivered CHD, Prismatic logged into 4Dwm with
the panel's saved Qix commands. The test shortened the live timeout to one
minute, left the desktop untouched and captured the animation with **F4**.
Two captures two seconds apart differed by 49,992 pixels on 6.5.22f and
51,201 on 6.5.30f within the sampled area. Pressing **Space** in the
Prismatic window restored the desktop on both. [Prismatic 6.5.22f capture](2026-11-27-indy-saver-prismatic.png).

Coverage is for unlocked Qix on emulated Indys. The other effects,
password locking and monitor power management await qualification.
[Hashes and measured frame differences](2026-11-27-indy-saver-repair.json) ·
[Build and regression commands](../../lab/sgi-saver/README.md#audio-v8-indy-repair).
