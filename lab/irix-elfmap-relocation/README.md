# ELF-map collision relocation

This checkpoint adds bounded relocation to `SGI_ELFMAP`. Original xclock asks
for libXmu addresses occupied by libXaw. The mapper keeps requested load
addresses when free; otherwise it finds one free span for the two segments and
applies a common displacement. It leaves caller headers and existing mappings
unchanged. The runtime performs ELF symbol relocations itself.

The NetBSD fork branch is `xiri/irix-elfmap-relocation`, based on the SIOCNREAD
checkpoint. Existing file, permission, segment, address-range, resource-limit
and single-thread restrictions remain. The search starts at `0x04000000` and
ends at `0x40000000`; gaps remain unmapped. Occupation of only the original
inter-segment gap does not force relocation. A failed insertion still rolls
back only newly owned mappings; an arbitrary ENOMEM does not trigger a retry.

The original assembly fixtures cover o32 and n32, root and uid 1234. They check
executable bytes, initialized data, partial/full/pure BSS, RX/RW/BSS collisions,
repeated competing maps, an occupied fallback address, gap-only occupation,
header immutability, preserved sentinels, differing alignments, upper addresses,
text/gap faults, and the preceding mapper's rejection cases. Records include
alignment residue rather than assuming the original kernel obeys our stricter
rule. See [reference.json](reference.json) for the original-system observations.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/build-irix-elfmap-relocation.py
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-reference-elfmap-relocation.py
```

Build LP64 and o32 kernels **sequentially**, with two compiler jobs. Use the
[SIOCNREAD build procedure](../irix-siocnread/README.md), substituting
`netbsd-irix-elfmap-relocation-build`, `XIRI_IRIX_ELFMAP_RELOCATION` and
`mips64eb`; for o32 substitute `netbsd-irix-elfmap-relocation-o32-build`,
`XIRI_IRIX_ELFMAP_RELOCATION_O32` and `mipseb`. The two baseline JSON files pin
clean source, configuration, emulator and kernel bytes.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 scripts/probe-irix-elfmap-relocation.py \
  --seed-directory .work/irix-xclock/runs/ci-0xaicapn
# Repeat with --mode ordinary and, separately, --kernel-abi o32.
# Focused RLIMIT_AS checks can be repeated with --limits-only.
```

The harness clones a stopped SIOCNREAD xclock disk, verifies inherited inputs,
installs the matching kernel, and brackets tests with native and original
vendor runtime controls. LP64 runs try original analog/digital xclock as both
identities with native X controls. Ten-second termination is intentional.
Window trees and XWD frames are captured inside the guest before downloading.
Vendor bytes, raw traces and screenshots remain in ignored `.work`.

The original IRIX guest cannot establish the 960 MiB `/dev/zero` mapping used
by the no-free-span case. That setup failure is retained and excluded from ABI
comparison. NetBSD can establish it and test its bounded search. RLIMIT_AS
checks must account for the reserved stack span, including inaccessible stack
pages: 120 MiB on the LP64 kernel and 32 MiB on o32. The native limit helper
allows 8 MiB above that reservation, then attempts a 16 MiB ELF data mapping.

Keep at most four IRIS instances and stop all owned instances afterward. No
leaked IRIX source is used: the evidence comes from original binaries and original
synthetic fixtures, plus the licensed historical NetBSD mapper and current UVM.


Qualification: [576 checks and original xclock windows](../../docs/results/2026-10-31-irix-elfmap-relocation.md).
The checked runs include both NetBSD kernel ABIs, eight original clock windows,
and six separately repeated resource-limit cases. Timekeeping remains open.

The later [subpage mapper](../irix-elfmap-subpage/README.md) retains these fixtures and qualifies the additional 4 KiB data boundaries encountered by original 4Dwm.
