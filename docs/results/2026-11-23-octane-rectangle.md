# Octane HQ4 rectangle on native NetBSD

![Octane High IMPACT scanout showing the amber rectangle on a blue background](2026-11-23-octane-rectangle.png)

The IP30 lab kernel sends 64-bit programmed-I/O commands through the HQ4
FIFO at XIO widget offset `0x020400`. It selects 24-bit RGB display mode,
disables the hardware cursor, fills the screen blue (`#21354b`) and draws an
amber rectangle (`#f4a139`) at (117, 203). The rectangle is 413×239 pixels,
with its last pixel at (529, 441). These unequal colour channels and
asymmetric coordinates expose red/blue swaps and coordinate errors.

The host requests a fresh guest scanout through `iris-ci` at the native
single-user shell prompt. The checker decodes the PNG and counts pixels
inside and outside the rectangle independently. The expected frame contains
98,707 amber pixels and 1,212,013 blue pixels at 1280×1024. Changing an
outside pixel to amber and swapping red/blue in one inside pixel each
produced one mismatch in the corresponding region.

## Qualification

| Emulated graphics | 6.5.22-line root | 6.5.30-line root |
| --- | --- | --- |
| Solid IMPACT | Zero pixel errors | Zero pixel errors |
| High IMPACT | Zero pixel errors | Zero pixel errors |

All four boots reached the native NetBSD shell with a read-only FFS root and
returned to the PROM after shutdown. The PNGs were byte-identical. A fifth
boot, using the native control disk with the board removed, found zero HQ4
widgets and issued no draw. The release labels identify the two disk images.
This check exercised native NetBSD. Octane Xorg, IRIX applications
and physical hardware need their own tests. Each run verified the source disk
and firmware hashes. [Per-run evidence](2026-11-23-octane-rectangle.json)

The IRIS fork merged 15 upstream commits through `a05289ef` at `08e53ba7`,
including changes to IOC3 serial timing. All 686 selected device and machine
tests and the three snapshot fixture checks passed. The first Solid IMPACT
capture also passed on the previously qualified interpreter at `592df243`.

## Reproduction

Start in the Xiri checkout with the Octane NetBSD topic at `8f744b33e95`,
the sgimips cross tools and a new build directory. The opt-in drawing kernel
uses the IMPACT register definitions from the NetBSD integration branch.
The original inventory kernel still builds without the drawing code.
[Previous native boot and firmware setup](2026-11-23-octane-impact.md)

```sh
repo=$(pwd -P)
tools="$repo/.work/netbsd-octane-build/tools/bin"
build="$repo/.work/ip30-rectangle-rebuild"
mkdir -p "$build"
git -C ../NetBSD-xiri show 60dd809ab7a:sys/arch/sgimips/gio/impactreg.h > "$build/impactreg.h"
"$tools/nbconfig" -s "$repo/../NetBSD-xiri/sys" -b "$build" \
    "$repo/lab/ip30-impact/XIRI_IP30_HQ4_FILL"
(cd "$build" && "$tools/nbmake-sgimips" -j2 depend netbsd)
```

Run the boot check on a host with Python 3, Pillow and the IRIS runtime
libraries. The serial firmware must have `console=d`. Each run uses a
private CHD copy. Pick a fresh output directory.

```sh
python3 lab/ip30-impact/check.py --rectangle --board highimpact \
    --emulator .work/octane-fill/emulator --kernel "$build/netbsd" \
    --firmware .work/octane-m4a-phys-readonly-20261116 \
    --disk .work/m4a-root.chd --output "$build/check-high"
```

The HQ4 FIFO layout and raster setup follow the local SGI IMPACT register
catalogue and the OpenBSD IMPACT driver. The kernel retains PROM display
timing and runs the test over the IOC3 serial console. A wsdisplay
attachment is the next step toward a graphical console and Xorg on Octane.
[OpenBSD impact(4)](https://man.openbsd.org/OpenBSD-6.6/impact.4)
