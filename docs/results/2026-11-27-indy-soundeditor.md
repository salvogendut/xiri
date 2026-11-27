# Recording with SGI Sound Editor on XiriBSD

As the ordinary `xiritest` user, Sound Editor recorded the emulated Indy
microphone, saved the clip to the user’s home directory, quit and reopened
the AIFF in a fresh editor. Playback produced the recorded tone at the HAL2
speaker output on both vendor releases.

| IRIX release and emulated CPU | Frames in saved AIFF | Frames in playback check |
| --- | ---: | ---: |
| 6.5.22f, R4400 | 154,080 | 123,262 |
| 6.5.30f, R5000 | 154,080 | 124,258 |

The input supplied 440 Hz on the left and 880 Hz on the right. The default
mono microphone produced 440 Hz in both AIFF channels. The same tone reached
both speaker channels at 48 kHz. The playback measurement covers the interval
between clicking Play and Stop. The original-system comparison used the
6.5.22f Indy. All hardware measurements here used IRIS emulation.
[Measurements and syscall traces](2026-11-27-indy-soundeditor.json) ·
[6.5.22f screenshot](2026-11-27-soundeditor-recording-6.5.22f.png) ·
[6.5.30f screenshot](2026-11-27-soundeditor-recording-6.5.30f.png)

## Original IRIX and the failing call

On the original-media IRIX 6.5.22f Indy, SGI’s `par` attached to the GUI
process after the launcher returned. Pressing Record created PID 1354 from PID
1346 through `sproc(PR_SALL)`. The child opened `/dev/hdsp/hdsp0r2`. Pressing
Stop closed the input port and the worker exited. An earlier recording on this
donor produced a 48 kHz AIFF with 440 Hz in both channels. The Indy’s default
mono microphone copies the left input into both channels of the stereo file.
[Original IRIX recording](2026-11-27-indy-microphone.md#sound-editor-comparison)

On the previous Xiri module, the same Record button reached syscall 129 with
flags `0x7f` on both 6.5.22f and 6.5.30f. NetBSD returned `EOPNOTSUPP` before
the child existed, and the editor displayed “Cannot create record thread.”
Both the original IRIX trace and the Xiri traces were taken from the actual
GUI process. The application forks away from its winterm launcher.
[Previous module qualification](2026-11-27-indy-autogrow.md)

## What changed

The IRIX compatibility module accepts the full sharing mask used by SGI libc.
The recording worker has its own PID, stack and PRDA. It shares the editor’s
ordinary memory, descriptor table, working directory and umask. When the audio
library closes its port, the module removes the entire audio-ring mapping
from both processes. This matters on repeated recordings in one editor.
The group remains limited to two processes. Credentials and file-size limit
are inherited and queryable. Partial unmapping of shared ranges remains
outside this implementation. On worker exit, SGI libc also probes
`PR_LASTSHEXIT`, which returns `ENOSYS` on Xiri, then queries the group size.
The recording worker exits and the editor can start a playback worker.
[NetBSD module change](https://github.com/salvogendut/NetBSD-xiri/commit/ebc133801e2) · [Process compatibility notes](../../lab/irix-sproc/README.md)

## Repeat the check

Start with the paired Indy reference bundles and the matching shared-file-growth
kernel. Build the updated module from NetBSD’s `xiri` branch. The following
commands assume the project root and the cross-toolchain used for the Indy
builds. The checker works on a private disk, boots it, installs the kernel and
module, and then cold-boots into xdm. Its only saved desktop file is inside
the disposable guest.

```sh
tools=.work/netbsd-octane-build/tools
kernel=.work/builds/indy-autogrow-20261127/kernel
build=.work/builds/indy-soundeditor-20261127
emu=.work/emulators/iris-xiri-65039d90/accelerated

toolbox run -c xiri-iris sh lab/ip28-kernel/build-module.sh ../NetBSD-xiri "$tools" "$build"
toolbox run -c xiri-iris sh lab/irix-sproc/build-fullshare.sh "$tools" "$build/fullshare"
for release in 6.5.22f 6.5.30f; do
    case "$release" in 6.5.22f) cpu=r4400 ;; 6.5.30f) cpu=r5000 ;; esac
    python3 lab/irix-hdsp/check-soundeditor.py \
        --bundle ".work/prismatic-indy-cdrom/$release" --cpu "$cpu" \
        --kernel "$kernel/netbsd" --boot-kernel "$kernel/netbsd.elf32" \
        --module "$build/module/compat_irix_o32.kmod" --share-probe "$build/fullshare" \
        --emulator "$emu" --output ".work/recording-$release"
done
```

The freestanding control verifies that the child receives the requested share
mask and private process ID, that its descriptor close reaches the parent, and
that its directory and umask place the parent’s new file at `child/result`
with mode `0600`. The control also creates a second worker in the older address/descriptor-sharing
mode and checks the sharing mask for both processes. It checks that releasing a new shared mapping
makes the address unreadable in the parent, while attempts to remove a partial
mapping or the process-private PRDA fail.
[Control source](../../lab/irix-sproc/fullshare.c) · [Desktop test](../../lab/irix-hdsp/check-soundeditor.py)
