# Indy MediaTools and their devices

These checks cover the emulated Indy. On the prepared 6.5.22f and 6.5.30f
desktops the original applications live in `/usr/sbin` under the IRIX
emulation root. The qualification target for each device is a visible or
audible result that can also be checked from the saved media.

| Device | Application | What will count as working |
| --- | --- | --- |
| Microphone / line input | Sound Editor (`soundeditor`) | Record an injected tone, save the clip, find the tone in its PCM samples and play it back. |
| Indy video input | Video In, Video Panel, Media Recorder | Preview the emulated moving test pattern and save frames with the expected colours and motion. Test a live camera separately. |
| CD-ROM / audio CD | `cdman`, `cdplayer` | Read a known file from a data CD. On audio media, list actual tracks, select one, play it and observe the expected sound. |
| DAT | `datman`, `datplayer` | Detect a sequential-access drive, write a known signal to scratch media, rewind and play it back. |

## Results on the two prepared desktops

The R4400 ran 6.5.22f and the R5000 ran 6.5.30f. Both used the qualified
IRIS binary at `0bc52567`, with HAL2 enabled, null host audio output,
the VINO moving test pattern and a read-only data CD at SCSI ID 4.
Each original application ran from the logged-in user's winterm. The
test sampled named X windows after five seconds and kept forked clients
alive through the observation. All 16 launches completed process cleanup.
[Guest measurements and launch logs](2026-11-27-indy-media-devices.json)

| Application | 6.5.22f | 6.5.30f |
| --- | --- | --- |
| Sound Editor | Could not get input sample rate | Same |
| Video In | Video Library failed to allocate a resource or memory | Reported `error opening video: InternAtom` |
| Video Panel | Two 1×1 `vcp` windows | Also created a 317×109 information dialog |
| Media Recorder | Shared arena creation failed, then the queue assertion aborted the process | Same |
| CD Manager and CD Player | Both terminated with a floating-point exception | Same |
| DAT Manager | Launcher exited successfully, no named window at the sample | Same |
| DAT Player | Terminated with a floating-point exception | Same |

Native NetBSD on both guests identified HAL2 and reported 16-bit stereo
playback at 48 kHz, with recording unavailable. `audiorecord` failed to
open the recording device. `xiritest` could read and verify
the file on the mounted data CD. Native `cdplay info` failed to read table
of contents entries with `EBADF` both as `xiritest` in `operator` and as
root. Resolve that native query before testing audio-track playback.
No tape drive attached, and native `mt status` reported “Device not
configured”. Real microphone and camera capture, audio CDs and tape
playback remain unqualified.

Repeat a run with `python3 lab/native-iso/check-media-devices.py --bundle BUNDLE --emulator EMULATOR_DIR --output NEW_DIRECTORY`.
The checker deletes its private disk, overlay and CD after power-off and
keeps the results in `NEW_DIRECTORY/result.json`.

The subsequent [Indy microphone check](2026-11-27-indy-microphone.md) covers
native and SGI microphone recording on an updated kernel and emulator.

## Where the device paths stop

* **Audio capture.** The native Indy HAL2 driver advertises playback.
  Its recording entry point leaves ADC DMA disabled and returns `ENXIO`.
  Xiri's HDSP handler returns `AL_NULL_RESOURCE` for the default input.
  At the other end, the emulator feeds zeros to codec B. Start by passing
  a synthetic tone through native NetBSD recording, then expose that same
  input to IRIX Audio Library clients. [NetBSD HAL2](https://github.com/salvogendut/NetBSD-xiri/blob/058c861ad699d2380b735911e87fd5114fe6e9df/sys/arch/sgimips/hpc/haltwo.c#L686) · [Xiri HDSP](https://github.com/salvogendut/NetBSD-xiri/blob/058c861ad699d2380b735911e87fd5114fe6e9df/sys/compat/irix_o32/irix_hdsp.c#L383) · [IRIS codec B](https://github.com/salvogendut/iris/blob/854d12c4d3900a9f99f8062fd40d4d444ff14d11/src/dev/hal2.rs#L614)
* **Video input.** IRIS supplies a moving pattern and a host camera source
  for the Indy VINO capture device. The sgimips source tree lacks a VINO
  capture driver. The pattern gives us a repeatable source for developing
  the native capture path and checking the vendor Video Library.
  [IRIS video sources](https://github.com/salvogendut/iris/blob/854d12c4d3900a9f99f8062fd40d4d444ff14d11/src/video_source.rs) · [NetBSD sgimips](https://github.com/salvogendut/NetBSD-xiri/tree/058c861ad699d2380b735911e87fd5114fe6e9df/sys/arch/sgimips)
* **CD audio and DAT.** IRIS builds its CD table of contents with one data
  track and a lead-out. A mixed-mode or audio-only fixture therefore needs
  emulator work before its track list can be qualified. The same SCSI
  implementation models disk and CD-ROM targets. A tape target and a
  scratch tape image are prerequisites for the DAT transport checks.
  [CD table of contents](https://github.com/salvogendut/iris/blob/854d12c4d3900a9f99f8062fd40d4d444ff14d11/src/scsi.rs#L1083) · [SCSI targets](https://github.com/salvogendut/iris/blob/854d12c4d3900a9f99f8062fd40d4d444ff14d11/src/scsi.rs#L124)
