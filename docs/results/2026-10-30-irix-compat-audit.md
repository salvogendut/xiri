# Historical IRIX compatibility audit — 2026-10-30

Follow-up: the [static o32 execution experiment](2026-10-30-irix-o32-execution.md)
now implements the bounded first step. This audit records the starting state
and original implementation plan.

The historical implementation is useful as an ABI reference, but restoring its
directory is not a viable first patch. Its ELF probes accept ABI mismatches,
its build depends on the subsequently removed SVR4 implementation, and its
process/VM interfaces need adaptation. The smallest useful next experiment is
an explicitly marked, static o32 executable using only `write` and `exit`.

The [synthetic fixture lab](../../lab/irix-o32/README.md) is now built and tested.
On the existing NetBSD 11.0 kernel, its native control prints exactly 15 bytes
and exits 37; both foreign fixtures are rejected with `ENOEXEC`. This passes in
CI and ordinary IRIS execution with clean shutdowns. **IRIX execution remains
unimplemented.** No NetBSD or IRIS source was modified for this audit.

## Source baselines

The user's `../NetBSD-nixbench` fork contains the historical commits locally.
The audit used `git show`/`git archive`, without changing its clean `trunk`
checkout. Historical source was exported only under `.work/irix-audit/`.

| Reference | Exact identity |
| --- | --- |
| IRIX removal, 2011-04-26 | `e958063324d8f5c70f0446049fc7178ab15abfce` |
| Historical implementation, parent of removal | `5aca2679d78276864d2980a08314887b2058fb2c` |
| SVR4 removal, 2018-12-19 | `43c9320743f41e4af2b1bc6fe9324e5bb70466e7` |
| Audited fork trunk, 2026-10-30 | `a852b4a03800c32a127640b784fcc9fc94159d12` |
| Running guest source | NetBSD 11.0 release source sets, pinned in [SHA512SUMS](../../lab/netbsd-11.0/SHA512SUMS) |
| Running kernel | `XIRI_INDY_20261030`, `GENERIC32_IP2x`, `MACHINE_ARCH=mipseb` |
| Tested IRIS fork | `484452d963d2da4e2a7559e88bcc33da0f2a0c01` |

The IRIX removal spans 61 files and 11,561 deleted lines, including integration
outside `sys/compat/irix`. NetBSD's [6.0 release notes](https://www.netbsd.org/releases/formal-6/NetBSD-6.0.html)
record its retirement. This audit pins the last pre-removal snapshot rather
than treating a moving historical release branch as the implementation baseline.

To reproduce the historical extraction from Xiri:

```sh
mkdir -p .work/irix-audit/historical
git -C ../NetBSD-nixbench archive 5aca2679d78276864d2980a08314887b2058fb2c \
    sys/compat/irix sys/arch/mips/mips/irix_syscall.c \
    sys/arch/mips/mips/syscall.c sys/kern/exec_elf32.c \
    sys/sys/exec.h sys/sys/syscallvar.h \
    | tar -x -C .work/irix-audit/historical
```

Current interfaces were checked in both the release tree and pinned fork:
`sys/sys/{proc,exec,syscallvar}.h`, `sys/kern/exec_elf{,32}.c`,
`sys/kern/kern_stub.c`, `sys/arch/mips/mips/{cpu_exec,syscall,mips_machdep}.c`,
and `sys/arch/mips/include/locore.h`. The release and trunk syscall dispatchers
are not identical: trunk adds sign extension of 32-bit returns on non-o32 ABIs.
Neither tree currently contains `compat/irix` or `compat/svr4`.

## Findings and implications

### ELF recognition must be replaced

In the pinned historical
[`irix_exec_elf32.c`](https://github.com/salvogendut/NetBSD-nixbench/blob/5aca2679d78276864d2980a08314887b2058fb2c/sys/compat/irix/irix_exec_elf32.c),
the o32, n32, and nominal n64 probes initialize `error` to zero and return it
when the ABI mask does **not** match. That reports probe success. The
[`module table`](https://github.com/salvogendut/NetBSD-nixbench/blob/5aca2679d78276864d2980a08314887b2058fb2c/sys/compat/irix/irix_mod.c)
places n32 before o32 at the same priority. These are source findings; this
audit did not boot the historical kernel to characterize the resulting failures.

The historical mask is `0x30`, with o32 `0`, n32 `0x20`, and nominal n64 `0x10`.
For dynamic files, the probes check interpreter names under `/lib`, `/lib32`,
or `/lib64` and their `/usr` counterparts. A static file has no interpreter,
and zero ABI bits alone do not uniquely identify IRIX. A corrected mismatch
return is therefore necessary but insufficient for reliable recognition.

The historical source contains an ELF64 probe, but the module table registers
only the two ELF32 entries. The nominal n64 probe even sets the process ABI to
n32. Its presence is not evidence of functioning n64 support.

The running kernel has `EXEC_ELF_NOTELESS` disabled. The proposed experiment
keeps it disabled and uses an explicit Xiri test note; it must preserve native
NetBSD ELF selection. General IRIX branding needs real reference binaries and
a separately justified identification policy.

### The syscall boundary is small enough to test independently

Historical
[`irix_syscall.c`](https://github.com/salvogendut/NetBSD-nixbench/blob/5aca2679d78276864d2980a08314887b2058fb2c/sys/arch/mips/mips/irix_syscall.c)
instantiates the common MIPS dispatcher with `SYSCALL_SHIFT=1000`.
[`syscalls.master`](https://github.com/salvogendut/NetBSD-nixbench/blob/5aca2679d78276864d2980a08314887b2058fb2c/sys/compat/irix/syscalls.master)
maps table slot 1 to `exit` and slot 4 to `write`, so their trap numbers are
1001 and 1004. The generated historical table has 256 entries. For o32, the
first four arguments occupy `a0`–`a3`; additional words start at `sp+16`.
Success returns a value in `v0` with `a3=0`; an error sets `a3` and returns the
foreign errno in `v0`.

The current
[`dispatcher`](https://github.com/salvogendut/NetBSD-nixbench/blob/a852b4a03800c32a127640b784fcc9fc94159d12/sys/arch/mips/mips/syscall.c)
still offers `EMULNAME` and `SYSCALL_SHIFT`, but must not be instantiated
blindly. It stores the shifted number in a signed `int` and checks only
`code >= e_nsysent` before indexing. The experimental dispatcher must validate
the full range before subtraction/indexing, including debug name lookups,
and handle low, high, and indirect numbers explicitly. Do not inherit the
native `syscall`/`__syscall` conventions without checking the foreign ABI.

Use current syscall metadata and argument definitions. `write`/`exit` can use
native kernel operations on this 32-bit host after argument validation, but
error numbers are not universally interchangeable: historical IRIX has
`EBADF=9`, `EFAULT=14`, `EINVAL=22`, and **`ENOSYS=89`**. Current
`sys_nosys` also sends `SIGSYS`, so an experiment promising an explicit
unsupported-call return needs its own handler. That return policy is a test
contract, not a claim about all original IRIX unsupported-call behavior.

### Wider ABI support needs a kernel decision

The running `GENERIC32_IP2x` kernel is o32. In current `cpu_exec.c`, the n32
ELF case is compiled out for `__mips_o32`; the dispatcher asserts that the
process ABI is o32. The historical `irix_n32_setregs` simply adds status bits
after native setup. Setting those bits and `md_abi` does not establish n32
support in this kernel.

The R4400's instruction capability is not the same as a qualified wider-ABI
kernel. n32 needs its own kernel/dispatch/structure-layout qualification and
remains required if the eventual desktop inventory demands it. n64 remains
outside this initial experiment.

### Integration gaps beyond the two calls

| Area | Historical implementation and current gap | First experiment |
| --- | --- | --- |
| Build dependencies | `files.irix` adds MIPS SVR4 glue and 14 SVR4 C files; the module requires `compat_svr4`, removed in 2018 | Add a small independent personality; do not restore the SVR4 tree |
| Process/VM hooks | `emul_irix` initializes removed `e_fault` and `e_tracesig` fields; `e_vm_default_addr` now takes four arguments | Use current designated initializers and explicit lifecycle behavior |
| Syscall tables | Old generated tables predate current metadata and generator conventions | Generate or define only the narrow table using current interfaces |
| Stack and auxv | Old copyargs duplicates argument copying, aligns the string block to 16 bytes, and supplies PHDR/PHENT/PHNUM/ENTRY/BASE/PAGESZ/NULL aux entries | Reuse current stack setup for the fixture; argument/auxv compatibility is untested |
| Ownership | Old `M_TEMP`/`M_EMULDATA` allocation patterns and manual `ep_emul_arg` freeing differ from current allocator and `ep_emul_arg_free` conventions | Follow current ownership and failure cleanup |
| Signals/FPU | IRIX uses libc trampolines and SVR4 signal layouts; `fpu_save_lwp` and zero-argument `fpu_discard()` need adaptation | No caught-signal ABI yet; default termination and timeout cleanup must work |
| Register access | `tf_regs` still exists as an alias for `tf_registers.r_regs` in current `locore.h` | Do not mistake this retained alias for an API removal |
| PRDA/sharing | Historical exec initializes a PRDA at `0x00200000`; `sproc`, shared VM, and usema have substantial lifecycle dependencies | Fixture accesses none of them; do not claim runtime coverage |
| Runtime lookup | Historical `/emul/irix` and ABI-specific libc interpreter paths require a coherent imported runtime | No interpreter or runtime tree in the first experiment |

Sources for these gaps include historical `files.irix`, `irix_exec.c`,
`irix_exec_elf32.c`, `irix_signal.c`, `irix_prctl.{c,h}`, and `irix_usema.c`,
compared with the current files listed above. This is a focused porting audit,
not an exhaustive review of every historical syscall.

## Measured negative baseline

The fixtures are original assembly built with NetBSD Binutils nb1 2.42,
big-endian MIPS III, ELF32 `ET_EXEC`. Their one executable load segment starts
at `0x00400000`. The foreign variants use System V OSABI and flags `0x20000101`;
the native control uses NetBSD OSABI and flags `0x20001101`. The marked fixture
adds the test note documented in the lab. Neither foreign file is a vendor
IRIX executable.

| Run | Duration | Native control | Marked foreign | Unbranded foreign | Shutdown |
| --- | --- | --- | --- | --- | --- |
| `ci-wkvfj17g` | 118.470 s | Exact stdout, exit 37 | `ENOEXEC` (8) | `ENOEXEC` (8) | Clean |
| `ordinary-ugv930m5` | 119.556 s | Exact stdout, exit 37 | `ENOEXEC` (8) | `ENOEXEC` (8) | Clean |

Both runs produced these direct-exec observations:

```text
EXEC ./native-o32 errno_bytes=0 errno=0 output_bytes=15 exit=37 signal=0
EXEC ./irix-o32-marked errno_bytes=4 errno=8 output_bytes=0 exit=126 signal=0
EXEC ./irix-o32-unbranded errno_bytes=4 errno=8 output_bytes=0 exit=126 signal=0
BASELINE_PASS native=works irix=ENOEXEC
```

Exit 126 is the native runner's child status after recording an `execve`
failure; it is not execution of the foreign program. The runner checks the
stdout contents as well as their length and observes `execve` through a
close-on-exec pipe, avoiding shell fallback on `ENOEXEC`.

The [retained JSON](2026-10-30-irix-baseline.json) records fixture/source/tool
identities, kernel, emulator, checkpoint and harness hashes, and both runs.
Full serial/configuration logs and disposable disks remain in
`.work/irix-o32-runs/`. The original checkpoint and release kernel are unchanged.
A second build reproduced the complete fixture manifest and binary hashes.
Python syntax checks, local documentation links, and whitespace checks passed;
the native guest runner compiled without compiler warnings in both runs.

## Next implementation and acceptance gate

1. Create a task branch/worktree in the user's NetBSD fork from the pinned
   trunk revision, with explicit source and separate tool/object/output paths.
   First cold-boot an unmodified kernel from that baseline and rerun the native
   smoke and rejection probes in both modes. Keep the qualified release kernel
   available. A trunk boot/build regression must be resolved or documented as
   a deliberate baseline change before attributing failures to compatibility.
2. Add an opt-in experimental kernel personality for the marked fixture.
   Use current exec registration, emulation metadata, MIPS setup, and syscall
   interfaces. Keep the name/configuration clearly experimental and o32-only.
   Validate ELF32/MSB/MIPS III/`ET_EXEC`, legacy o32 flags, the exact note, load
   bounds, and no dynamic/interpreter segments. Rejected probes must not leave
   changed ABI state behind. Reject contradictory branding rather than
   overriding a native NetBSD executable.
3. Implement direct calls 1004 and 1001 with correct pointer/count handling,
   returns and errno translation. Unsupported calls must fail explicitly;
   validate range before indexing, handle indirect forms as unsupported for
   now, and preserve kernel return/restart and default signal semantics.
   Keep caught signal handlers and broader runtime interfaces unavailable.
4. Extend the fixture and harness with the acceptance matrix below, cold-boot
   the changed kernel, and repeat in CI and ordinary execution. Record separate
   execution-success and negative-baseline results; retain native regression
   coverage and clean shutdown requirements.

| Case | Required outcome on the experimental kernel |
| --- | --- |
| Marked static o32 write/exit | Exact 15-byte stdout, exit 37, no signal or timeout |
| Native control and existing smoke probe | Continue to pass |
| Unbranded foreign file | `ENOEXEC` |
| Wrong/missing/truncated note or contradictory identity | Reject without committing a foreign personality |
| n32/n64, little-endian, PIE, interpreter/dynamic segments | Reject; do not silently select o32 |
| Bad descriptor / inaccessible write buffer | Correct `a3` error flag and IRIX `EBADF` / `EFAULT` |
| Unsupported, below-base, out-of-range and indirect call numbers | Explicit error (test contract: IRIX `ENOSYS=89`), no native fallback or table overrun |
| Repeated execution, forced timeout, ordinary termination | Parent remains usable, no panic, bounded cleanup, clean halt |

Only the current baseline rows have been measured; the experimental-kernel
matrix is future work. A successful marked fixture will establish the first
execution boundary, not general static IRIX recognition, an IRIX libc runtime,
dynamic linking, n32, original desktop behavior, or physical-hardware support.
