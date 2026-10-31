# Original xclock: measured libXmu mapping collision

Follow-up: see the [next checkpoint](2026-10-31-irix-elfmap-relocation.md). This report preserves the earlier observed boundary.

The original n32 runtime requests both `libXmu.so` segments inside the already
mapped text of `libXaw.so.2`. The current bounded `SGI_ELFMAP` implementation
maps only at the requested addresses and returns `ENOMEM` for that collision.
This explains the [earlier xclock loader failure](2026-10-31-irix-xclock.md)
with actual syscall arguments and memory contents. No kernel or emulator code
was changed, and original xclock still exits 1 before reaching X.

The [structured report](2026-10-31-irix-xclock-elfmap.json) records two root
captures, analog and digital, in CI mode on the pinned
`XIRI_IRIX_XSTAT_20261031` LP64 kernel. Both observe the same sequence:

| Mapped object | Requested RX start / size | Requested RW start / size | Return v0 / a3 |
| --- | --- | --- | --- |
| `/lib32/rld` | `0x0fb60000` / `0x25000` | `0x0fbd8000` / `0x7000` | `0x0fb60000` / 0 |
| `/usr/lib32/libXaw.so.2` | `0x0f400000` / `0x42000` | `0x0f444000` / `0x6000` | `0x0f400000` / 0 |
| `/usr/lib32/libXmu.so` | `0x0f400000` / `0x17000` | `0x0f418000` / `0x1000` | 12 / 1 (`ENOMEM`) |

The sizes above are the requested ELF memory sizes, before 8 KiB rounding.
Each object has two `PT_LOAD` headers, RX then RW, with 16 KiB alignment and
equal file/memory sizes. The submitted headers exactly match each original
file's load headers and remain unchanged after each syscall. Thus rld passes
the preferred linked addresses here; it does not relocate libXmu's request
before calling the kernel.

Immediately before the failing call, reads at `0x0f400000` and `0x0f418000`
both succeed. Each 128-byte sample exactly matches the corresponding libXaw
file bytes at offsets zero and `0x18000`. Both addresses lie inside libXaw's
RX interval `[0x0f400000, 0x0f442000)`. The same reads before libXaw is mapped
fail with native ptrace `EINVAL`; that is a memory-read result, separate from
the foreign syscall's `ENOMEM`.

## Capture controls and limits

The original native helper
[`elfmap-trace.c`](../../lab/irix-xclock/elfmap-trace.c) installs software
breakpoints immediately before and after the pinned libc/rld `syssgi` traps.
It reads the actual argument registers, two program headers, syscall return
registers and existing bytes at each requested address. It verifies the
original syscall/branch instructions before changing them and restores each
instruction before execution. Vendor files remain unchanged; ptrace changes
the traced process's instruction pages. Raw instruction/memory output stays
in ignored `.work/irix-xclock-loader`.

A native o32 control before and after the vendor captures traps at its known
entry `0x00400090`, restores that instruction, continues and exits 37. The
38-slot, 64-bit kernel register capture has an intact guard. The helper uses
NetBSD's MIPS debugger BREAK code 514, which preserves EPC. A preliminary run
using BREAK code zero failed the native control because NetBSD deliberately
advances EPC for that instruction. It stopped before vendor capture and halted
cleanly; it contributes no vendor evidence.

The completed run is `.work/irix-xclock-loader/runs/ci-nqn5qcww`. Both vendor
children exit 1 naturally and retain the same libXmu console diagnostic as
the preceding unmodified runs. The guest halts cleanly and its IRIS process
exits. The qualifier re-decodes private captures, verifies their hashes,
compares submitted headers with the pinned original files, and compares the
two memory samples with libXaw. Only addresses, return values, hashes and
other metadata are published.

This diagnostic qualifies root CI observations on the xstat kernel. It does
not qualify a new mapper, an ordinary-mode breakpoint run, an original-IRIX
n32 relocation oracle, or a graphical vendor application. The earlier xclock
experiment separately establishes the same unmodified loader failure in
CI/ordinary execution under root and uid 1234.

## Bounded next change

The next mapper change should add collision relocation to the existing two
load-segment contract. Preserve the current descriptor, layout, permissions,
file-size, RLIMIT_AS, single-LWP and unshared-vmspace checks. Detect occupied
requested load ranges before insertion, find a free span for the entire
layout, and apply one displacement to both kernel-local header addresses.
Return the actual first load address so rld can perform its relocations.
Leave the caller's header array unchanged. Keep requested placement when the
load ranges are free; occupation of the unmapped inter-segment gap alone
should not force a relocation.

The displacement must preserve every segment's alignment/congruence, including
different `p_align` values. Check rounded ends, span arithmetic and the chosen
address against the existing bounded address window. Continue refusing to
replace mappings and retain rollback of only newly owned ranges. Distinguish
an observed address collision from other mapping failures instead of treating
every `ENOMEM` as permission to retry elsewhere. Leave gaps unmapped.

There is already an original-IRIX o32 oracle: the two collision cases in
[`elfmap-reference.json`](../../lab/irix-o32/elfmap-reference.json) return a
new base at `0x5dc00000`, execute the relocated function, check initialized
data/BSS, and preserve the old sentinel. The
[original result](2026-10-30-irix-o32-elfmap.md) records this deliberate gap in
the current implementation. That observed address is not a required placement
constant, and lies outside Xiri's current bounded window.

The licensed historical NetBSD implementation at audited revision
`5aca2679d78276864d2980a08314887b2058fb2c` also relocates colliding ELF maps,
using `IRIX_MAPELF_RELOCATE=0x04000000` as a search hint, changing only local
headers and returning the new base. It provides design evidence; its old UVM
calls are not directly suitable for the current tree. Current
`uvm_map_findspace` requires the map to be at least read-locked.

Before calling a bounded implementation qualified, extend the original
libc-free fixtures and compare both o32 and n32 on original IRIX and NetBSD:

- Collision in RX, RW and BSS; preserve old sentinels and execute/check every
  new relocated segment, including zero fill and partial tails.
- Repeated competing maps, an occupied preferred fallback area, and a gap-only
  occupant; return a usable base while retaining existing mappings.
- Header-array immutability, one common displacement, different segment
  alignments, returned-address bounds and overflow rejection.
- Text write protection, unmapped gaps, failure/rollback after partial
  insertion, and resource-limit exhaustion without clobbering old data.
- Existing positive and rejection tests under both kernel ABIs; preserve
  historical reports and give changed collision expectations a new baseline.
- Original analog/digital xclock under root and uid 1234 in CI/ordinary mode,
  with native X controls and traces of the next loader or application boundary.

Further libraries have overlapping linked defaults. Mapping libXmu alone will
not establish a working clock or desktop; its next observable behavior remains
to be measured after a separately qualified mapper change.
