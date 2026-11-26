# In-place Indy audio upgrade and rollback

The starting disks were the published Indy v6 CHDs with Mozilla enabled.
IRIX 6.5.22f used the R4400 and 6.5.30f used the R5000. Each ran in
Prismatic with a private writable overlay. The two update CDs were built
from their release's v6 and audio-v7 installers. Each changes 59 paths,
including the kernel, PROM boot wrapper, IRIX module and 43 additions to
the vendor payload. [Update and rollback instructions](../NATIVE-PACKAGE.md#upgrade-an-installed-indy-from-v6-to-audio-v7).

## What the guest checks cover

* Before the update, `xiritest` saved a private document and a solid backdrop
  in `~/.Sgiresources`. 6.5.22f used `#7d9ec0` and 6.5.30f used
  `#9ddb9d`. Each graphical login checked Icon Catalog, winterm and the
  active 4Dwm root-window backdrop property.
* The checksums cover the document, preferences, `.xsession`, native
  account and group databases, xdm configuration, Mozilla's installation
  plan and the existing executables in the IRIX bin, sbin and Mozilla
  directories. That inventory contains 200 files on 6.5.22f and 199 on
  6.5.30f.
* The upgrade deliberately encountered a local file at the proposed
  `sfplay` destination. It preserved the file and stopped before writing
  a transaction. A second test interrupted the installer after it recorded
  its plan and resumed it from the same CD.
* Each direction checks the four desktop receipts, Mozilla identity,
  on-disk kernel and module, changed files and links, then boots the
  selected kernel and checks `modstat`. Rollback also compares the three
  boot files and the desktop and Mozilla receipts with their original v6
  hashes.

## First-boot volume

The stock v6 Indys have an active HAL2 driver, an initial master level of
0,0 and mixer persistence disabled. Enabling persistence before the last
v6 shutdown originally saved that zero setting. The updater now defers the
first save until the audio-v7 HAL2 driver exposes the speaker mute control.
At first startup the mixer configuration becomes the same default installed
by the full audio-v7 CD. A locally supplied configuration keeps precedence.

The first login on each updated disk played SGI's `emptyDumpster.aiff`
using `sfplay` at 64,64. The Audio Panel Mute box drove both channels to
digital zero and restored playback when cleared. The screenshots show
the checked box and the user's restored backdrop.
[6.5.22f Audio Panel](2026-11-27-indy-audio-upgrade-6.5.22f.png) ·
[6.5.30f Audio Panel](2026-11-27-indy-audio-upgrade-6.5.30f.png).

After rollback, the tests saved a muted mixer at 80,96 on 6.5.22f and
96,112 on 6.5.30f. Reapplying the update preserved the checksum of
`/var/db/mixer0.conf` and restored those exact levels with mute on.
The SGI playback check then set both channels to 64 to compare the
output with the first upgrade.

| Release | First upgrade, waveform correlation | Reapplied, waveform correlation | Muted peak, L/R |
| --- | ---: | ---: | --- |
| 6.5.22f | 0.9987 | 0.9938 | 0 / 0 |
| 6.5.30f | 0.9972 | 0.9980 | 0 / 0 |

Each muted play captured 190,464 stereo frames at 48 kHz. The two
channels matched for this mono AIFF. The comparison uses the
[donor waveform checker](../../lab/irix-hdsp/playback/verify.py).
One interaction remains open. When Audio Panel started muted and the
native `mixerctl` command cleared mute while the panel was open, its
next click left the native mixer unmuted. Reopening the panel and using
its checkbox for both transitions passed on both releases.

Both rebuilds reproduced all 69 entries in their CD checksum lists.
The 106 host tests passed. The [per-release records](2026-11-27-indy-audio-upgrade.json)
include the original CHD and update CD hashes, both installed generations
and the PCM measurements.
