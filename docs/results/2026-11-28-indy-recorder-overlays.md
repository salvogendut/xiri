# Record from the Indy desktop microphone

Log in through xdm, double-click **microphone**, then press **Record** and
**Stop**. SGI Media Recorder lists the take in its window. With the default
destination, run `sfplay ~/audio1.aiff` in winterm to hear the first take.
This passed as `xiritest` on both emulated Indy desktops.

| Donor and emulated Indy | Desktop action | Saved stereo AIFF at 44.1 kHz | Replay measured at HAL2 |
| --- | --- | --- | --- |
| 6.5.22f, R4400 | Original SGI microphone device | 144,915 frames | 440 Hz in both channels |
| 6.5.30f, R5000 | Original SGI recorder with its Audio menu | 176,908 frames | 440 Hz in both channels |

The test fed 440 Hz on the left and 880 Hz on the right through IRIS's
48 kHz input FIFO. The default mono microphone copied the left input to
both channels. Each AIFF belonged to the logged-in user with mode 600.
Playback used the donor's `sfplay` as the same user. The measurements cover
emulated input and output. [6.5.22f screenshot](2026-11-28-recorder-mic-6.5.22f.png) ·
[6.5.30f screenshot](2026-11-28-recorder-mic-6.5.30f.png) ·
[Tone measurements and image hashes](2026-11-28-indy-recorder-overlays.json)

## Why the microphone can work without graphics overlays

On an original-media IRIX 6.5.30f O2, Xsgi advertised overlay visual
`0x25` in `SERVER_OVERLAY_VISUALS`. It was an 8-bit PseudoColor visual with
256 entries, transparent pixel zero and layer one. Media Recorder's
main window used ordinary visual `0x20`. We traced individual X11
requests from the vendor recorder through SGI's `xscope -v2`.

| Original recorder operation | Reads of the overlay property | Overlay colormaps | Overlay windows |
| --- | ---: | ---: | ---: |
| `-media audio -jack Microphone -allowmenu audio`, Record and Stop | 2 | 0 | 0 |
| `-media image -source screen -screensel method=adjustable` | 2 | 1 | 1, mapped |

The audio run saved a 414,220-byte AIFF on original IRIX. On the Xiri
Indy, Xorg reported a 24-plane root and no overlay property. The 6.5.30f
recorder calls ViewKit's overlay availability check while constructing the
audio window. The desktop microphone launcher supplies that one callback
through the n32 loader for the matching vendor executable and selects
SGI's `-allowmenu audio`. The callback restores the previous library list
before any recorder helpers run. An unrestricted launch after the microphone
test still showed SGI's overlay error. Screen selection remains open work.
[SGI recorder options](https://man.freebsd.org/cgi/man.cgi?manpath=IRIX+6.5.30&query=mediarecorder&sektion=1) ·
[SGI runtime loader](https://man.freebsd.org/cgi/man.cgi?manpath=IRIX+6.5.30&query=rld&sektion=1)

The desktop checks the HAL2 recording inventory at login. The affected
6.5.30f setup uses a filetype action with the donor's microphone artwork
and localized label. SGI File Manager starts the action through
`/rescue/sh`, and the NetBSD IRIX module requires execute permission
on its shared object. Other recorder versions and displays advertising
overlays use the SGI device action. [Desktop action](../../runtime/libexec/recorder-microphone) ·
[Filetype](../../runtime/etc/applications.ftr)

## Try it in Prismatic

Start with a private copy of either [prepared Indy desktop](2026-11-27-indy-cdrom.md#ready-to-boot-prismatic-systems).
Attach `.work/images/xiri-indy-microphone-update.iso` as a CD-ROM at
SCSI ID 6. This cumulative update includes the [previous kernel, module
and device service](2026-11-28-indy-mediarecorder.md#repeat-the-comparison)
and the microphone desktop files. Install as root on the prepared 11.99.11 guest.

```sh
set -e
install -r -m 444 /CDROM/netbsd /netbsd
install -r -m 444 /CDROM/netbsd.boot /netbsd.boot
install -r -m 444 /CDROM/module "$(sysctl -n kern.module.path)/compat_irix_o32/compat_irix_o32.kmod"
install -r -m 555 /CDROM/devices /etc/rc.d/xiri_devices
for file in desktop-clients.sh recorder-microphone recorder-audio.so; do
    install -r -m 555 "/CDROM/$file" "/usr/local/libexec/xiri/$file"
done
for file in applications.ftr microphone; do
    install -r -m 444 "/CDROM/$file" "/usr/local/share/xiri/$file"
done
/usr/local/sbin/xiri-update-filetypes
sync
shutdown -p now
```

Detach the disc, boot the guest, and log back in. A foreground test of the
same audio action is `/usr/local/libexec/xiri/recorder-microphone`.
Provide a PCM source in IRIS to record an audible signal. The emulator's
default input is silence. [IRIS microphone setup](2026-11-27-indy-microphone.md)
