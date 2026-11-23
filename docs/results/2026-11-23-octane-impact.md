# Octane IMPACT discovery under native NetBSD

The IP30 topic branch at `8f744b33e95` already boots NetBSD 11.99.9 on an
emulated R10000 Octane. Its earlier tests reached a multi-user serial login,
preserved a file across a reboot and checked filesystem recovery. At the time of this test the Octane code was on
`topic/sgimips-octane`. The subsequent desktop milestone merged it into the
NetBSD fork’s `xiri` branch alongside the Indigo2 graphics driver. [IP30 handover](https://github.com/salvogendut/NetBSD-xiri/blob/8f744b33e95b4ef132ed5ffd9f8e7d96c38e2134/xiri/platforms/ip30/HANDOVER)

## Native boot results

| IRIS board selection | NetBSD kernel inventory | Native serial shell | Clean halt to PROM |
| --- | --- | --- | --- |
| Solid IMPACT | Widget 11, ID `0x0c003555` | Passed | Passed |
| High IMPACT | Widget 11, ID `0x0c003555` | Passed | Passed |
| No graphics board | Zero IMPACT widgets | Passed | Passed |

All three boots used one R10000, 512 MiB and the same test kernel. Each
mounted FFS read-only from QLogic SCSI, wrote to the IOC3 console, and
recorded both receive and transmit interrupts. Solid IMPACT also passed
with the archived November 22 interpreter. Each run verified the original
disk and firmware hashes after shutdown. The kernel and interpreter used
for the three-way comparison are retained in
`.work/octane-impact-20261123/{boot,emulator}/`. [Run records and hashes](2026-11-23-octane-impact.json)

This cycle merged five IRIS upstream commits through `c13ec795` into
`xiri` at `592df243`. The 159 targeted Octane, chipset and timer tests
and two host clock and video lifecycle tests passed. On the NetBSD side,
a merge preview found 26 conflicting hunks across the two MIPS assembly
files and the MIPS and sgimips machine-dependent C files. Bringing the
Octane topic onto `xiri` needs boot regressions for both IP28 and IP30.
The checkout and test kernel used here have the existing Octane boot code.

## What transfers from Indigo2

Both machines use the IMPACT raster command set. On Indigo2, commands enter
through HQ3 on GIO. On Octane, HQ4 exposes the command FIFO at a different
offset in an XIO widget. HQ4 also has a separate DMA page-table port and sends
interrupts to HEART. The existing Indigo2 `genfb` shadow, changed-span
detection and drawing commands are candidates for reuse. The subsequent
[programmed-I/O rectangle test](2026-11-23-octane-rectangle.md) checks
the colour and bounds on HQ4 scanout. DMA remains a separate milestone.
[IRIS HQ4 register map](https://github.com/salvogendut/iris/blob/592df243/src/dev/mgras/hq4.rs)
and [OpenBSD IMPACT attachments](https://man.openbsd.org/OpenBSD-6.6/impact.4).

## Reproduce the discovery kernel

For these historical commands use Xiri lab revision `b367bec` with the
Octane topic revision recorded here. Current NetBSD `xiri` contains the
drivers and kernel configurations in-tree.

The [lab kernel configuration](../../lab/ip30-impact/XIRI_IP30_HQ4) extends
the Octane read-only-root configuration. Its probe reads the Crossbow identity,
checks the external links and reads each live widget's part and manufacturer.
The IOC3 serial console stays available throughout the test. The probe issues
no drawing commands. The widget ID register identifies the HQ4 family. The
Solid and High variants are selected in IRIS.

Run from the Xiri checkout with the sibling NetBSD tree at the IP30 revision
above and the existing sgimips tools. Use a fresh build directory.

```sh
repo=$(pwd -P)
tools="$repo/.work/netbsd-octane-build/tools/bin"
build="$repo/.work/ip30-hq4-rebuild"
mkdir -p "$build"
"$tools/nbconfig" -s "$repo/../NetBSD-xiri/sys" -b "$build" \
    "$repo/lab/ip30-impact/XIRI_IP30_HQ4"
(cd "$build" && "$tools/nbmake-sgimips" -j2 depend netbsd)
```

Run the [boot check](../../lab/ip30-impact/check.py) in the IRIS build
container with a stopped native root CHD and a firmware directory containing
`flash.bin` and `nvram.bin`. Use an NVRAM previously saved with
`setenv console d` so the PROM accepts serial input with graphics installed.
The historical graphical NVRAM sent the PROM output to the display and
timed out at the serial prompt.

```sh
for board in solidimpact highimpact none; do
    python3 lab/ip30-impact/check.py --board "$board" \
        --emulator .work/octane-impact-20261123/emulator \
        --kernel "$build/netbsd" --disk .work/m4a-root.chd \
        --firmware .work/octane-m4a-phys-readonly-20261116 \
        --output "$build/check-$board" || exit 1
done
```
