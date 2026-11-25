# SGI Software Manager on Indy with xosview and UnZip

The May 2004 Freeware CD 4 supplies xosview and one release of UnZip.
Installing the older SGI UnZip 5.40 tardist first lets Software Manager
upgrade the runtime to 5.50 from CD 4. Both versions use the SGI subsystem
`fw_unzip.sw.unzip`. Software Manager 4.1 labels the newer product
**Upgrade** when it opens CD 4 with 5.40 installed.

| Xiri desktop | CPU and memory meters | Upgrade selected | SGI completion dialog |
| --- | --- | --- | --- |
| 6.5.22f · R4400 | [xosview](2026-11-26-freeware-upgrade-6.5.22f-xosview.png) | [5.50 upgrade](2026-11-26-freeware-upgrade-6.5.22f-selection.png) | [Completed](2026-11-26-freeware-upgrade-6.5.22f-upgraded.png) |
| 6.5.30f · R5000 | [xosview](2026-11-26-freeware-upgrade-6.5.30f-xosview.png) | [5.50 upgrade](2026-11-26-freeware-upgrade-6.5.30f-selection.png) | [Completed](2026-11-26-freeware-upgrade-6.5.30f-upgraded.png) |

## What the guest checks

1. Boot a private copy of the clean Mozilla Indy and prepare SGI's base
   installation history with the matching supplement. Log in through xdm.
2. Install `fw_xosview.sw.xosview` with Software Manager. Check the original
   binary, application defaults and SGI history. Run xosview as `xiritest`
   (UID 1234) and capture the CPU and memory meters. The runtime ships
   an executable and X resources, so users launch it from winterm. The load-average and
   graphics meters are disabled for this check. [Meter coverage](2026-11-24-indy-xosview.md).
3. Install UnZip 5.40 and open the 5.50 distribution while xosview is still
   installed. After each transaction check SGI's subsystem
   history, the executable checksum and extraction of a deflated
   ZIP as `xiritest`. The two binaries have different checksums and both
   retain the relative `zipinfo → unzip` link.
4. Reboot, repeat the extraction with 5.50 and check that the compiled
   desktop table and xosview executable survived. Remove UnZip through the
   GUI. Check the original desktop table, account database, user session
   selection and native package receipts. Remove xosview separately, compare
   the full SGI inventory with the starting inventory and return to xdm.

UnZip 5.50 introduces `/usr/lib/filetype/install/unzip.ftr`. Its SGI
exit command runs make in the IRIX root. The helper compiles that rule
with SGI's `fftr`, combines it with the release's existing desktop table,
and restores the saved table on removal. This tests the compiled filetype
table. Opening ZIP files in File Manager is a separate desktop check.

Each release restored its own desktop table byte for byte and returned to
the original SGI inventory after removal. The published CHD and NVRAM
digests for both clean Mozilla images still matched their manifests.

Both versions printed `(warning) cannot set times` during ordinary-user
extraction. The decompressed contents matched the reference file.
[Per-release history, digests and guest observations](2026-11-26-freeware-upgrade.json)
· [Manual installation and removal](../../lab/irix-installer/README.md#install-xosview-and-upgrade-unzip-in-software-manager)
· [Automated reproduction](../../lab/native-package/README.md#original-sgi-installers-and-freeware-cd-4).
