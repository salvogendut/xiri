# Native xdm image baseline

This directory pins the kernel/module pair used by the xdm CHD. NetBSD
`xiri` commit `9390bc04900a0d04796d494aca5b00651f12954d` adds the native UVM
allocation fix documented in the [fault investigation](../../docs/results/2026-11-03-uvm-pglist.md).
The [image record](../../docs/results/2026-11-03-xiri-xdm-image.md) owns the
preparation, disk-boot and session results. The older `lab/irix-module` pins
remain unchanged for reproduction.

Build from the NetBSD integration checkout into a fresh output directory:

```sh
XIRI_NETBSD_SOURCE_DIR="$PWD/../NetBSD-xiri" \
XIRI_NETBSD_BUILD_DIR="$PWD/.work/netbsd-xdm-build" \
XIRI_NETBSD_TFTP_DIR="$PWD/.work/netbsd-xdm-build/tftp" \
XIRI_NETBSD_CONFIG="$PWD/lab/irix-module/XIRI_IRIX_MODULE" \
XIRI_NETBSD_ARCH=mips64eb XIRI_BUILD_JOBS=2 \
  scripts/build-netbsd-kernel.sh all
python3 scripts/build-irix-module.py --build .work/netbsd-xdm-build
python3 scripts/test-uvm-pglist.py
```

The recorded build reused a copy of the existing mips64eb toolchain and ran
the `kernel` operation in a new object directory. The commands above also
build the toolchain when starting fresh. A rebuild can have different hashes;
create new build/baseline manifests for those artifacts rather than replacing
the checked-in pins or previously qualified outputs.

`build.json` records the matched artifacts, module imports/relocations and
source hashes, including `sys/uvm/uvm_pglist.c`. `image-baseline.json` retains
the qualified emulator and vendor-runtime hashes while selecting this new
kernel/module build. No vendor payload is stored here.
