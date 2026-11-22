# Native NetBSD on Indigo2 IP28

This fixture qualifies the first native IP28/R10000 kernel: ARCS64 startup,
1 GiB RAM, serial console, interrupts/timers, HPC3 SCSI/FFS, Ethernet and
clean halt. It does not qualify an IMPACT framebuffer, Xorg or an IP28 IRIX
compatibility module. See the [result](../../docs/results/2026-11-22-ip28-kernel.md).

## Build

Use the NetBSD fork's `xiri` branch containing `GENERIC64_IP28`. The script
uses an existing cross-toolchain without rewriting its shared wrappers.
All outputs go into the supplied directory; compilation uses two jobs.
Run this in the existing build container where the tools execute:

```sh
lab/ip28-kernel/build.sh NETBSD_SOURCE NETBSD_TOOLS BUILD_DIRECTORY
```

The kernel is `BUILD_DIRECTORY/kernel/netbsd`, an ELF64 image linked at
`0xa800000020080000`. An optional fourth argument selects another kernel
configuration for regression builds. The standalone loader is built with
[the boot64 fixture](../ip28-boot64/README.md); its load address is
`0xa800000020003000`.

## Prepare an isolated disk

Keep the two release lines separate. Use the respective qualified
6.5.22 or 6.5.30 Xiri base CHD; the native checks do not run its vendor desktop.
Create a Rock Ridge ISO containing `netbsd`, `ip28boot` and a NetBSD-format
`SHA256` manifest, then run:

```sh
python3 lab/ip28-kernel/check.py \
  --iris IRIS_BINARY --disk BASE_CHD --tftp BUILD_DIRECTORY/kernel \
  --media INSTALL_ISO --output PREPARATION_DIRECTORY
```

The script uses a private copy-on-write overlay, fresh firmware state and
private control ports. It selects `sd0a` during the initial TFTP boot, checks
native commands and installs `/netbsd.ip28` and `/usr/mdec/ip28boot`. It writes
`ip28boot` as `boot` in that overlay's volume header. The existing `/netbsd`
and IRIX module are retained, but are not qualified as an IP28 pair.

Then cold-boot through the installed loader:

```sh
python3 lab/ip28-kernel/check.py \
  --iris IRIS_BINARY --disk BASE_CHD --kernel netbsd.ip28 \
  --overlay-dir PREPARATION_DIRECTORY --output DISK_BOOT_DIRECTORY
```

A pass requires the expected machine identity, native shell, FFS write/read
comparison, process execution, timer commands, Ethernet replies, and an actual
`halting...` followed by the PROM menu. `halt: halted by root` alone is not
shutdown evidence. Address readiness is awaited with `ifconfig -w 20` before
pinging the local IRIS NAT gateway. Tests stop their own emulator on completion
or failure, and verify that the supplied base CHD is unchanged.

Package a successful, halted overlay without a large raw intermediate:

```sh
chdman copy -i OVERLAY_CHD -ip BASE_CHD -o CANDIDATE_CHD -c zlib -np 2
chdman verify -i CANDIDATE_CHD
python3 lab/ip28-kernel/check.py \
  --iris IRIS_BINARY --disk CANDIDATE_CHD --kernel netbsd.ip28 \
  --kernel-sha256 EXPECTED_KERNEL_SHA256 --output PACKAGED_BOOT_DIRECTORY
```

Use `--firmware-dir BUNDLE_DIRECTORY` for a further cold boot using its saved
`nvram.bin` and `nveeprom.bin` without issuing any `setenv` commands.

Only a separately cold-booted packaged CHD is a retained candidate. Preserve
both previous qualified Indy images. Remove disposable overlays and build
objects after saving the source, logs and qualified replacements.

## Indy regression

Build `lab/irix-module/XIRI_IRIX_MODULE` with the same source/toolchain in a
separate output directory. Boot its `netbsd.elf32` using
`--machine indy-r4400` for the 6.5.22 base or `--machine indy-r5000` for 6.5.30,
`--tftp REGRESSION_BUILD/kernel --kernel netbsd.elf32`, and:

```text
--irix-module /stand/sgimips/11.99.9/modules/compat_irix_o32/compat_irix_o32.kmod
```

This additionally loads the existing module and runs the original IRIX shell.
It checks shared-kernel regression coverage, not a new graphical qualification.

## Manual serial boot

The retained bundles are:

- `.work/native/xiri-ip28-6.5.22-20261122/`
- `.work/native/xiri-ip28-6.5.30-20261122/`

Run their `run-iris.sh` from any directory. They select IP28/R10000, High
IMPACT and 1 GiB RAM, with `console=d`; the graphical window does not contain
the NetBSD console. Connect a second terminal to the serial port listed in the
bundle's `README.txt`. If execution is paused, type `start` at the IRIS monitor.
Choose PROM option 5, then `boot`; press Return for `/bin/sh`.

The saved settings use compact firmware paths:

```text
setenv console d
setenv SystemPartition dksc(0,1,8)
setenv OSLoader boot
setenv OSLoadPartition dksc(0,1,0)
setenv OSLoadFilename netbsd.ip28
setenv OSLoadOptions single
boot
```

Use `mount -u -w /` for writes and `/sbin/halt` before closing IRIS. The
bundles keep manual changes in their own overlays. They intentionally start
in single-user mode: an IP28 desktop still needs its display/input support and
a matching modular Xiri kernel. The native IRIX IMPACT disk and the qualified
Indy desktop bundles are separate and unchanged.
