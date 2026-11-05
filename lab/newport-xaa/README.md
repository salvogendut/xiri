# Newport XAA clipped and repeated textures

This is an Xorg userspace driver correction, separate from NetBSD's kernel
`newport.c` and the IRIS RGB24 physical-plane correction. The source lives in
NetBSD **xsrc**, not the NetBSD kernel repository. Keep the pinned source patch
here until a corresponding xsrc fork/upstream change is available.

The original IRIX xmahjongg 3.6.1 chooses the deepest TrueColor visual, including
the ARGB32 visual supplied by Composite. Automatic redirection then exercises
XAA's CPU-to-screen Render texture callback. The callback receives clipped
copy rectangles, not scaling requests. The original Newport code scales these
rectangles, adds the source X offset again at each row boundary, and drifts the
repeated tile's X origin between rows. It also mishandles negative repeat
origins and packs solid A8-mask colors in the reverse HOSTRW byte order.

`texture-coordinates.patch` corrects these operations. It does not implement
partial-alpha blending or qualify every Render operator. `source.json` pins
NetBSD xsrc, each original file, and the matching public xmahjongg source.
Vendor IRIX binaries/data are unchanged and remain outside Git.

The later [text-fallback correction](../newport-text/README.md) builds on
this patch. Use its preparation script when reproducing the driver that also
restores disabled Toolchest labels and native Xft/Render text. This directory
retains the texture-only baseline and its original build inputs.

## Rebuild

Prepare the source on the host (Python 3 and Git required):

```sh
python3 lab/newport-xaa/prepare-source.py .work/newport-xaa-source
```

For an offline build, add `--cache PATH` pointing at the original source files;
all hashes are still checked. The destination must be new. Transfer that
source directory, `config.h` (already copied into it), and `build-driver.sh`
to a disposable NetBSD/sgimips guest containing the matching X11 development
sets. In that guest:

```sh
sh build-driver.sh /path/to/source /root/newport-build
```

The observed build uses GCC 12.5.0 and Xorg 1.10.6, video-driver ABI 10.0.
Install `/root/newport-build/newport_drv.so` as
`/usr/X11R7/lib/modules/drivers/newport_drv.so` while Xorg is stopped, then
restart Xorg. This module is not portable across arbitrary Xorg ABIs.

## Regression

Compile and run `render-probe.c` against a fresh Xorg display:

```sh
cc -O2 -Wall -Wextra -Werror -I/usr/X11R7/include -L/usr/X11R7/lib \
  -Wl,-rpath,/usr/X11R7/lib render-probe.c -lXrender -lX11 -o render-probe
DISPLAY=127.0.0.1:0 ./render-probe
```

It compares 8,536 pixels across twelve ARGB/A8 cases: full texture, clipped
origin, nonzero origin, right/bottom edge, repeat, and negative repeat. An
untouched one-pixel border catches overruns. Only opaque ARGB, binary masks
and PictOpOver are used. Original release and source-built drivers fail;
software rendering and the patched module pass.

`scripts/probe-xiri-desktop-usability.py --newport-driver PATH
--check-xmahjongg` installs and hashes the replacement module, runs the Render
check in both desktop sessions, and exercises board 12345, hint/take, undo,
resize/redraw and quit. Use its existing accelerated configuration, kernel,
emulator and prepared-seed arguments. It also checks graphical login, the
xiritest shell identity/home, both logout routes and service cleanup.

See the [cycle record](../../docs/results/2026-11-03-newport-xmahjongg.md)
for observed results and the manual image.
