# Toolchest: empty environment diagnosed; select and xstat exposed

Date: 2026-10-31. This follows the [legacy recvmsg result](2026-10-31-irix-recvmsg.md).
The kernel and emulator are unchanged. The [lab](../../lab/irix-toolchest/README.md)
provides the bounded native session wrapper, fault tracer and reproduction
commands. [Machine-readable evidence](2026-10-31-irix-toolchest-session.json)
records the reviewed runs and input hashes.

## Crash cause

The original native runner deliberately passes an empty environment. When
Toolchest reaches `ProcessConfigFile`, it obtains `getenv("HOME")` and passes
the result directly to `strcpy` without checking for NULL. Native ptrace captured
SIGSEGV/SEGV_MAPERR at address zero, PC `0x0fa4fe64` (`libc strcpy+4`), source
register a1 zero, and return address `0x1000fd88` in `ProcessConfigFile`.
The destination a0 was a stack address, `0x7fff7570`.

Private ELF/GOT inspection ties the helper at `0x10010220` to the `HOME` string
at `0x1001a6d7` and libc `getenv`; the caller then invokes `strcpy` with that
return value. The supplied Toolchest executable and libc hashes match the
existing desktop inventory. Raw vendor bytes and disassembly are not published.

Keeping the same executable, kernel, libraries and diagnostic priority while
adding only `HOME` avoids that fault and reaches a configuration error instead.
The earlier failed open of `/var/config/desktop` was the last trace observation,
not the cause of this null dereference. No kernel patch is needed for this cause.

The native tracer was checked against a static program's known entry PC and a
labelled native null-load instruction, with a guard beyond the register buffer.
Its final SIGKILL is deliberate cleanup after recording the fault. Native guest
GDB crashed internally while loading a diagnostic core; the diagnosis uses the
validated ptrace capture and static caller analysis instead. That debugger issue
remains outside this checkpoint.

## Subsequent boundaries

The reviewed environment contains only `HOME=/tmp/xiri-home`; the earlier
exploratory positive control used `HOME=/root`. The wrapper preserves argv and
the existing native runner's identity and output/deadline controls. It does not
invent a complete IRIX login environment.

Toolchest reports that it cannot open `/usr/lib/X11/system.chestrc`. Installing
the supplied, hash-verified menu file does not remove that error. Adding the
supplied Toolchest app-defaults and locale indexes also leaves the same boundary.
The metadata check immediately preceding the message is `xstat` (1158), version
2, with the constant path address `0x10019348` identifying that configuration
file. The unimplemented syscall returns IRIX ENOSYS (89). Its absence prevents
this check from reaching a successful file lookup; copying resources cannot
supply the missing interface. Other resource dependencies remain unqualified.

A separate timing-dependent failure can occur earlier: Toolchest invokes
`select` (1100) when an X reply is not ready and exits with XIO error 89 because
that syscall is unimplemented. Traces include nfds 4, a read-set pointer and
NULL write/exception sets. An X connection that happens to have queued replies
can advance farther. Lowering the client's priority helped isolate later startup
but did not eliminate this failure. Consequently the earlier successful X
receives do not establish reliable X event handling.

## Reviewed runs

Both modes completed with identical runner observations and fault registers.
The final runs use the same stopped recvmsg seed and unchanged kernel/emulator
inputs; the JSON evidence pins each result, source set, ISO, configuration and
private trace capture.

| Observation | CI | Ordinary |
| --- | ---: | ---: |
| Runner controls passed (native/asa/echo and exact environment) | 13 | 13 |
| Empty-environment Toolchest SIGSEGV | 2 | 2 |
| Earlier select/XIO failure | 1 | 1 |
| HOME-configured Toolchest reaches xstat/configuration error | 8 | 8 |
| Native ptrace controls passed | 2 | 2 |
| Toolchest fault captured at strcpy+4 with a1 zero | 1 | 1 |

This totals 48 runner cases and six ptrace launches. All 16 HOME-configured
Toolchest launches avoided SIGSEGV; none constitutes a working application.
Native X access passed before and after in both modes. Both guests halted
cleanly, and the final host check found no `iris` or `iris-ci` processes.
The NetBSD and IRIS source worktrees remained clean.

## Scope and next work

The focused CI and ordinary runs check exact environment replacement, native
o32 execution, vendor o32 asa and n32 echo under root/non-root IDs, native tracer
controls and native TCP X access before/after foreign clients. Each resource
stage retains its observations, including early select failures.

One preliminary harness run was interrupted because it included excessive
native syscall records in the serial dump; it halted cleanly and is excluded
from the final run totals. The final harness uses the existing foreign-record
and pathname trace selection. The historical 4,285-scenario recvmsg qualification remains unchanged; this checkpoint does not
claim a new full ABI regression or a new original-IRIX comparison.

Next measure and implement the required `select` contract with paired original
IRIX fd-set/timeval/error probes, then the version-2 `xstat` layout and errors.
Repeat these staged launches before claiming window creation or an event loop.
4Dwm's library mapping/relocation work remains separate. The ultimate acceptance
criteria remain the [full original desktop plan](../ROADMAP.md#milestone-3-original-desktop-proof).

Only public helpers, metadata and interpretations enter Git. Vendor resources,
raw traces, diagnostic memory/core data and disks stay in `.work`. Resource
transfer used a read-only ISO. All diagnostic guests were halted cleanly, including the interrupted preliminary
run. No emulator was left running.
