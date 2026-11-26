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

## Playback across Mozilla installation and removal

Both tests started from a copy of the published audio-v7 Indy disk and
its matching installer CD. At each stage, the ordinary `xiritest` account
played the installed `emptyDumpster.aiff` with the original SGI `sfplay`.
Prismatic captured both output channels as 48 kHz signed 16-bit PCM.
The comparison uses the loudest 512-frame passage of the donor AIFF and
the [playback checker](../../lab/irix-hdsp/playback/verify.py).

To repeat, play the file once on the base installation. Mount the matching
CD, run `sh /cdrom/install.sh --mozilla` as root, reboot and play the file
again. Mount the CD again, run `sh /cdrom/install.sh --remove-mozilla`,
reboot and repeat the play. The test checked the component receipt and
browser executable after each installer operation. It also checked the
kernel, PROM boot wrapper, IRIX module, HDSP startup scripts, player,
`libaudio`, desktop receipt and greeter configuration against their initial
SHA-256 hashes.

| Indy release | Base | After enabling Mozilla and rebooting | After removing Mozilla and rebooting |
| --- | ---: | ---: | ---: |
| 6.5.22f, waveform correlation | 0.9960 | 0.9977 | 0.9988 |
| 6.5.30f, waveform correlation | 0.9953 | 0.9970 | 0.9959 |

Left and right gave the same score for the mono source. Across all six
plays, the peak on each channel was between 4,168 and 4,180 counts.
Both desktops returned to xdm with the XiriBSD logo after each reboot.
At final shutdown both serial logs reached the end of the shutdown hooks
and both Prismatic logs recorded `Machine: soft power-off`.
These checks cover the audio-v7 component lifecycle. An in-place desktop
upgrade from v6 to the audio-v7 base remains a separate qualification.
