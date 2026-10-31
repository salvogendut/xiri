# IRIX getpeername — 2026-10-31

Unmodified Toolchest now completes both socket-address queries after connecting
to native Xvfb. Startup then encounters unsupported gethostname, fcntl and
sendmsg; shutdown is also unsupported on its error path. It exits 1 with
`Error: Can't open display: 127.0.0.1:98`. The same boundary appears as root
and UID 1234. No completed X handshake or Toolchest window is qualified.

## Implementation and interface evidence

NetBSD branch `xiri/irix-peername`, revision `3757758901bdc140bc89ba103eaba6d8faef55a8`, adds trap 1093
and factors the IPv4 output conversion into a shared helper with getsockname.
The native kernel supplies descriptor ownership and connection state; the
wrapper supplies explicit 32-bit arguments and the 16-byte foreign address.
See the [lab](../../lab/irix-peername/README.md) for build commands and exact
LP64/o32 kernel and input pins. No emulator change is required.

Original IRIX 6.5.22m distinguishes socket state from output validation:

| Tested condition | Observed result |
| --- | --- |
| Never-connected socket, readable length pointer | ENOTCONN (134); output untouched |
| Unconnected socket with unreadable length pointer | EFAULT (14), before the connection-state error |
| Bad/closed fd; regular-file fd | EBADF (9); ENOTSOCK (95), before length-pointer errors |
| Socket after refused TCP connect | EINVAL (22); output untouched |
| Connected socket, negative capacity | EFAULT (14) |
| Connected socket, capacity 0 through tested short values | Copy only the requested prefix; report full size 16 |
| Connected socket, capacity 16, 17, 32 or INT_MAX | Copy 16 bytes; report 16 |
| Invalid/read-only address output | EFAULT; length unchanged |
| Read-only length output | Address copied first, then EFAULT |
| Null address with zero capacity | Success; length becomes 16 |
| Unaligned outputs; identical address/length pointers | Success; address copied before the length |

The getpeername path holds one native fd reference while reading the foreign
length. It then locks the socket to inspect connection state and obtain the
peer address. The socket lock is not held across user-memory access. A
connected socket uses the native protocol callback; native disconnected
state returns EINVAL, qualified here through connection refusal. A fresh
unconnected socket returns ENOTCONN. Other disconnect transitions are not
qualified by this checkpoint. No private fd-state table is introduced.

The shared output helper builds the foreign address from explicitly copied
fields and zeroes padding. Getsockname retains its existing ordering;
getpeername applies the separately measured length/state ordering. Negative
lengths never reach native unsigned copy sizes.

The connected tests independently query the server's own accepted socket
address, check it against the bound loopback endpoint, and keep the
connection alive until the foreign query completes. No ephemeral-port
normalization is needed for getpeername. The output record retains all
padding and guards, including any partial output before an error.

The new 156 direct/indirect o32/n32 probes include connected, unconnected
and refused connections, output capacities/pointers, descriptor errors,
alignment and aliasing, unusable stacks and delay slots. Selected cases
also run as an ordinary user. All 324 earlier TCP and getsockname fixtures
are reused unchanged, exercising both paths through the shared conversion.

All 152 new cases that return records match original IRIX byte for byte,
including padding and guards. The four new delay-slot cases retain the
established difference: original IRIX terminates with SIGSYS (shell status
140), while NetBSD executes the syscall. Across all 464 paired cases, 436
records match; the remaining 28 are these four plus the previous checkpoints’
24 documented differences.

## Qualification

| Run | Scenarios | Seconds | Result |
| --- | ---: | ---: | --- |
| LP64 socket/desktop/controls, CI (desktop reviewed) | 582 | 627.351 | Pass |
| LP64 socket/desktop/controls, ordinary | 582 | 548.104 | Pass |
| O32 socket probes and controls, CI | 289 | 425.437 | Pass |
| Original IRIX paired socket probes | 464 | 477.114 | Pass |
| Existing LP64 loader/dispatch/heap regressions | 243 | 293.090 | Pass |
| Existing o32 runtime/dispatch regressions | 148 | 282.551 | Pass |
| Existing o32 static/native regressions | 89 | 215.987 | Pass |

All 2,397 scenarios were qualified across 7 fresh guests with clean shutdowns.
CI first measured the new desktop boundary; its complete result was reviewed against the new
pin and retained alongside a separate qualification record. The ordinary run repeated that pin.
All fixture checks passed during the original CI run; CI and ordinary fixture records match.
The desktop cases qualify startup boundaries, not a window. All three peers completed.
The earlier loader/heap/dispatch and o32 runtime/static expectations remain unchanged.

The [JSON evidence](2026-10-31-irix-peername.json) records source/input hashes,
peer completion, observations and paths to private raw evidence. Native
X connections before and after Toolchest are required. Vendor applications
and libraries are unchanged.

## Remaining desktop work

The trace after successful connect, getsockname and getpeername is:

| Trap | Operation and observed arguments | Result |
| --- | --- | --- |
| 1108 | gethostname, capacity 256 | ENOSYS (89) |
| 1062 | fcntl, fd 3, command 2, argument 1 | ENOSYS (89) |
| 1102 | sendmsg, fd 3, flags 0 | ENOSYS (89) |
| 1062 | fcntl, fd 3, command 3 | ENOSYS (89) |
| 1106 | shutdown, fd 3, direction 2 | ENOSYS (89) |
| 1006 | close, fd 3 | Success |

Earlier fcntl command-3 queries on standard descriptors remain unsupported
as in the preceding checkpoint. The new socket operations expose the next
startup work; this trace alone does not establish which earlier errors the
application tolerates or the contents of its sendmsg buffer. Qualify the
hostname output, descriptor flags, foreign message/iovec layout, transfer
errors and shutdown semantics with paired probes before retrying Toolchest.
The historical syscall table retained by the [compatibility audit](2026-10-30-irix-compat-audit.md)
identifies these traps; full arguments and returns are retained in the JSON.
The expectation filter includes these returns for this checkpoint while
preserving earlier checkpoint signatures.

4Dwm still requires the separate 4 KiB library mapping and relocation work
on the 8 KiB LP64 kernel. Resources, authentication and session integration
remain unqualified. Xvfb authentication is disabled only in the disposable
guest. No physical SGI or remote-network qualification is claimed, and the
reference installation's existing XFS alerts remain open.
