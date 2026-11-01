# IRIX signals and child completion on NetBSD

**1,216 native signal records and 76 native/vendor controls pass** on the
NetBSD `xiri` signal implementation. The [machine-readable result](2026-11-01-irix-signal.json)
pins final source `4680cd61b625a5eaa393a0deaea73f4b9f7ed7bc`, both clean
kernel builds and their exact artifacts. LP64 CI and ordinary execution each
pass 480 records; o32 CI passes 240. Sixteen additional LP64 records cover
inherited handlers and invalid return contexts. All fixtures exit normally,
all case groups are absent and every guest halts cleanly.

The corrected fixture also passes [480 original-IRIX executions](2026-11-01-irix-signal-reference-v2.json)
before the native comparison. The original v1 source and archive remain
unchanged. Its capture trampoline used kernel-reserved k0 across interrupts;
NetBSD may clobber that register. V2 saves AT on the stack and uses AT for
capture, reconstructing original AT/SP and excluding k0/k1. The qualifier
checks actual MIPS III SD/LD opcodes, so the earlier o32 assembler-macro
problem cannot silently return.

## Implementation

New `irix_signal.c` implements traditional-signal sigaction, kill, delivery
and sigreturn using native disposition, pending-signal, mask and machine
context facilities. It explicitly serializes legacy and SA_SIGINFO o32/n32
frames. It preserves the measured argument registers, user trampoline,
handler masks, GPR/PC state and FPU state. The process metadata is copied on
fork and reset on exec; disposition changes use native `sigaction1`.

Waitsys now accepts the measured `P_ALL`/id=0 exit callback and WTRAPPED
option, in addition to the previous positive-child mode. Original-reference
handlers and native handlers reap the already-exited child successfully.
Native wait facilities continue to own child selection and reaping.

Two implementation details were exposed by the comparisons:

- FPU return initially copied the replacement state but left native lazy-FPU
  ownership invalid. The next COP1 trap initialized zeros. After native
  `cpu_setmcontext`, the adapter now marks the replacement PCB valid through
  the native PCU interface; all qualified FPU restoration cases pass.
- Native o32 bulk copyout stopped after a 16-byte unrolled block on a page
  fault, while IRIX returned a 28-byte action prefix. The final adapter
  serializes this 32-byte output bytewise, preserving the measured 4/28-byte
  prefixes and copyout-before-install ordering on both kernels.

The malformed-context cases reject unknown flags, high or unaligned PC,
high SP, unmapped mask bits, invalid stack flags and a cross-page context.
They verify the active mask is unchanged; the n32 case also confirms user
status-register bits are ignored. The fork case requires an inherited child
handler to run before its expected exit. These are native policy checks;
they do not invent additional original-IRIX behavior.

## Scope and regressions

This is the measured traditional-signal subset, not complete signal support.
Sigaction returns EOPNOTSUPP for signals 32..64 and unsupported action-mask
bits, and EINVAL for invalid signal numbers. Kill admits 0..31 and returns
EINVAL outside that range. SIGCHLD-specific high action flags and multiple
LWPs are rejected. Reserved action output is zeroed; the native runner's
initial SIGCHLD flags differ from the reference shell's inherited flags.
The qualifier checks these explicit differences before comparing measured
fields. Raw context padding and original kernel ownership values are not
contracts. Frame storage is 1,024 bytes with measured offsets/alignment.

Alternate-stack setup, nesting, syscall restart, realtime delivery, broad
fault siginfo translation, tracing and concurrent multi-child waits remain
unqualified. The tested wait-any case has one already-exited child. Natural
GUI exit, terminal resize and application-specific callbacks require their
own tests. The original installer is deliberately not retried in this cycle:
the user selected the [installed-image import path](2026-11-01-irix-installed-desktop.md).

Existing regressions pass on source `1e29ed231349`, immediately before the
isolated bytewise sigaction output correction:

| Regression | Evidence |
| --- | --- |
| Process | [944 cases, 1,248 records, 12 vendor/native controls and eight process controls](2026-11-01-irix-signal-process-regression.json) |
| sproc | [136 executions, 240 records and 16 controls](2026-11-01-irix-signal-sproc-regression.json); all groups absent, including 16 expected watchdog groups |
| Time | [192 records and 16 controls](2026-11-01-irix-signal-time-regression.json) |

Eight additional host-side record corruptions are rejected: registration
return, handler count, restored mask, restored FPU value, child status,
partial-copyout guard, unsupported-signal result and siginfo errno. Each
unchanged record is accepted first.

Those reports retain the earlier exact build pin; they are not represented
as final-build reruns. The complete final signal matrices exercise the only
subsequent code change. Earlier failed FPU/capture diagnostics, the o32
16-byte-prefix run and the first extra fixture with SIGCHLD still blocked
are retained privately, excluded from acceptance.

Reproduction commands and record layouts are in the
[signal lab](../../lab/irix-signal/README.md). Sequential two-job builds and
at most four owned emulators preserve the resource limit. IRIS source and
the pinned emulators are unchanged; no new core-kernel hook is added by this
adapter. Deployment remains built in, pending the planned compat_linux-style
module.
