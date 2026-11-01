# Native 64-bit Indy qualification — 2026-10-30

This checkpoint qualifies a separate LP64 NetBSD kernel over the installed
o32 userland, with native n32/n64 probes. It prepares the kernel route needed
by the supplied IRIX n32 echo and desktop executables. The IRIX personality
is disabled in this kernel; foreign application compatibility is a later
step. The successful [o32 asa baseline](2026-10-30-irix-o32-dispatch.md)
remains separately pinned.

Reproduction commands are in the [lab](../../lab/netbsd64/README.md).
[baseline.json](../../lab/netbsd64/baseline.json) pins the kernel, emulator,
config and seed media. The accompanying [JSON record](2026-10-30-netbsd64-native.json)
retains the final observations and regression summaries.

## Source and build

NetBSD branch
[`xiri/irix-n32-baseline`](https://github.com/salvogendut/NetBSD-xiri/tree/40d3a490765b8babc8c9cd2aa03a80fa26567320)
adds commit `40d3a490765b8babc8c9cd2aa03a80fa26567320` to the previous
o32 personality revision. Its only source change is the LP64 SGI ARCS
firmware-call bridge in `sys/dev/arcbios/arcbios_calls.S`. The sibling fork
checkout and earlier o32 worktree stay unchanged.

IRIS branch
[`xiri/netbsd64-tlb`](https://github.com/salvogendut/iris/tree/9df1df14334838a989253efefe26f0547e6da592)
adds commit `9df1df14334838a989253efefe26f0547e6da592` to the qualified
Newport revision. It corrects TLB tag comparisons and adds a focused
regression. Its build lives in `.work/target-netbsd64`, using the existing
locked dependencies and Rust nightly 2026-10-28.

The platform is a 256 MiB R4400 Indy/IP24 with Newport. The config includes
`GENERIC64_IP2x`, `COMPAT_NETBSD32`, and native ELF64 execution. It excludes
IP20 Hollywood audio because that driver requires 4 KiB pages. This kernel
uses the default 8 KiB pages. The host build target is `mips64eb`; the kernel
is n64/LP64, while installed NetBSD 11.0 programs remain o32.

| Artifact | SHA-256 |
| --- | --- |
| PROM-bootable ELF32 wrapper | `5892bba9bcd6c81dd77a33cd8d0797606af4bb6ce58ecec48808a18de321c299` |
| Native ELF64 kernel, installed as `/netbsd` | `092c6121033d63f2e998293ba3e25aa227a8f84b2b37a678469e47726eea2547` |
| Debug kernel | `5e2d9509f64f981ee1847099c672c035a070a962a8ecfca5b6679ef791891397` |
| IRIS | `1b3f7702ba7f43b5c4fca8ba8884243559f46371d8d67a36ce5e6fee1e595eba` |

Ident is `XIRI_INDY64_20261030`, NetBSD 11.99.9. The final incremental build
records clean committed source; kernel bytes match the last implementation
build. The seed disk still contains its earlier `/netbsd`, so startup's
savecore query reports a kernel-symbol mismatch before the harness installs
the matching ELF64 file. No core-dump recovery is qualified by this run.

## Two boot blockers

The initial kernel failed during console initialization. A debugger trace
showed the o32 PROM truncating the kernel's XKPHYS stack address when it
adjusted the stack using a 32-bit instruction. The later memory-controller
fault was a consequence of that address loss.

The NetBSD bridge gives firmware a KSEG0 alias for cached XKPHYS arguments
and stack addresses in low RAM, supplies the o32 stack argument area, and
preserves full-width callee-saved GPRs, curlwp, original stack and Status.
It disables interrupts and selects paired FPR mode for the firmware call,
then restores Status. The same bridge covers non-returning ARCS calls.
It is scoped to the IP2x low cached RAM mapping below 512 MiB; it is not a
general bounce-buffer or 64-bit firmware-structure conversion facility.
Existing o32 and other-platform wrapper code remains unchanged.

After that fix, the kernel mounted root and entered init, but the o32 shell
faulted while executing a page of zeros and kernel pointers. Its on-disk
bytes matched the release shell. A TLB dump established that a global xkseg
entry for `0xc00000000002a000` incorrectly matched the o32 user page
`0x0002a000`. The user's missing page should have faulted into the VM
system; the emulator's 32-bit comparison mask dropped Region and VPN bits
39:32, causing a false hit on the kernel mapping.

IRIS now retains those tag bits in both address modes, including TLB probe
and reconstruction after snapshot load. Privilege and refill-vector
selection remain separate. Valid 32-bit addresses are already
sign-extended internally; clearing UX/KX does not make an existing extended
mapping equivalent to its low 32 bits. This follows the address and EntryHi
definitions in the [R4000/R4400 manual](https://nekofiles.irixnet.org/Documents/doc/R4400/User_Manual/R4400_Uman_book_Ed2.pdf),
printed pages 70 and 74.

The new regression fails on the previous emulator and passes after the
change. It covers fetch/read/write, global and ASID-qualified entries,
different regions and upper VPN bits, cached lookup collisions, TLBP and
snapshot reconstruction. All 14 TLB tests and all 258 CPU tests pass; the
14 are included in the 258, not additional tests.

A temporary 4 KiB kernel experiment did not solve the issue and panicked
before init. It remains an unqualified diagnostic artifact. The final
config restores 8 KiB pages. Initial failed boots, the 4 KiB experiment,
and harness runs using unsupported `getconf LONG_BIT` or failing to restore
the ordinary-user fixture's read permission after copying are excluded from
the final qualification.

## Native checks

The original assembly fixtures execute native NetBSD calls, without libc.
Each ABI has eight cases: full-width saved registers across repeated traps,
FR=1 odd floating-point registers, seek beyond 4 GiB with a wide return,
private mapping at an 8 KiB file offset, indirect mmap using eight register
slots, error returns, a syscall in a branch delay slot, and a protected-text
write. Successful probes emit exact output and exit 37; protected writes
must terminate with SIGSEGV.

The installed compiler builds an o32 compatibility test. It checks 32-bit
pointers/longs and 64-bit file offsets, the actual page size, clock, stat,
sparse file operations, private mapping and protection, fork/wait, pipe/poll,
exec of `/bin/sh`, and SIGUSR1 delivery on an alternate signal stack. It runs
as root and UID 1234/GID 5678. Floating-point arithmetic after signal return
works, but this is not a full floating-point signal-context preservation
test. The n64 fixtures use low virtual addresses and do not qualify a complete
n64 userland or high-address application mappings.

The harness also repeats o32/n32/n64 executions, checks native state before
and after, requires unchanged input hashes, and verifies that all four vendor
candidates fail exec with `ENOEXEC`. Kernel/file/swap controls and clean guest
halt are mandatory. Every run starts from private disk and NVRAM copies.
No proprietary files or instruction dumps are committed.

## Final qualification

| Run | Scenarios | Seconds | Result |
| --- | ---: | ---: | --- |
| LP64 native, CI | 33 | 166.788 | Pass |
| LP64 native, ordinary | 33 | 167.803 | Pass |
| Existing o32 runtime/dispatch, CI | 148 | 207.107 | Pass |
| Existing o32 runtime/dispatch, ordinary | 148 | 229.812 | Pass |
| Existing o32 static/native, CI | 89 | 169.351 | Pass |
| Existing o32 static/native, ordinary | 89 | 163.586 | Pass |
| Original IRIX reference, CI | 51 | 303.360 | Pass |

All seven runs used the new IRIS build and required clean guest shutdown.
The 66 native scenarios are additional to the 474 existing NetBSD o32
scenarios and 51 original-IRIX cases. CPU unit tests are counted separately.
The o32 regressions use the unchanged `XIRI_IRIX_DISPATCH` kernel, including
all seven vendor asa inputs as root and ordinary user in both modes. They
preserve the completed application path while qualifying the emulator fix;
they do not port asa to the new LP64 kernel.

Full local logs are retained under the paths in the JSON record, which
contains complete native observations and hashed regression summaries.
The original-IRIX reference checks the raw image's size on each run and
relies on its previously established intake hash for content identity.
The shared harness accepts `XIRI_IRIS_BIN_DIR` to select this isolated
emulator/CI-client pair without replacing the previous default build.

## Next compatibility boundary

Native n32 execution does not establish IRIX n32 syscall or runtime support.
The current foreign personality explicitly requires an o32 kernel and
32-bit `register_t`. Its dispatcher cannot be enabled unchanged on LP64.

1. Port the bounded o32 personality to LP64 with explicit 32-bit wire types,
   checked pointer widening, four register arguments plus 32-bit stack
   spills, correct return extension, and ABI-specific exec setup. Preserve
   the existing 32-bit kernel route and rerun its tests.
2. Add separate n32 recognition and dispatch. n32 has 32-bit pointers but
   eight 64-bit argument registers; wide arguments, returns, indirect calls,
   errors, delay slots and malformed inputs need original synthetic probes
   paired with the IRIX reference. Commit process ABI state only after
   executable selection succeeds.
3. Qualify ELF32 n32 text/data/BSS, stack and auxiliary data, then the original
   `/lib32/libc.so.1` and unmodified echo. Investigate the 8 KiB native-page
   boundary explicitly: the previous o32 loader/runtime experiments used
   4 KiB pages, and their alignment assumptions cannot simply be retained.
4. Require successful o32 asa alongside n32 echo on the new route before
   treating it as a replacement for the existing application baseline.

IRIX n64, caught foreign signals, general relocation, shared address spaces,
desktop services, graphics and physical hardware remain outside this step.
