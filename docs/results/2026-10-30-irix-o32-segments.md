# Static o32 writable data and BSS — 2026-10-30

The experimental NetBSD personality now loads a separate writable data/BSS
segment alongside its marked static o32 text segment. All 89 cases pass in CI
and ordinary IRIS execution. Initialized data, zero-fill, repeated execution,
text write protection, unmapped-page faults, and malformed-segment rejection
pass; both guests shut down cleanly. Executable-file hashes remain unchanged
after the programs modify every declared data/BSS byte.

This extends the [static argument/file/memory subset](2026-10-30-irix-o32-basics.md).
The marker and accepted ELF layout remain synthetic conventions. No vendor
IRIX program, runtime, dynamic loader, desktop, or physical machine was tested.

## Source and kernel

The NetBSD fork branch
[`xiri/irix-o32-segments`](https://github.com/salvogendut/NetBSD-xiri/tree/6a162a938061d16a60842fd9bb31d69e546d66dc)
contains commit `6a162a938061d16a60842fd9bb31d69e546d66dc`, based on the
previous implementation `c9ab9ccc062650870e17006571c93e665e2133d9`. The original
trunk base remains `a852b4a03800c32a127640b784fcc9fc94159d12`. Only the
personality's recognition function and scope README change in this step.
The sibling primary checkout stays on `trunk`.

The existing native ELF mapper in `sys/kern/exec_elf.c` already supplies private
file mappings, reads the partial writable file page into zero-filled memory,
and adds zero mappings for subsequent BSS pages. The personality validates the
new layout before these VM commands are generated. No native mapper or IRIS
change was needed.

The isolated GCC 14.4 build uses
[`XIRI_IRIX_SEGMENTS`](../../lab/irix-o32/XIRI_IRIX_SEGMENTS), identifier
`XIRI_IRIX_SEGMENTS_20261030`, and `.work/netbsd-irix-build/segments-tftp/`.
Kernel SHA-256 is
`8d91316b80352d4f271bb97ac993947f309275433709a7f32df73e40fc005366`.
The incremental rebuild from clean committed source matches the tested kernel.
Debug-image and source hashes are retained in the JSON record.

IRIS remains at `484452d963d2da4e2a7559e88bcc33da0f2a0c01`, binary SHA-256
`cc6561d0bdfec6ce30d656caf4a6eaee6ffbf622e5348c3b77b73810d5293f56`.
The profile remains R4400, 256 MiB, Newport, a NetBSD 11.99.9 kernel and
NetBSD 11.0 userland. Each run cold-boots a private disk/NVRAM clone and
installs matching `/netbsd`. The release and earlier fork kernels remain in
their own TFTP directories; X11 was not requalified here.

## Accepted static layout

The original two-header text/note layout remains accepted. A three-header
layout must have RX text, RW data/BSS, then the exact Xiri note, in that order.
ELF32/MSB MIPS III identity, System V OSABI, static `ET_EXEC`, and the existing
flags and note checks are unchanged.

| Segment | Validated bounds |
| --- | --- |
| Text | File offset zero, virtual address `0x00400000`, exactly R/X, equal file/memory size up to 1 MiB; contains headers, note, and aligned entry point |
| Data/BSS | Exactly R/W, nonzero memory size up to 1 MiB, file size no larger than memory size; zero file size permits pure BSS |
| Data alignment | Page-aligned virtual address and file offset, congruent modulo a power-of-two ELF alignment from one page through 1 MiB |
| Virtual ranges | Data starts at or beyond the rounded text end and ends at or below `0x01000000`; overlapping pages and wrapping/high ranges are rejected |
| File ranges | Data extent fits the actual file and native signed 32-bit offset range; nonempty file data starts after the rounded text file extent |

The image window below 16 MiB is an experiment constraint. It does not implement
general IRIX reserved-range policy. Partial pages retain native page-granularity
behavior. Entry points in data, BSS, or an unmapped gap are rejected. Writable
text, executable data, unknown flags, extra segment types, and malformed
alignment/size/offset combinations are rejected before mapping.

## Results

| Run | Cases | Duration | Shutdown |
| --- | --- | --- | --- |
| `segments-compat-ci-brgvfjv0` | 89 passed | 159.419 s | Clean |
| `segments-compat-ordinary-fldahga5` | 89 passed | 163.573 s | Clean |

The version 3 manifest has 70 fixtures: all 34 earlier fixtures are unchanged,
plus eight segment programs and 28 rejection variants. Five original
marked/native pairs and three additional data/BSS/native triples bring each
run to 89 cases. The [JSON record](2026-10-30-irix-o32-segments.json) retains
all 178 observations, fixture/source hashes, program headers, and timings.
The `segments` arrays use ELF32 program-header field order: type, offset,
virtual address, physical address, file size, memory size, flags, alignment.

| New program | Observation |
| --- | --- |
| `irix-segments` | 4112 initialized bytes and 8208 BSS bytes pass full checks and writes, including file-page tail and whole zero pages |
| `irix-segments-short` | 32 initialized bytes and 64 BSS bytes in the same page pass |
| `irix-segments-aligned` | 4096 file bytes followed by 8208 BSS bytes pass across an aligned boundary |
| `irix-segments-bss` | File size zero with 8208 BSS bytes passes |
| `irix-segments-adjacent` | RW data at `0x00401000`, immediately after rounded RX text, passes |
| `irix-text-write` | Emits the exact marker, then a store to text terminates with `SIGSEGV` |
| `irix-segment-gap` | Emits the marker, then a load from the gap at `0x00500000` terminates with `SIGSEGV` |
| `irix-segment-end` | Emits the marker, then a load from the first page after rounded BSS terminates with `SIGSEGV` |

The five successful layouts verify every declared initialized byte and every
BSS byte before modifying and reading them back. Nonzero `0xa5` file bytes
immediately following initialized data ensure that BSS is zero-filled instead
of copied from the file. The programs then read `/dev/zero` into BSS, use BSS
as the source for the exact 15-byte `XIRI_ABI_PROBE\n` output, and exit 37.
Assertion failures exit 99. Repeated data and pure-BSS executions start with
the original contents. A final guest `sha256 -c SHA256` checks every executable
against its original fixture hash.

The three fault programs use the new `fault-output` runner expectation: exactly
15 output bytes followed by signal 11, with no parent kill. A crash before
the marker cannot pass. These checks establish text write protection and
unmapped-page faults; they do not establish hardware-enforced non-executable
data or protection within the padding of a mapped page.

The 28 new rejection fixtures cover file size exceeding memory size, empty or
oversized data, virtual overflow/kernel/window/overlap ranges, address/offset
misalignment, invalid ELF alignment and congruence, overlapping/past-EOF/wrapping
file offsets, R/W/X and unknown flags, wrong segment types, entry points outside
text, text BSS, and truncated data. All return `ENOEXEC` through direct `execve`.

Both modes retain the earlier static ABI/error/rejection checks, bounded loop
cleanup, and native kernel/file/swap smoke test. The native runner compiles
with `-Wall -Wextra -Werror`. Post-run native identity/file checks and private
file-mapping integrity checks also pass. Each mode writes its own disk clone
directly, without snapshots or CI rollback. Full serial logs, media, configs,
and disposable disks remain in `.work/irix-experiment-runs/`.

Reproduction commands are in the
[fixture lab](../../lab/irix-o32/README.md#writable-elf-data-and-bss).

## Next boundary

Interpreter loading, runtime-path policy, and dynamic auxiliary data are next,
starting with a synthetic dynamically linked probe. The current loader does
not accept `PT_INTERP`, `PT_DYNAMIC`, arbitrary segment layouts, PIE, or general
unbranded IRIX ELF. Vendor runtime behavior, n32/n64, PRDA, process sharing,
caught signals, the original desktop, and physical Indy qualification remain
separate work. Original-IRIX comparison still needs a reference installation.
