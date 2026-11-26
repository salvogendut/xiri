# Indy Display and desktop sound effects

The two IRIX desktops run on the same NetBSD 11.99.11 Indy kernel and
matching IRIX module. Each private update uses that release's own SGI
resources. Both updates installed twice on separate power-menu disk copies.
The previous images remain available for comparison.

## Display

The unmodified SGI Display application probes the SGI-VIDEO-CONTROL X
extension during startup. A native 6.5.22f Indy supplied the wire replies
for screen, channel, format and gamma queries. Its Xsgi screen ran at
1280×1024 at 60 Hz. Xiri's Xorg extension reads the current Newport modeline
from the server and enumerates one active format. The panel also reads the
RGB gamma ramp and sends gamma writes as it initializes.

On **both releases**, double-clicking Display in Icon Catalog opened
**Graphics Back End Control**. It showed **1280×1024_75**, **75.03 Hz**
and a **135.00 MHz** pixel clock. The panel stayed open through page
changes and closed on Ctrl+Q. RandR reported the same active mode
before and after. Changing resolution or refresh rate remains a separate
qualification. [6.5.22f screenshot](2026-11-26-indy-display-6.5.22f.png) ·
[6.5.30f screenshot](2026-11-26-indy-display-6.5.30f.png).

## Audio

A per-session native client owns the original SoundScheme X selection.
The vendor's `ssplay` sends a named event, a level in millionths, or a mute
request. The client plays the selected donor sample through NetBSD’s
`/dev/audio`. Each release's default scheme supplied 70 names and 37
distinct audio files. General IRIX applications using the mapped HDSP
ring, including `sfplay`, and the separate IRIX system-wide master mute
are still open.

Prismatic’s first SDL capture exposed a sample-layout error. The previous
build peaked at 53 on a signed 16-bit scale and lost the expected change
when SoundScheme volume was halved. NetBSD’s haltwo driver programs HPC3
channel zero with 0x08208844 and sends consecutive signed halfwords.
Reading both samples exposed a second failure. Without the channel-zero
descriptor interrupt, NetBSD timed out draining audio and the emulated
device repeatedly read the same DMA ring. The playback channel now raises
IOC Local 1 bit 4 at descriptor completion and clears it when NetBSD reads
the channel control register. The regression checks both signed samples
and interrupt acknowledgement. A separate test covers the word-strided
PROM convention.
[Linux HAL2 driver](https://raw.githubusercontent.com/torvalds/linux/master/sound/mips/hal2.c).


### What reached Prismatic

Both sessions cold-booted through xdm as `xiritest` with HAL2 master
at 128,128. The SDL disk driver captured the actual frontend output at
48 kHz in stereo. The rows give absolute peak amplitudes in signed
16-bit PCM for the same original `ssplay EmptyDumpster` request.

| Setting | 6.5.22f | 6.5.30f |
| --- | ---: | ---: |
| Both volume controls at full | 5,984 | 5,982 |
| SGI SoundScheme at 50% | 2,964 | 2,992 |
| Prismatic F9 volume at 50% | 2,982 | 2,973 |
| SGI scheme muted | 0 | 0 |
| Prismatic muted | 0 | 0 |
| Native HAL2 master at zero | 0 | 0 |
| Native master restored to 128,128 | 5,982 | 5,956 |

A double-click on the **xiritest home folder** opened the original File
Manager and played the donor's `OpenFolder` effect on each release.
Running the original Empty Dumpster action on a single test file removed
it and played the scheme's `Remove` effect. Each match compared a loud
512-frame passage of the donor with both channels of the SDL output.
The lowest correlation across these two desktop actions was 0.9928.
The guest reported no audio-drain timeouts during the corrected run.
[6.5.22f measurements](2026-11-26-indy-display-sound-6.5.22f.json) ·
[6.5.30f measurements](2026-11-26-indy-display-sound-6.5.30f.json).

## Images and update media

From Xiri, choose the [Prismatic launcher for your release](../XIRI-IMAGE.md#indy-display-and-desktop-sounds).
Both use Prismatic `63b6cc8` and a private build of its matching IRIS core
at `707912dd` with IRIS commits `1b4b140e` and `7c713c13`. The frontend
SHA-256 is `15b501f37e8a5fab34b00e4f41658812ccb77f43bf799b7562005ddd473cffcb`.
The original base CHDs and earlier qualified power-menu copies remain available. The NetBSD kernel and IRIX
module are the same as on those power-menu copies.

| Private CD under `.work/installers/indy-11.99.11/desktop-display-sound-v1/` | SHA-256 |
| --- | --- |
| `6.5.22f.iso` | `0863ead10580013a37e0bb66da4a82826cd596e6c9c9da90d6a04088e89bda64` |
| `6.5.30f.iso` | `517c63d2813c2ebf918cb06d519ac5639309cc12bfb1dcda8a52c3cd74ccc365` |

[Donor paths, native build and update procedure](../../lab/indy-desktop-sound/README.md).
