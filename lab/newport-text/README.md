# Newport software text and Courier selection

The [font/menu record](../../docs/results/2026-11-05-newport-text.md) and
[native controls](../../docs/results/2026-11-05-newport-text-controls.json)
reproduce missing disabled Toolchest labels and native Xft/Render glyphs.
Both draw correctly into pixmaps but disappear from Newport windows with
the previous accelerated driver. The same requests pass with `NoAccel`.

Newport's XAA driver allocates a software shadow framebuffer, but previously
installed its refresh hooks only when acceleration was disabled. XAA's
unaccelerated operations therefore changed memory that never reached the
display. `shadow-fallback.patch` installs `ShadowFBInit2` below XAA: read the
affected window rectangle from Newport before software drawing, then upload
it through XAA's image writer. Using those driver operations also keeps the
cached REX3 register state consistent. Accelerated operations bypass this
layer. Clip state is restored after each transfer.

This patch applies after the existing
[texture correction](../newport-xaa/README.md). It changes the Xorg userspace
driver from NetBSD **xsrc**, with no kernel/module or IRIS source changes.
The pinned source remains in this repository until an xsrc fork or upstream
submission is available. Vendor binaries and menu files are unchanged.

Prepare a new source directory:

```sh
python3 lab/newport-text/prepare-source.py .work/newport-text-source
```

`--cache PATH` uses the original source files offline and verifies their
hashes. `source.json` also pins the preceding patch, preparation script and
build inputs. Use `lab/newport-xaa/build-driver.sh` in a disposable NetBSD
guest with the matching Xorg SDK; `build.json` records GCC 12.5.0, Xorg 1.10.6,
video ABI 10.0, prepared sources and the resulting module. Stop Xorg before
replacing `/usr/X11R7/lib/modules/drivers/newport_drv.so`.

`text-pixels.c` compares window and pixmap text for solid, transparent and
opaque stipple, tiled text, and ImageText. Three clipping cases include two
disjoint rectangles and a negative text origin; the window origin is not
aligned to an eight-pixel pattern. Run it with `fixed`, the Toolchest
Helvetica pattern and the Courier face in `font-profile.json`: 45 cases.
`xft-pixels.c` adds 24 cases across clipping, Render, antialiasing and two
foreground colors. Every case requires visible pixels and exact agreement
with the pixmap control, including the untouched background. Together they
compare 1,242,000 pixels. Also retain the existing 8,536-pixel texture test.

Build on NetBSD with `-O2 -Wall -Wextra -Werror`, X11 headers/libraries under
`/usr/X11R7`, and `-Wl,-rpath,/usr/X11R7/lib`. Core text needs `-lX11`;
Xft needs `-I/usr/X11R7/include/freetype2 -lXft -lX11 -lfontconfig`.
The maintained cold-image test compiles and runs them at the greeter,
three IRIX logins and the native ctwm login:

```sh
python3 scripts/probe-xiri-xdm.py --bundle PATH_TO_BUNDLE --winterm --fonts
```

`font-profile.json` pins the native Courier bitmap, terminal resources,
greeter resources and corrected driver. Image preparation adopts these only
with `--refresh-font-resources`; `--newport-driver PATH` verifies the build
manifest before installing the module. Normal installation continues to
preserve administrator configuration and write `.example` files.

The explicit 20-pixel Courier bitmap gives winterm 11×20 cells and avoids the
wildcard choosing scalable IBM Courier. This does not repair the separate,
intermittent Type1 metric collapse. The later
[native FPU correction](../../docs/results/2026-11-05-type1-scaler.md) addresses
that cause while retaining this appearance profile. The imported SGI Screen face remains
available. No additional IRIX font is installed: `compare-courier.py` compares
the decompressed reference/native PCFs and records 188 identical glyphs,
three punctuation differences and one additional native glyph. Its Latin-1
decoder accounts for a nonzero first character column; the initial unmodified
Pillow decoder comparison is excluded from evidence.

Qualification covers this pinned 24-bit Xorg/driver/emulator combination.
Arbitrary Render operators, every software-fallback operation and physical
Newport hardware remain outside this result.
