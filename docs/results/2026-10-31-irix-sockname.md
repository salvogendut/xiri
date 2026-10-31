# IRIX getsockname — 2026-10-31

This checkpoint adds IRIX getsockname (trap 1094) to the shared o32/n32
personality and repeats the unchanged Toolchest workload against native
NetBSD Xvfb. Toolchest now passes the local-address query, then calls unsupported getpeername
(trap 1093), receives IRIX ENOSYS (89), closes its socket and exits 1 with
the display-open error. No X protocol handshake or window is qualified.

## Implementation and interface evidence

NetBSD branch `xiri/irix-sockname`, revision
[`058b87a92a4`](https://github.com/salvogendut/NetBSD-nixbench/commit/058b87a92a43e7989bccfd4efdd2fe3a0ad93aab), contains the
wrapper. The [lab](../../lab/irix-sockname/README.md) records reproduction
commands and exact LP64/o32 input pins. No emulator changes are required.
Previous kernel artifacts remain separate.

The kernel obtains the native socket address into a bounded kernel buffer,
checks its family and size, and constructs a zero-initialized 16-byte foreign
IPv4 address. The foreign family is a big-endian 16-bit value; the native
length/family byte pair is never copied to user memory. Port and address
remain in network byte order. Native descriptor ownership and socket state
are preserved. Other address families are outside this implementation.

The supplied IRIX 6.5.22m reference establishes these rules:

| Input or output condition | Observed result |
| --- | --- |
| Capacity 0, 1, 2, 3, 4, 8 or 15 | Copy only that prefix; report full length 16 |
| Capacity 16, 17, 32 or INT_MAX | Copy exactly 16 bytes; report 16 |
| Capacity -1 | EFAULT (14), with output untouched |
| Bad/closed fd; regular-file fd | EBADF (9); ENOTSOCK (95), before invalid length-pointer checks |
| Invalid length pointer | EFAULT; address buffer unchanged |
| Invalid/read-only address pointer with positive capacity | EFAULT; length unchanged |
| Read-only length output | Address copied first, then EFAULT writing the length |
| Null address with zero capacity | Success; length becomes 16 |
| Unaligned outputs | Success |
| Same address and length pointer | Address copied first, then the length overwrites its four bytes |

The wrapper follows these observed rules. It rejects negative capacities
before converting to a native copy size and reports the full address size
independently of the number of bytes copied.

The original probes measure the actual caller-visible bytes, including
untouched guard regions and partial output on errors. Connected cases use a
separate peer's accepted client address as an independent oracle. They
verify the ephemeral port before normalizing it in the result record, so
repeatable comparisons cannot hide an incorrect port. The reference peer
is original assembly; the NetBSD peer is native C.

There are 140 new direct/indirect o32/n32 cases. They cover short, zero,
exact, oversized and negative capacities; descriptor errors; invalid and
read-only outputs; unaligned and overlapping buffers; stack and delay-slot
behavior; and both unbound and connected sockets. Selected cases repeat as
an ordinary user. The existing 184 TCP probes are retained unchanged.

All 136 new cases that return a record match original IRIX byte for byte,
including output padding and guards. Four new delay-slot cases preserve the
established difference: original IRIX terminates them with SIGSYS (shell
status 140), while NetBSD executes them successfully. Across the combined
308 paired cases, 284 records match; the other 24 include those four and
the TCP checkpoint's 20 documented differences. No additional getsockname
behavior difference is introduced for the tested inputs.

Only the defined endpoint fields (family, port and address) are compared
with the peer's accept result. Padding from that different interface is not
an endpoint property. The getsockname output padding is retained in each
record and independently required to be zero.

## Qualification

| Run | Scenarios | Seconds | Result |
| --- | ---: | ---: | --- |
| LP64 TCP/getsockname, desktop and controls, CI | 402 | 599.751 | Pass |
| LP64 TCP/getsockname, desktop and controls, ordinary | 402 | 602.470 | Pass |
| O32 TCP/getsockname and controls, CI | 199 | 368.521 | Pass |
| Original IRIX paired socket probes | 308 | 359.632 | Pass |
| Existing LP64 loader/dispatch/heap regressions, CI | 243 | 251.005 | Pass |
| Existing o32 runtime/dispatch regressions, CI | 148 | 270.638 | Pass |
| Existing o32 static/native regressions, CI | 89 | 211.491 | Pass |

All 1,791 scenarios across 7 fresh runs passed with clean shutdowns.
Both native peers completed their expected requests. CI and ordinary fixture records match.
The desktop cases qualify expected startup boundaries; they do not qualify a window.

Only final pinned guest workloads are counted. The reference archive was re-decoded with the
corrected host parser: all 308 fixture records and both successful peer exit-status files were
already present, but IRIX sh printed the unsupported `$()` substitution literally. The original
run result is preserved alongside a separate validation report with both hashes. No guest
observation was changed. Exploratory runs established IRIX length/error behavior,
exposed IRIX archive/child-status limits and separated peer endpoint fields from padding.
The earlier LP64 loader/heap/dispatch and o32 runtime/static expectations remain unchanged.

The [machine-readable evidence](2026-10-31-irix-sockname.json) records
source/input hashes, independent peer completion, comparison results,
startup observations and paths to private raw evidence. Native X clients
must work before and after Toolchest, and all guests must shut down cleanly.
Vendor libraries and applications remain unchanged local inputs.

## Remaining desktop work

Next, qualify getpeername with the same paired output-buffer checks and
an independently known peer endpoint, including the unconnected-socket
error. Then rerun unchanged Toolchest to observe its next requirement.
Later X protocol and event-loop calls should follow observed evidence.

4Dwm still stops at libimdUtil's 4 KiB data-load boundary on the 8 KiB LP64
kernel, and its broader library closure has overlapping linked address
ranges. That mapping/relocation work remains separate. Resource files,
authentication, event handling and full session integration remain pending.
The Xvfb display disables authentication only inside the disposable guest.
No physical SGI hardware, remote networking or general desktop compatibility
is qualified. Existing reference XFS alerts remain open.
