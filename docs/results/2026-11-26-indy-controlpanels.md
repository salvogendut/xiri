# Four SGI control panels on the Indy v6 desktop

The 6.5.22f R4400 and 6.5.30f R5000 give the same results when
`xiritest` double-clicks these entries on Icon Catalog's ControlPanels page
or starts the original binaries from winterm.

| Entry | What appeared | What the test verified |
| --- | --- | --- |
| Display | An `XSetmon` error dialog reports that the target display lacks XSGIvc. | OK closes it. Xorg advertises RandR, DPMS and XF86VidMode. `xrandr -q` reports an active 1280×1024 mode at 75 Hz. |
| Audio Panel | A warning says the machine has no audio driver. | OK closes it. Even with HAL2 and the native mixer working, the original program's open of `/dev/hdsp/hdsp0master` returns `ENOENT`. |
| Sounds | An error says the computer has no audio output hardware. | OK closes it. The original `dtSounds` fails opening the same HDSP master device before showing its volume, bell or key-click controls. |
| Screen Saver | The settings window opens. The clean v6 disk has an empty saver list and shows “No Power Saver”. | The checkbox changes the Xorg timeout from 0 to 600 seconds and back to 0. Close exits. |

The visible dialogs and panel were identified by their X window classes
and framebuffer captures. The one-pixel windows named “Audio Panel” and
“System & Desktop Sounds” belong to the applications, but the windows the
user can interact with contain only the errors. Both audio traces record
the attempted emulation-root and native paths before the failed open.
[6.5.22f measurements](2026-11-26-controlpanels-6.5.22f.json) ·
[6.5.30f measurements](2026-11-26-controlpanels-6.5.30f.json).

| Indy release | Screen Saver | Display | Audio Panel | Sounds |
| --- | --- | --- | --- | --- |
| 6.5.22f | [Panel](2026-11-26-controlpanels-6.5.22f-screensaver.png) | [Dialog](2026-11-26-controlpanels-6.5.22f-display.png) | [Dialog](2026-11-26-controlpanels-6.5.22f-audiopanel.png) | [Dialog](2026-11-26-controlpanels-6.5.22f-sounds.png) |
| 6.5.30f | [Panel](2026-11-26-controlpanels-6.5.30f-screensaver.png) | [Dialog](2026-11-26-controlpanels-6.5.30f-display.png) | [Dialog](2026-11-26-controlpanels-6.5.30f-audiopanel.png) | [Dialog](2026-11-26-controlpanels-6.5.30f-sounds.png) |

## Enabling the native Indy audio controller

The initial v6 bundles inherited `no_audio = true` from the installer.
On the pinned IRIS Indy, this makes the HAL2 revision register report an
absent device. The kernel already contains the driver. With
`no_audio = false` in the top-level `iris.toml`, both kernels attached
`haltwo0` revision 4.1.0 and `audio0` for stereo playback. Each native
mixer read back `0,0 → 64,96 → 0,0`. Each guest wrote 8192 bytes to
`/dev/audio` and closed the device successfully. Host speaker output and
audio capture were outside this check.

The graphical packager now enables HAL2. To use an older bundle, change
that one setting in its `iris.toml` while the emulator is stopped, then
cold-boot the same disk. Query the device from winterm with
`/usr/bin/audioctl -n name` and `/usr/bin/mixerctl outputs.master`.
[IRIS Indy hardware selection](https://github.com/techomancer/iris/blob/6ec1ebf379228d572026a9ae8d291511ed28af74/src/dev/hpc3.rs).

The regression checked the IRIX user's login/logout and native
`netbsdtest` ctwm login/logout with HAL2 enabled. Each guest halted.
The R4400 run used a copy of the NVRAM from the existing manual session.
Its digest differs from the original v6 NVRAM and is recorded with the
results. The CHD digests matched the published release records.

## The empty Screen Saver list

Both original-media donors have 16 definitions in
`/usr/lib/X11/savers/defaults`. Eleven use SGI xlock. The optional saver CD
adds those definitions, the n32 `xlock.so` configuration plug-in, xlock
itself and its three IRIX PAM libraries under `/emul/irix`. Each release
uses its own donor. The vendor binaries and libraries have mode 0555 so
an ordinary user's IRIX runtime linker can map them.

With the files installed, the original panel lists presets and selecting
**Qix** displays its settings. **Demo** still reaches an X server
dependency. SGI xlock uses the experimental `SCREEN-SAVER` extension's
enable/disable requests and start/end events. The client reports that the
extension is missing. The standard Xorg blanking timer still works.
Screen locking and the five `haven` presets are outside this qualification.

**Qix itself animates on both Indys.** From winterm, run
`/emul/irix/usr/bin/X11/xlock -nolock -mode qix`. Press Space to return
to the shell. Three timed framebuffer samples showed 16,670 and 23,030
pixels changing between frames on the R4400, and 29,789 and 26,383 on the
R5000. A serial process-name poll timed out during the animation. The
independent IRIS monitor captured both the moving lines and the return
to the prompt. Both test guests then halted cleanly.

| Release | Original panel with the CD | Standalone animation | After Space |
| --- | --- | --- | --- |
| 6.5.22f | [Qix settings](2026-11-26-controlpanels-6.5.22f-qix-panel.png) | [Qix on the R4400](2026-11-26-controlpanels-6.5.22f-qix.png) | [winterm](2026-11-26-controlpanels-6.5.22f-qix-exit.png) |
| 6.5.30f | [Qix settings](2026-11-26-controlpanels-6.5.30f-qix-panel.png) | [Qix on the R5000](2026-11-26-controlpanels-6.5.30f-qix.png) | [winterm](2026-11-26-controlpanels-6.5.30f-qix-exit.png) |

Each release passed installation, repeat installation and hash/mode checks
on all 16 added files. Both installers rejected the other release's CD.
An existing, different Qix preset survived the installation attempt, and
the conflict was reported before the installer added xlock.

From the Xiri checkout, attach the CD for your installed release:

```sh
release=6.5.22f  # or 6.5.30f
.work/images/xiri-clean-indy-${release}-v6-20261126/run-iris.sh \
  --cdrom4 "$PWD/.work/installers/indy-11.99.11/savers-v1/${release}.iso"
```

In a NetBSD root shell, mount the disc and install the files. Then close
and reopen **ControlPanels → screensaver** as the desktop user.

```sh
mkdir -p /cdrom
mount -rt cd9660 /dev/cd0a /cdrom
sh /cdrom/install.sh
umount /cdrom
```

To build the CD from your own qualified donor, use a fresh output directory:

```sh
./xiri import --profile "profiles/irix-${release}-xlock-savers-v1.json" \
  --source ".work/donors/irix-${release}-original-media/irix-donor.chd" \
  --output ".work/imports/irix-${release}-xlock-savers-v1"
python3 lab/native-package/package-indy-savers.py \
  --imported ".work/imports/irix-${release}-xlock-savers-v1" \
  --output ".work/installers/indy-11.99.11/savers-v1/${release}.iso"
```

## Remaining device interfaces

The next shared audio test is to trace the first successful master-device
requests on original IRIX, implement the matching resource and mixer
operations, then change volume in each SGI panel and read it back through
NetBSD. Both installed donors carry `/usr/include/sys/hdsp.h`.

For Display, the SDK contains `X11/extensions/XSGIvcproto.h`. Start with
the queries that `xsetmon` issues to the original server, then map supported
channel and video-format queries to Newport's actual screen and modes.
[SGI video-control programming example](https://techpubs.jurassic.nl/library/manuals/3000/007-3313-001/sgi_html/ch03.html).
