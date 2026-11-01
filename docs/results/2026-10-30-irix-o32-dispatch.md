# Unmodified IRIX asa on NetBSD — 2026-10-30

**The original IRIX 6.5.22m asa now runs its filter on Xiri's experimental
NetBSD kernel, using unchanged libc and rld.** Seven stdin cases produce the
same bytes as original IRIX and exit zero. They run as root and as
UID 1234/GID 5678 on NetBSD. This is the first completed vendor application
path; it does not establish general IRIX application or desktop compatibility.

The [previous checkpoint](2026-10-30-irix-o32-elfmap.md) entered rld but failed
after an unsupported indirect page-size query. The
[JSON record](2026-10-30-irix-o32-dispatch.json) contains the final inputs,
source hashes, observations, paired records, and 24-call vendor trace.

## Source and build

NetBSD branch
[`xiri/irix-o32-dispatch`](https://github.com/salvogendut/NetBSD-xiri/tree/6abdd05eca298e29af07d6176ea453e696de90a3)
contains commit `6abdd05eca298e29af07d6176ea453e696de90a3`, based on
`755afd768ae96bfde4a52705f1afe0fe1889d068`. Changes are confined to the
personality's C file and README in the isolated worktree. The sibling checkout
remains on trunk. Neither IRIS nor the native VM implementation changed.

The clean-source build uses
[`XIRI_IRIX_DISPATCH`](../../lab/irix-o32/XIRI_IRIX_DISPATCH), ident
`XIRI_IRIX_DISPATCH_20261030`. Kernel SHA-256:
`be05f4da8539da2be40addd3fdb7bd734a2e203bbc89f0f04fb5450229ded55e`.
Debug kernel SHA-256:
`d43b50185c2ef63359ace6246e59f5117ad9eb59ac6f6e2f746e99da2d87d87a`.
The final incremental build records the clean committed source; its kernel
bytes match the last implementation build. The platform remains a 256 MiB
R4400 Indy/Newport, NetBSD 11.99.9 kernel and installed 11.0 userland.
IRIS remains revision `484452d963d2da4e2a7559e88bcc33da0f2a0c01`, binary
SHA-256 `cc6561d0bdfec6ce30d656caf4a6eaee6ffbf622e5348c3b77b73810d5293f56`.

The [runtime pin](../../lab/irix-o32/dispatch.json) and
[media manifest](../../lab/irix-reference/manifest.json) retain the unchanged
vendor identities:

| File | SHA-256 |
| --- | --- |
| `/usr/bin/asa` | `c87a69be927e9f1a7649a8d01ae79b890395fb279e44daa6945392bb5a4731de` |
| `/usr/lib/libc.so.1` | `ea766492103a193e9d404942705e4e28987545e37f699ede232b6c0f8c97c954` |
| `/lib/rld` | `30228b54c1e5585b365514eb7c9895b03cc0f61cb898e05e3ddafece87863439` |

No vendor code, headers, firmware, disks, or disassembly are committed. The
original media remains untouched; every execution uses private disk/NVRAM
copies and the reference uses an overlay.

## Implemented behavior

Trap 1000 implements one level of `syscall(number, ...)`. The selected number
passes through the same explicit allowlist as direct calls. The selector
occupies a0, arguments start in a1..a3, and remaining words start at sp+16.
Direct arguments still use a0..a3 and sp+16 onward. The dispatcher checks
the complete spill range for arithmetic overflow before copyin. Unsupported
or nested selectors use the zero-argument ENOSYS handler without reading the
stack. The saved original trap and argument registers preserve the existing
restart path; branch-delay return remains handled by native MIPS logic.
This adds neither `__syscall` nor 64-bit argument marshalling.

Trap 1056 implements `sysmp(MP_PGSIZE)`, command 14, returning PAGE_SIZE.
It marshals all five o32 argument words, as specified by the historical
interface. The original reference confirms EFAULT on inaccessible spill
slots even for this query. Only the command is interpreted; other sysmp
requests return the subset's explicit ENOSYS.

Mmap now accepts nonzero user-space hints with its existing private/non-fixed
flags, positive length, basic protections, and nonnegative aligned 32-bit
file offset. Hints at or above VM_MAXUSER_ADDRESS return EINVAL, as in the
tested reference case. Native non-fixed VM placement may round or fall back;
it never uses MAP_FIXED or removes occupied mappings. IRIX SGI_ANYADDR,
shared mappings, and other previously unsupported flags remain rejected.

Rld's query now returns 4096. Its first allocation requests 0x6000 bytes of
`/dev/zero` at hint `0x0fbda000`, replacing the previous invalid page-size
arithmetic and eventual zero-length request. Startup continues to asa's
reads, output write, and exit 0. The trace records trap entries and selected
arguments; it is not a syscall-return trace. Direct probes and the completed
filter independently establish the new behavior.

Optional `syssgi` requests RXEV_GET (92), USE_FP_BCOPY (129), and TOSSTSAVE
(108), terminal `ioctl` 1054, and `prctl` 1130 (LASTSHEXIT 22, GETNSHARE 14)
still return unsupported errors. The tested non-terminal filter path tolerates
them. No dummy successes were added for those calls.

## Paired probes and output

[`dispatch.S`](../../lab/irix-o32/dispatch.S) is original libc-free assembly.
Its builder emits 44 small executables and deterministic input files. A normal
probe emits exactly eight big-endian words: magic, case, v0, v1, a3, assertion
bits, a preserved value, and a reserved word. Indirect exit deliberately emits
nothing and exits 37. The cases cover zero/one/three/four/five/six-argument
dispatch, open/read/close, errors, unknown selectors, delay slots, null/wrapping
stacks, a partially readable spill region, and direct/indirect mappings.
Mapping probes verify alignment, expected bytes at a nonzero file offset,
private writes followed by fresh contents after remapping, and preservation
of occupied data or executable text.

The same bytes execute on original IRIX 6.5.22m. The paired observations
explicitly retain differences:

| Case | Original IRIX | Xiri |
| --- | --- | --- |
| Valid direct/indirect page-size query | 4096 | 4096 |
| Bad sysmp or mmap spill stack | EFAULT | EFAULT |
| Tested invalid fd/pointer | EBADF/EFAULT | EBADF/EFAULT |
| Free or unaligned user hint | Uses/rounds hint | Uses/rounds hint |
| Occupied hint | Alternate free mapping, old bytes intact | Alternate free mapping, old bytes intact |
| Kernel-space hint | EINVAL | EINVAL |
| Unknown syscall selector / sysmp command | EINVAL | ENOSYS, explicit subset policy |
| Nested indirect selector / syscall in branch delay slot | Shell status 140 (SIGSYS) | ENOSYS for nesting; normal success/error return for delay slots |

Mapping fallback addresses differ by native placement policy. The host checks
aligned user addresses and distinct occupied mappings, while the probe checks
the contents. It does not require identical virtual addresses across kernels.
NetBSD also repeats indirect UID/GID probes under ordinary, effective-root,
and real-root credential profiles; v0/v1 must reflect the actual native IDs.

Asa's seven cases cover the original single line, multiple lines, double
spacing, page advance, overprinting, an unterminated final line, and empty
input. Every NetBSD case requires exact stdout, empty stderr, exit zero,
successful exec, no signal, and no timeout. The ordinary-user cases use the
native parent to clear groups and set credentials before foreign exec.
Original IRIX runs the same inputs with its installed asa and verifies the
asa/libc/rld checksums against the extracted copies.

The bytes below use escaped control characters; each displayed input starts
with the literal ASA control character, including a space where shown.

| Input | Output on both kernels |
| --- | --- |
| ` XIRI_VENDOR_O32\n` | `XIRI_VENDOR_O32\n` |
| ` Alpha\n Beta\n` | `Alpha\nBeta\n` |
| ` Alpha\n0Beta\n` | `Alpha\n\nBeta\n` |
| ` Alpha\n1Beta\n` | `Alpha\n\fBeta\n` |
| ` Alpha\n+Beta\n` | `Alpha\rBeta\n` |
| ` Tail` | `Tail\n` |
| Empty | Empty |

## Final qualification

| Run | Top-level scenarios | Seconds | Result |
| --- | ---: | ---: | --- |
| NetBSD runtime/dispatch, CI | 148 | 233.121 | Pass |
| NetBSD runtime/dispatch, ordinary | 148 | 233.674 | Pass |
| NetBSD static/native regressions, CI | 89 | 159.457 | Pass |
| NetBSD static/native regressions, ordinary | 89 | 172.919 | Pass |
| Original IRIX, CI | 51 | 319.229 | Pass |

The 474 NetBSD scenarios include 88 ELF-map records, 128 query records,
100 dispatch executions (including six credential variants per mode), and
28 vendor asa executions. These are subsets of the scenario count, not
additional tests. The original reference contributes 44 interface executions
and seven asa cases. All final runs require clean guest halt and owned process
cleanup. Native kernel/file/swap controls and fixture checksums remain checked.

Static regression version 4 preserves the 70-fixture/89-execution suite while
updating two obsolete assumptions: trap 1000 may now dispatch a supported
call, and a nonzero mmap hint is accepted before the invalid fd is rejected.
The older suites and pinned kernels remain available. Exploratory runs that
still expected the previous asa error are recorded locally as failed; only
the final pinned runs count above.

Reproduction commands are in the
[lab](../../lab/irix-o32/README.md#vendor-asa-execution). Full serial logs,
reference archives, and private disk copies remain under `.work/`.
The reference checks raw-disk size and relies on the intake SHA-256 instead
of rehashing its 94 GiB logical image on every run. Its pre-existing XFS and
optional-service warnings remain outside this limited file/syscall comparison.

## Remaining scope

This qualifies asa's tested stdin/stdout path and the relocations required by
that run, not arbitrary dynamic libraries, environment/argument combinations,
terminal behavior, fork/exec, caught signals, process sharing, or restart under
signal delivery. Wider ELF layouts and general relocation remain bounded as
documented in the mapping experiment. n32 echo, 4Dwm, and Toolchest still fail
foreign exec on this kernel; physical hardware remains untested.

The next step is a separate GENERIC64_IP2x/COMPAT_NETBSD32 boot/native baseline,
then synthetic n32 dispatch/loading and unchanged echo. The existing o32
personality explicitly requires a 32-bit kernel, so retaining its successful
asa path on the 64-bit route must be designed and tested separately.
