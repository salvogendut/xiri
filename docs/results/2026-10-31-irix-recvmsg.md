# IRIX legacy recvmsg — 2026-10-31

Follow-up: the [Toolchest session diagnosis](2026-10-31-irix-toolchest-session.md) identifies the later SIGSEGV as an empty-environment `HOME` null dereference. Supplying `HOME` exposed unsupported `select` and configuration `xstat` calls. The later [select adapter](2026-10-31-irix-select.md) implements the measured readiness/timeout subset; `xstat` remains next. The historical observations below are preserved.

Legacy `recvmsg` now works for the measured short TCP subset. Unmodified
Toolchest receives a 32-byte X reply instead of terminating at ENOSYS, then
advances through later X reads and resource lookups before SIGSEGV. Its last
recorded operation is a failed open of `/var/config/desktop`. This is a new
reproducible boundary, not a qualified window or desktop session.

## Interface contract

NetBSD branch `xiri/irix-recvmsg`, revision `4a033ead228acb1d810151c6956b1399a09e3a69`, extends the
shared o32/n32 personality with the measured legacy recvmsg interface (1099).
The 24-byte foreign header and 8-byte vectors use explicit 32-bit fields.
No foreign flag word is forwarded into native kernel ownership flags.

The measured subset is connected IPv4 TCP, with flags zero or legacy
`MSG_PEEK` (2), and 1–16 vectors. A zero-length vector succeeds without
consuming data; zero, negative or excessive vector counts return EMSGSIZE.
Individual lengths and their sum must fit a signed 32-bit count.

Header copyin, vector-count validation and vector copyin precede descriptor
validation. Descriptor validation precedes vector-length validation. Thus
an invalid descriptor with a null header or vector returns EFAULT, with an
empty vector list returns EMSGSIZE, and with an excessive vector length
returns EBADF. These priorities were measured explicitly in the expanded
reference run.

Normal receives consume queued bytes before copying them to user buffers.
A first-buffer fault returns EFAULT after consuming the tested eight bytes;
a fault in the second vector returns the successfully copied three-byte
prefix while consuming all eight. Peeking leaves all eight queued, including
when a later vector faults. EOF returns zero; an empty socket set nonblocking
through fcntl returns EAGAIN. Payload guards, input vectors and the follow-up
drain distinguish these outcomes.

TCP supplies no sender address or access rights on this path. IRIX clears
the corresponding output length only when its pointer is non-null, without
dereferencing the pointed-to buffer. Null pointers leave their length fields
unchanged. Successful zero-byte and EOF receives also clear eligible lengths;
EAGAIN does not. A partial buffer fault that returns a successful prefix does.
**Length-field copyout faults are ignored:** a read-only header still reports
success and its original lengths remain intact. This last observation corrected
the initial implementation before any NetBSD qualification run.

The wrapper requests native-owned mbufs for consuming receives, then scatters
them into the foreign vectors and frees them. This matches the measured
fault-consumption behavior without allocating the foreign requested length.
Peeking uses the native user-vector receive path. Foreign flags are explicitly
translated; unsupported bits are rejected before receiving.

## Qualification

| Run | Scenarios | Seconds | Result |
| --- | ---: | ---: | --- |
| LP64 receive/socket/desktop controls, CI (reviewed) | 1286 | 950.671 | Pass |
| LP64 receive/socket/desktop controls, ordinary | 1286 | 953.266 | Pass |
| O32 receive/socket/native/vendor controls, CI | 641 | 514.466 | Pass |
| Original IRIX paired probes (reviewed) | 1072 | 587.664 | Pass |

All 4,285 scenarios were qualified across four final guests with clean shutdowns.
CI and ordinary fixture records and both message/source peer receipts match.
The first CI run recorded desktop observations for explicit review; its raw
result is preserved beside the qualified result. The fresh ordinary run
reproduced the reviewed desktop expectations. Native X controls pass before
and after both LP64 runs. The original 32-bit kernel route passes separately.
The host process check after the batch found no running `iris` or `iris-ci`
instances.

All 844 earlier fixture programs are retained unchanged. New receive probes
cover guarded scatter buffers, vector limits and overflow, header/vector/data
faults, read-only and unaligned structures, EOF, empty nonblocking sockets,
peeking, descriptor errors, legacy header output, unusable stacks and delay
slots. Selected cases repeat as an ordinary user. A source peer independently
records what it sends; a follow-up client drain checks consumption even when
the tested call fails. All five peers must complete successfully.

Of 1,072 paired cases, 1,016 records match original IRIX exactly, including
268 new returning receive records. Four new delay-slot probes terminate with
SIGSYS on original IRIX while NetBSD returns normally. Together with the
previous 52 differences (including eight rejected extra descriptor-flag
cases), these account for all 56 nonmatching pairs. The four new unsupported
receive-flag cases enforce the bounded policy and are not paired claims.

The receive source records 292 connections per LP64 run, 146 on the o32
kernel, and 260 on original IRIX. Its transmitted lengths and all client
drains match their expected records. The older message peers also retain
all 192/96/168 expected receipts.

An initial reference attempt exceeded the upload timeout before executing
probes: default linker padding expanded the transfer to about 18 MB.
The guest did not reach the clean-halt marker within cleanup's timeout and
was stopped by the harness. This failed attempt is retained and excluded
from qualification totals. The new probes use validated 8 KiB ELF alignment,
reducing the initial compact fixture set to about 3.5 MB before tar padding.
Recvmsg transfer timeouts are bounded separately. Failure cleanup now
interrupts any foreground console command before requesting shutdown.

The [JSON evidence](2026-10-31-irix-recvmsg.json) records exact inputs, source
revisions, observations and comparisons. The [lab](../../lab/irix-recvmsg/README.md)
provides reproduction commands. The previous loader/heap/runtime/static suites
remain recorded at earlier checkpoints; this change reruns socket coverage
with native/vendor controls on both kernel architectures.

## Desktop boundary and limits

Toolchest’s root attempt returns 32 from recvmsg (1099); the ordinary-user
attempt returns 420 and then 32. These calls use flags zero, after successful
12- and 20-byte sendmsg calls. They then terminate with signal 11 without
the earlier XIO error. The trace includes
missing `/usr/lib/X11/locale/locale.alias` and `locale.dir` lookups and
unsupported xstat (1158), getmountid (1203), systeminfo (1156), sigaction
(1162) and SGI multiplexed queries. These remain explicit errors. Its last
recorded call opens `/var/config/desktop` and returns ENOENT. The existing library-only closure
experiment does not install the complete desktop resources or session setup.
Both locale files are present in the supplied image’s recorded resource
inventory; their absence here is a test-environment omission. The existing
inventory does not establish whether `/var/config/desktop` exists on the
reference image.

The next experiment must capture the faulting PC/registers and isolate the
missing dependencies with controlled original-IRIX comparisons. These traces
do not establish that the last missing file causes the crash. A pass for the
desktop boundary means this observed failure and the surrounding native/vendor
controls reproduced; it does not mean Toolchest is usable.

The transfer contract is bounded to short streams. Large transfers, faults
across multiple mbufs, concurrent readers, signal interruption, remote peers,
datagrams, ancillary data and extended/XPG flags remain unqualified. No
`MSG_WAITALL` or per-call nonblocking flag is accepted; fcntl nonblocking is
tested. The first 216 receive observations were repeated in the expanded
reference run; four of these are delay-slot terminations. Fixture IDs changed
for later groups, so that comparison normalizes IDs while preserving every
other recorded byte.

This checkpoint does not establish a complete desktop session. 4Dwm's
unaligned data-load boundaries and overlapping linked library ranges still
need explicit mapping and relocation support. Resources, authentication,
services and session behavior remain separate work. The [desktop acceptance
plan](../ROADMAP.md#milestone-3-original-desktop-proof) retains the supplied SGI
guidelines. Reference XFS alerts remain open; no physical hardware result is claimed.
