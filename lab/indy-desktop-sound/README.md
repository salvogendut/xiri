# Original SGI Display and desktop effects on the Indy

The update targets an Indy v6 guest with the shutdown-menu and HDSP updates.
Build both native binaries once for the matching NetBSD 11.99.11 MIPS o32
system and Xorg 1.10.6. Prepare a separate CD from each licensed donor.

```sh
lab/sgi-video/build.sh "$NETBSD_CC" "$SYSROOT" "$X11_INCLUDE" "$PWD/libsgivc.so"
make -C runtime BUILDDIR="$PWD/build" "$PWD/build/desktop-sound"
lab/indy-desktop-sound/package.sh 6.5.22f "$DONOR_22" libsgivc.so build/desktop-sound 6.5.22f.iso
lab/indy-desktop-sound/package.sh 6.5.30f "$DONOR_30" libsgivc.so build/desktop-sound 6.5.30f.iso
```

Run the Makefile on NetBSD, or supply its target compiler, sysroot and
X11 flags when cross-compiling. `X11_INCLUDE` is the target
`/usr/X11R7/include` from the matching X11 development set, including its
`xorg` and `pixman-1` subdirectories. The host packager uses Python 3,
ffmpeg, sha256sum and genisoimage. It checks the release against the original
`ssplay` hash and refuses to overwrite existing media.

| Source | Guest destination | Purpose |
| --- | --- | --- |
| Donor `/usr/sbin/ssplay` | `/emul/irix/usr/sbin/ssplay` | Original SoundScheme client |
| Donor `/usr/share/data/sounds/soundscheme/schemes/defaultScheme.ss` and `soundfiles/` | `/usr/local/share/xiri/sounds/effects` and numbered `.pcm` files | Map event names to the donor samples, converted once to stereo 48 kHz signed 16-bit big-endian PCM |
| Native `desktop-sound` and updated `desktop-clients.sh` | `/usr/local/libexec/xiri/` | Own the SoundScheme X selection in the logged-in desktop and feed NetBSD audio |
| Native `libsgivc.so` | `/usr/X11R7/lib/modules/extensions/` | Serve XSGIvc requests using Newport’s current Xorg timing and gamma ramp |
| Xorg module configuration | `/etc/X11/xorg.conf.d/91-xiri-sgivc.conf` | Load the extension at X server startup |

To apply the CD, attach it to a spare SCSI slot, mount the matching device
read-only, then run `sh /cdrom/install.sh` as root. Restart xdm or reboot
after logging out. The installer verifies its manifest, release, expected
base launcher and any existing files before installing. Reapplying identical
media is supported. Keep a copy of the previous disk and overlay for rollback.
The update leaves site mixer preferences alone. The development profiles
enable NetBSD's mixerctl service separately and save a starting speaker
setting of 128,128 with `/etc/rc.d/mixerctl stop`.

[Manual testing](../../docs/XIRI-IMAGE.md#indy-display-and-desktop-sounds) ·
[Measurements and emulator revisions](../../docs/results/2026-11-26-indy-display-sound.md).

## Rebuild the Prismatic used for these images

The private build pairs Prismatic `63b6cc8` with IRIS `707912dd` and the
two HPC3 changes from the integration branch. These commands stage sources in
a temporary directory and preserve the original checkouts. Run them from
Xiri with a working Prismatic Rust/SDL3 build environment, including
libpcap and the SDL3 development linker names.

```sh
scratch=$(mktemp -d)
mkdir "$scratch/iris" "$scratch/prismatic"
git -C ../iris archive 707912dd | tar -x -C "$scratch/iris"
git -C ../prismatic archive 63b6cc8 | tar -x -C "$scratch/prismatic"
git -C ../iris diff '1b4b140e^' 7c713c13 -- src/dev/hpc3.rs > "$scratch/playback.patch"
(cd "$scratch/iris" && patch -p1 < "$scratch/playback.patch")
(cd "$scratch/prismatic" && cargo build --locked --release --features pcap,idle-pause,jitv2,iris/rex-jit)
```

The resulting executable is `$scratch/prismatic/target/release/prismatic`.
Each manual launcher uses the private executable in its parent directory.

## Recheck an SDL capture

Prismatic can record the samples it sends to the host when launched with
`SDL_AUDIO_DRIVER=disk` and `SDL_AUDIO_DISK_OUTPUT_FILE` set to a private file.
Use a separate test config for each Indy. Verify the SDL log reports signed
16-bit little-endian stereo at 48 kHz. Log in to 4Dwm and use the original
`/emul/irix/usr/sbin/ssplay EmptyDumpster` once per setting. Cut a stereo
frame-aligned segment around each play and include the trailing silence.

| Segment | Guest and frontend settings |
| --- | --- |
| `full.pcm` | Guest mixer 128,128, `ssplay -m 0`, `ssplay -l 1`, Prismatic at 100% |
| `scheme_half.pcm`, `scheme_muted.pcm`, `restored.pcm` | Set `ssplay -l 0.5`, then `-m 1`, then restore level 1 and mute 0 |
| `prismatic_half.pcm`, `prismatic_muted.pcm`, `prismatic_restored.pcm` | Use F9 General volume 50%, enable mute, then restore 100% and unmute |
| `native_mixer_zero.pcm`, `native_mixer_restored.pcm` | Use `mixerctl -w outputs.master=0,0`, then restore 128,128 |

Find the sample number for `EmptyDumpster` in the prepared `effects`
manifest. Run `python3 verify-capture.py /path/to/that.pcm /path/to/segments`
with NumPy installed to compare each channel, the peak-volume ratios and
digital silence. Keep the private captures and donor sample out of Git.
