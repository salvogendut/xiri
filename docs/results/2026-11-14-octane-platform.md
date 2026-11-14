# Octane feasibility for the 6.5.30 Xiri line

Octane is not currently a working NetBSD/Xiri target. The source audit finds
missing Octane board support, and a bounded firmware boot check confirms that
switching the existing O2 kernel to the Octane machine is insufficient.
No IRIX 6.5.30 application was executed in this check.

## Source boundary

The audited NetBSD `xiri` revision is
`2a7184ec4c66b324c8c027b577a81c1e41575504`. Both `GENERIC32_IP3x` and
`GENERIC64_IP3x` explicitly say they support **O2/IP32**. Their devices are
CRIME, the CRM framebuffer, MACE and MACE PCI, not the Octane's hardware.
The existing `MACH_SGI_IP30` cases in machine/clock selection are preliminary
recognition, not a complete platform implementation.

| Area | Required Octane work in NetBSD |
| --- | --- |
| Boot and firmware | Review the ELF64 entry/load placement, Octane physical-memory layout and ARCS64 structures/calling convention. Current `sys/dev/arcbios/arcbios.h` uses 32-bit firmware-vector/component pointers, and `arcbios_calls.S` supplies an o32 firmware bridge for the n64 kernel. |
| Memory, interrupts and buses | Add HEART and the Crossbow/XIO/Bridge attachment, interrupt routing and bus/DMA mapping in the sgimips port. Existing O2 CRIME/MACE attachments cannot supply these. |
| Essential I/O | Add Octane IOC3 serial, clock, Ethernet and input attachments, then connect storage through its PCI bus. NetBSD already has a generic QLogic ISP1040 PCI driver; the Octane board connection remains missing. |
| Display | Add the selected Octane IMPACT/VPro display/input path and a usable native Xorg path, then qualify desktop drawing. Newport and O2's `crime` are different hardware. |

These are native platform dependencies. They do not add an IRIX personality
hook to the [three existing core interfaces](../NETBSD-UPSTREAM.md).
Octane remains the separately scoped expansion milestone in the
[roadmap](../ROADMAP.md#milestone-5-indigo2-and-octane-expansion).

## Bounded boot check

The fixture uses IRIS `xiri` `7d46498b`, one R10000, 512 MB and a serial
console. It copies the existing Octane installation's flash and NVRAM into
private state. **No disks are attached**, so no installed IRIX or NetBSD
filesystem can be changed. The PROM's missing-SCSI diagnostic is expected
and acknowledged before entering its maintenance menu.

The kernel is the retained, hash-pinned O2 N64 build from the
[previous trial](2026-11-14-irix-6.5.30.md), not a newly implemented Octane
kernel. The first network boot uses its ELF32 PROM wrapper. Octane reports:

```text
Can't boot 32 bit ELF
Unable to execute bootp():netbsd-XIRI_O2: execute format error
```

The underlying ELF64 kernel is checked separately. After beginning to load
its text segment, the PROM reports a data-bus exception at
`0xffffffff9fc87a3c`, followed by `PANIC: Unexpected exception`. NetBSD's
entry point is `0xffffffff80069000`; no NetBSD banner or login appears. This
is a firmware loading failure with the O2-linked kernel, not a measured IRIX
application failure. The exact cause of the PROM exception is not diagnosed
by this bounded check.

The [machine-readable result](2026-11-14-octane-platform.json) pins the two
variants, firmware source files, source audit and retained transcripts.
Both tests stop their owned emulator and verify the original firmware/kernel
hashes. The fixture's initial startup error (IRIS's implicit disk defaults)
is retained separately; the maintained fixture explicitly disables disks.

## Existing native IRIX evidence

The user's original-media installation is under
`~/Downloads/IRIX media/Installed/Octane-R10000-6.5.30/`. Its November 6 notes
record **IRIX64 6.5.30f on IP30**, one 195 MHz R10000, 512 MB and a Solid
IMPACT desktop at 1280×1024, followed by cold boot and clean power-off. Those
are prior native IRIX results, not a fresh IRIX boot in this cycle or evidence
that NetBSD runs on Octane. Its image, sector overlay, dirty map and original
firmware state remain untouched.

## Reproduction and next decision

```sh
python3 scripts/probe-netbsd-octane.py \
  --kernel-build .work/netbsd-o2-build \
  --kernel-image native \
  --emulator .work/emulators/iris-xiri-20261114-r5k-config \
  --nvram .work/platform-checks/octane-20261114/inputs/nvram.bin \
  --flash .work/platform-checks/octane-20261114/inputs/flash.bin \
  --output .work/octane-native64-check
```

The output directory must be new; `--kernel-image boot` selects the ELF32
wrapper. The probe owns and stops its emulator, preserves an exact executed
script, and checks that both firmware source files and the kernel are
unchanged. It has a five-minute bound on the network boot phase.

The subsequent [Indy/R5000 retry](2026-11-14-r5000-6.5.30.md) boots NetBSD
through native login and full-screen xdm with the corrected Config handling;
it is the active 6.5.30 application test path. Octane requires its own NetBSD
board-port cycle, and O2 requires native boot/driver repair before either can
host Xiri. Keep both 6.5.22 and 6.5.30 deliverables
separate and retain the qualified 6.5.22 manual image.

IRIS upstream was fetched for this cycle: `5fb831ce` is already contained in
`xiri` at `7d46498b`, with no new commits or merge required. Neither fork's
source changed. The probe passed Python syntax checks and was exercised in
both kernel-image modes; no desktop acceptance test is claimed.

Compact transcripts, input state and exact probes are retained in
`.work/platform-checks/octane-20261114/`. Temporary run directories were
removed; no large disk copies, raw images, CHDs or build caches were created.
All owned IRIS instances are stopped.
