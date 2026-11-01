# Original IRIX signal and child-completion reference

The [installer helper diagnosis](2026-11-01-irix-installer-helpers.md) now has
a measured signal reference: **480 executions pass** on the supplied IRIX
6.5.22m installation. The [independent qualification](2026-11-01-irix-signal-reference.json)
covers o32/n32, direct/indirect dispatch and root/UID1234. It includes 120
handler deliveries, 24 FPU restoration checks, 32 invalid sigreturn requests
and 32 child-exit callbacks, including 16 successful reaps inside the handler.

This cycle changes probes and documentation. NetBSD still lacks foreign
sigaction/delivery/sigreturn and the measured wait-any mode. Original `inst`
has not been rerun or advanced beyond its unreaped helper; xmahjongg remains
uninstalled. The existing time/gettimeofday kernel remains qualified.

## Registration

Raw sigaction 1162 takes signal, new action, old action and trampoline pointers.
Both ABIs use a 32-byte action: flags at byte 0, 32-bit handler at 4, four
32-bit mask words at 8 and eight reserved bytes. Successful calls return
V0=0/A3=0 and preserve the V1 sentinel.

| Request | Observed result |
| --- | --- |
| Signal 1, 16, 18, 31, 32, 33 or 64 | Registration succeeds. |
| Signal 0, 65, 128 or -1 | EINVAL (22). |
| Change SIGKILL (9) or SIGSTOP (23) | EINVAL; querying them succeeds. |
| Bad input plus invalid signal | Input EFAULT (14) takes precedence. |
| Null input or output pointer | Query-only or omitted old-action output succeeds. |
| Input/output shifted by one byte | Accepted; surrounding guards survive. |
| Input with only 4 or 28 bytes readable | EFAULT; the full 32 bytes are required. |
| Read-only input / read-only output | Input succeeds; output gives EFAULT. |
| Output with only 4 or 28 bytes writable | EFAULT after that prefix is written; the new disposition is not installed. |
| Default, ignore, address 2, high or misaligned handler; null/high trampoline | Accepted at registration. Delivery to invalid targets was not attempted. |
| All mask bits set | Query returns `ffbffeff ffffffff 00000000 00000000`: KILL/STOP removed and bits above 64 discarded. |

For SIGUSR1, low flag bits `0x1f` round-trip; tested `0x20`, `0x10000`,
`0x20000` and `0x80000000` are ignored. This does not establish the behavior
of child-specific flags when applied to SIGCHLD. The launch shell has already
set SIGCHLD's `0x20000` flag; it is inherited state, not a universal default.
Reserved action bytes are retained privately but excluded from the contract.

## Trampoline, frame and return

At raw trampoline entry, A0 is the signal number, tagged with bit 31 for
SA_SIGINFO. A1 is zero for the legacy form or points to 128-byte siginfo;
A2 points to the context and equals SP; A3 is the registered handler.
o32 SP is aligned to eight bytes, n32 to sixteen. The independent assembly
fixture captures 64-bit GPRs before calling C; k0 is scratch and excluded.

| Field | Legacy sigcontext, both ABIs | o32 SA_SIGINFO ucontext | n32 SA_SIGINFO ucontext |
| --- | --- | --- | --- |
| Saved mask | Byte 584, four 32-bit words | Byte 8, four 32-bit words | Byte 8, four 32-bit words |
| GPR array | Byte 16, 32 × 64-bit | Byte 40, 36 × 32-bit | Byte 40, 37 × 64-bit |
| Saved PC | Byte 8, 64-bit | GPR slot 35 | GPR slot 35 |
| Floating-point array | Byte 272, 32 × 64-bit | Byte 184, 32 × 32-bit | Byte 336, 32 × 64-bit |
| FPU control/status | Byte 532 | Byte 312 | Byte 592 |
| Siginfo relative to context | Absent | Byte 512 | Byte 800 |

Legacy regmask is `0xffffffff`. Its field at byte 528 is zero without FPU
use and nonzero with it; the nonzero value is not a stable boolean encoding.
Ucontext flags are 7 without FPU use and 15 with it. The o32 FPU layouts
place a double's low half in the even register and high half in the odd
register, even in the legacy 64-bit slots; n32 uses whole 64-bit values.
Four seeded doubles and FCSR=2 survive a handler that overwrites them and
sets FCSR=3. This conversion cannot be replaced with a raw native PCB copy.

Saved PC follows the triggering syscall; the qualifier checks that instruction
in each frozen ELF. Baseline SIGTERM masking, the action mask and automatic
masking of the delivered signal are checked. NODEFER suppresses the latter.
RESETHAND resets the disposition while preserving its queried flags and still
blocks the delivered signal in this case. Every handler adds SIGUSR2 to its
mask; successful sigreturn restores the original SIGTERM-only mask.

Raw sigreturn 1088 receives `(sigcontext, 0, signo)` for legacy delivery or
`(0, ucontext, tagged_signo)` for SA_SIGINFO. Both direct and indirect returns
succeed. High legacy pointer, high ucontext pointer, both null, and high
legacy pointer plus valid ucontext each return EFAULT; a subsequent valid
return succeeds. These errors establish only the tested pointer behavior.

The measured interrupted-SP minus entry-SP gaps are 920/928 bytes for
o32/n32 legacy delivery and 1000/992 for o32/n32 SA_SIGINFO. These are observed
stack allocations, not inferred structure sizes or permission to copy padding.

## SIGCHLD and wait-any

Each child exits 37 while SIGCHLD is blocked. A positive-child WNOWAIT wait
establishes the exited child before unblocking. The handler receives signal
18 and, with SA_SIGINFO, CLD_EXITED code 1, child PID and status 37. The
child's user-time word is zero for these tiny fixtures; it is not a UID field.

The reaping handler calls raw waitsys 1170 with selector **7 (P_ALL)**, ID 0,
options **0x43 (WEXITED | WTRAPPED | WNOHANG)** and null rusage. It returns
V0=0, V1=`37 << 8`, A3=0, and the expected child siginfo. A later positive-child
wait gives ECHILD. Controls that leave the child unreaped successfully wait
after the handler returns. Thus the call previously predicted from the
installer's library has an original-IRIX runtime reference. It has still not
been observed running inside `inst` on NetBSD.

## Evidence and scope

The [lab](../../lab/irix-signal/README.md) contains reproduction commands and
the record layout. The accepted run is
`.work/irix-reference/signal-records-runs/ci-owmvsiu2`, seeded from the clean
time reference `ci-cmkx7nzx`. All 480 executions exit zero, emit exactly 2048
bytes and have empty stderr. Uploaded checksums cover all 240 frozen ELFs.
The qualifier independently reads the archive, verifies source/ELF hashes,
constructs expected registration errors, masks and copyout boundaries, and
checks actual trampoline instructions and context contents. Public JSON
retains normalized observations and provenance; complete frames and vendor
binary disassembly stay under `.work`.

Eight deliberate evidence corruptions are rejected: registration return,
old-output guard, active mask, saved PC, restored FPU value, siginfo signal,
handler reap return and trampoline opcode. Python syntax and local
documentation links also pass their host checks.

The initial smoke run `ci-1yvq7gag` exposed a fixture bug: o32 GAS expanded
`sd` into a pair of 32-bit register stores. Sixteen o32 deliveries failed
with SIGBUS. Encoding the actual MIPS III SD instruction fixed capture;
the final qualifier checks all 32 instruction words. That diagnostic is
retained separately and is not counted as an IRIX compatibility failure.
Both reference guests halted cleanly. At most two emulators overlapped, and
the final host process check found none running. Existing image startup/XFS
warnings remain outside filesystem qualification.

Source evidence combines these independent probes with licensed historical
NetBSD commit `5aca2679d78276864d2980a08314887b2058fb2c`, particularly
`sys/compat/irix/irix_signal.{h,c}`, `sys/compat/svr4/svr4_{signal,wait}.h`
and `sys/arch/mips/include/svr4_machdep.h`. Its old implementation is design
evidence, not current NetBSD code. Private inspection of the supplied n32
libc's `_sigtramp` at `0x0fafd878` corroborates the tag and three-argument
return convention. Libc SHA-256 is
`38c7424498abda279fb6a9e0c68bb76e41442bcc16e8d86a299506595feb5e1e`;
the fixture links no IRIX library and copies no vendor trampoline.

## Next implementation

Implement explicit foreign serializers and native signal integration on
NetBSD `xiri`, including disposition/trampoline inheritance and exec cleanup.
Use native process, signal and wait machinery with measured foreign layouts;
preserve native authorization and machine-state validation. Do not restore
processor status directly from a user-supplied context. Initialize reserved
output bytes rather than reproducing unrelated reference stack contents.

Extend original probes for no-event/multiple-child wait-any, context restoration
validation, disposition lifecycle, alternate stacks, nested signals and
restart behavior as those paths are admitted. The present matrix does not
qualify those, real-time signal delivery, tracing or general sproc sharing of
signal dispositions. Compare the implemented subset on LP64 and o32 kernels,
run existing process/sproc/time controls, then retry unchanged `inst` in CI
and ordinary execution. Native `stat -qd` remains a separate helper mismatch.
The desired delivery form remains a module modeled on `compat_linux`.
