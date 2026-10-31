# IRIX fxstat and Toolchest resource loading

Descriptor metadata lets Toolchest read its app-defaults and complete menu
without the observed allocator SIGSEGV. It now reaches unsupported SIOCNREAD
during X I/O. A usable window and event loop remain unqualified.

## Measured descriptor contract

The user's IRIX 6.5.22m installation ran 260 original static fixtures as root
and uid/gid 1234: 520 complete 576-byte records. The identical executable bytes
cover o32/n32 through direct and indirect syscall dispatch. The reference guest
halted cleanly. [The lab](../../lab/irix-fxstat/README.md) contains reproduction
commands and the [ABI contract](../../lab/irix-fxstat/abi.json).

Descriptor lookup precedes version and output validation. Invalid and closed
descriptors return EBADF (9), even with an invalid version or buffer. After a
valid descriptor, versions 0, 1, 4 and -1 return EINVAL (22). Version 2 writes
136 bytes on o32 and 152 on n32; version 3 writes 152 on either ABI, matching
the measured xstat layouts.

Read-only, write-only and read-write file descriptors all support metadata
lookup. A mode-0000 file inherited through stdin remains stat-able after the
process drops credentials. A closed descriptor is rejected; closing and
reopening its number returns metadata for the new file. Regular/empty files,
a directory, a FIFO and `/dev/null` are covered. The sparse 2 GiB + 1024 byte
file saturates the o32 version-2 size at `INT32_MAX`; wide layouts retain its
full size.

Unaligned output is accepted. Crossing into an inaccessible page writes the
accessible prefix and returns EFAULT. Inaccessible/read-only output returns
EFAULT without changing the writable guards. Reserved fields and padding are
zero. The v1 sentinel and tested n32 saved register survive the call.

The decoder reconstructs all 520 original records. Four deliberate corruption
controls reject changed guards, padding, return flags and a partial-copy byte.

## Implementation

NetBSD revision `ef34f8afe16d5cf80a743b208dccc3a4f355efe2`, branch
`xiri/irix-fxstat`, uses native `do_sys_fstat` for descriptor ownership and
metadata, then the same fixed-width serializer as xstat. Native descriptor
references and file operations remain authoritative. The xstat pathname logic
is unchanged. Both kernels were built sequentially with two compiler jobs;
the emulator remains at `9df1df14334838a989253efefe26f0547e6da592`.

An independent native `fstat` observer records each descriptor class's
metadata under both identities. The comparator packs those named values into
the measured layout and checks every byte, including guards and fault prefixes.
Filesystem-dependent device/inode identity, times and allocation are checked
against the actual native descriptor. The filesystem string is `unknown` and
project ID zero; this does not implement XFS or project accounting.

Sockets, anonymous pipes, concurrent descriptor changes, untested overflow
ranges, legacy fstat/lstat/lxstat and general application compatibility remain
outside this qualification. No leaked proprietary source was used. Vendor
binaries, disk images, raw vendor traces and framebuffers remain private.

## Validation record

The [machine-readable report](2026-10-31-irix-fxstat.json) qualifies the bounded
fxstat subset on the clean source revision above. Its offline qualifier checks
all reference/NetBSD record bytes, primary identities, current helper hashes,
native/vendor controls, exact resource read sequences, the paired SIOCNREAD
return, frame hashes, regression coverage and clean shutdowns.

| Kernel and emulator mode | fxstat records | Native/vendor controls | Staged Toolchest attempts |
| --- | ---: | ---: | ---: |
| LP64, CI | 520 | 12 | 12 |
| LP64, ordinary | 520 | 12 | 12 |
| o32, CI | 260 | 8 | 0 |

All 1,300 records match. All 32 native/vendor controls pass. The 24 Toolchest
attempts reproduce 12 missing-menu errors with libraries alone and 12 later
XIO exits with supplied resources, with no allocator SIGSEGV. Native X checks
pass before and after both LP64 workloads. The resource-stage frames match
the inspected Xvfb background capture; a usable window is not qualified.

The shared serializer also passes 1,620 xstat records across LP64 CI/ordinary
and o32, with all 32 bracketing native/vendor controls passing. Fresh transport
regressions pass 1,284 LP64 and 641 o32 cases, including the reviewed desktop
boundaries and native peers. The LP64 select regression passes all 552 records
with its existing explicit descriptor-policy differences.

The final original-IRIX reference, three focused guests and six regression
guests all halt cleanly. The earlier diagnostic attempts remain excluded as
explained below. The final host audit found no remaining IRIS or iris-ci processes after guest
shutdown. Up to four independent guests ran concurrently; kernel builds were
sequential with at most two compiler jobs.

## Fixture correction

The first paired attempt exposed a descriptor-setup divergence before fxstat:
IRIX accepted a read-only open of the mode-0751 directory under uid 1234, while
native NetBSD open returned EACCES. All four non-root directory fixtures then
exited 99 during setup, without calling fxstat. The other 516 LP64 records
matched. The native observer independently reported the same open failure.

The final setup makes the directory mode 0755 on both systems and repeats the
original reference and focused runs. This keeps the descriptor-stat test
independent of that setup divergence. The reference changes primary uid/gid but
does not clear supplementary groups, while the native runner does; retained
group 0 could explain read access to the mode-0751 root-owned directory.
Supplementary groups were not recorded after the reference credential change,
so this does not establish a kernel open-policy difference. Earlier runs remain
private diagnostic evidence and are excluded from final qualification. The
mode-0000 inherited-file case still tests metadata access without file read
permission after the descriptor has already been opened.

The initial harness also replaced asa’s leading carriage-control space when
creating the 16-byte inherited-file fixture. Its final asa control therefore
reported an invalid first input character despite exiting normally. The final
harness restores asa’s original space-prefixed input after collecting metadata
records and before the final controls. This is a test-input correction, not a
change to vendor behavior or the kernel.

## Toolchest advance and next boundary

With only libraries, Toolchest retains its missing-menu error. With the supplied
app-defaults, menu and locale indexes, xstat/open/fxstat succeed. The app-defaults
read now requests and returns exactly 4,281 bytes, replacing the earlier
`0xffffffff` request. The menu is opened and read in 4,096- and 2,364-byte chunks,
then EOF: all 6,460 bytes. No oversized read or allocator SIGSEGV occurs in the
repeated staged observations.

Toolchest then exits 1 with XIO error 89. The last operation on its connected
X socket is ioctl `0x4004730a`, IRIX `SIOCNREAD`, which returns ENOSYS. It queries
a four-byte readable-byte count and corresponds to native FIONREAD. The
[separate investigation](2026-10-31-irix-toolchest-siocnread.md) records the exact
trace, licensed definitions and original libX11 error-path corroboration.
Those strongly support this as the next X I/O blocker; a qualified adapter
rerun is still needed to demonstrate causality and expose subsequent behavior.
Earlier TCGETA failures are tolerated during file input and are a different
request.

The stderr diagnostic reports 263–264 X requests, with 259–260 known processed
in the initial runs. These are application-reported counters, not an
independent protocol decode, and vary between attempts. Qualification preserves
each counter while checking the stable error/warning text and requiring more
than 250 reported processed requests. It also pairs each recorded ioctl with
its return and follows successful open/read/close sequences to verify resource
byte totals rather than inferring them from pathnames alone.

Separate warnings identify missing `SGIGray76`/`SGIDarkGray` color definitions
and OSF keysyms from `XKeysymDB`; these resources need qualification after the
transport query. Some window-tree samples show widget hierarchies, while the
captured frames show the Xvfb background. Sampling does not rule out transient
windows between captures. A usable mapped Toolchest window and event loop are
still unqualified, and the full IRIX desktop remains a later milestone.

The parallel [xclock loader investigation](2026-10-31-irix-xclock-elfmap.md)
confirms a separate blocker: rld asks to map both libXmu segments over live
libXaw text. It needs a measured, bounded relocation implementation. That work
is separate from the descriptor-stat change and subsequent SIOCNREAD query.

## Transport expectation review

The initial LP64 transport comparison matched all 1,272 synthetic records,
native/vendor outputs and peer checks. Both 4Dwm trace signatures were
unchanged. The closed-display Toolchest output was also unchanged, but its
trace advanced: after successful directory fxstat it performs a second fxstat
and `ngetdents(1207)`, with one break call reordered. That directory-read call
remains unsupported; execution continues to the same display error. Paths and
the selected transport returns are unchanged.

The original failed comparison is retained. The checkpoint's `desktop.json`
records the reviewed trace expectations for fresh transport regressions,
without rewriting historical xstat results.
