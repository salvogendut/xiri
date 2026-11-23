# Modular Xiri on the emulated Octane

NetBSD `xiri` now includes the Octane board support, Solid and High IMPACT
framebuffer, and IOC3 keyboard and mouse. The previous Octane topic and the
Indigo2 port had independently implemented a 64-bit boot stack and exception
vector pointers. The merge shares these while preserving Octane's firmware
entry, memory attributes, HEART interrupts and Bridge/QLogic disk path.
The desktop kernel configuration lives in the NetBSD fork and builds without
a sibling Xiri source checkout. [NetBSD desktop configuration](https://github.com/salvogendut/NetBSD-xiri/blob/fbb11636cc40bfeab24f055be133801c919c702e/sys/arch/sgimips/conf/XIRI_IP30_DESKTOP)

The desktop kernel enables loadable modules, local IP networking and System V
IPC. All 172 external symbols used by `compat_irix_o32.kmod` resolve in the
kernel. The guest checks an actual foreign executable before load, after
load, after unload and after reload. While IRIX `asa` is active, the module
returns `EBUSY` on unload. After it exits, unload succeeds. Each release disk
also runs its own IRIX `/bin/sh` and `echo`.

The merged MIPS startup code passed separate native shell and shutdown
regressions on Indy/R4400, Indigo2/R10000 and O2/R10000. The Indy and
Indigo2 checks also exercised disk writes and network traffic. All 83
repository host tests and all 17 NetBSD platform-harness tests passed. The IRIS upstream check found `a05289ef` already included in
`xiri` at `08e53ba7`.

## Desktop checks

| IRIX release in the root CHD | Emulated Octane graphics | Screenshot |
| --- | --- | --- |
| 6.5.22 | Solid IMPACT | [6.5.22 desktop](2026-11-23-octane-desktop-6.5.22.png) |
| 6.5.30 | High IMPACT | [6.5.30 desktop](2026-11-23-octane-desktop-6.5.30.png) |

Each guest starts the installed desktop through `xiri-desktop`, with
original 4Dwm, Toolchest, Icon Catalog and winterm running as the configured
user. The host checks the 1280×1024 scanout after the terminal has executed
a command. The guest verifies the terminal's UID (1234) and working directory
(`/usr/people/xiritest`). The host then types a command into winterm. The guest waits for the
file created by that command before requesting logout. Both
4Dwm and Xorg exit, the guest unmounts the root filesystem and the PROM
returns. A separate boardless boot checks recovery through IOC3 serial.
[Run records and artifact hashes](2026-11-23-octane-desktop.json)

The single-user launcher initializes loopback and the PTY namespace first.
The previous 30-second startup check could expire during service preparation,
so the Octane fixture allows up to 180 polling iterations. While Xorg owns
the screen, wsdisplay suppresses text-console writes. The fixture sends its
frame-ready notification directly to `/dev/dtyC0` and prints the transcript
after logout. Some transcript markers retain the names of the shared IP28
module and desktop fixtures. The boot banner identifies `XIRI_IP30_DESKTOP`.

The tests cover a BOOTP-loaded kernel, local display and loopback services.
The subsequent [standalone Octane CHD check](2026-11-23-octane-xdm.md)
qualifies disk boot and authenticated xdm login on both release lines.
Physical hardware, native IOC3 Ethernet and HQ4 DMA still need their own tests.

## Reproduce

Use the NetBSD fork's `xiri` branch and an sgimips/mips64eb cross-toolchain.
Run these commands from the Xiri checkout.

```sh
src=$(cd ../NetBSD-xiri && pwd)
tools="$PWD/.work/netbsd-octane-build/tools"
build="$PWD/.work/ip30-desktop-rebuild"
sh lab/ip28-kernel/build.sh "$src" "$tools" "$build" \
    "$src/sys/arch/sgimips/conf/XIRI_IP30_DESKTOP"
sh lab/ip28-kernel/build-module.sh "$src" "$tools" "$build"
```

Use separate stopped release CHDs, an Octane firmware directory saved with
`console=d`, and the local IRIX `/usr/bin/asa` listed in the reference
manifest. The example uses the retained 6.5.22-line root. The harness boots
the new kernel over BOOTP, mounts a read-only test CD and loads that build's
module. Each run gets private firmware, a disk copy and its own write overlay.

```sh
python3 lab/ip30-impact/check.py --board solidimpact \
    --desktop "$build/module/compat_irix_o32.kmod" --vendor-asa "$ASA" \
    --kernel "$build/kernel/netbsd" --emulator .work/octane-fill/emulator \
    --firmware .work/octane-m4a-phys-readonly-20261116 \
    --disk .work/native/xiri-ip28-dma-6.5.22-20261122/netbsd-xiri.chd \
    --output "$build/solid-22"
```

To reproduce the 6.5.30 check, use `--board highimpact`, the separate
6.5.30 root CHD and a fresh output directory.
The retained pair on this workstation is under `.work/octane-desktop/qualified/`.
