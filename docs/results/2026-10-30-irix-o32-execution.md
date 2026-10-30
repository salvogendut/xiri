# Static IRIX o32 execution experiment — 2026-10-30

Follow-up: the [static interface extension](2026-10-30-irix-o32-basics.md)
qualifies a bounded argument, file, and memory subset with 44 cases in each
mode. This record preserves the original 33-case execution milestone.

The NetBSD fork now executes an explicitly marked, synthetic static o32
program using IRIX trap numbers 1004 (`write`) and 1001 (`exit`). It prints
exactly `XIRI_ABI_PROBE\n` (15 bytes), verifies the write result, and exits 37.
All 33 cases pass in CI and ordinary IRIS execution, including native
regressions, error returns, rejection cases, and process cleanup.

This establishes the first foreign execution boundary. The accepted image
layout is deliberately narrow and the marker is a Xiri test convention. No
vendor IRIX executable, libc, dynamic loader, original desktop, or physical
machine was tested.

## Sources and isolated kernel builds

The implementation lives in the user's NetBSD fork on
[`xiri/irix-o32`](https://github.com/salvogendut/NetBSD-nixbench/tree/xiri/irix-o32),
commit `6b6a7967685baff3fa1d1fb7e1e50113470fb2a6`. Its worktree is
`.work/netbsd-irix-src`; the sibling checkout remains on clean `trunk`.
The branch starts at the audited revision
`a852b4a03800c32a127640b784fcc9fc94159d12`.

The unmodified baseline was built and tested before adding compatibility.
It identifies as NetBSD 11.99.9. The guests retain the installed NetBSD 11.0
userland, with matching `/netbsd` supplied from each tested kernel's virtual
CD. This is an explicit kernel baseline transition, not an update of the
qualified release checkpoint.

The [build script](../../scripts/build-netbsd-kernel.sh) now accepts explicit
source, build, TFTP, and configuration paths. It rejects release-output reuse
for fork builds and records source revision/status/patch and output hashes.
The fork uses `.work/netbsd-irix-build/`, its own GCC 14.4 cross-tools, and
separate configuration object directories. Baseline and compatibility kernel
images remain in distinct TFTP directories. The final incremental build from
the clean committed tree produced exactly the initially tested kernel hash.

| Kernel | Configuration identifier | SHA-256 |
| --- | --- | --- |
| Unmodified fork | `XIRI_ABI_BASELINE_20261030` | `649f19b13113efb41f7ed198275c5f06192f461f231e27a6415cd3badcb17912` |
| Compatibility | `XIRI_IRIX_O32_20261030` | `ff334c14611be89a978a2feb527f30a053d50dc39c49ffc7d51fe81d38e3a9bf` |

The hardware profile remains R4400, 256 MiB, Newport, and a disposable clone
of the existing SCSI disk/NVRAM checkpoint. IRIS is unchanged at
`484452d963d2da4e2a7559e88bcc33da0f2a0c01`, binary SHA-256
`cc6561d0bdfec6ce30d656caf4a6eaee6ffbf622e5348c3b77b73810d5293f56`.
No emulator fix was needed for this step. The release kernel, checkpoint,
and previous X11 qualification remain separate; X11 was not requalified on
the trunk kernel here.

## Implemented boundary

`COMPAT_IRIX_O32` is an opt-in built-in execution module, restricted at build
time to big-endian o32 MIPS kernels. It adds five files/changes in the fork:
MIPS configuration registration, the loader/dispatcher, historical errno
definitions with their license, a symbolic errno map, and a scope README.
It does not restore SVR4 or the historical IRIX process/VM implementation.

The loader requires ELF32/MSB MIPS III `ET_EXEC`, System V OSABI, ABI version
zero, and flags `0x20000101`. Its two program headers must describe one fixed
read/execute load segment at `0x00400000` and one exact 24-byte Xiri note.
The file/memory sizes must match and be at most 1 MiB; the loader checks file,
entry, note, and alignment bounds. There is no interpreter, dynamic segment,
writable data segment, or BSS. Failed recognition does not change process ABI
state; o32 setup happens only when execution is committed. Native ELF keeps
its existing priority.

The dispatcher selects only slots 1 and 4 for direct numbers 1001 and 1004.
Everything else selects a dedicated unsupported-call handler, so low, high,
negative-bit-pattern, and indirect numbers never index a table unchecked.
It uses current native syscall argument structures and `sy_invoke`, handles
the MIPS branch-delay return path and kernel restart convention, translates
errno, and returns through normal kernel `userret` processing. The test
contract for unsupported calls is `a3=1`, `v0=89` (IRIX `ENOSYS`) without
posting `SIGSYS`. That is an explicit experiment policy.

The errno map uses symbolic native indices rather than the old positional
array; unmapped host errors become IRIX `EIO`, never success. Default signal
termination works. There is no syscall for installing a foreign handler;
a defensive hook terminates if caught-signal delivery is attempted. Full
signal frames, restart interruption behavior, and IRIX core formats are not
qualified by these tests.

## Results

| Run | Mode / expectation | Cases | Duration | Shutdown |
| --- | --- | --- | --- | --- |
| `baseline-ci-we7mwlty` | CI / reject foreign | 33 passed | 143.190 s | Clean |
| `baseline-ordinary-2p4o2pih` | Ordinary / reject foreign | 33 passed | 145.469 s | Clean |
| `compat-ci-5h6s9ebj` | CI / execute marked fixtures | 33 passed | 145.809 s | Clean |
| `compat-ordinary-1bgudewe` | Ordinary / execute marked fixtures | 33 passed | 148.288 s | Clean |

The initial compatibility runs also passed before the final manifest-completeness
guard was added. The table records the final compatibility harness runs. The
baseline runs predate the manifest's version field, but every fixture byte,
source hash, and expectation matches the final matrix.

| Check | Compatibility-kernel observation |
| --- | --- |
| Marked o32 and native control | Both write the exact 15 bytes and exit 37 |
| Invalid descriptor | IRIX `EBADF=9`, with error flag set |
| Inaccessible buffer | IRIX `EFAULT=14`, with error flag set |
| Zero-byte write | Zero return, error flag clear |
| Ten unsupported/indirect/range cases | IRIX `ENOSYS=89`; fixture completes and exits 37 |
| Write in taken branch delay slot | Correct continuation, exact output, exit 37 |
| Infinite loop | Parent kills with `SIGKILL` after a bounded wait and reaps it |
| Null-address load | Default `SIGSEGV`, no harness kill or guest panic |
| Unbranded and 15 mutated ELF files | `execve` returns `ENOEXEC` (8) |
| Five additional marked/native pairs | All execute successfully |
| Native regression | Kernel/file/swap smoke passes before; kernel identity and retained-file checks pass after |

The ten unsupported numbers are 0, 1, 999, 1000, 1002, 1198, 1255, 1256,
`0x7fffffff`, and `0xffffffff`. For indirect candidates, `a0` deliberately
contains 1001; it must not dispatch `exit`.

Negative ELF variants change note name/version/size/offset, OSABI, n32 flags,
ELF64 class, byte order, ELF type, interpreter/dynamic program-header type,
entry point, load size, program-header count, or truncate the file. These are
synthetic rejection inputs; they do not qualify valid n32/n64 programs.

The native runner calls `execve` directly and records execution errors through
a close-on-exec pipe, so a shell cannot turn `ENOEXEC` into a script attempt.
It compares actual stdout contents, exit status, and signal/timeout outcomes.
It compiles in the guest with `-Wall -Wextra -Werror`. Each run verifies the
fixture hashes and executes the existing native file/swap/kernel smoke probe.
Both execution modes write only their own disk clones, without snapshots or
CI disk rollback.

The [retained JSON](2026-10-30-irix-o32-execution.json) contains all 132 case
observations, source/fixture/kernel hashes, identities, and run timings. Full
serial logs, configuration, virtual CD and disposable disks remain under
`.work/irix-experiment-runs/`. Reproduction commands are in the
[lab README](../../lab/irix-o32/README.md#fork-kernel-and-execution-matrix).
Python/Bash syntax and whitespace checks pass. Direct preflight checks also
verify rejection of incomplete fixture manifests and accidental fork builds
using release output paths.

## Remaining scope

The static execution item in Milestone 2 is satisfied for this constrained,
marked fixture. General static ELF recognition, argv/envp/auxv compatibility,
file operations, memory mappings, dynamic loading, an IRIX runtime, n32/n64,
PRDA/process sharing, caught signals, and physical Indy validation remain open.
The next bounded step is to establish static argument, file, and memory probes
before expanding the loader and runtime. Original desktop work still needs
the reference IRIX installation and its ABI/dependency inventory.
