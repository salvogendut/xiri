# Indy Audio Panel mute and fresh audio installations

Both release-matched installers booted from a stock NetBSD 11.0/sgimips
installation with the shared 11.99.11 Indy kernel and IRIX module. On the
first graphical login, `xiritest` could play the installed SGI AIFF using
`sfplay` and the named `EmptyDumpster` effect using `ssplay`. The two
installations used separate donor payloads, CDs, disks and writable test
overlays. Each installer recovered from an interrupted run, preserved an
administrator's conflicting file and passed a repeat installation. Both
halted raw disk images matched the CHDs' uncompressed SHA-1 digests.
[Media, disk and guest records](2026-11-26-indy-audio-installer.json).

## Audio Panel on a playing Indy

In a graphical Prismatic session, the test logged in through xdm, opened
ControlPanels in Icon Catalog and double-clicked the original Audio Panel.
A single original `sfplay` process ran as `xiritest` across both mouse clicks.
The source was a continuous 48 kHz WAV with a 440 Hz left channel and a
730 Hz right channel. With the mixer at 64,128, the following peaks reached
Prismatic's 16-bit stereo SDL output.

| IRIX release | Before mute, L/R | Muted, L/R | Muted stereo frames | After unmute, L/R | Same player PID |
| --- | --- | --- | ---: | --- | ---: |
| 6.5.22f | 4016 / 8031 | 0 / 0 | 53,248 | 4016 / 8031 | 721 |
| 6.5.30f | 4016 / 8031 | 0 / 0 | 53,248 | 4016 / 8031 | 722 |

Both sliders remained at 64,128. The HAL2 mute control went from off to on
and back to off. The restored channel frequencies measured 440 and 730 Hz.
The PNGs show the checked Mute box during playback.
[6.5.22f screenshot](2026-11-26-indy-audio-mute-6.5.22f.png) ·
[6.5.30f screenshot](2026-11-26-indy-audio-mute-6.5.30f.png) ·
[Repeat the measurement](../../lab/irix-hdsp/playback/README.md#measure-the-panels-mute-control-during-one-play).

## Hardware and installer changes

The original 6.5.22f Indy (A2) and 6.5.30f O2 (A3) donors both accepted
0 and 1 for `AL_MUTE`. Both retained mute across a direct `AL_GAIN` write.
Their scalar mute-change events carried the new setting. On both Xiri
Indys, NetBSD-xiri commit `b4aaf854968` exposes the HAL2 codec mute bit as
`outputs.master.mute`. The IRIX module maps the output and speaker resource
queries, writes and subscriptions to that control.

The native package owns the HDSP startup scripts and device links. The
release-specific vendor payload supplies the player, its audio libraries
and converters, the AIFF and the default desktop sound effects. The first
startup selected 64,64 on both clean installations. The test recorded peak
counts of 4159 and 4117 for the SGI AIFF and 2990 and 2984 for the named
effect on 6.5.22f and 6.5.30f respectively.
[Installation and local media build](../NATIVE-PACKAGE.md#fresh-indy-installation-with-hal2-audio).

The desktop qualification used the base install on each CD. The optional
Mozilla component was packaged on both CDs. Its install/remove cycle and
an in-place upgrade from a previous Indy image were outside this run.
