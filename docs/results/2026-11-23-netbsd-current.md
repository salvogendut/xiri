# NetBSD-current integration on the SGI ports

NetBSD `xiri` moved from 11.99.9 to **11.99.11**. The first merge brought
in the fork's November 2 `origin/trunk` tip, including 30 commits absent
from `xiri`. The second brought in the following 311 official NetBSD
commits through November 23. Both merged cleanly. [NetBSD integration commit](https://github.com/salvogendut/NetBSD-xiri/commit/c096ddb347d6babc60e611de433a3ba016b103ec)

The upstream changes include the console debugger changes in `cnmagic`, a
`wsdisplay` fix when leaving dumb framebuffer mode, and a change to the
position of `p_pgrp` in `struct proc` during fork. The Xiri module source
was identical on either side of the merge. Its build uses the new kernel
headers, and NetBSD looks for it in the 11.99.11 module directory.

## What ran

| Emulated SGI | IRIX 6.5.22 | IRIX 6.5.30 |
| --- | --- | --- |
| Indy | R4400, original IRIX shell, FFS write/read, Ethernet | R5000, same checks |
| Indigo2 | R10000, original IRIX shell, FFS write/read, Ethernet | R10000, same checks |
| Octane | Solid IMPACT, module load/unload/reload, 4Dwm and winterm at 1280×1024, logout | High IMPACT, same checks |
| O2 | Cold boot from SCSI, module loaded at securelevel 1, xdm login, 4Dwm and Icon Catalog at 1280×1024, logout | Same checks on the separate 6.5.30 disk |

All 172 imports of the rebuilt module resolved against each of the four
kernels. The host suites passed 83 Xiri tests and 17 NetBSD platform
tests. IRIS upstream `a05289ef` was already included in `xiri` at
`08e53ba7`. O2 and Octane used that build. Indy and Indigo2 used their
previously qualified accelerated build at `0bc52567`.
[Kernels, module, disks and results](2026-11-23-netbsd-current.json)

The current manual CHDs still boot their pinned 11.99.9 kernels. The four
tested kernels, the two ELF32 wrappers and the shared module are retained
locally in `.work/netbsd-sync-20261123/sgimips-11.99.11.tar.gz` with a
SHA-256 manifest. Sibling `qualification.tar.gz` contains the test logs,
and `screens/` contains the four desktop captures. All guest checks used
private overlays. Physical SGI hardware remains a separate qualification target.

## Reproducing the checks

From the Xiri checkout, make a fresh build directory for each configuration.
Use the sgimips/mips64eb tools with the [kernel builder](../../lab/ip28-kernel/build.sh)
and [module builder](../../lab/ip28-kernel/build-module.sh). For example, the
Octane build uses these commands.

```sh
src=$(realpath ../NetBSD-xiri)
tools=$PWD/.work/netbsd-octane-build/tools
build=$PWD/.work/netbsd-current-test/ip30
sh lab/ip28-kernel/build.sh "$src" "$tools" "$build" "$src/sys/arch/sgimips/conf/XIRI_IP30_DESKTOP"
sh lab/ip28-kernel/build-module.sh "$src" "$tools" "$build"
```

The other configurations are `XIRI_IP32_DESKTOP` for O2, `XIRI_IP28` for
Indigo2, and the lab's `lab/irix-module/XIRI_IRIX_MODULE` for Indy. The Indy
and O2 boot loaders take `netbsd.elf32`. The Octane and Indigo2 PROM tests
load the native ELF64 kernel.

For the Octane run the [module and desktop checks](2026-11-23-octane-desktop.md#reproduce)
with the newly built kernel/module pair. For O2, start each release's framed
disk on its own private overlay, stage the new kernel as `/netbsd`, the ELF32
wrapper as `/netbsd.boot`, and the new module as
`/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod`.
Halt to the PROM, cold-boot the same overlay with the installation CD
detached and log in through xdm. [O2 launchers and frame checks](2026-11-23-o2-frame.md)

For Indy and Indigo2, use the [native boot checker](../../lab/ip28-kernel/check.py)
with `--tftp` pointing at the new kernel's directory. Attach a Rock Ridge
ISO with the new module and its NetBSD-format `SHA256` manifest using
`--fixture-media`. Choose `--irix-module /cdrom/compat_irix_o32.kmod` so
the kernel loads the matching build before launching the installed vendor
shell.
