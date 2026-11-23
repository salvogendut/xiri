# O2/R10000 qualification fixture

The emulated O2 boots from its own SCSI disk on both the 6.5.22 and 6.5.30
Xiri lines with the R10000 JIT. See the [November 23 disk boot check](../../docs/results/2026-11-23-o2-r10000-boot.md) for launchers, screenshots and the graphical results.

The original November 14 run stopped during AIC-7880 attachment. On
November 15 the IRIS fix for the wide MACE PCI address window let the same
kernel reach single-user NetBSD in the interpreter. [Original result](../../docs/results/2026-11-14-irix-6.5.30.md) · [November 15 record](https://github.com/salvogendut/NetBSD-xiri/blob/33b5dda6a45/xiri/platforms/2026-11-15-results.json)

`XIRI_O2` includes NetBSD's `GENERIC64_IP3x`, `MODULAR`, a symbol table and an
`sd0a` root. The compatibility personality remains a loadable module. The
native userland/X sets are NetBSD 11.0 o32. `xorg.conf` selects the stock
`crime` driver at 1280×1024. O2 requires `ip3xboot` in the SGI volume header,
`mec0` Ethernet and `ttyC0` for the first serial port.

The final November 23 disks use the newer `compat_irix_o32.kmod` from
`.work/octane-frame/qualified/` with the retained IP32 kernel. The original
O2 module below predates the 6.5.30 n32 interpreter fix.

The retained build is `.work/netbsd-o2-build/`; [build.json](build.json) pins
the kernel, boot wrapper and module. It was built from NetBSD `xiri`
`a4a70956805` plus the cache-alignment correction subsequently committed as
`2a7184ec4c6`. Its source patch and before/after regressions are retained under
`verification/`. No previously qualified Indy artifacts were overwritten.

With isolated MIPS64 tools/obj directories prepared, the kernel command is:

```sh
xiri_repo=$PWD
(
  cd ../NetBSD-xiri
  ./build.sh -m sgimips -a mips64eb -U -u -j 2 \
    -O "$xiri_repo/.work/netbsd-o2-build/obj" \
    -T "$xiri_repo/.work/netbsd-o2-build/tools" \
    -D "$xiri_repo/.work/netbsd-o2-build/dest" \
    -V MKX11=no -V 'HOST_CC=cc -std=gnu17' -V 'HOST_CFLAGS=-O2 -std=gnu17' \
    kernel.gdb="$xiri_repo/lab/irix-o2/XIRI_O2"
)
```

Run from the Xiri checkout; the recorded build used the NetBSD source as its
working directory with absolute paths. Stage `netbsd` under `kernel-media/`
and `netbsd.elf32` as `tftp/netbsd-XIRI_O2`, then run:

```sh
python3 scripts/build-irix-module.py --build .work/netbsd-o2-build \
  --config lab/irix-o2/XIRI_O2 \
  --boot-kernel .work/netbsd-o2-build/tftp/netbsd-XIRI_O2
python3 lab/irix-o2/check-cache-alignment.py \
  ../NetBSD-xiri/sys/arch/mips/mips/cache_r10k.c
```

The alignment regression extracts the actual secondary-cache macros and
checks 32/64-bit arithmetic with 64/128-byte lines and high kernel addresses.
It fails on the original source for 64-bit addresses. A new kernel build
requires updated hashes/provenance and its full `kern.version` digest in
[`netbsd-sgimips-o2-native-v1.json`](../../profiles/netbsd-sgimips-o2-native-v1.json).
The build-specific package uses five explicit artifacts (kernel, boot,
module, FAM, rpcbind), without the Indy Newport replacement.
The vendor profile's descriptive native-prerequisite list was inherited from
the Indy import and mentions Newport; the O2 native profile supplies `crime`
instead. Vendor payload files do not select the native display driver.

The disposable trial command is:

```sh
python3 scripts/prepare-o2-platform.py \
  --base .work/images/xiri-netbsd-desktop-20261114-controls \
  --kernel-build .work/netbsd-o2-build \
  --native-package .work/packages/netbsd-sgimips-o2-native-v1 \
  --payload .work/imports/irix-6.5.30f-v1 \
  --emulator .work/emulators/iris-xiri-20261114-r5k-config \
  --nvram .work/donors/irix-6.5.30f-original-media/nvram.bin \
  --output .work/o2-6.5.30-prepare
```

The output directory must be new. This fixture intentionally uses serial
single-user boot while preparing a private image and flash copy. It network
boots the matching kernel with `boot -f bootp():netbsd-XIRI_O2 --s` and fails
early if the kernel traps. The November 23 cold-boot check starts from a separately prepared disk for each vendor release. The 6.5.22 reference remains the selected manual image.

Temporary compiler outputs and failed guest disks are removed after retaining
the build artifacts, logs, exact executed probes and failure evidence. Rebuild
the isolated tools/objects before doing another kernel development cycle.
