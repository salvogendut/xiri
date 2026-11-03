# Framed console and accelerated Newport trial

The user requested `feature/newport-framed-console` and enabled Xorg Newport
acceleration. The established `20261102-behavior` CHD and its software-rendered
configuration remain preserved for comparison.

The build snapshot is based on NetBSD commit
`314c8c32e84e41a0eda05366d3004bb10a68c86e`, with the branch's then-uncommitted
framed-console work copied into `.work/netbsd-newport-frame-src`.
`source-snapshot.json` records the tracked patch and every untracked input.
The exact patch and extra files are retained in
`.work/newport-accel/source-snapshot`; the active shared checkout is untouched.
A branch name or base commit alone does not reproduce this working snapshot.

During the trial, the frame's owning task committed it as
`a536d8c4da20c1eef2c7ff209ba51223dde00b61`. All twelve files in that commit
were compared byte-for-byte with the build snapshot; the
`committed-source-equivalence.json` record preserves their hashes. The
original build provenance remains explicit rather than being relabeled as
a build performed from a clean commit. The checkout is now `../NetBSD-xiri`,
with `../NetBSD-nixbench` retained as a compatibility symlink.

`XIRI_NEWPORT_FRAME` combines GENERIC64_IP2x, COMPAT_IRIX_O32 and NEWPORT_FRAME.
It retains the existing o32/n32 desktop compatibility while enabling the
framed console. Build it with the established mips64eb toolchain:

```sh
XIRI_NETBSD_SOURCE_DIR="$PWD/.work/netbsd-newport-frame-src" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-newport-frame-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-newport-frame-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/newport-accel/XIRI_NEWPORT_FRAME" \
XIRI_NETBSD_ARCH=mips64eb XIRI_BUILD_JOBS=2 scripts/build-netbsd-kernel.sh kernel
```

The current IRIS `xiri` integration revision is built separately under
`.work/target-newport-accel`. Its source revision and executable hashes, and
the kernel hashes, are recorded in `corrected-baseline.json`.
No qualified emulator executable is overwritten.

The native drawing comparison reuses the existing fill/copy/XOR/upload,
composed-pixel and keyboard/mouse tests on a disposable prepared-image copy:

```sh
XIRI_IRIS_BIN_DIR="$PWD/.work/target-newport-accel/release" \
  python3 scripts/qualify-netbsd-x11.py --mode ordinary --boot-timeout 600 \
  --seed .work/xiri-image/prepared-seed-20261102-behavior \
  --baseline lab/newport-accel/corrected-baseline.json \
  --kernel-build .work/netbsd-newport-frame-build
```

Repeat with `--accelerated` and compare both results. A drawing failure is
retained as a failure even when Xorg and applications continue running.
This checks correctness; complete run times include boot/startup and are not
acceleration benchmarks.

The graphical image test installs `xorg.conf` from this directory, where
`NoAccel` is false, and uses the same isolated kernel and emulator:

```sh
python3 scripts/probe-xiri-desktop-usability.py \
  --seed .work/xiri-image/prepared-seed-20261102-behavior \
  --kernel-build .work/netbsd-newport-frame-build \
  --baseline lab/newport-accel/corrected-baseline.json \
  --iris-bin-dir .work/target-newport-accel/release \
  --xorg-config lab/newport-accel/xorg.conf --arrange-winterm
```

`--arrange-winterm` records the initial window geometry and resizes it for
diagnostic input checks. It leaves the installed launcher unchanged; the
intermittent font-metric/startup-size issue is not qualified by this run.

Capture and compare the console before and after Xorg, as well as the desktop.
Package only a cleanly halted disk; keep diagnostic images distinct from the
qualified software-rendered image when rendering checks fail.

## Corrected renderer

`corrected-baseline.json` keeps the same kernel/resource provenance and pins
IRIS `xiri` commit `819c6825504d40ad9f9aa00554249affd2da9446`. Use this baseline
for the corrected native and desktop commands above. `baseline.json` and the
before-fix results remain the original failing trial. The corrected native
probe adds channel-mask fill/copy checks: all 20 composed samples and XGetImage
readbacks pass, and its software/XAA PNG files are identical.

The [cycle record](../../docs/results/2026-11-02-newport-framed-acceleration.md)
links the positive and negative tests. The hardware reference discovery is
recorded in `hardware-sources.json`; `../sgi` led to the RB2 specification.

Build the manual bundle with `scripts/build-xiri-image.py --iris-bin-dir`
to include exactly the pinned IRIS and iris-ci executables. The generated
`run-iris.sh` uses that local backend. An existing Prismatic binary embeds its
own backend and needs rebuilding before it can provide the same correction.

The final native regression also checks narrow subrectangles, shifted mask
origins, monochrome expansion, little-endian image data and overlapping copies
in all eight directions (1,404,075 image-pixel comparisons). At this checkpoint,
full-desktop XAA still corrupts xmahjongg artwork. Disabling image writes, color expansion or
screen copies individually does not fix it. The manual accelerated bundle is
explicitly experimental and does not replace the software-rendered image.

After a clean direct CHD probe, use `scripts/qualify-xiri-image.py
--record-bundle` to retain the verification and tested diagnostic NVRAM in
this bundle. Omit `--promote` for this older control; the default image pointer
follows the newer tested bundle. The graphical NVRAM is preserved.

The subsequent [Xorg texture repair](../newport-xaa/README.md) fixes that game
corruption while retaining this kernel/emulator pin. Keep this earlier CHD
and its manually used NVRAM/overlay as controls; use the new bundle for the
patched Xorg module. The promotion instructions above apply to this older
control, not to the replacement image.
