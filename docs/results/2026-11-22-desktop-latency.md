# 4Dwm dragging and winterm scrolling on Indy and Indigo2

A held title-bar move and an eight-line winterm scroll both took longer to appear on emulated High IMPACT than on Newport. The comparisons below used the same IRIS executable and a separate, cold-booted Xiri disk for each machine and vendor release. Each timed guest ran alone.

| IRIX release | Visible operation | Indy / Newport | Indigo2 R10000 / High IMPACT | Indigo2 ÷ Indy |
| --- | --- | ---: | ---: | ---: |
| 6.5.22 | 112-pixel 4Dwm move | 82 ms | 237 ms | 2.9× |
| 6.5.22 | Eight-line winterm scroll | 137 ms | 220 ms | 1.6× |
| 6.5.30 | 112-pixel 4Dwm move | 135 ms | 236 ms | 1.8× |
| 6.5.30 | Eight-line winterm scroll | 136 ms | 235 ms | 1.7× |

Each figure is the median of eight wall-clock observations. The Indy used its qualified R4400 configuration for 6.5.22 and R5000 with shadow cache for 6.5.30. Both Indigo2 images use the R10000. The comparison measures the complete emulated workstation, including the CPU, OS, Xorg, native driver, guest scheduling and host display sampling.

## What moved on screen

The test logged in through xdm as `xiritest`. It selected opaque movement, pressed and held the 4Dwm title bar of the existing 639×300 winterm, and alternated its position between (170, 160) and (282, 160). The client geometry followed the pointer before button release. All four runs used a 56-column, 15-row terminal. The scrolling stimulus wrote eight lines through its existing PTY and moved the old glyphs up 160 pixels.

Timing started when the host submitted each serial trigger. It ended on the first capture in which at least 98% of the stable, changed pixels matched the destination state. Both states were observed twice during calibration. Median capture times ranged from 59 to 78 ms, so the observations are upper bounds on visible completion under this sampler. They describe discrete moves and bursts of text. Continuous drag frame rate and physical SGI hardware require their own measurements.

[Screenshot during a held move](2026-11-22-desktop-latency-winterm.png) · [Sample timings, transfer counts, hashes and pixel checks](2026-11-22-desktop-latency.json) · [Reproduce the benchmark](../../lab/ip28-kernel/README.md#measuring-4dwm-and-winterm)

## Where to spend the next driver cycle

Xorg on the Indigo2 uses `wsfb` and draws into RAM. The native IMPACT worker compares that image with its previous image, sends changed spans or fills through the command FIFO, then sleeps for roughly 50 ms of guest time. The Indy Xorg driver uses its Newport acceleration path. [Earlier fill and copy measurements](2026-11-22-ip28-2d.md)

Across the eight timed transitions, the emulated IMPACT raster engine reported these 64-bit programmed-I/O transfer counts. Each doubleword carries up to eight bytes. The counts include background desktop drawing. The record includes one-second idle controls.

| IRIX release | Window moves | Terminal scrolls | DMA bytes in either workload |
| --- | ---: | ---: | ---: |
| 6.5.22 | 498,848 | 277,696 | 0 |
| 6.5.30 | 506,624 | 272,384 | 0 |

In each run all 56,740 changed pixels in the sampled moving window interior matched pixels already visible 112 pixels to the left. All 19,859 compared glyph pixels in the retained rows matched their previous positions eight rows down. This makes an overlap-safe rectangle copy the first acceleration candidate. Newly exposed areas still need repainting.

First qualify the board operation in isolation with overlapping copies in both directions, clipped rectangles, and matching scanout and RAM contents. Then connect the successful operation to Xorg and repeat these two workloads on both release lines. Keep the current `wsfb` path as the baseline. NetBSD already defines `WSDISPLAYIO_DOBLIT` and `WSFB_BLIT_COPY` in `sys/dev/wscons/wsconsio.h`. The OpenBSD IMPACT console reference in `../sgi/impact/originals/openbsd/impact.c` implements console scrolling by repainting characters. A native High IMPACT copy command still needs a verified implementation.

## Revisions and qualification

The benchmark used the accelerated IRIS binary from the qualified interactive image bundle. During this cycle the IRIS fork merged three upstream commits through `6b6c8cea` and pushed `775be6ce` on `xiri`. They cover JIT software interrupts and Origin/VPro tracing. The interrupt, tracing, flow-control and Bedrock PI groups passed 42 tests in total, with two tracing tests ignored. Xiri’s 83 host tests passed with loopback access.

The initial 6.5.22 pilots overlapped other jobs and were excluded from the table. The four reported guests each returned to PROM after shutdown and retained the expected SHA-256 of their base CHD.
