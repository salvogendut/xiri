# Audio CDs on the emulated Indy

Insert an audio-only CHD in the CD-ROM drive at SCSI ID 6. The SGI desktop
adds its music-note artwork to **CDROM**. Double-click the icon and choose
**Track 2** to play just that track. Selecting another track changes what
plays. **Stop** and **Close** release the player. Eject the disc from the
desktop to use the drive for a data CD again.

| Guest | Track 2 at the HAL2 output | Desktop checks |
| --- | --- | --- |
| [Xiri 6.5.22f, Indy R4400](2026-11-27-cd-audio-6.5.22f.png) | 880 Hz in both channels in all twelve one-second windows | Open, select, stop, close, eject and read the next data disc passed |
| [Xiri 6.5.30f, Indy R5000](2026-11-27-cd-audio-6.5.30f.png) | 881 Hz in the first window and 880 Hz in the remaining eleven, in both channels | The same sequence passed |

Both guests reported track starts at sectors 0 and 900, with lead-out at
1800. Track one contains 440 Hz, so the recorded pitch also checks that the
desktop selected the second track. NetBSD sent the output to HAL2 at
48 kHz. [Measurements and artifact checksums](2026-11-27-indy-cd-audio.json)

The Xiri track selector invokes NetBSD `cdplay` as the logged-in user.
The user needs read access to `/dev/rcd0c` and playback access to
`/dev/sound`. The test account `xiritest` has both through the existing
system configuration. To inspect the track list and play track two from
winterm, use:

```sh
cdplay -f /dev/rcd0c info
cdplay -a /dev/sound -f /dev/rcd0c play 2 2
```

The selector uses `/rescue/sh` explicitly. When SGI File Manager launched
the first version with a `/bin/sh` interpreter, it found the donor's
Bourne shell, which failed on the script's arithmetic expansion.

## Comparison with original IRIX

On the original 6.5.22f Indy, `mediad` published `/CDROM/Track01.aiff`,
`Track02.aiff` and `info.disc`. SGI CD Player displayed both tracks.
Selecting track 2 and pressing Play produced an 880 Hz tone in both channels
at the HAL2 output, sampled at 44.1 kHz. Opening the exported AIFF with
`sfplay` still gave a read error in this emulator configuration.
[Original SGI CD Player](2026-11-27-cd-audio-irix.png)

On the audio-CD build, tracing SGI `cdman` found its first blocking operation before
the drive was opened. Its allocator requests a writable 64 KiB shared,
file-backed `MAP_AUTOGROW` mapping. That module returned `EINVAL`, then
SGI libc raises `SIGFPE` while initializing the arena. Sound Editor
also requested file-backed growth.
[Sound Editor comparison](2026-11-27-indy-microphone.md)

The subsequent [shared-file mapping check](2026-11-27-indy-autogrow.md)
records the new kernel behavior and the SGI application results.

## Reproduce the desktop check

IRIS `xiri` commit `65039d90` reads audio-only CHDs, reports the track
starts and lead-out, and serves digital samples through MMC READ CD.
The tested layout has one INDEX 01 per track and no explicit gaps.
Mixed audio/data discs, explicit gaps and analogue drive playback remain
open. NetBSD `xiri` commit `375916d7bba` translates the TOC, subchannel
and flat-buffer SCSI requests from 32-bit applications to the Indy’s
64-bit kernel. The desktop uses the donor release's existing music artwork.

The test fixture contains twelve seconds each of 440 Hz and 880 Hz stereo
PCM. Generate it with:

```sh
python3 lab/native-iso/make-audio-cd.py two-tones.chd
```

The [desktop acceptance check](../../lab/native-iso/check-audio-cd.py)
uses private copies of the [prepared data-CD systems](2026-11-27-indy-cdrom.md#ready-to-boot-prismatic-systems).
It installs the matched kernel, boot kernel, module, daemon, selector
and SGI filetype rules, then cold-boots, logs in through xdm, clicks the
actual desktop controls and captures HAL2 output. Use Python 3 with NumPy
and Pillow, plus `genisoimage`. Run it once per release:

```sh
python3 lab/native-iso/check-audio-cd.py \
  --bundle .work/prismatic-indy-cdrom/6.5.22f --cpu r4400 \
  --emulator .work/emulators/iris-xiri-65039d90/accelerated \
  --kernel "$KERNEL" --boot-kernel "$BOOT_KERNEL" --module "$MODULE" \
  --daemon "$CDROMD" --disc two-tones.chd --output "$RESULTS"
```

Use the 6.5.30f bundle and `--cpu r5000` for the second run. The kernel
build outputs are `netbsd`, `netbsd.elf32` and `compat_irix_o32.kmod`.
The acceptance update and two-tone disc are local test media. Existing
installer ISOs and data-CD Prismatic images predate this update.

The local update disc is `.work/images/xiri-indy-cd-audio-update.iso`. On a
disposable copy of either prepared Indy disk, boot with that disc in drive 6
and run these commands as root after it mounts. Install the module alongside
its matching kernel before rebooting.

```sh
set -e
install -r -m 444 /CDROM/netbsd /netbsd
install -r -m 444 /CDROM/netbsd.boot /netbsd.boot
install -r -m 444 /CDROM/module "$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod"
install -r -m 555 /CDROM/daemon /usr/local/libexec/xiri/cdromd
install -r -m 555 /CDROM/player /usr/local/libexec/xiri/cd-player.sh
install -r -m 444 /CDROM/rules /usr/local/share/xiri/applications.ftr
/usr/local/sbin/xiri-update-filetypes
sync
shutdown -p now
```

Boot that copy with the audio-capable IRIS build above. Insert
`.work/images/xiri-two-tone-audio.chd` as a CD-ROM. An older Prismatic
binary needs to be rebuilt against an audio-capable IRIS backend to read it.
