# SGI Screen Saver on NetBSD Xorg

The Indy v6 disk uses the old Xorg 1.10.6 from NetBSD 11.0/sgimips. IRIX
xlock registers with the SGI `SCREEN-SAVER` extension. The NetBSD X server
already handles idle time, input and the MIT screen saver. The patch adds
one SGI saver owner per screen and sends its two events from those existing
paths. Xorg releases the registration when the client disconnects.

Use a NetBSD cross-build wrapper for `MACHINE=sgimips`, `MACHINE_ARCH=mipseb`,
and a matching NetBSD 11.0/sgimips destination tree with the X development
headers and libraries (base, comp and xcomp sets). Extract
`external/mit/xorg-server.old` from the [NetBSD 11.0 X sources](https://cdn.netbsd.org/pub/NetBSD/NetBSD-11.0/source/sets/xsrc.tgz)
under the X source directory. The build script works on a temporary copy.

```sh
sh lab/sgi-saver/build.sh "$NBMAKE_SGIMIPS" "$XSRCDIR" "$DESTDIR" ./libextmod.so.0
python3 lab/native-package/package-indy-savers.py \
  --imported ".work/imports/irix-${release}-xlock-savers-v1" \
  --xorg-extmod ./libextmod.so.0 --output "./savers-${release}.iso"
```

Run the framebuffer regression with the matching v6 bundle, uncompressed
v6 kernel (for its shutdown log symbols), pinned emulator directory and a
fresh output directory. It uses a disposable disk and the actual Catalog
entry, shortens the idle interval for the test and captures successive frames.

```sh
python3 lab/sgi-saver/check.py --release "$release" --bundle "$BUNDLE" \
  --kernel "$KERNEL" --emulator "$EMULATOR" --media "$ISO" --output "$RESULT"
```

## Audio-v8 Indy repair

For each release, build a private repair ISO using its savers-v2 CD.
The builder checks the contents of the input files, so a CD rebuilt
from the same files may have different ISO timestamps. The extra installer
updates the desktop session to restart the chosen IRIX saver on login.

```sh
release=6.5.22f  # repeat with 6.5.30f
media=.work/installers/indy-11.99.11
python3 lab/sgi-saver/package-audio-v8.py --release "$release" \
  --saver-cd "$media/savers-v2/$release.iso" --output "./repair-$release.iso"
```

Use the original, clean audio-v8 base CHD for the regression. The runner
creates a separate disk and overlay. It checks Demo, activation by ordinary
inactivity, wake with Space, saved settings and animation after a second
xdm login, disabling the saver and clean shutdown.

```sh
scratch=$(mktemp -d)
isoinfo -R -i .work/builds/indy-mute-sync-20261127/boot.iso -x /netbsd > "$scratch/netbsd"
python3 lab/sgi-saver/check.py --audio-v8 --release "$release" \
  --bundle ".work/prismatic-indy-audio-v8/$release" --media "./repair-$release.iso" \
  --kernel "$scratch/netbsd" --emulator .work/emulators/iris-xiri-20261122/accelerated \
  --output "$scratch/test"
```

[Manual installation](../../docs/NATIVE-PACKAGE.md#add-screen-saver-to-an-audio-v8-indy) ·
[Image hashes, measurements and screenshots](../../docs/results/2026-11-27-indy-saver-repair.md).
