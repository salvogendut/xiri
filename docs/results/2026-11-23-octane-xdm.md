# Octane disk boot and native xdm

## Manual testing

The two local bundles contain separate NetBSD disks with the corresponding
IRIX desktop, an Octane flash file and saved NVRAM. From the Xiri checkout,
run the launcher for the desired release.

```sh
.work/native/xiri-ip30-xdm-6.5.22-20261123/run-iris.sh
```

```sh
.work/native/xiri-ip30-xdm-6.5.30-20261123/run-iris.sh
```

The launchers open an IRIS window with an R10000, 512 MiB, and a disk at
internal SCSI ID 1. The 6.5.22 bundle selects Solid IMPACT and the 6.5.30
bundle selects High IMPACT. If using a developer build that starts paused,
press Ctrl-P. Allow the initial PROM diagnostics and NetBSD service startup
to finish. The login panel is centered on the 1280×1024 screen.

| xdm account | Password | Session |
| --- | --- | --- |
| `xiritest` | `xiritest` | IRIX 4Dwm, home `/usr/people/xiritest` |
| `netbsdtest` | `netbsdtest` | NetBSD ctwm, home `/home/netbsdtest`, wheel access |

Use Toolchest **Log Out** or run `xiri-logout` from winterm to return to xdm.
For shutdown, use `su -` from the wheel account or log in as root on IOC3
serial A. Use the graphical terminal for long commands. The serial console
occasionally drops input characters during multiuser operation. The local serial ports are 20723 for 6.5.22 and 20731 for 6.5.30.
Run `shutdown -h now` and wait for the PROM menu before closing IRIS. Each
launcher saves changes in its own CHD overlay. The inherited guest hostname
is `xiri-indy`. On the Octane, `sysctl -n hw.model` reports `IP30`.

## What makes these disks boot

The PROM loads the ELF64 NetBSD `ip30boot` stored as `boot` in the SGI
volume header. The loader opens FFS on partition 0 and loads `/netbsd.ip30`.
The previous loader address, `0xa800000020080000`, was inside the desktop
kernel's load segment. The loader now runs at `0xa800000021000000`, in free
RAM above the PROM reservation. The kernel retains its qualified entry point
at `0xa800000020010000`. [NetBSD loader change](https://github.com/salvogendut/NetBSD-xiri/commit/47c9acf14a4)

The shipped flash and NVRAM contain these settings. To configure a separate
Octane firmware state manually, enter them at the PROM command monitor.

```text
setenv SystemPartition scsi(0)disk(1)rdisk(0)partition(8)
setenv OSLoader boot
setenv OSLoadPartition scsi(0)disk(1)rdisk(0)partition(0)
setenv OSLoadFilename /netbsd.ip30
setenv OSLoadOptions auto
setenv AutoLoad Yes
setenv console d
boot
```

NetBSD rc.d loads the matching `compat_irix_o32.kmod`, prepares the IRIX
PTYs and local services, and starts xdm with the existing wsfb configuration.
The disk enables the IOC3 `ttyC0` getty and disables the old `ttyZ0` getty.
The Octane image uses loopback for these services. The DHCP client inherited
from the Indy's `sq0` configuration is disabled. Native IOC3 Ethernet and
physical Octane hardware remain open. This kernel has no time-of-day clock
driver or crash dump device. It uses the saved filesystem time at startup
and the inherited savecore service can print a namelist warning.

## Qualification

| Release | Login screen | IRIX session | NetBSD session |
| --- | --- | --- | --- |
| 6.5.22 | [xdm](2026-11-23-octane-xdm-greeter-6.5.22.png) | [4Dwm and winterm](2026-11-23-octane-xdm-irix-6.5.22.png) | [ctwm and UXTerm](2026-11-23-octane-xdm-native-6.5.22.png) |
| 6.5.30 | [xdm](2026-11-23-octane-xdm-greeter-6.5.30.png) | [4Dwm and winterm](2026-11-23-octane-xdm-irix-6.5.30.png) | [ctwm and UXTerm](2026-11-23-octane-xdm-native-6.5.30.png) |

On each disk the tests logged in through native xdm as `xiritest`, ran a
command in winterm, logged out, then exercised the standard NetBSD ctwm
session as `netbsdtest` and returned to the greeter. Both desktops reported
1280×1024. Guest-side records confirmed the actual window manager, UID,
working directory, home and groups. The native account retained wheel access.
A further native login used `su -` to verify the Octane model, securelevel 1
and the loaded IRIX module, then shut down cleanly to the PROM.
The host test controller restarted during verification and reconnected to the
same running guests. The serial records cover each cold boot through halt.
A separate ordinary IRIS window also displayed the greeter after cold boot.
Repackaging the halted 6.5.22 installation produced a byte-identical CHD.
[Qualification records and image hashes](2026-11-23-octane-xdm.json)

## Reproduce a release

Use the matching release's stopped IP28 DMA CHD and its adjacent
`qualification.json`. Use the previously qualified IP30 kernel and module or
build them from the fork. [Kernel and module build](2026-11-23-octane-desktop.md#reproduce)

```sh
src=$(cd ../NetBSD-xiri && pwd)
tools="$PWD/.work/netbsd-octane-build/tools"
work="$PWD/.work/ip30-rebuild"
sh lab/ip28-boot64/build.sh "$src" "$tools" "$work/loader"
loader="$work/loader/obj/sys/arch/sgimips/stand/boot64/ip30boot"
kernel="$PWD/.work/octane-desktop/qualified/netbsd"
module="$PWD/.work/octane-desktop/qualified/compat_irix_o32.kmod"
emulator="$PWD/.work/octane-fill/emulator"

release=6.5.22
board=solidimpact
source_disk="$PWD/.work/native/xiri-ip28-dma-$release-20261122/netbsd-xiri.chd"
python3 lab/ip30-impact/disk.py install --board "$board" --emulator "$emulator" \
  --kernel "$kernel" --module "$module" --loader "$loader" \
  --firmware .work/octane-m4a-phys-readonly-20261116 --disk "$source_disk" \
  --output "$work/install-$release"
python3 lab/ip30-impact/package-disk.py --release "$release" \
  "$work/install-$release" "$work/bundle-$release"
python3 lab/ip30-impact/disk.py qualify --board "$board" --emulator "$emulator" \
  --kernel "$kernel" --module "$module" --loader "$loader" \
  --firmware "$work/bundle-$release" --disk "$work/bundle-$release/netbsd-xiri.chd" \
  --output "$work/check-$release"
```

For 6.5.30 set `release=6.5.30` and `board=highimpact`. The installer uses
BOOTP and a read-only ISO to prepare its private overlay. Packaging flattens
the halted overlay and verifies the standalone CHD with `chdman`. The cold
boot uses only the disk and saved firmware. To run a bundle elsewhere, set
`XIRI_IRIS` to the absolute path of an Octane-capable IRIS executable.

This cycle checked IRIS upstream `a05289ef`, already included in the
fork's `xiri` branch at `08e53ba7`.
