# Window copies on Indigo2 High IMPACT

On native IRIX 6.5.22f, Xsgi handled an overlapping 144×95 TrueColor
`XCopyArea` with two DMA reads into system RAM and one DMA write back to
the destination. The reads split each row into 137 pixels and seven pixels.
The write covered the full 144. All three operations shared one staging
buffer and a stride of 576 bytes. The counters advanced by exactly
109,440 bytes, twice the size of the rectangle. They stayed still during a
one-second idle control. [Captured HQ3 and raster commands](2026-11-22-impact-xsgi-copy.trace.gz)

SGI describes a raster-engine-to-geometry-engine path for screen copies.
IRIS names the HQ3 tokens `FAST_COPY_PIXELS` and `COPY_PIXELS` in its
trace decoder. The observed Xsgi command stream used the host DMA engine.
This test establishes the path used by this X server and visual. The
microcode sequence for an entirely on-board copy remains an open question.
[SGI Indigo2 IMPACT hardware guide, §1.8.1](https://techpubs.jurassic.nl/manuals/hdwr/service/108-0131-002.pdf)

## Pixel checks

The test reseeded a 192×128 window before each copy. It exercised overlap
left, right, up, down and diagonally, destination clipping, a one-pixel
corner, and identical source and destination. A saved image of the source
specified the expected displayed result, including every pixel outside the
destination. XGetImage independently checked the X server. On NetBSD the
client also read the wsdisplay framebuffer, and the host checked the emitted
RGB values. Native Xsgi uses its own display gamma.

The qualified PIO kernel passed all ten cases on both Xiri release lines.
For the 144×95 copy it sent 9,120 programmed-I/O doublewords on each
release, with zero DMA bytes. Native Xsgi passed the same ten cases
with zero programmed-I/O pixel transfers in the measured copies. The
capture and counter window ended before XGetImage. [Machine-readable results](2026-11-22-impact-window-copy.json) · [Reproduction](../../lab/ip28-kernel/README.md#checking-overlapping-window-copies)

## NetBSD upload prototype

Xorg already performs the overlap-safe copy into RAM. The driver can upload
the completed destination directly to HQ3, avoiding a readback to stage
the source. The prototype uses a private bus_dma buffer and an HQ3 page
table, explicit cache synchronization, and a bounded wait for completion.
It collects nearby changed pixels from eight scanlines at a time. Small
changes can use the existing PIO path and solid regions can use the
hardware fill. The wsfb/Xorg interface stays the same.

The first DMA build exposed a red/blue channel reversal on scanout. The
X server's readback was correct. Comparing the displayed seed against its
expected colour values caught 24,384 mismatched pixels out of 24,576.
The second build swaps the two colour lanes when preparing the DMA payload.

Both Xiri release lines then passed all ten cases with zero RGB, scanout,
XGetImage or framebuffer mismatches. For the 144×95 rightward copy, each
issued 13 host-to-board writes (79,872 bytes), with zero board reads and
zero programmed-I/O pixels. Eight-line bands and 64-pixel tile boundaries
explain why the uploads cover more than the 54,720 bytes of destination
pixels. The one-pixel corner case used the small PIO path. A copy to the
same coordinates produced no pixel traffic.

IRIS upstream was checked at `6b6c8cea`. The fork's `xiri` branch at
`775be6ce` already contained it. The reference and candidate runs used the
same archived accelerated IRIS binary as the [Indy and Indigo2 baseline](2026-11-22-desktop-latency.md).

## Interactive latency

Each value is the median of eight trials, measured from the serial trigger to the first scanout matching at least 98% of the changed pixels.

| IRIX userspace | Operation | Indy / Newport | Indigo2 PIO | Indigo2 DMA |
| --- | --- | ---: | ---: | ---: |
| 6.5.22 | 112-pixel 4Dwm move | 82 ms | 237 ms | 165 ms |
| 6.5.22 | Eight-line winterm scroll | 137 ms | 220 ms | 157 ms |
| 6.5.30 | 112-pixel 4Dwm move | 135 ms | 236 ms | 174 ms |
| 6.5.30 | Eight-line winterm scroll | 136 ms | 235 ms | 170 ms |

The two Indigo2 runs used the same R10000 profile, accelerated IRIS executable and framed base image for each release. Each timing guest ran alone. The sampling interval and capture cost limit the precision of these wall-clock comparisons. The raw samples, transfer counters and idle controls are in the machine-readable record.

Scrolling preserved all 19,859 sampled glyph pixels on each release. Across
the two workloads, the Indigo2 medians improved by 26–30%. The Indy remained
faster in every comparison. The driver and kernel option are on the NetBSD
fork at `60dd809ab7a`. The fallback driver also cross-compiled with
`IMPACT_DMA` disabled. All 172 imports in the existing IRIX kernel module
resolved in the new kernel.

## Manual test images

Each standalone CHD was verified with chdman and cold-booted through the saved graphical PROM settings. Both passed the framed console, keyboard and debugger checks. Each image started 4Dwm for xiritest, ctwm for netbsdtest, and a second 4Dwm session for xiritest, then returned to xdm after logout and to the PROM on shutdown. The previous framed-console CHDs are kept separately.

- **6.5.22** — `.work/native/xiri-ip28-dma-6.5.22-20261122/run-iris.sh`. [4Dwm screenshot](2026-11-22-impact-dma-6.5.22.png)
- **6.5.30** — `.work/native/xiri-ip28-dma-6.5.30-20261122/run-iris.sh`. [4Dwm screenshot](2026-11-22-impact-dma-6.5.30.png)

The retained native kernel, debug symbols, loader, module and kernel configurations are in `.work/native/netbsd-ip28-dma-20261122/`. Both launchers select the Indigo2 R10000 with one High IMPACT display. The qualification used the emulator. Physical High IMPACT hardware still needs a separate test.
