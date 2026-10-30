# IRIX o32 interpreter bring-up — 2026-10-30

Unmodified IRIX 6.5.22m asa now passes `execve` on the experimental NetBSD kernel
and enters the original libc interpreter. Libc calls
`syssgi(SGI_SYSCONF, _SC_CAP)`, receives an unsupported-call error, writes
`Error getting capabilities or system config\n` to stderr, and exits 239.
This moves beyond the [vendor ENOEXEC baseline](2026-10-30-irix-vendor-baseline.md).
It is not successful execution of asa's filter; neither rld nor asa's main entry
has been reached. n32 echo, 4Dwm, and Toolchest still return `ENOEXEC`.

## Sources and inputs

The NetBSD fork branch
[`xiri/irix-o32-runtime`](https://github.com/salvogendut/NetBSD-nixbench/tree/xiri/irix-o32-runtime)
contains commit `64915ea0900cd81e3bc2577504c709fb33051854`, based on the
segment implementation `6a162a938061d16a60842fd9bb31d69e546d66dc`.
Changes are confined to `sys/compat/irix_o32/irix_o32.c` and its scope README.
No native ELF mapper or emulator changes were needed. The sibling fork checkout
remains on its original trunk. Historical ABI definitions and copyargs behavior
were checked against snapshot `5aca2679d78276864d2980a08314887b2058fb2c`.

The clean committed build uses GCC 14.4, configuration
[`XIRI_IRIX_RUNTIME`](../../lab/irix-o32/XIRI_IRIX_RUNTIME), identifier
`XIRI_IRIX_RUNTIME_20261030`, and `.work/netbsd-irix-build/runtime-tftp/`.
Kernel SHA-256 is
`3ca169e95f44368afa024d31c9a253aa9c7a493ea38efdca43f610fc4da4ffd5`.
The emulator remains IRIS `484452d963d2da4e2a7559e88bcc33da0f2a0c01`, binary
SHA-256 `cc6561d0bdfec6ce30d656caf4a6eaee6ffbf622e5348c3b77b73810d5293f56`.
The machine remains an R4400 Indy with 256 MiB and Newport, running this
NetBSD 11.99.9 kernel over the installed NetBSD 11.0 userland.

| Imported file | SHA-256 |
| --- | --- |
| `/usr/bin/asa` | `c87a69be927e9f1a7649a8d01ae79b890395fb279e44daa6945392bb5a4731de` |
| `/usr/lib/libc.so.1` | `ea766492103a193e9d404942705e4e28987545e37f699ede232b6c0f8c97c954` |
| `/lib/rld` | `30228b54c1e5585b365514eb7c9895b03cc0f61cb898e05e3ddafece87863439` |

Read-only guestfish extraction confirms `/usr/lib/libc.so.1` matches `/lib/libc.so.1`
in the supplied image. Executables and runtime files remain unchanged and outside
Git. The original archive, CHD, and reference disk are not modified. The previous
native IRIX reference ran the same asa input successfully; this step does not
repeat the reference boot or resolve its recorded XFS alerts.

## Loader contract

The existing marked static probe is retained. A separate dynamic probe recognizes
ELF32/MSB/System V MIPS II or III, ET_EXEC, exact flags `0x10000005` or
`0x20000005`, and the exact interpreter `/lib/libc.so.1` or `/usr/lib/libc.so.1`.
Those combined properties select this experimental IRIX subset; they do not
authenticate a file's origin. n32 and other interpreter names remain rejected.

Both executable and interpreter require two ordered loads: RX text at file
offset zero and RW data/BSS. Each segment is at most 16 MiB, fits within the
`0x00400000..0x40000000` window, and has valid file bounds, page alignment,
power-of-two ELF alignment up to 1 MiB, and congruent offset/address. File and
virtual ranges cannot overlap; entry must be aligned inside file-backed text.
The header table follows the ELF header and contains at most 16 entries.
PHDR/INTERP/DYNAMIC metadata must lie in corresponding file-backed bytes;
duplicates and unknown types are rejected. MIPS OPTIONS, REGINFO, and RTPROC
are allowed but not interpreted by the kernel.

The interpreter requires ET_DYN with flags `0x10000003` or `0x20000003`, no
nested interpreter, and a reserved span that does not overlap the executable.
The probe validates and marks the interpreter vnode as text before native
mapping; the native loader retains execution-permission and mount checks.
Self-interpreter vnode recursion is rejected in source. `/emul/irix` uses
NetBSD's normal emulation-root lookup with native-path fallback, not a chroot.

IRIX libc needs its linked base: its startup GOT is already populated with
linked addresses. The probe requests `ELF32_LINK_ADDR`. Asa maps text at
`0x00400000`, data at `0x10004000`, and libc at `0x0f9f0000`, with interpreter
entry `0x0fb02ae0`. The kernel supplies PHDR, PHENT, PHNUM, ENTRY, BASE, PAGESZ,
and NULL auxiliary entries. Static files still receive only NULL. Argument
strings are 16-byte aligned; the o32 stack retains eight-byte alignment.
Current NetBSD copying, `elf_args` cleanup, and private data/BSS VM commands
are reused. No dynamic relocation or `SGI_ELFMAP` implementation is added.

## Measured vendor boundary

The native parent supplies ` XIRI_VENDOR_O32\n` on stdin, one argv entry, and an
empty environment. It separates `execve` failure from runtime exit and captures
stdout and stderr independently, with a five-second child timeout. Asa returns:

```text
errno_bytes=0 errno=0 exit=239 signal=0 killed=0
STDOUT bytes=0
STDERR bytes=44: Error getting capabilities or system config\n
```

Explicit `ktrace -t u` records actual trap numbers, PCs, and the first four
argument registers, including calls sent to the unsupported table slot.
The decoded sequence is:

| Trap | PC | Relevant arguments | Interpretation |
| --- | --- | --- | --- |
| 1040 | `0x0fa362c4` | a0=22, a1=29 | `syssgi(SGI_SYSCONF, _SC_CAP)` |
| 1004 | `0x0fa566e4` | fd=2, buffer=`0x0fb3ac00`, length=44 | Write libc's startup diagnostic |
| 1001 | `0x0fa410e0` | status=`0xdeadbeef` | Exit, observed low byte 239 |

The dispatcher returns IRIX ENOSYS 89 for trap 1040 by inspection of the tested
implementation. These entry records do not independently sample the return
registers. Disassembly identifies libc entry `__exec_rld`, then `__get_rld`,
which invokes the configuration/capability check before opening rld. The later
path uses `__elfmap` and syssgi request 68 (`SGI_ELFMAP`), a future requirement
inferred from code, not an observed call in this run.

No security-query result was fabricated to advance the program. Implementing
the necessary query semantics, checking them on original IRIX, and addressing
the following process-attribute and ELF-map requirements are next.

## Validation

| Run | Cases | Duration | Shutdown |
| --- | --- | --- | --- |
| `ci-uictjt6r` | 37 passed | 155.950 s | Clean |
| `ordinary-x6fc64rk` | 37 passed | 157.250 s | Clean |
| `segments-compat-ci-hn4x4y9k` | 89 passed | 160.515 s | Clean |
| `segments-compat-ordinary-gaynzw3b` | 89 passed | 164.695 s | Clean |

The [JSON record](2026-10-30-irix-o32-runtime.json) retains exact run identities,
timings, kernel/source hashes, all observations, and decoded vendor traces.
Each mode runs 37 runtime cases and all 89 existing static cases on fresh
disk/NVRAM clones, with native kernel/file/swap controls, post-run hashes,
and clean shutdown. CI and ordinary execution are qualified separately.

The runtime matrix includes a synthetic interpreter twice, 28 malformed
executable/interpreter cases, a missing interpreter (ENOENT), four vendor files,
and native controls before and after. The original synthetic interpreter checks
every auxiliary value, argv/envp placement, initialized data and all declared
BSS in both mappings, private writes, and transfer to the executable's entry.
Nonzero bytes after p_filesz expose incorrect BSS copying. Its main executable
prints the exact 15-byte marker and exits 37. This checks loader mechanics;
it does not exercise vendor relocations.

The initial exploratory kernel exposed a diagnostic bug: `ktruser` reads a
user pointer and cannot take a kernel buffer. Its malformed zero-length record
caused kdump to produce excessive output. The guest was interrupted and halted
cleanly. The committed code uses `ktr_kuser`, and final tests require the exact
three-call trace. Exploratory results are retained locally and excluded from
the final qualification counts.

Reproduction commands, fixture details, and input paths are in the
[o32 lab](../../lab/irix-o32/README.md#vendor-interpreter-bring-up). The earlier
vendor rejection experiment remains independently pinned and reproducible.

## n32 kernel route

This source audit establishes a candidate route; it does not qualify an n32
kernel or execute n32 IRIX code. At the pinned fork baseline:

| Source | Finding and consequence |
| --- | --- |
| `sys/arch/mips/include/types.h` | o32 builds use 32-bit register storage; non-o32 builds use 64-bit storage |
| `sys/arch/mips/mips/cpu_exec.c` | Native n32 recognition is excluded under `__mips_o32` |
| `sys/arch/mips/mips/syscall.c` | Non-o32 builds support eight argument registers and remarshal o32 arguments; the current Xiri dispatcher is explicitly four-register/o32 |
| `sys/arch/mips/mips/mips_machdep.c` | Non-o32 setregs configures UX/FR and PK_32 for n32; changing ELF flags alone in the current kernel is insufficient |
| `sys/arch/sgimips/conf/GENERIC64_IP2x`, `std.sgimips64` | Existing Indy configuration selects `mips64eb`, LP64, EXEC_ELF64, and COMPAT_NETBSD32 |
| `sys/arch/mips/conf/Makefile.mips` | LP64 builds use `-mabi=64` and emit an additional `netbsd.elf32` container for firmware compatibility |
| `build.sh` | `-m sgimips -a mips64eb` is an available build target; Xiri's current wrapper is fixed to mipseb |

Next, provision separate mips64eb tools/object/TFTP directories and cold-boot a
GENERIC64_IP2x-derived native kernel on the existing o32 root. Qualify the PROM
image format, native o32 regression behavior, 64-bit register preservation, and
a synthetic n32 call before importing n32 libc. The current personality's
o32-only assertions and native syscall argument layouts must be adapted with
explicit 32-bit pointer conversions and 64-bit register handling. They cannot
simply be enabled on the 64-bit kernel. The supplied n32 echo remains the small
vendor target before 4Dwm and Toolchest.

General IRIX layouts, complete dynamic loading, PRDA, process sharing, caught
signals, desktop execution, and physical hardware qualification remain open.
