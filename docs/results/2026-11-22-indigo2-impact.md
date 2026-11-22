# Indigo2 R10000 / High IMPACT investigation, 2026-11-22

The IMPACT GPU failure reported in the November 22 IRIS refresh came from
an out-of-range read in the regression test. The correction is committed
and pushed on IRIS `xiri` as
[`eb21c6ec`](https://github.com/salvogendut/iris/commit/eb21c6ec).
It changes the test and its investigation notes; production rendering,
shaders and readback code are unchanged.

## What failed

`dev::mgras::wgpu::tests::transfer_reads_see_the_drawing` uses seed `0x4EAD`.
At step 64 it armed a transfer from `(42,38)` to `(71,40)`, a three-row
block, with 42 output bytes per row. Its independently randomized read count
then requested line index 4, the fifth row.

The GPU renderer refreshes its CPU mirror only within the armed transfer
rectangle. The reference CPU renderer already has all its pixels in memory.
Comparing a row outside that rectangle therefore compared an unsynchronized
GPU mirror with the current reference image. A diagnostic full synchronization
made the failing line match exactly.

The test now limits its reads to `transfer_shape().0`. It retains the random
draw, the fixed seed, the requirement to read more than 500 lines and the
assertions that real GPU readback occurred.

| Check | Result |
| --- | --- |
| Original test, unchanged integration | Reproduced step 64 / line 4 failure |
| Diagnostic full synchronization | Failing line then matched the CPU reference |
| All IMPACT wgpu tests with bounded reads | 13 passed |
| Final readback test, hardware Vulkan | Passed |
| Final readback test, Lavapipe software Vulkan | Passed |

The all-13 run still contained the failure-only diagnostic; it was never
triggered. The two final targeted runs used the published patch with that
diagnostic removed. No GPU initialization was skipped.

## Native Indigo2 setup

The guest uses the already-qualified November 22 accelerated binary from
IRIS `0bc52567`, whose production code is unchanged by `eb21c6ec`:

- `machine.profile = "indigo2_ip28"`, `cpu = "r10000"`;
- built-in IP28 PROM 6.2 Rev A, reporting a 195 MHz R10000;
- `banks = [512, 512, 0, 0]`, 1 GiB RAM;
- `graphics.board = "highimpact"`, one head, guest-selected resolution;
- `graphics.raster = "wgpu"`, `gpu_backend = "vulkan"`;
- host adapter: AMD Radeon 780M, RADV / Mesa 26.2.5;
- a new private 8 GiB CHD at SCSI ID 1, with independent EEPROM and NVRAM.

Graphics remain enabled during installation so `inst` selects the graphics
drivers. The original installation ISOs are served by Prismatic's existing
Instigator binary over a private Unix network socket. Existing donors and
Xiri preview images are unchanged.

Both release lines were attempted separately:

| Release | Native IP28 result |
| --- | --- |
| 6.5.22f | Original-media installation, disk boot, native desktop and graphics readback passed |
| 6.5.30 | Original `sash64` loader refuses the platform before copying the miniroot |

The 6.5.30 loader prints `Platform Unsupported in this level of IRIX..`.
That attempt was stopped, its never-installed disk removed, and the console
evidence retained. This is separate from the IMPACT test failure. The existing
6.5.30 O2/Octane installations and NetBSD/Xiri preview remain available;
this investigation does not produce or qualify a 6.5.30 Indigo2 image.

### Native graphics validation

The installed system reports `6.5 6.5.22f`, a 195 MHz IP28/R10000,
1024 MiB RAM, and High IMPACT with one GE, one RE and four TRAMs.
`gfxinfo` reports 1280×1024 at 60 Hz. Native Xsgi, 4Dwm and Toolchest
run successfully, and Icon Catalog displays its application icons.

After a clean shutdown, the installation was folded into a standalone
compressed CHD with `chdman copy`, verified with `chdman verify`, and cold
booted without Instigator or installation media. Normal graphical root
login works on both boots. Root autologin remains disabled.

The existing local IRIS `test/gltest/glprim` executable is an IRIX n32
MIPS-III binary, used as-is and identified by SHA-256 in the JSON record.
This command exercises drawing and two native pixel-read paths:

```sh
DISPLAY=:0 /tmp/glprim --size 64x64 --prim points --mono --rgb 1,1,1 \
  --clear 1,0,0 --nodither --read ximage,front \
  --readout /tmp/impact-readback --hold 500
```

Both XGetImage and OpenGL `glReadPixels` return OpenGL error zero and the
same checksum, `e9fd2bf7`. The two retrieved PPMs are byte-identical:
all 4,096 pixels match, comprising 4,093 red background pixels and three
white points. Their SHA-256 is
`40e335ee4eb13e46cd7938317b25f08d9dfe62da1d06aadd8d6a39abdd4b7033`.

A separate smoothly shaded OpenGL triangle and native xclock are visible
in the [desktop PNG](2026-11-22-indigo2-impact.png), alongside Toolchest
and populated Icon Catalog. Mouse-driven window movement also worked.
The recorded IMPACT counters show 31,605 GPU records in 420 batches,
zero dropped records, and 14 MiB of GPU readback in 82 synchronizations.
The host window uses the GL presenter; the IMPACT rasterizer uses Vulkan.

This is a focused native IRIX graphics qualification. It does not establish
complete OpenGL coverage or NetBSD/Xiri support on IP28.

### Manual use

The separate native image bundle is
`.work/native/indigo2-ip28-6.5.22f-20261122/`. From the Xiri repository:

```sh
./.work/native/indigo2-ip28-6.5.22f-20261122/run-iris.sh
```

The PROM boots the disk automatically. Firmware output remains on serial;
the visible display appears when Xsgi starts. Select `root` at the normal
graphical login and use the fresh installation's empty password. The image
does not enable root autologin. Shut down through IRIX when finished.

The standalone CHD is 8 GiB logically and about 580 MiB compressed. Its
SHA-256 is `cb5f8b5bd3417acf53092e1f25fb5d1e73d932bf53189344a7b613fc70071414`.
The launcher uses a private write overlay, the existing accelerated IRIS
binary, and the bundle's independent PROM state. Keep the overlay to retain
manual-test changes. The probe executables and scratch disk are excluded.

The final packaged configuration was tested without entering any PROM commands:
it booted automatically, reached the normal graphical login with zero pixels
differing from the reference capture, and shut down cleanly. The bundle includes
`qualification.json` with its configuration and firmware hashes.

### Installation sequence

Use the [Prismatic original-media installation procedure](https://github.com/salvogendut/prismatic/blob/main/docs/installing-irix.md)
with the IP28 configuration above. For this machine, the network paths are:

```text
setenv netaddr 192.168.0.2
bootp():/6.5.22/stand/fx.64 -x
```

In `fx`, select controller 0 / drive 1, repartition as a root disk with XFS,
write the SGI label, and return to PROM. Before loading the installer:

```text
setenv SystemPartition scsi(0)disk(1)rdisk(0)partition(8)
setenv OSLoadPartition scsi(0)disk(1)rdisk(0)partition(0)
unsetenv OSLoader
unsetenv OSLoadFilename
unsetenv OSLoadOptions
setenv tapedevice bootp():/6.5.22/dist/sa
boot -f $tapedevice(sash64) --m
```

The miniroot copies to swap and boots `dist/miniroot/unix.IP28`. Create the
new XFS root with 4096-byte blocks. In `inst`, select the feature stream and
open all three 6.5.22 overlays, both 6.5 foundations and the November 2003
applications catalog. Use `keep *`, `install standard`, and resolve the
optional Java/Mozilla and Inventor development prerequisites by deselecting
`java2_plugin.sw32.mozilla_freeware`, `inventor_dev.sw.base` and
`inventor_dev.sw.lib`. Proceed only after `conflicts` reports no conflicts.

## Evidence and source status

The local evidence directory is `.work/iris-impact-20261122/`. It contains
the patch, lockfile, baseline and passing test logs, machine configurations,
original-media catalog checks, and serial/installer logs for both releases.
The [machine-readable result](2026-11-22-indigo2-impact.json) records the
native readback comparison, manual boot check, artifact hashes and cleanup.

IRIS upstream was fetched and checked at
`6ec1ebf379228d572026a9ae8d291511ed28af74`; there were no new commits beyond
the earlier November 22 integration. The temporary topic branch and source
worktree were removed after pushing `eb21c6ec`, and the private build target
was deleted. The last qualified artifacts for both vendor releases are preserved.

All test emulators and the build container started for this investigation are
stopped. Installation overlays, the unsupported-release blank disk, scratch
disk, temporary source/build tree and test-only write overlays were removed.
Together these occupied approximately 2.45 GiB of allocated storage; the
filesystem's measured free-space gain during cleanup was approximately
1.26 GiB, with compression and other activity affecting that measurement.
The retained manual image is about 580 MiB, plus small configuration and
evidence files. Its files belong to the host user so the launcher can write
its local overlay and PROM state.
