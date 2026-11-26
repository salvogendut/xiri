# Indy IRIX Audio Library playback

The NetBSD compatibility module exposes the shared playback queue used by
the original IRIX Audio Library. Each open has its own queue and native
HAL2 playback track. The SGI library expands mono into stereo. NetBSD
converts the selected track rate to the device's native rate and mixes the
output with other clients. A stream takes its rate when it acquires the
port. The supported IRIX output clock choices are 44.1 and 48 kHz.

## Build the private update

Use an Indy v6 desktop with the [HDSP update](../README.md), a matching
NetBSD source tree, and a private extraction from the selected donor.
Build the module once. Package each donor separately.

```sh
sh lab/ip28-kernel/build-module.sh ../NetBSD-xiri .work/netbsd-octane-build/tools ./pcm-build
sh lab/irix-hdsp/playback/package.sh 6.5.22f "$DONOR22" ./pcm-build/module/compat_irix_o32.kmod ./pcm-6.5.22f.iso
sh lab/irix-hdsp/playback/package.sh 6.5.30f "$DONOR30" ./pcm-build/module/compat_irix_o32.kmod ./pcm-6.5.30f.iso
```

| Donor source | NetBSD destination |
| --- | --- |
| `/usr/sbin/sfplay` | `/emul/irix/usr/sbin/sfplay` |
| `/usr/lib32/lib{audio,audiofile,awareaudio,dmedia,m,malloc,mutex}.so`, `libC.so.2`, `libCsup.so` | Same paths under `/emul/irix`. The installer checks existing files against the selected donor. |
| `/usr/lib32/dmedia/audioconverters/libaudioconvert.so` and `libaudiorateconv.so` | Same directory under `/emul/irix`. SGI opens these converters by absolute path during playback. |
| `/usr/share/data/sounds/soundscheme/soundfiles/emptyDumpster.aiff` | `example.aiff` on the private update CD |

The desktop provides the matching rld and libc. The update installs the
NetBSD module in the running kernel's module directory, the boot script
in `/etc/rc.d/xiri_pcm`, and the `hdsp0r2` link in `/emul/irix/dev/hdsp`.
The boot script creates the character device using the module's assigned
major. Capture and direct digital I/O are outside this playback implementation.

Attach the CD at SCSI ID 4 to a copy of the desktop. As root, mount it,
install the update and reboot. A matching CD can be applied again. Keep
the previous disk and its overlay together for rollback.

```sh
mkdir -p /cdrom
mount -rt cd9660 /dev/cd0a /cdrom
sh /cdrom/install.sh
shutdown -r now
```

After reboot, mount the CD again. In winterm as an ordinary user, play the
supplied sample or substitute another local sound file.

```sh
/emul/irix/usr/sbin/sfplay /../cdrom/example.aiff
```

## Repeat the waveform check

Generate the three-second stereo WAV on the host and make it available to
the guest on a second CD. Each second uses different frequencies in each
channel. This crosses the player's one-second queue boundary twice.

```sh
python3 lab/irix-hdsp/playback/verify.py generate stereo.wav
```

Start the matching Prismatic profile with SDL's disk audio driver as
described in the [desktop sound capture instructions](../../indy-desktop-sound/README.md#recheck-an-sdl-capture).
Capture each complete play plus the surrounding silence in a separate
48 kHz signed 16-bit little-endian stereo file. Use the original player
as `xiritest` and the [n32 HDSP probe](../README.md) for the gain settings.

| Capture | Input and master gain |
| --- | --- |
| `stereo.pcm` | Generated WAV, native mixer `outputs.master=128,128` |
| `effect.pcm` | Release CD's `example.aiff`, same gain |
| `muted.pcm` | Generated WAV after `hdsp-query --silence-test-gain`. Confirm native mixer reads `0,0`. |
| `restored.pcm` | Generated WAV after `hdsp-query --set-test-gain`. Confirm native mixer reads `64,128`. |

Restore the starting mixer setting. Check the captures with NumPy and FFmpeg.

```sh
python3 lab/irix-hdsp/playback/verify.py check /path/to/captures /path/to/example.aiff
```

The SGI manual describes application-side Audio Library ports and the use
of frame counts and fill points. [Digital Media Programming Guide, chapter 4](https://techpubs.jurassic.nl/library/manuals/1000/007-1799-060/sgi_html/ch04.html).

For the 48 kHz check, generate the same WAV with `--rate 48000` and save
that play as `native48.pcm`. Generate two more WAVs at 48 kHz, one with
`--channel 0` and the other with `--channel 1`. Start both original
players in the same shell in the background, wait for both, and capture
their combined output as `overlap.pcm`. Pass `--extra` to the checker to
test both captures.

## Measure the panel's Mute control during one play

On a disposable Indy, select **ControlPanels → audiopanel** in Icon Catalog.
Use the normal xdm user and start a continuous stereo WAV with the original
`sfplay`. The following command generates three minutes of 440 Hz on the
left and 730 Hz on the right.

```sh
python3 lab/irix-hdsp/playback/live.py generate tone.wav
```

Mount the WAV on a test CD. Before launching the player, set the two
channels to 64,128 with `hdsp-query --set-test-gain`. During playback,
click **Mute** under the two Analog Out sliders, then click it again.
Read `mixerctl outputs.master outputs.master.mute` at each step and verify
the same user's player PID remains alive. Capture a settled interval of
at least half a second of 48 kHz S16LE stereo SDL output in each state,
as `playing.pcm`, `muted.pcm` and `restored.pcm`. Check all three with:

```sh
python3 lab/irix-hdsp/playback/live.py check /path/to/captures
```

The checker requires digital zero throughout the muted interval, distinct
frequencies in the expected channels before and after mute, and restoration
of each channel's level to within five percent. The donor probe's
`--mute-test` also prints the original choices, reads gain while muted and
records the parameter-change event.
