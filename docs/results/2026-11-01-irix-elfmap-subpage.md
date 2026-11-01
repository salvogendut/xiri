# Native-page mappings for 4Dwm's 4 KiB data segments

The mapper now accepts the data layout used by original libimdUtil and libXpm:
their virtual address and file offset begin halfway through an 8 KiB native
page. Previously SGI_ELFMAP rejected that boundary. This is a bounded loader
extension on top of the working winterm shell kernel.

The implementation is pinned at NetBSD `c819dd1c090` on
`xiri/irix-elfmap-subpage`. Both kernels and the unchanged IRIS executable are
pinned in the [subpage lab](../../lab/irix-elfmap-subpage/README.md).

## Mapping behavior

The mapper validates the original two PT_LOAD headers, then normalizes its
private copy of the data header to the native page boundary. Nonempty data
includes the preceding file bytes; pure BSS receives zero-filled padding.
It accounts for and checks collisions across the complete native pages before
mapping. Code and data virtual pages must remain separate. The caller's
headers, returned code base and common relocation displacement are preserved.

The original libraries share a backing file page between the end of code and
the beginning of data, at different virtual addresses. Native private COW
keeps a write through the data alias from modifying the code alias or backing
file. The fixtures verify that relationship, active data bytes, all declared
BSS bytes, prefix contents, RX protection, gaps and existing sentinels.

This does not admit arbitrary ELF layouts. Native-page incongruence and
virtual code/data page overlap are still rejected on LP64. Both kernels retain
stricter file bounds, logical file-segment overlap, flags, alignment, size,
permissions, single-thread and resource-limit policy. Native o32 and original
IRIX use 4 KiB pages, so they need no extra preceding half-page. The report
retains every original/native record difference, including placement.

## Verification

The 74 input variants include the previous 57 relocation cases unchanged and
17 new cases. Both foreign ABIs run under root and UID1234 on IRIX and LP64;
the o32 kernel runs the o32 cases. Original fixtures use direct syscall traps.
Independent comparison checks every 48-byte observation and fixture hash;
active payload checks run inside the mapped process. The native harness checks
the backing input hash before and after every case, brackets the suite with
native and original vendor programs, and runs explicit RLIMIT_AS checks.

The original IRIX reference contains 296 executions and shuts down cleanly.
Its four no-bounded-space cases cannot establish the 960 MiB occupant and are
explicitly excluded from mapper behavior comparison. Native tests establish
that occupant and check the bounded search failure. IRIX accepts some invalid
layouts without touching their pages; this does not weaken the native policy.

The complete matrix passes: **740 mapping cases, 10 limit checks and 32
controls**, with clean shutdown in every run.

| Run | Mapping cases | Limit cases | Controls |
| --- | ---: | ---: | ---: |
| LP64 CI `lp64-ci-1slll0pa` | 296 | 4 | 12 |
| LP64 ordinary `lp64-ordinary-2af0n1nx` | 296 | 4 | 12 |
| o32 CI `o32-ci-532cq5jw` | 148 | 2 | 8 |

The [qualification JSON](2026-11-01-irix-elfmap-subpage.json) binds exact
inputs, kernels, harnesses, observations and all oracle differences. The
[original reference records](../../lab/irix-elfmap-subpage/reference.json)
retain the independently decoded IRIX results. The [live 4Dwm comparison](2026-11-01-irix-4dwm-loader.json) confirms that the original library boundary is removed. No graphical success is claimed yet.

## Application follow-up

The [4Dwm lab](../../lab/irix-4dwm/README.md) separately captures the actual
unchanged application, its library headers and startup behavior on native X.
The new kernel loads past libimdUtil and libXpm, then original GL initialization
opens `/dev/zero` and requests `mmap(0, 4096, 3, 0x92, ...)`. The existing wrapper
returns EINVAL; GL reports the failed mapping, followed by SIGSEGV. Native X and
cleanup controls pass. The next implementation boundary is this fixed/local
private mapping request; the six arguments and following fault are being
captured separately. The next graphical acceptance gate is ownership of window management and decoration of
a native client, followed by focus/movement and the working winterm shell.
Window management, terminal resize, desks, restoration and desktop services
remain distinct checks.
