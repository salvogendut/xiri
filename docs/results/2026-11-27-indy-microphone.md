# Indy microphone recording

On both emulated Indys, the ordinary `xiritest` user recorded a one-second
WAV with SGI’s `sfrecord` and played it with SGI’s `sfplay`. The input
stream contained a 440 Hz tone on the left and an 880 Hz tone on the right.

| Recording or replay | 6.5.22f, R4400 | 6.5.30f, R5000 |
| --- | --- | --- |
| Native `audiorecord` during simultaneous playback | 49,152 frames, 440 Hz left / 880 Hz right | Same |
| SGI `sfrecord`, default mono microphone | 48,000 frames, 440 Hz in both channels | Same |
| SGI `sfrecord`, stereo microphone selected | 48,000 frames, 440 Hz left / 880 Hz right | Same |
| SGI `sfplay` replay of the stereo recording | Both tones measured at HAL2 speaker output | Same |

All checks used 16-bit stereo at 48 kHz. Each expected tone measured
12,000 PCM units, the injected amplitude. The other frequency rounded to
zero in the middle 100 ms window. The fixture streamed through a Unix FIFO.
[Per-release measurements and artifact digests](2026-11-27-indy-microphone.json)

The NetBSD HAL2 driver routes the microphone to codec B, assigns it its own
clock, PBUS DMA channel and descriptors, and services its interrupts alongside
playback. IRIS accepts an optional PCM source for codec B. The default input
is silence. [NetBSD driver](https://github.com/salvogendut/NetBSD-xiri/commit/59ed2e1d479)
· [IRIS PCM source and DMA](https://github.com/salvogendut/iris/commit/befb3a66)

The original IRIX Indy identified its default input as `A2.AnalogIn`, selected
`A2.Microphone`, and returned both a 48 kHz input rate and an input-present
value of one. The compatibility module exposes this input and transfers native
HAL2 samples into the SGI Audio Library input ring. The donor-matched conversion
libraries and command-line clients come from the installed IRIX disk. The test
installed them twice and checked the device aliases after a cold boot.
[NetBSD IRIX audio input](https://github.com/salvogendut/NetBSD-xiri/commit/8e78bdf18a2)

## Microphone on the 4Dwm desktop

On the original 6.5.22f Indy, the login script runs `genDeviceIcons` against
`/var/X11/xdm/DefaultDeviceList` and passes its output to `bgicons`. The
Indy's HAL2 revision 4.1.0 produces the following microphone record.

```text
1:ImdDeviceModel:C%3a10 T%3a3 S%3a16400 ftr%3amicrophone!o=
```

Xiri's IRIX hardware inventory currently reports memory only. At login, the
Xiri desktop reads NetBSD's `audiocfg list` and supplies this record to SGI's
`bgicons` when a HAL2 device reports a recording format. Each user's host
icon directory has its own `XiriMicrophoneDB`. A failed inventory query
leaves the last successful result in place.
[Desktop session script](../../runtime/libexec/desktop-clients.sh)

On both emulated Indys, `xiritest` saw the SGI microphone below the
Dumpster after xdm login. A second login kept one icon. Feeding the
installed login code a playback-only HAL2 inventory plus a different
recording device removed the microphone. Restoring the real inventory brought
it back. [6.5.22f screenshot](2026-11-27-indy-microphone-icon-6.5.22f.png)
· [6.5.30f screenshot](2026-11-27-indy-microphone-icon-6.5.30f.png)

Tracing a double-click on each release confirmed that the SGI icon started
`mediarecorder`. Running the same `-media audio -jack Microphone` action
from a shell showed that `libmovierecord` failed to create a shared
arena, asserted in `events.c` at line 580, and exited with status 134 before
opening a recorder window. The command-line recording results above apply
independently. [MediaTools results](2026-11-27-indy-media-devices.md)

To apply just this desktop change to a guest already running the recording
kernel, install the updated script as root and log back in as the desktop user.

```sh
install -m 555 desktop-clients.sh /usr/local/libexec/xiri/desktop-clients.sh
```

## Sound Editor comparison

The subsequent [Sound Editor qualification](2026-11-27-indy-soundeditor.md)
covers the recording worker, the saved AIFF and playback on both Xiri Indys.

On a private copy of the original-media 6.5.22f Indy, Sound Editor opens
a 700×500 “SoundEditor: Untitled” window. Its Record and Stop buttons
captured a four-second clip at 48 kHz and File → Save As produced a
two-channel, 16-bit AIFF with 191,040 frames. In a 100 ms window its
440 Hz component measured 12,000 in both channels, and the 880 Hz component
rounded to zero. The comparison exposed a lost byte in the emulator’s
word-strided ADC data and verified the correction in the saved file.
[IRIS correction](https://github.com/salvogendut/iris/commit/1a4844c6)

An SGI `par` trace also shows a successful shared
file mapping with `MAP_AUTOGROW`.
[Sound Editor recording on original IRIX](2026-11-27-soundeditor-original-irix.png)

The original donor defaults to the Indy’s mono microphone, which copies the
left input to both channels of a stereo file. Setting the `A2.Microphone`
channel count to two on the original Indy produced independent 440 Hz and
880 Hz tones in the file recorded by SGI’s `sfrecord`. Restoring the
channel count to one succeeded. XiriBSD implements the same control. The
Audio Panel preference dialog still needs an interactive check.
[NetBSD microphone modes](https://github.com/salvogendut/NetBSD-xiri/commit/0ff9181c3d7) ·
[SGI Audio Panel guide](https://techpubs.jurassic.nl/library/manuals/2000/007-2275-008/sgi_html/apb.html)

On the microphone build, both vendor releases passed the input-rate query and the
`F_ALLOCSP` scratch-file operation. Both then requested a writable 64 KiB
shared mapping with `MAP_AUTOGROW`. That module returned `EINVAL`, and the editor
removed its scratch file and exited before opening a window. A private
experiment allowing mappings within an already allocated file also failed
at this call.
The original IRIX reference previously showed that even a *read* past EOF
can grow the file, while creating the mapping leaves its length alone.
[File-mapping reference checks](../../lab/irix-mmap-shared/README.md) ·
[SGI shared arena documentation](https://techpubs.jurassic.nl/library/manuals/2000/007-2478-008/sgi_html/ch03.html)

The scratch-file probes exercise IRIX `F_ALLOCSP` and `F_FREESP` with
offsets relative to the start, current position and end. They grow a new
file to 65,536 bytes, shrink it to 64,512 bytes and then one byte, and
check that a read-only descriptor rejects resizing. The same n32 and o32
probes passed on original IRIX 6.5.22f on the Indy and 6.5.30f on the O2,
and on both XiriBSD Indys. Use a fresh filename
when running either probe. [NetBSD scratch-file operations](https://github.com/salvogendut/NetBSD-xiri/commit/176ffc8ff5d) · [SGI fcntl(2)](https://help.graphica.com.au/irix-6.5.30/man/2/fcntl)

The subsequent [shared-file mapping check](2026-11-27-indy-autogrow.md)
records the new kernel behavior and the SGI application results.

## Reproduce on the lab Indys

Build the Indy kernel, matching module and scratch-file probes with the
NetBSD sgimips cross-toolchain. The fourth argument to the kernel build
selects the Indy configuration.

```sh
sh lab/ip28-kernel/build.sh ../NetBSD-xiri "$TOOLDIR" "$BUILD_DIR" "$PWD/lab/irix-module/XIRI_IRIX_MODULE"
sh lab/ip28-kernel/build-module.sh ../NetBSD-xiri "$TOOLDIR" "$BUILD_DIR"
sh lab/irix-hdsp/build.sh "$TOOLDIR/bin/mips64--netbsd" "$PROBES"
```

Run once per release with a separate output directory. The checker installs
the candidate on a private overlay, saves the measurements, and removes the
overlay, its temporary CD and the test audio.

```sh
python3 lab/native-iso/check-haltwo-record.py \
  --bundle "$BUNDLE" --bootstrap "$BOOTSTRAP_IRIS_DIR" \
  --emulator "$CAPTURE_IRIS_DIR" --build "$BUILD_DIR" --output "$RESULT_DIR" \
  --donor "$IRIX_DONOR_CHD" --probes "$PROBES"
```

The retained workstation build has `iris` and `iris-ci` under
`.work/emulators/iris-xiri-1a4844c6/accelerated`, and the Indy kernel and
matching module under `.work/builds/indy-microphone-20261127`. These tests
used private overlays of the November 27 desktop CHDs.

For a live microphone on a Linux workstation with PulseAudio or PipeWire's
PulseAudio service, create a FIFO in a private directory. Set `input_file`
in the Indy emulator's existing `[audio]` section to its absolute path,
enable audio for the machine, and start the writer when ready to record.
Choose the guest ADC rate for the producer. The measurements above used
synthetic samples. Physical microphone levels and latency remain unmeasured.

```sh
micdir=$(mktemp -d)
mkfifo "$micdir/indy-mic.pcm"
echo "$micdir/indy-mic.pcm"
parec --raw --format=s16le --rate=48000 --channels=2 > "$micdir/indy-mic.pcm"
```

On a guest running the capture kernel, record with
`audiorecord -e slinear_le -P 16 -s 48000 -c 2 -t 5 mic.wav`.
The writer may exit when the guest closes the FIFO. Start it again for
the next take.

With a matching donor prepared by the updated `xiriprep`, the same take
can be made from winterm with the original SGI programs.

```sh
/emul/irix/usr/sbin/sfrecord -channels 2 -width 16 -rate 48000 -time 5 -fileformat wave mic.wav
/emul/irix/usr/sbin/sfplay mic.wav
```
