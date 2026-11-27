# SGI CD Player on the emulated Indy

The original SGI CD Player reads an audio CD and plays the selected track
through HAL2 on both emulated Indys. The player runs as the desktop user.
It needs root to assign round-robin scheduling to the open player for sound.
Double-clicking the **CDROM** music icon opens the ordinary-user NetBSD
track selector.

| Desktop | SGI CD Player with round-robin scheduling | NetBSD track selector |
| --- | --- | --- |
| [6.5.22f on Indy R4400](2026-11-28-cdplayer-6.5.22f.png) | Track 2, 880 Hz in both channels | Track 2, 880 Hz stereo |
| [6.5.30f on Indy R5000](2026-11-28-cdplayer-6.5.30f.png) | Track 2, 880 Hz in both channels | Track 2, 880 Hz stereo |

The test disc contains 440 Hz on track one and 880 Hz on track two.
The emulator recorded HAL2 output at 48 kHz. Eleven complete one-second
windows from the SGI player and twelve from the NetBSD selector measured
880 Hz in each channel. In the ordinary-user comparison, the SGI player
opened from the disc menu and read track 2 at sector 900, but produced zero
DAC samples. Ctrl+Q closed the SGI window in all four runs. Both desktops
then ejected the music disc and mounted the next data CD.
[Measurements](2026-11-28-indy-cdplayer.json) · [Original IRIX audio comparison](2026-11-27-indy-cd-audio.md#comparison-with-original-irix)

## Play an audio CD

1. Insert the audio CD. In 4Dwm, select its desktop icon and choose **SGI
   CD Player** from the right-button menu. Alternatively, run
   `/emul/irix/usr/sbin/cdman` from winterm.
2. Before pressing **Play**, find the open player's PID from a root shell on
   the guest. Check the owner and command in the output, then use that PID
   for the scheduling command. For example, if the PID is 314:

   ```sh
   ps -axww -o user,pid,args | grep '[c]dman'
   /usr/sbin/schedctl -C SCHED_RR -P 0 -p 314
   ```

3. Select a track in SGI CD Player and press **Play**. Repeat the scheduling
   command for the new PID if you quit and relaunch the player.

The SGI worker requests nondegrading priority 39 before sending samples to
HDSP. Xiri maps that request to NetBSD’s lowest round-robin priority. The
worker inherits its parent’s scheduling class. This grants scheduling to a
single player instance and keeps the account’s ordinary permissions.

## How the SGI player finds the music

On the original 6.5.22f Indy, the hardware inventory reported a removable
SCSI-2 CD-ROM at controller 0, target 6. With the test disc inserted,
`mediad` published this entry in `/etc/mtab`:

```text
/dev/scsi/sc0d6l0 /CDROM cdda ro,nosuid 0 0
```

SGI CD Player uses the inventory to discover the drive, the mount entry to detect
music and `/CDROM/info.disc` to populate the track list. Xiri derives the address
from NetBSD's attached SCSI drive. It translates the player's read-only
`DS_ENTER` commands on the native CD descriptor, including MMC READ CD with
Q subchannel data. The native device's access permissions still apply.

The media service generates track metadata from the disc's table of contents.
It includes the two-second lead-in in MSF addresses and ends the last track
one frame before lead-out, as on the original. The test disc reports starts
at `00:02:00` and `00:14:00`, durations of `00:12:00` and `00:11:74`,
and lead-out at `00:26:00`. The compatibility mount entry and metadata view
are withdrawn when the tray changes. Data discs use the native read-only
mount at `/CDROM`. Per-track AIFF file export and album database keys remain
outside this implementation.

## Reproduction

Use the two prepared Indy bundles and the kernel and emulator arguments from
the [desktop CD test](2026-11-27-indy-cd-audio.md#reproduce-the-desktop-check).
Build `cdromd` from this revision and use the matching
[NetBSD module](https://github.com/salvogendut/NetBSD-xiri/commit/51ae5f2886ef1cd3c3089e8aabf6fcce3c4de740).
Run `lab/native-iso/check-audio-cd.py` with `--sgi-realtime` to check the
original player with the per-process scheduling grant and measure its stereo
output. Use `--sgi` to check the ordinary desktop account. Both modes verify
the desktop track selector, ordinary-user eject and mounting the next data
disc. Each run takes a separate output directory.

The local update disc for the prepared Indy guests is
`.work/images/xiri-indy-cdplayer-update.iso`. Attach it at SCSI ID 6. On
a copy of the guest disk, follow the [CD update commands](2026-11-27-indy-cd-audio.md#reproduce-the-desktop-check)
with this ISO. Add the following command before the filetype update and
reboot, to install the startup script that creates the SGI drive alias:

```sh
install -r -m 555 /CDROM/devices /etc/rc.d/xiri_devices
```

After reboot, insert `.work/images/xiri-two-tone-audio.chd` to repeat the
two-track test in Prismatic with its audio-capable IRIS backend.
