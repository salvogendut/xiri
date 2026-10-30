# IRIX o32 runtime queries — 2026-10-30

Unmodified IRIX 6.5.22m asa now gets through libc's configuration and capability
queries on the experimental NetBSD kernel. Libc opens `/lib/rld`, reads its ELF
headers, and requests `syssgi(SGI_ELFMAP, fd, phdrs, 2)`. That mapping operation
remains unsupported: libc writes `Could not map rld from file /lib/rld\n` and
exits 239, with no stdout. The same outcome is measured as root and an ordinary
user. **Neither rld nor asa's main entry has executed.** n32 echo, 4Dwm, and
Toolchest still return `ENOEXEC`.

This extends the [interpreter baseline](2026-10-30-irix-o32-runtime.md). The
[JSON record](2026-10-30-irix-o32-queries.json) retains hashes, individual query
returns, all guest observations, vendor traces, and reference measurements.

## Implementation and inputs

The NetBSD fork branch
[`xiri/irix-o32-queries`](https://github.com/salvogendut/NetBSD-nixbench/tree/xiri/irix-o32-queries)
contains commit `dc08d65a8e7b3e6cdbd7ca978a200b6f50a42ad5`, based on runtime
commit `64915ea0900cd81e3bc2577504c709fb33051854`. Changes are confined to
`sys/compat/irix_o32/irix_o32.c` and its README. The sibling fork checkout stays
on its original trunk; the implementation uses the isolated worktree.

The clean committed build uses GCC 14.4, configuration
[`XIRI_IRIX_QUERIES`](../../lab/irix-o32/XIRI_IRIX_QUERIES), and identifier
`XIRI_IRIX_QUERIES_20261030`. Kernel SHA-256:
`3b56ce39455425ac8cc5b610439a68f78c4573a9e565f43a22deb184eb2af697`.
The R4400 Indy remains at 256 MiB with Newport, using NetBSD 11.99.9 over the
installed 11.0 userland. IRIS remains revision
`484452d963d2da4e2a7559e88bcc33da0f2a0c01`, binary SHA-256
`cc6561d0bdfec6ce30d656caf4a6eaee6ffbf622e5348c3b77b73810d5293f56`.
No ELF mapper or emulator code changes were needed.

Asa retains its [media-manifest hash](../../lab/irix-reference/manifest.json);
`/usr/lib/libc.so.1` and `/lib/rld` retain their
[runtime hashes](../../lab/irix-o32/queries.json). No vendor file is patched.
Binaries, firmware, reference headers, kernel disassembly, and disk
images remain outside Git. The supplied archives/CHD and extracted reference
disk are unchanged; guest writes use private clones and overlays.

## Bounded query contract

| Interface | Implemented result |
| --- | --- |
| Trap 1040, `SGI_SYSCONF` (22), `_SC_PAGESIZE` (11) | Native page size, measured as 4096 |
| `SGI_SYSCONF`, `_SC_CAP` (29) | `CAP_SYS_DISABLED` (0): traditional superuser permissions |
| Other sysconf names | `EINVAL` (22) |
| `SGI_PROC_ATTR_GET` (85), `SGI_CAP_PROCESS` | Three zero 64-bit capability masks, exactly 24 bytes |
| Other attribute names | `ENOATTR` (1009) |
| Null attribute name or output pointer | `EINVAL` (22) |
| Non-null bad name/output or read-only output | Checked copy faults, `EFAULT` (14) |
| Name requiring more than 80 bytes including NUL | `ENAMETOOLONG` (78) |
| Trap 1024 | Real UID in v0, effective UID in v1 |
| Trap 1047 | Real GID in v0, effective GID in v1 |
| Other syssgi requests, including setters and `SGI_ELFMAP` | Existing unsupported-call policy, `ENOSYS` (89) |

Xiri has no IRIX capability enforcement or foreign credential-changing calls.
The empty masks describe that absence; the successful query grants no
privileges. Every native operation retains NetBSD credential and authorization
checks. The native `sys_getuid_with_euid` and `sys_getgid_with_egid` operations
provide the identity pairs. Queries use four 32-bit argument words; unused
stack arguments are not fetched.

Two differences from the reference are intentional. The installed IRIX reports
mode 1 (`CAP_SYS_SUPERUSER`), while Xiri advertises mode 0 to describe its smaller
permission model. Original IRIX returns `EINVAL` for the tested unknown syssgi
request, while Xiri retains `ENOSYS` for unsupported operations. The paired
decoder checks these different expectations explicitly.

## Original IRIX comparison

The original, libc-free [`queries.S`](../../lab/irix-o32/queries.S) probe is
3,060 bytes, SHA-256
`08a682297105ab234008f513bedfdd533f2632344fae2f25ac93edeb4854bd08`.
Exactly the same binary runs on both kernels. Each execution emits sixteen
64-byte records containing a magic value, case index, v0/v1/a3, a poisoned
24-byte capability buffer, and surrounding guard words. The decoder requires
all 1,024 bytes, exact record order, expected returns, v1 preservation outside
identity calls, only the intended 24-byte write, and unchanged guards.

On original IRIX, root and UID/GID 60001 both report zero capability masks.
Page size, identity pairs, unknown attributes/sysconf, null/bad pointers,
read-only output, and name lengths match the table. A 79-character unknown name
plus NUL fits and returns ENOATTR; 80 and 256 characters return ENAMETOOLONG.
Native setup in Xiri's parent additionally tests different real/effective IDs
and clears supplementary groups. The IRIX probe uses its reference-only
setgid/setuid path for UID/GID 60001; it does not clear supplementary groups.

The supplied `/usr/include/sys/capability.h` defines the three 64-bit fields
and modes 0/1/2. The supplied syssgi/unistd headers establish the request and
sysconf numbers. Disassembly of `proc_attr_get` at `0x881b7420` in the supplied
unstripped kernel confirms the 80-byte name limit, 24-byte copyout, and relevant
error paths. Only semantic findings and input hashes are retained here.
Historical NetBSD snapshot `5aca2679d78276864d2980a08314887b2058fb2c` independently
supports capability mode 0 and the paired native identity operations.

The final reference run checks native asa/libc/rld checksums against the offline
copies, runs all 32 query records, and repeats native asa's successful filter:
input ` XIRI_VENDOR_O32\n`, output `XIRI_VENDOR_O32\n`, exit zero. The firmware
and uploaded probe are hash-checked; the 94 GiB logical raw disk is size-checked
and relies on the SHA-256 established at intake. The reference harness records
its decoder hash at launch. A later unrelated addition to the NetBSD test
matrix changed that module's hash; both raw reference outputs were revalidated
with the final decoder, with identical records.

Reference shutdown reached `Okay to power off the system now.` before emulator
exit. Existing XFS alerts and optional/third-party service warnings remain;
these checks qualify the measured calls and files, not filesystem health or a
graphical desktop session.

## Measured vendor boundary

The native parent supplies the same stdin, one argv entry, and empty environment
as the runtime baseline, with separate exec-error/stdout/stderr pipes and a
five-second child timeout. Both root and UID 1234/GID 5678 return:

```text
errno_bytes=0 errno=0 exit=239 signal=0 killed=0
STDOUT bytes=0
STDERR bytes=37: Could not map rld from file /lib/rld\n
```

Root asa's eleven-call trace is pinned; the ordinary-user case runs untraced.

| Trap | PC | Operation |
| --- | --- | --- |
| 1040 | `0x0fa362c4` | `syssgi(SGI_SYSCONF, _SC_CAP)` |
| 1040 | `0x0fa362c4` | `syssgi(SGI_PROC_ATTR_GET, "SGI_CAP_PROCESS", buffer)` |
| 1024 | `0x0fa530e4` | Get real/effective UID |
| 1005 | `0x0fa36524` | Open `/lib/rld` read-only through `/emul/irix` |
| 1003 | `0x0fa38f94` | Read 512 bytes from fd 3 |
| 1040 | `0x0fa362c4` | `syssgi(SGI_ELFMAP, 3, phdrs, 2)` |
| 1006 | `0x0fa363a4` | Close fd 3 |
| 1004 × 3 | `0x0fa566e4` | Write diagnostic fragments of 28, 8, and 1 bytes |
| 1001 | `0x0fa410e0` | Exit with `0xdeadbeef`, observed low byte 239 |

These are syscall entry records, not independent samples of return registers.
The direct query probe supplies return-register measurements for the query
subset. Reaching ELFMAP implies the read returned exactly 512 bytes because
the inspected libc path checks that count first. The tested dispatcher returns
IRIX ENOSYS 89 for ELFMAP; no mapping or rld execution is implemented.

## Validation and next step

Each NetBSD mode passes 42 runtime scenarios and 89 static regressions: **262
top-level scenarios** across both modes. The four query executions per mode
contain 128 checked records in total, included within those scenario counts.
The original-IRIX reference adds 32 records and one successful native asa
control, counted separately. All five final guests halt cleanly.

| Run | Cases | Duration |
| --- | --- | --- |
| `ci-gamtlke0` | 42 runtime | 163.441 s |
| `ordinary-l_xj6jev` | 42 runtime | 164.853 s |
| `segments-compat-ci-e4q20e0q` | 89 static | 162.615 s |
| `segments-compat-ordinary-_h9xgtzv` | 89 static | 164.894 s |
| Reference `ci-iei_ocx2` | 32 query records + native asa | 286.513 s |

Every NetBSD run cold-boots a fresh disk/NVRAM clone with the same committed
kernel, verifies imported hashes, compiles its native runner with warnings as
errors, and runs kernel/file/swap and native execution controls. Post-run file
hashes and clean shutdown are required. CI and ordinary execution are measured
separately. Reproduction is in the
[query lab](../../lab/irix-o32/README.md#runtime-capability-and-identity-queries).

Exploratory runs exposed reference-harness issues: sending a PROM selection too
early, using an account without a login shell, a path-serialization mistake,
and a shutdown timeout shorter than the installed services need. The final
harness waits for the PROM menu, uses direct credential setup, serializes paths,
and allows up to five minutes for shutdown. Earlier partial/unclean runs remain
local and are excluded from the qualification counts. The exploratory NetBSD
query run reached ELFMAP but failed its older expected diagnostic; final runs
use the new pinned boundary.

Next implement a bounded `SGI_ELFMAP` contract: validate the descriptor, header
count, file/virtual ranges, protections, overlap, and failure cleanup before
mapping rld. Compare positive and malformed cases with original IRIX and then
trace the unchanged vendor runtime again. The historical mapper is a reference,
not a drop-in implementation. Wider layouts, relocation success, PRDA, process
sharing, caught signals, desktop execution, and hardware remain unqualified.
The separate [n32 kernel route](2026-10-30-irix-o32-runtime.md#n32-kernel-route)
is still a source audit, with echo as the first vendor target after native
64-bit-kernel qualification.
