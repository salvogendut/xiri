# Indy microphone recording

On both emulated Indys, the ordinary `xiritest` user recorded a streamed
stereo signal with SGI’s original `sfrecord` and played the WAV with SGI’s
`sfplay`. Each vendor recording contained exactly 48,000 frames at 48 kHz.
During replay the emulator measured 440 Hz on the left and 880 Hz on the
right at the HAL2 speaker output, both at the injected amplitude of 12,000.
Native NetBSD `audiorecord` also captured the signal during native playback.

| Xiri donor release | Indy CPU | Native recording | Left | Right |
| --- | --- | --- | --- | --- |
| 6.5.22f | R4400 | 49,152 stereo frames at 48 kHz | 440 Hz | 880 Hz |
| 6.5.30f | R5000 | 49,152 stereo frames at 48 kHz | 440 Hz | 880 Hz |

Both channels measured 12,000 PCM units at their injected frequency. The
other channel's frequency measured zero to the nearest PCM unit in the
central 100 ms window. The fixture supplied signed little-endian 16-bit
stereo through a Unix FIFO. The playback and recording tracks completed
and both guests powered off. [Per-release measurements and artifact
digests](2026-11-27-indy-microphone.json)

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

## Reproduce on the lab Indys

Build the Indy kernel with `lab/ip28-kernel/build.sh` and the matching
module with `lab/ip28-kernel/build-module.sh`, using the same build directory.
Run once per release with a separate output directory. The checker installs
the candidate on a private overlay, saves the measurements, and removes the
overlay, its temporary CD and the test audio.

```sh
python3 lab/native-iso/check-haltwo-record.py \
  --bundle "$BUNDLE" --bootstrap "$BOOTSTRAP_IRIS_DIR" \
  --emulator "$CAPTURE_IRIS_DIR" --build "$BUILD_DIR" --output "$RESULT_DIR" \
  --donor "$IRIX_DONOR_CHD"
```

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
