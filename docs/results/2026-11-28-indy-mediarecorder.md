# SGI Media Recorder and the Indy desktop microphone

Double-clicking the microphone as `xiritest` starts the original Media
Recorder on both Xiri Indys. It aborts before displaying its window or saving
audio. Repeating the icon's command from winterm returned status 134 on both
releases. The GUI left a `mediarecorder.core` in the user's home on each
disposable disk.

| System | Microphone action |
| --- | --- |
| Original IRIX 6.5.22f, Indy R4400 | Media Recorder opens with **Audio**, **Microphone** and **General** selected. Record followed by Stop saves `audio1.aiff` in the displayed directory. |
| Xiri with 6.5.22f, Indy R4400 | No window. The audio launch reports a shared arena failure, followed by the queue assertion in `events.c` at line 580. |
| Xiri with 6.5.30f, Indy R5000 | Same failure before recording starts. |

On the original graphical reference, the desktop user was root and the
displayed destination was `/`. We supplied 440 Hz on the left and 880 Hz on
the right at the recorder's 44.1 kHz setting. Stop saved a 184,534-frame
AIFF (4.18 seconds). The default mono microphone copied the left channel to
both channels of the file. Replaying that file
with the vendor's `sfplay` reproduced the tone at the emulated HAL2 output.
[Saved take on original IRIX](2026-11-28-mediarecorder-original-irix.png) ·
[Measurements, releases and disk checksums](2026-11-28-indy-mediarecorder.json)

## Where Xiri stops

The message about available disk or swap space comes from libmovierecord.
Both Xiri traces show that the allocator successfully creates and locks its scratch
file in `/var/tmp`, allocates 5,232 bytes and maps 66,672 bytes with
`MAP_SHARED | MAP_AUTOGROW`. The first failing operation is a signal-mask
query. SGI libc asks the kernel to write the old mask at offset 9,536
(`0x2540`) in that mapping. Xiri returns `EINVAL`, unmaps the region and
removes the file. This happens before opening an audio input port.

A freestanding n32 program compared three destinations for that same
`sigprocmask(SIG_NOP, NULL, oldset)` call. It measured the backing file with
`lseek` before and after each access. The original 6.5.22f reference ran on
an Indy and the original 6.5.30f reference on an O2. Both Xiri tests ran on
Indys with NetBSD `51ae5f2886e` and IRIS `65039d90`.

| Destination | Both original IRIX releases | Both Xiri releases |
| --- | --- | --- |
| Stack and a mapped offset inside the file | Success, file stays at 5,232 bytes | Same |
| Untouched mapped page beyond EOF | Success, file grows to 12,288 bytes | `EINVAL`, file stays at 5,232 bytes |
| Same address after a user-mode store | Success, file is 12,288 bytes | Success, file grows to 16,384 bytes on the user store |

The page sizes are 4 KiB on original IRIX and 8 KiB on the tested NetBSD
kernels. The next compatibility change is to handle a kernel write to an
untouched autogrow page. The original application trace goes on to
`msync(MS_INVALIDATE)` and opens the pollable semaphore device
`/dev/usemaclone`. The standalone check found that device on both original
systems and got `ENOENT` on both Xiri systems. The failing Xiri application
has yet to reach either operation. For recording and replay on the current
Indy images, Sound Editor already passes both checks.
[Shared-file growth](2026-11-27-indy-autogrow.md) ·
[Sound Editor record and replay](2026-11-27-indy-soundeditor.md)

## Repeat the comparison

On a disposable desktop with the matching kernel and module, double-click
the microphone. For the diagnostic output, run the same launch from winterm:

```sh
/emul/irix/usr/sbin/mediarecorder -media audio -jack Microphone
```

To repeat the memory check, build the [probe](../../lab/irix-mmap-shared/recorder-arena.c)
on the host and copy the resulting executable to each guest:

```sh
sh lab/irix-mmap-shared/build-recorder-arena.sh \
    .work/netbsd-octane-build/tools/bin/mips64--netbsd recorder-arena
```

In a fresh writable directory on the guest, run the commands below.
The nine big-endian words are the `MREC` identifier, stack and in-file
query results, initial size, past-EOF query result and size, post-store
query result and size, and the result of opening the semaphore device.
Negative values are errno numbers with the sign reversed.

```sh
dd if=/dev/zero of=arena bs=5232 count=1
/path/to/recorder-arena arena > record
od -A n -t d4 record
```
