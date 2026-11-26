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
