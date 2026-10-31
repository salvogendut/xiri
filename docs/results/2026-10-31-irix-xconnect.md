# IRIX X-client startup interfaces — 2026-10-31

Unmodified IRIX Toolchest now completes the X connection setup and sends
requests processed by native Xvfb on NetBSD. This advances beyond the earlier
connection/address queries. It still exits with an X I/O error at
unsupported recvmsg (1099); no Toolchest window or usable event loop is qualified.

## Interface implementation

NetBSD branch `xiri/irix-xconnect`, revision `2bb38d1b030a8a9a5766d2fac3eb6d2273d5b0f8`, adds
gethostname (1108), bounded fcntl (1062), sendmsg (1102) and shutdown (1106).
Both o32 and n32 arguments use explicit 32-bit fields. The same source builds
on the LP64 8 KiB and original o32 4 KiB kernels. No emulator changes are needed.

The repeated original-IRIX probes establish these rules:

| Interface | Observed behavior |
| --- | --- |
| gethostname | Copies the bounded prefix and forces its final byte to NUL; short capacities succeed |
| gethostname, capacity zero | Writes a NUL one byte before the supplied pointer; a null pointer fails with EFAULT |
| fcntl F_GETFL on TCP sockets | Includes the legacy 0x200 bit, including after append/nonblocking changes |
| fcntl F_SETFD | Original IRIX retains eight descriptor bits; this subset supports only close-on-exec and rejects other bits |
| sendmsg | Validates the fd before the message pointer; rejects zero, negative and greater-than-16 vector counts with EMSGSIZE |
| shutdown | Validates fd and connection before direction; a never-connected socket returns ENOTCONN even for an invalid direction |
| repeated shutdown | Read/write half shutdowns succeed again; a repeated full shutdown returns ENOTCONN |

The zero-capacity hostname quirk is reproduced through checked user-memory
copyout and explicit unsigned address arithmetic. It does not permit kernel
memory access. Full shutdown marks the native endpoint disconnected while
TCP retains ownership of protocol teardown. Repeated write shutdown avoids
advancing TCP's close state a second time, preserving the readable half.

The hostname wrapper snapshots the current native name under the sysctl
lock, then copies to foreign memory after releasing that lock. Descriptor
queries translate flag values explicitly. Close-on-exec changes retain
NetBSD's independent close-on-fork setting. Supported file-status changes
use native fcntl so inherited/shared descriptions and actual I/O state agree.

The legacy message header occupies 24 bytes, with 8-byte iovec entries in
both supported ABIs. Foreign pointers are sign-extended through the existing
pointer helper. Vector counts and signed 32-bit transfer totals are bounded
before native I/O; user message flags never become native kernel ownership
flags. Native socket references remain held through conversion and transfer.
The tested stream path reuses native send and shutdown operations.

This is a bounded subset: F_GETFD/F_SETFD cover close-on-exec only;
F_SETFL covers append and POSIX nonblocking, accepting the access-mode and
legacy socket bits returned by F_GETFL without changing access mode or
truncating anything. Other descriptor commands, locking, duplication and
legacy NDELAY behavior are not implemented. Descriptor flag values 2 and 255 are
explicit EINVAL differences from the original implementation.

Sendmsg accepts connected IPv4 TCP, the legacy 24-byte header, 1–16 vectors,
a signed 32-bit total, flags zero, no destination and no access rights.
Extended/XPG layouts, ancillary data, datagrams, urgent data, other flags,
signals, remote network behavior and large/blocking partial transfers remain
unqualified. The peer verifies the tested short-transfer error cases.

## Qualification

| Run | Scenarios | Seconds | Result |
| --- | ---: | ---: | --- |
| LP64 socket/startup/desktop controls, CI | 982 | 773.781 | Pass |
| LP64 socket/startup/desktop controls, ordinary | 982 | 775.172 | Pass |
| O32 socket/startup/native/vendor controls, CI | 489 | 422.504 | Pass |
| Repeated original IRIX paired probes (reviewed) | 800 | 442.482 | Pass |

All 3,253 scenarios were qualified across four final qualification guests with clean shutdowns.
The earlier reference measurement also halted cleanly. Its observations and received bytes
were reproduced by the final-fixture reference run. Two preliminary NetBSD runs exposed
harness errors and are excluded from these totals; both failed results remain private.
Fresh CI and ordinary runs reproduce the reviewed desktop pins.
CI and ordinary fixture records and message receipts match. The prior loader/heap/runtime/static
suites remain recorded at earlier checkpoints; this change reruns the socket suite with native
and vendor controls on both kernel architectures.

The earlier 480 fixture programs are reused unchanged. New probes cover
hostname guards and output capacities, descriptor controls, message/vector
faults, actual received bytes, and shutdown directions and repeated calls.
Direct and indirect o32/n32 forms check preserved state, unusable stacks and
delay slots; selected cases repeat under an ordinary user. All four network
helpers must complete. Native observers check shared file-status flags and
write-shutdown acknowledgments before the client closes its read side.

An initial NetBSD run exposed two harness problems: the earlier peers expired
while waiting through the added tests, and the guest's o32 `kdump` crashed
interpreting a native LP64 message-header trace. The failed result is retained
privately and excluded from qualification totals. The corrected harness runs
the earlier socket cases first and decodes foreign call/return traces from
`kdump -x` raw bytes. Peer deadlines and kernel behavior are unchanged by
these harness fixes. A subsequent preliminary run exposed console tab expansion
in the raw-trace parser. That failed result is also retained and excluded;
its six desktop observations were decoded and reviewed as expectations for
fresh CI and ordinary runs using the corrected parser.

Of 800 paired cases, 748 returning records match original IRIX exactly.
The new interfaces contribute 312 exact records. Eight cases expose the
intentional rejection of extra descriptor bits; 16 new delay-slot cases
terminate with SIGSYS on original IRIX while NetBSD returns. Together with
the previous 28 differences, these account for all 52 nonmatching pairs.

The message peer receives eight bytes even when the original delay-slot
sendmsg probe subsequently dies with SIGSYS. Its side effect therefore
matches NetBSD despite the different process result. Received-byte records
are checked independently of syscall return records, including partial-fault
and empty-vector cases.

The [JSON evidence](2026-10-31-irix-xconnect.json) and [lab](../../lab/irix-xconnect/README.md)
record input hashes, kernel revisions, helper observations and reproduction
commands. Original binaries and libraries are unchanged.

## Desktop boundary and remaining work

Both root and ordinary-user Toolchest pass gethostname and the observed
fcntl operations. Their sendmsg calls return 12 and 20 bytes. Xlib then
reports 20 processed requests for root and 17 for the ordinary user, with
zero events remaining. In both traces, recvmsg (1099) on descriptor 3 with
flags zero returns IRIX ENOSYS (89), followed by the fatal X I/O diagnostic
and exit 1. This is the next receive-path contract to measure and implement.

The traces also contain unsupported xstat (1158), getmountid (1203),
systeminfo (1156), sigaction (1162), prctl (1130) and SGI multiplexed queries.
Some are already tolerated during startup or reached during error handling;
their presence does not establish the requirements of a working session.
Keep these visible and investigate the required metadata/runtime behavior
after the receive path advances. No missing call is masked as successful.

Closed-display Toolchest still reports connection refusal. 4Dwm retains its
previous library-map failure, and native X clients passed before and after
the live Toolchest attempts. Authentication remains disabled only in the
disposable Xvfb test guest.

4Dwm's 4 KiB library boundaries and overlapping linked ranges still require
separate mapping/relocation work. Full desktop resources, authentication,
services and session integration remain unqualified. The [desktop plan](../ROADMAP.md#milestone-3-original-desktop-proof)
uses the user-supplied SGI interface guidelines once IRIX X applications work.
Reference XFS alerts remain open; no physical hardware qualification is claimed.
