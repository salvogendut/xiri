# NetBSD 11.0 on the IRIS Indy — 2026-10-29

NetBSD 11.0 installed to a disposable disk and reached a serial multiuser
login with the R4400 profile. Two full emulator restarts booted from disk,
and a file written before shutdown retained its checksum on both. This
establishes the initial guest baseline with CI enabled; full emulator
qualification remains incomplete.

## Environment

| Item | Recorded value |
| --- | --- |
| Host and emulator build | [Fedora 44 host](2026-10-29-host-inventory.md), `xiri-iris` Toolbox, [pinned IRIS build](2026-10-29-iris-build.md) |
| IRIS revision | `b188bb9a82842948ddf2534f07d718df8473942c`, no source changes |
| Profile | `indy_ip24`, R4400, 256 MiB, Newport enabled, audio disabled |
| Runtime | CI enabled, offscreen Newport, `scsi_deferred_int = true`; no JIT or instruction-fusion features |
| Firmware | IRIS embedded PROM fallback; startup reported missing `prom.bin` and selected the embedded image |
| Console | PROM `console=d`; NetBSD `zstty0` / `constty` |
| Storage | SCSI ID 1, 8 GiB raw writable disk; SCSI ID 4, ISO containing the verified sets |
| Network | NAT `192.168.231.0/24`, gateway `192.168.231.1`, guest DHCP `192.168.231.2`, MAC `08:00:69:12:34:57` |
| NetBSD inputs | [Signed and verified 11.0 release inputs](2026-10-29-netbsd-inputs.md), `INSTALL32_IP2x` and `GENERIC32_IP2x` |
| Guest settings | `xiri-indy`, UTC, root shell `/bin/sh`, empty root password, sshd disabled |

The retained [TOML configuration](../../lab/indy-netbsd/iris.toml) and
[lab procedure](../../lab/indy-netbsd/README.md) give the setup commands.
The guest identifies the board as `SGI-IP22` and the CPU as
`MIPS R4400 CPU (0x440) Rev. 4.0`.

## Installation and disk layout

The PROM fetched the uncompressed ELF installation kernel from IRIS TFTP:

```text
boot -f bootp()/netbsd-INSTALL32_IP2x
```

The installer recognized 256 MiB RAM, Newport, Seeq Ethernet, the SCSI disk,
and the virtual CD. `sysinst` created the SGI volume header and FFS root,
writing `aoutboot` and `boot` (`ip2xboot`) into the volume header. The final
installation used the virtual CD (`cd0a`, binary set directory `/`). All six
sets unpacked successfully: `kern-GENERIC32_IP2x`, `modules`, `base`, `etc`,
`comp`, and `rescue`. Device-node creation and certificate rehash completed.

| Partition | Start sector | Sector count | Use |
| --- | ---: | ---: | --- |
| a | 8,256 | 16,703,488 | FFS root, about 7.8 GiB usable |
| b | 16,711,744 | 65,472 | Swap, 32,736 KiB |
| c | 0 | 16,777,216 | Whole disk |
| d | 64 | 8,192 | Reserved area, shown as unused by `disklabel` |

Sectors are 512 bytes. The installer layout initially omitted swap. After
checking the disklabel and the unused tail of the disk, the following guest
commands added it without moving the root partition:

```sh
disklabel sd0 > /tmp/dl
echo ' b: 65472 16711744 swap' >> /tmp/dl
disklabel -R sd0 /tmp/dl
swapctl -a /dev/sd0b
echo '/dev/sd0b none swap sw 0 0' >> /etc/fstab
```

The first disk boot consequently reported missing swap; the following cold
boot activated `sd0b` and no longer reported that startup failure.

The PROM disk-boot variables are retained in the lab procedure. They were
saved with `iris-ci rtc-save`; automatic boot then loaded `boot` from the
volume header and `netbsd` from partition 0.

## Boot and persistence evidence

The installation run used this command from the repository root:

```sh
toolbox run -c xiri-iris "$PWD/.work/target/release/iris" \
  --config lab/indy-netbsd/iris.toml --ci \
  --ci-socket .work/indy-netbsd/cd.sock \
  --serial-log .work/indy-netbsd/cd.serial.log \
  > .work/indy-netbsd/cd.stdout.log 2>&1
.work/target/release/iris-ci --socket .work/indy-netbsd/cd.sock start
```

Run the controller in a separate terminal while IRIS is running. Installation
was driven using `serial-send` and serial logs; the IRIX-specific `boot` and
`login` helpers were not used. The installed guest first booted after the
installer reboot. A clean `shutdown -h now` synced and unmounted FFS before
`iris-ci quit` stopped the emulator.

The next process used the same invocation with `cold.sock`,
`cold.serial.log`, and `cold.stdout.log`. It loaded the saved NVRAM and disk
from process startup and booted automatically without PROM input. Selected
serial evidence:

```text
NetBSD/sgimips 11.0 Bootstrap, Revision 1.5 (Thu Jul 30 15:23:12 UTC 2026)
devopen: scsi(0)disk(1)rdisk(0)partition(0) type scsi file netbsd
[   1.0000000] NetBSD 11.0 (GENERIC32_IP2x) #0: Thu Jul 30 15:23:12 UTC 2026
[   1.0000000] total memory = 256 MB
[   3.1609879] boot device: sd0
[   3.1713109] root on sd0a dumps on sd0b
[   3.1909848] root file system type: ffs
/dev/rsd0a: file system is clean; not checking
swapctl: adding /dev/sd0b as swap device at priority 0
NetBSD/sgimips (xiri-indy) (constty)
login: root
xiri-indy# cksum /root/xiri-probe; swapctl -l; ifconfig sq0
3540535338 33 /root/xiri-probe
Device      1K-blocks     Used    Avail Capacity  Priority
/dev/sd0b       32736        0    32736     0%    0
        inet 192.168.231.2/24 broadcast 192.168.231.255 flags 0
```

The marker was created before shutdown with
`printf XIRI_NETBSD_DISK_PROBE_2026-10-29 > /root/xiri-probe`; the checks
before and after reboot returned `3540535338 33`. The guest was shut down
cleanly again. A second new emulator process used `cold2.sock`,
`cold2.serial.log`, and `cold2.stdout.log`; it also booted automatically to
multiuser, returned the same marker checksum, and reported active swap.
The guest was cleanly halted and IRIS stopped after this check. This passes
the persistent-guest gate for this CI configuration, with a small file check;
sustained disk stress and network-integrity testing remain pending.

## Retained artifacts

All images and complete serial/host logs remain outside Git in
`.work/indy-netbsd/`. The clean checkpoint under `base/` was copied after the
first successful cold boot and clean shutdown; it is a disk/NVRAM checkpoint,
not a RAM snapshot. The working disk may subsequently change as tests run.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `base/disk.raw` | 8,589,934,592 | `8f896ab101a1cb27e29bfe87cc4048cc61c17f2a148f58d24bba0fb1d0c21926` |
| `base/nvram.bin` | 8,192 | `602d954b2e8f076887c54ed301dff7dbd9cc0c6be138e537e5bc732c948d344e` |
| `sets.iso` | 242,653,184 | `88b77c852a1553489ae889ed93df85f48c00fe2bbfeb07eba841e7ade33a7d93` |

The sparse disk occupied approximately 899 MiB. The ISO hash identifies this
run's artifact; regeneration can change ISO timestamps. The individual set
hashes remain pinned in the [input manifest](../../lab/netbsd-11.0/SHA512SUMS).

## Failures and remaining qualification

- R5000 reached the install kernel but panicked with
  `panic: r5k picache line size 16`. NetBSD's `sys/arch/mips/mips/cache.c`
  rejects that R5000 cache geometry. The IRIS CP0 Config write mask is a
  candidate for investigation; no emulator patch or confirmed root cause
  resulted from this run. `serial.log` retains the panic; `r4400.serial.log`
  retains the successful comparison boot.
- The NFS source attempt stalled. The guest tried TCP port 2049 while the
  inspected IRIS built-in NFS service handles UDP. No manual UDP-mount test
  was completed.
- A loopback HTTP server reached through the NAT gateway transferred the
  kernel and modules. `base.tgz` stopped advancing around 6.4 MiB. Monitor
  counters showed receive refusals; the TCP NAT entry eventually disappeared.
  The cause remains unresolved. `install.serial.log` and `http.log` retain
  this attempt. The temporary HTTP server was stopped after the experiment.
- Stopping that incomplete installation without a guest shutdown left an
  FFS inconsistency. The final CD installation reformatted the disposable
  root filesystem; subsequent clean shutdown/boot checks reported it clean.
- Entropy warnings remain. No strong entropy source or secure-key setup was
  qualified. The empty root password and disabled sshd are lab settings.
- Host logs contain REX3 unhandled-register messages and GIO timeout/bus-error
  diagnostics during device probing. The guest continues to multiuser; these
  diagnostics have not been fully explained. Newport detection does not
  establish a working X display.

All guest runs in this record used CI mode. Ordinary execution, sustained
disk/network checks, a changed host-built kernel, debugger continuation,
automated probes, snapshots, X11, MAME comparison, and physical hardware
remain to be qualified. The next development step is to build the NetBSD
cross-tools and a distinguishable `GENERIC32_IP2x` kernel on the modern host,
then cold-boot it through the working TFTP path.
