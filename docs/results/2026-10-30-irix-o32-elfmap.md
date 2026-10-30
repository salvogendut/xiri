# IRIX o32 rld mapping — 2026-10-30

**Original rld code now executes on the experimental NetBSD kernel.** Asa's
unchanged libc maps `/lib/rld` with `SGI_ELFMAP` and transfers control into it.
Rld then makes an unsupported indirect page-size query, reaches an allocation
failure, writes `rld_sbrk: Can't map /dev/zero -- probably not enough virtual memory\n`,
and exits 1. This outcome is measured as root and as UID 1234/GID 5678.
Asa's filter has not executed; n32 echo, 4Dwm, and Toolchest remain rejected.

This advances the [query checkpoint](2026-10-30-irix-o32-queries.md), where libc
could read rld's headers but could not map it. The
[JSON record](2026-10-30-irix-o32-elfmap.json) retains input/source hashes, all
observations, the sixteen-call vendor trace, and the original-IRIX comparison.

## Sources and input identity

NetBSD fork branch
[`xiri/irix-o32-elfmap`](https://github.com/salvogendut/NetBSD-nixbench/tree/xiri/irix-o32-elfmap)
contains commit `755afd768ae96bfde4a52705f1afe0fe1889d068`, based on query commit
`dc08d65a8e7b3e6cdbd7ca978a200b6f50a42ad5`. Changes are confined to
`sys/compat/irix_o32/irix_o32.c` and its README in the isolated worktree.
The sibling checkout remains on trunk. No emulator or native mapper code changed.

The committed-source build uses GCC 14.4 and
[`XIRI_IRIX_ELFMAP`](../../lab/irix-o32/XIRI_IRIX_ELFMAP), identifier
`XIRI_IRIX_ELFMAP_20261030`. Its kernel SHA-256 is
`c43f4aea546155dbb2019e065a22730ab48e3f3e68377cae25fe9c50d756f670`.
The kernel bytes match the exploratory build: the implementation was unchanged
when committed, and the final incremental build records clean source status.
IRIS remains `484452d963d2da4e2a7559e88bcc33da0f2a0c01`, binary SHA-256
`cc6561d0bdfec6ce30d656caf4a6eaee6ffbf622e5348c3b77b73810d5293f56`.
The machine remains a 256 MiB R4400 Indy/Newport with a NetBSD 11.99.9 kernel
over the installed 11.0 userland.

Asa and its runtime retain the [media](../../lab/irix-reference/manifest.json)
and [runtime pins](../../lab/irix-o32/elfmap.json). In particular, rld remains
SHA-256 `30228b54c1e5585b365514eb7c9895b03cc0f61cb898e05e3ddafece87863439`.
Its two load segments are:

| Segment | File offset | Linked address | File bytes | Memory bytes |
| --- | --- | --- | --- | --- |
| RX | `0` | `0x0fb60000` | `0x37000` | `0x37000` |
| RW/BSS | `0x38000` | `0x0fbd8000` | `0x1000` | `0x16e4` |

Both have ELF alignment `0x4000`; entry is `0x0fb60150`. No vendor bytes are
modified or included in Git. The original media and extracted reference disk
are preserved; runs use private clones/overlays. Reference binaries, headers,
and disassembly stay in the ignored workspace.

## Mapping contract and cleanup

Trap 1040, request 68 takes a readable regular-file descriptor, a pointer to
exactly two ELF32 program headers, and count 2. The headers are copied once into
a fixed 64-byte kernel array. The syscall returns the first linked address in
v0 and preserves v1. It uses the supplied load descriptions without parsing
an ELF header in the file.

The accepted layout is ordered PT_LOAD RX text at file offset zero with equal
file/memory size, then RW data with optional BSS. Each segment is at most
16 MiB; the virtual span is at most 32 MiB within `0x00400000..0x40000000`.
Addresses and offsets must be page-aligned; ELF alignment must be a power of
two between one page and 1 MiB with congruent offset/address. File extents must
fit the file and signed 32-bit offset range. File and rounded virtual ranges
cannot overlap or wrap. Physical-address fields are ignored; gaps remain
unmapped. Page padding follows the native exec mapper's granularity.

Invalid counts return EINVAL, bad header pointers EFAULT, invalid/non-readable
descriptors EBADF, non-regular descriptors EINVAL, and unsupported layouts
ENOEXEC. Native VEXEC and noexec-mount checks apply. `vn_marktext` rejects active
writers, and file size is checked again after marking text. Native mapping
helpers retain PaX checks and vnode mapping checks for paged file mappings.
The implementation checks RLIMIT_AS and rejects shared vmspaces, multiple LWPs,
and future-wired maps. These restrictions are explicit; the personality has
no calls creating those process states.

At most four native exec VM operations map private full file pages, a partial
RW page, and whole BSS pages. The partial page starts zero-filled and reads
only the remaining initialized bytes, excluding nonzero file poison beyond
p_filesz. Fixed insertions refuse overlaps without removing existing entries.
A journal records each successful insertion, including the partial page before
its read can fail. On failure, only those ranges are unmapped. The single-LWP,
unshared-vmspace restriction protects that ownership during rollback; this is
not a general transaction for shared address spaces. Existing collisions return
ENOMEM. Relocation is outside this subset.
Native vnode text marking follows NetBSD's reference lifetime; mapping rollback
does not forcibly clear flags shared by other vnode users.

Two probes force later mapping failures. One collides at RW insertion after RX
has been created. The other collides at BSS insertion after RX, a full RW page,
and a partial RW page. Both verify that an old data sentinel survives and that
an immediate retry can reuse every newly created range. I/O-error injection,
concurrent/shared mapping, resource-limit exhaustion, and physical hardware
remain unqualified; the tested rollback paths are recorded precisely.

## Paired original-IRIX observations

The original, libc-free [`elfmap.S`](../../lab/irix-o32/elfmap.S) probe is
2,552 bytes, SHA-256
`8c9fa30d68e5bf8a896f750908e836861964d4b5f8b1efefc0603faa661a405b`.
It and all payload bytes are identical on both kernels. Each 48-byte record
contains a magic/case pair, v0/v1/a3, assertion flags, retry results, and an
old-data sentinel. Positive cases execute a mapped function and check every
declared initialized/BSS byte. Repeat mapping checks fresh contents after
private writes and unmapping; text writes and gap reads must fault.

The original system agrees on those positive results, v1 preservation, and
the tested EFAULT/EBADF cases. On address collisions it relocates to a different
base (observed `0x5dc00000`); the probe checks relocated execution/data/BSS and
the old sentinel. Xiri instead tests explicit rejection and rollback. The
reference permits additional layouts and descriptor states:

| Case | Original IRIX observation | Xiri policy |
| --- | --- | --- |
| One load header | Success | EINVAL; exactly two required |
| Three-header fixture, with poisoned third header | ENOEXEC | EINVAL before reading headers |
| Directory descriptor | ENODEV | EINVAL; regular files only |
| `/dev/zero` descriptor | Success | EINVAL; no device mappings |
| Read/write descriptor | Success | ETXTBSY from native text checks |
| Non-executable regular file | Success | EACCES from native execution checks |
| Tested extra permissions, text BSS, loose alignment, reversed/file-overlapping ranges, wider size/span, short file | Success return | ENOEXEC; outside bounded contract |
| Zero memory size | EAGAIN | ENOEXEC |
| Overlapping virtual ranges / wrapped address | ENOMEM | ENOEXEC |
| Wrapped file offset | EFAULT | ENOEXEC |

Malformed/wider reference cases record syscall return values without accessing
the resulting ranges. A success return does not qualify their mapping contents
or protections. All individual observations and fixture hashes are pinned in
[`elfmap-reference.json`](../../lab/irix-o32/elfmap-reference.json).

The final reference run repeats 42 root cases plus a UID/GID 60001 control,
verifies uploaded checksums and native asa/libc/rld checksums, and halts cleanly.
Its user setup uses direct setgid/setuid without clearing supplementary groups;
NetBSD's native parent clears groups before setting its ordinary credentials.
Firmware/probe hashes are checked. The raw image is size-checked, relying on
the intake SHA-256 record rather than rehashing its 94 GiB logical length.
Existing XFS and optional-service warnings remain separate from these results;
no clean graphical-reference qualification is claimed.

## Vendor execution and next blocker

The native parent supplies ` XIRI_VENDOR_O32\n`, one argv entry, an empty
environment, separate output/exec-error pipes, and a five-second child timeout.
Both root and ordinary-user asa return exec success, empty stdout, the exact
68-byte rld diagnostic, exit 1, no signal, and no timeout kill. Only root is
traced. The pinned sixteen-entry sequence is:

| Phase | Observed calls |
| --- | --- |
| Libc startup | Capability configuration, process capability get, UID pair |
| Load rld | Open, read 512 header bytes, SGI_ELFMAP with two headers, close |
| Original rld code | Trap 1000 at `0x0fb8c614`, a0=1056, a1=14: indirect `sysmp(MP_PGSIZE)` |
| First allocation | Open `/dev/zero`, mmap with null hint, length `0x8000`, RW/private, close |
| Following allocation | Open `/dev/zero`, mmap with non-null hint `0x7def8000` and length zero |
| Failure | Write 68-byte diagnostic, unsupported prctl trap 1130, exit 1 |

Rld's syscall PCs lie inside its newly mapped RX range, establishing execution
beyond libc. Entry traces do not independently capture syscall returns. The
inspected `_getpagesize`/`_sysmp`/`sgi_main` path explains the failure: trap 1000
is unsupported, its wrapper returns -1, and rld stores that value as page size
without checking it. `_sbrk` then uses it in rounding arithmetic. The first mmap
succeeds, as established by the subsequent close path; a later zero-length
hinted request is rejected by the existing mmap subset. This is an inference
from the trace, tested dispatcher, and original disassembly, not evidence of
host memory exhaustion.

The next change is checked indirect syscall argument dispatch and the real
`sysmp(MP_PGSIZE)` result, followed by measured mmap-hint behavior. It should
retain explicit unsupported-operation failures and retrace the unchanged rld.
Asa's main entry, full vendor relocation, wider ELF mapping, caught signals,
PRDA, process sharing, desktop execution, and physical hardware remain open.
The separate [n32 kernel route](2026-10-30-irix-o32-runtime.md#n32-kernel-route)
remains a source audit, with echo preceding the n32 desktop binaries.

## Validation and reproduction

Each NetBSD mode passes 86 runtime/query/mapping scenarios and 89 static
regressions: **350 top-level scenarios** in total. Within those counts are
88 mapping records and 128 query records. Original IRIX adds 43 mapping records,
counted separately. All five final guests halt cleanly.

| Run | Cases | Duration |
| --- | --- | --- |
| `ci-fv7hf_k2` | 86 runtime/query/mapping | 223.354 s |
| `ordinary-n97jf8bp` | 86 runtime/query/mapping | 227.021 s |
| `segments-compat-ci-d578gshr` | 89 static | 197.164 s |
| `segments-compat-ordinary-vf08hw4_` | 89 static | 200.852 s |
| Original IRIX `ci-ijy93sa1` | 43 mapping | 285.225 s |

Both modes cold-boot fresh disk/NVRAM clones with the committed kernel, compile
native runners with warnings as errors, verify imported hashes, and pass the
kernel/file/swap and native execution controls. Post-run hashes confirm fixture
and mapping-source immutability. A separate NetBSD case temporarily marks its
virtual CD noexec and requires EACCES when mapping the unchanged payload there.
Reproduction commands and artifact paths are in the
[mapping lab](../../lab/irix-o32/README.md#bounded-rld-mapping).

Exploratory NetBSD runs passed the mapping cases but intentionally failed the
previous vendor expectation, exposing the new rld boundary. Both halted cleanly.
The first reference attempt detected a rebuilt fixture after its long boot and
aborted before probes, then halted cleanly. The harness now freezes inputs
before boot. A complete observation run then established reference expectations;
the final run repeats those checks against the pin. These exploratory runs are
retained locally and excluded from final qualification counts.
