# Indy hard links, SGI Clock and xosview

The experiments used private copies of the 6.5.22f R4400 and 6.5.30f
R5000 v4 Indy images. Each cold-booted the modular NetBSD 11.99.11 kernel.
For graphical checks, xiritest logged in through xdm to the 1280×1024
Newport Xorg desktop.

## Timezone aliases

The [previous installer run](2026-11-24-indy-inst-followup.md) isolated
a missing syscall when SGI's `zic` created an alias. IRIX trap 1009 now
passes both foreign pathname pointers to native `do_sys_linkat`. Its
flags preserve a source symlink, including one whose target is absent.
SGI documents this distinction for its two hard-link interfaces.
[IRIX link(2)](https://www.typewritten.org/Manual/SGI/IRIX/6.5.3f/man2/link.html)

Each release's own overlay compiler exited 0. Its primary zone and its
alias had the same device and inode and a link count of two. Removing
the primary left a nonempty compiled alias with a link count of one.
Direct o32 and n32 callers also verified ordinary files, dangling symlinks,
an existing destination (`EEXIST`), a missing source (`ENOENT`), and a
directory source (`EPERM`). Run the [guest regression](../../lab/irix-installer/check-zic-links.sh)
with the matching vendor compiler. The wider base-install exit hooks still
need an end-to-end run.

## SGI Clock

The DesktopTools entry selects `/usr/sbin/clock`. Its parent exits 0
after forking. On both releases the child exited with status 255 before
mapping a window. In both executables, `main` calls `fminit()`, then
`fmfindfont("Iris")`. At `0x10005158` a null handle branches to
`exit(-1)`. Path tracing showed the child looking up SGI's bitmap font
indexes and `/usr/lib/X11/fonts/ps2xlfd_map`. Original IRIX
`/usr/bin/X11/xclock` mapped its window on the same authenticated display.

We tried the SGI Foundation 1 font map alone and the child still exited
255. We then installed `iris10.pcf.Z`, `iris12.pcf.Z` and `iris13.pcf.Z`
under `/emul/irix/usr/lib/X11/fonts/misc` and ran NetBSD's `mkfontdir`
there. The bitmap digests match both releases' first overlays. The overlay
map has additional entries and the same `Iris` mapping as the Foundation
map. With the indexed bitmaps installed, both displays stopped serving
clients during Clock startup. Both Xorg logs recorded signal 11 with the
same stack through GLX dispatch and Mesa's `swrast_dri.so`.
The font additions were confined to the private test disks. The [Background
panel check](2026-11-06-desktop-colours.md) previously encountered this
rendering path in another SGI client.

The [Xorg follow-up](2026-11-24-indy-glx.md) shows Clock rendering and
advancing on both releases with the corrected server and GLX module.

During teardown both guest session supervisors reported zero sessions left.
Both shutdowns then waited at `Stopping xdm`. The two disposable emulator
process groups were stopped from the host.

## SGI Freeware xosview

The clean original-media profiles omit xosview. For this check we staged
the same original n32 Freeware executable on both releases and used each
desktop's own shared libraries. It printed `sysinfo scall interface not
supported`, exited 0 and left no window. Its CPU-meter constructor calls
`sysmp(MP_SASZ, MPSA_SINFO)` and takes the diagnostic branch when the
kernel returns an error. This is a request for the size of the system
activity record. The binary also asks for the processor count and the
real-memory record size. Xiri currently implements the page-size query.

Supporting the default meters requires real counters as well as record
sizes. The CPU reader in the binary uses `MP_SAGET` for totals and
`MP_SAGET1` for one CPU. SGI's installed SDK headers identify the activity
and memory selectors as `MPSA_SINFO` (1) and `MPSA_RMINFO` (8).
The [earlier syscall capture](2026-11-02-irix-elfmap-high.md) recorded the
processor count and both size queries returning `ENOSYS`.

## Revisions

The NetBSD module change is on `xiri` at `344706654ba`.
Both guests loaded module SHA256
`ad182dbb2bb0e36eca636dc2f2989ed1bc79eae0c313bb5fbb61a9b60d9830b8`.
IRIS `xiri` at `39ef6dff` already contained upstream `057ba095` when
fetched for this cycle. All 94 host tests passed. The published v4 CHD
and NVRAM checksums still match both release manifests. The [per-release
records](2026-11-24-indy-link-clock-xosview.json) pin the binaries and
record the observed process and filesystem outcomes.
