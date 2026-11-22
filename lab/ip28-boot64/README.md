# IP28 standalone BSD loader

This fixture tests NetBSD's `ip28boot` on an emulated Indigo2 R10000. It is
a small BSD loader test, not a NetBSD installation. The ELF64 payload checks
initialized data, zero-valued BSS, arguments and NetBSD boot information,
then returns to the loader. The loader returns to the PROM menu.

The [qualification report](../../docs/results/2026-11-22-ip28-boot64.md)
records the tested binary, source commit and remaining kernel limitations.

## Build

Use NetBSD `xiri` at `b84b5316b3a` or a descendant and an existing sgimips
cross-tool directory. Run in the environment where that toolchain works;
the recorded run used the `xiri-iris` container. For example:

```sh
sh lab/ip28-boot64/build.sh ../NetBSD-xiri .work/netbsd-octane-build/tools \
  .work/ip28-loader-build
```

The script builds `boot64` and the legacy `boot` targets with separate objects,
then creates `ip28boot` and `fixture/disk.raw` under the output directory.
It uses the underlying `nbmake` directly, leaving existing machine wrappers
and other build trees alone. The raw disk is 32 MiB with an SGI volume header,
`boot` in partition 8, and a big-endian FFSv1 filesystem at partition 0.
Its only filesystem payload is the source-built handoff probe.

## Check

Run from a graphical host session with the qualified accelerated IRIS binary:

```sh
python3 lab/ip28-boot64/check.py \
  --iris .work/emulators/iris-xiri-20261122/accelerated/iris \
  --disk .work/ip28-loader-build/fixture/disk.raw \
  --output .work/ip28-loader-check
```

Use a new output directory for each check. The runner creates independent
firmware state and a private disk overlay, boots through the disk's volume
header, requires the handoff marker and return to PROM, and stops its IRIS
instance. Logs and `result.json` remain in the output directory. Serial
`console=d` is intentional for these automated standalone checks.

The retained compressed fixture can replace `--disk` with
`.work/native/netbsd-ip28-loader-20261122/loader-test.chd`.
To test network loading of the bootstrap, pass `--tftp` with a directory
containing `ip28boot`; the payload still comes from FFS on the disk.
For either existing Xiri disk, use `--kernel netbsd --expect wrong-address`
and `--tftp`: those Indy kernels must be rejected before they overwrite RAM
at addresses unsuitable for IP28. This rejection is not a kernel boot pass.

For a manually configured IP28 machine using the fixture disk at SCSI ID 1:

```text
setenv SystemPartition scsi(0)disk(1)rdisk(0)partition(8)
setenv OSLoadPartition scsi(0)disk(1)rdisk(0)partition(0)
setenv OSLoader boot
setenv OSLoadFilename xiri-ip28-probe
setenv OSLoadOptions auto
boot
```

`OSLoader=boot` selects the BSD loader installed in the SGI volume header.
Changing that variable alone does not convert the older ELF32 `boot` file
into an IP28-compatible loader.
