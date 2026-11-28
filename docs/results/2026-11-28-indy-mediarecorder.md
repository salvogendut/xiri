# SGI Media Recorder and the Indy desktop microphone

On the Xiri Indy with 6.5.22f, double-clicking the microphone opens SGI
Media Recorder and the user can save a take. On 6.5.30f, the same action
opens a dialog asking for graphics overlay planes. Both releases pass the
shared-file operation that previously aborted the program. [Desktop retest](#desktop-retest)

## Original comparison and failure

Before the fix, repeating the icon's command from winterm returned status
134 on both releases. The GUI left a `mediarecorder.core` in the user's
home on each disposable disk.

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

## Diagnosing the original abort

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
kernels. The original application trace goes on to
`msync(MS_INVALIDATE)` and opens the pollable semaphore device
`/dev/usemaclone`. The standalone check found that device on both original
systems and got `ENOENT` on both Xiri systems before the fix.
[Shared-file growth](2026-11-27-indy-autogrow.md) ·
[Sound Editor record and replay](2026-11-27-indy-soundeditor.md)

## Desktop retest

Both tests used the Indy Newport Xorg desktop, an xdm login as `xiritest`,
and NetBSD module `b187ffa60fd6`. Each test started by double-clicking the
microphone in the user's desktop.

| IRIX donor on Xiri | Result |
| --- | --- |
| 6.5.22f, Indy R4400 | The recorder opens with Audio and Microphone selected. Record followed by Stop creates `/usr/people/xiritest/audio1.aiff` and adds it to the recorder's list. [Saved take](2026-11-28-mediarecorder-xiri-6.5.22f.png) |
| 6.5.30f, Indy R5000 | The application displays a fatal dialog saying overlay planes are unavailable. Starting it in winterm with `-media audio -jack Microphone -allowmenu audio` gives the same dialog. [Audio-only launch](2026-11-28-mediarecorder-xiri-6.5.30f.png) |

The 6.5.22f take contains 163,735 stereo frames at 44,100 Hz (3.71 s).
The Xiri test fed the emulator 48,000 frames/s, with a 440 Hz tone on the
left and 880 Hz on the right. The recorder's default mono microphone wrote
the left input to both file channels, as it did on original IRIX. A 100 ms
window in the saved take measured 11,995 at 440 Hz and 4 at 880 Hz, on an
input amplitude of 12,000. Replaying that AIFF in winterm with SGI
`sfplay` returned zero. The emulated HAL2 speaker output measured 11,991
at 440 Hz and 4 at 880 Hz on each channel. In a control run, feeding the Xiri FIFO samples
prepared for 44,100 Hz shifted the tone up to about 482 Hz.

Both Xorg servers reported a 24-plane root window, 241 visuals and no
`SERVER_OVERLAY_VISUALS` property. SGI documents an overlay requirement
for the 6.5.30 recorder. Sound Editor remains usable on both systems. With
the updated module it recorded, saved, reopened and replayed a measured
440 Hz microphone tone on both Indys. [SGI Media Recorder manual](https://man.freebsd.org/cgi/man.cgi?manpath=IRIX+6.5.30&query=mediarecorder&sektion=1) ·
[Per-release measurements](2026-11-28-indy-recorder-fix.json)

### Shared file and pollable semaphore

On both release lines the signal-mask query now grows the 5,232-byte
scratch file to 16,384 bytes at offset 9,536. A second query spanning the
24,576-byte boundary grows the file to 32,768 bytes. Both match the original
IRIX rule of extending to the end of the last page touched. A failed copy
into an ordinary shared mapping leaves the file size intact. IRIX returned
`EFAULT` there and Xiri returned `EINVAL`. Both reject an unmapped
destination with `EFAULT`. Both accept the recorder’s `msync(MS_INVALIDATE)`.
NetBSD rejects an undocumented flag bit (8) that the two IRIX references accepted.

Fixing the write exposed a second error from `usopenpollsema()`. The
original 6.5.22f recorder opens `/dev/usemaclone`, sets mode 0600,
registers the owner field and queues itself before displaying its window.
The Xiri module now provides a per-open pollable semaphore for this path.
An inherited descriptor lets a child wake a waiting parent. Repeated polls
stay readable for that parent until it queues again. Two early wakeups
are counted separately. The scope is the clone and inherited descriptors.
Independent attachment through `/dev/usema` and checkpoint/restore ioctls
remain open. [SGI semaphore driver manual](https://man.freebsd.org/cgi/man.cgi?manpath=IRIX+6.5.30&query=usemaclone&sektion=7M)

## Repeat the comparison

Start with a private copy of either [prepared Indy desktop](2026-11-27-indy-cdrom.md#ready-to-boot-prismatic-systems).
In Prismatic, attach `.work/images/xiri-indy-mediarecorder-update.iso` as a
CD-ROM at ID 6. This update disc holds the tested NetBSD kernel, boot kernel,
compatibility module and device startup script. Install them as root:

```sh
set -e
install -r -m 444 /CDROM/netbsd /netbsd
install -r -m 444 /CDROM/netbsd.boot /netbsd.boot
install -r -m 444 /CDROM/module "$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod"
install -r -m 555 /CDROM/devices /etc/rc.d/xiri_devices
sync
shutdown -p now
```

Detach the update CD and boot the guest. Verify
`test -c /emul/irix/dev/usemaclone` after startup.
To rebuild the module, use `lab/ip28-kernel/build-module.sh` with NetBSD
`b187ffa60fd6` and the matching [shared-file-growth kernel](2026-11-27-indy-autogrow.md#reproduction).
The tested local module is `.work/builds/indy-mediarecorder-20261128/module/compat_irix_o32.kmod`.

Log in through xdm as `xiritest` and double-click the microphone. For the
diagnostic output, run the same launch from winterm.

```sh
/emul/irix/usr/sbin/mediarecorder -media audio -jack Microphone
```

On 6.5.22f choose a writable destination, press Record and then Stop.
The file list shows the new take. From winterm in that directory, run
`sfplay audio1.aiff` to replay the first take. For this Xiri configuration,
feed the [Indy microphone FIFO](2026-11-27-indy-microphone.md) at 48,000 Hz
and leave Media Recorder at its default 44,100 Hz.

To repeat the memory check, build the [probe](../../lab/irix-mmap-shared/recorder-arena.c)
on the host and copy the resulting executable to each guest:

```sh
sh lab/irix-mmap-shared/build-recorder-arena.sh \
    .work/netbsd-octane-build/tools/bin/mips64--netbsd recorder-arena
```

In a fresh writable directory on the guest, run the commands below.
The first nine big-endian words are the `MREC` identifier, stack and in-file
query results, initial size, past-EOF query result and size, post-store
query result and size, and the result of opening the semaphore device.
The last seven give the valid and unsupported-flag `msync` results,
cross-page query and size, ordinary-mapping query and size, and invalid
pointer result. Negative error values are errno numbers with the sign
reversed. Running the probe without arguments checks the semaphore through
a fork and returns zero on success.

```sh
dd if=/dev/zero of=arena bs=5232 count=1
/path/to/recorder-arena arena > record
od -A n -t d4 record
/path/to/recorder-arena
```
