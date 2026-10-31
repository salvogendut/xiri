# IRIX SIOCNREAD checkpoint

Follow-up: the [resource/input checkpoint](2026-10-31-irix-toolchest-input.md) removes the color/keysym warnings and adds bounded menu navigation on this unchanged kernel. The observations below retain the earlier display/redraw checkpoint.

The NetBSD fork implements the measured `ioctl(1054)` selector `0x4004730a`
used by original Toolchest's X transport. Source commit
`355e0ca310039839b426e66d00744edab5cd5608` is on `xiri/irix-siocnread`.
The IRIS fork remains at `9df1df14334838a989253efefe26f0547e6da592`.
The [lab](../../lab/irix-siocnread/README.md) contains original synthetic fixtures,
[ABI details](../../lab/irix-siocnread/abi.json),
[reference records](../../lab/irix-siocnread/reference.json), and kernel pins.
No proprietary source was used.

## Measured contract

The corrected original IRIX 6.5.22m run produces 336 complete records: 42
variants, o32/n32, direct/indirect dispatch, and root/uid 1234. Every byte of
its 160-byte records is independently reconstructed, including return registers,
primary identity, output guards, accessible page tails and drained TCP payload.

| Condition | Original IRIX result |
| --- | --- |
| Empty connected or unconnected TCP stream | Success; four-byte count 0 |
| Seventeen queued bytes | Success; count 17; repeated query unchanged |
| Five bytes read from that payload | Success; count 12 |
| All bytes and FIN consumed | ECONNRESET (131); output untouched |
| EOF plus null output | ECONNRESET before output-pointer validation |
| Invalid or closed descriptor | EBADF (9), including null output |
| Regular file or directory | ENOTTY (25), including regular-file null output |
| FIFO or `/dev/null` | EINVAL (22) |
| Unaligned output | Success; exactly four bytes written |
| Null, high, wrapped or read-only output | EFAULT (14) |
| One to three writable bytes before inaccessible page | Accessible prefix written, then EFAULT |
| Four writable bytes before inaccessible page | Success; adjacent guards unchanged |

Counts come from a controlled peer. MSG_PEEK establishes all 17 bytes before
querying; later ordinary reads verify that the ioctl consumed no data. The peer
records every fixture ID and state. Nonblocking mode does not change the tested
count/EOF behavior. The three arguments fit registers even for indirect o32
calls, so the tested invalid user stack pointers do not affect dispatch. Full
n32 saved-register values survive the calls.

## Adapter and limits

The adapter retains a native file reference, restricts the implemented socket
path to IPv4 TCP, and holds the socket lock across native FIONREAD and the EOF
check. Native ioctl receives a kernel integer, never the foreign user pointer.
After unlocking, the adapter copies a fixed-width four-byte integer to user
memory. Regular files and devices never receive the translated socket command.

Other command encodings retain ENOSYS (89). This deliberately includes
`0x4004667f`, which original IRIX accepts as another byte-count query, and bad-fd
unknown commands, where IRIX returns EBADF. Unknown/wrong-size commands and
TCGETA return 122 on the tested IRIX socket; a regular-file unknown command
returns ENOTTY. These differences are explicit expected policy checks, not
masked bytes. General ioctl, AF_UNIX, datagrams, listening sockets, urgent data,
resets, local shutdown, concurrent changes and large queues remain unqualified.

## Toolchest and xclock

The staged Toolchest runs make the before/after distinction explicit. Library-only
launches still exit 1 because the menu file is absent. All 12 resource-enabled
launches, across both LP64 modes and identities, now survive until their
five-second parent timeout. The connected X descriptor's SIOCNREAD calls succeed;
the earlier XIO exit is gone. An idle trace reaches select, which is interrupted
when the test parent deliberately kills the client. A visible menu appears in
some one-second captures; other samples catch early setup, so these snapshots
alone do not establish a visibility difference between identities.

A separate 60-second run confirms sustained visibility and Expose handling as
both root and uid 1234. After an eight-second startup delay, X reports a viewable
103×158 Toolchest window and seven viewable descendants. The native observer
grabs its private X server, clears the viewable windows while retaining Expose
notifications, then releases the server and allows the client to repaint.
Both identities restore the original root-pixel checksum:

| Identity | Viewable windows | Before clear | Cleared | After repaint |
| --- | ---: | --- | --- | --- |
| root | 8 | `7d0188af` | `f39d93b5` | `7d0188af` |
| uid 1234 | 8 | `7d0188af` | `f39d93b5` | `7d0188af` |

An independent native X client passes the same clear/repaint control before and
afterward. Both final XWD images have the identical SHA-256 listed below and
show the same menu. These are bounded display/redraw checks, not mouse/keyboard
menu, application-launch or full-session qualification. The parent intentionally
terminates each client at 60 seconds.

SGIGray76/SGIDarkGray and osf* keysym warnings remain. The menu therefore does
not yet have a qualified original SGI appearance or keyboard behavior.
`gettimeofday` (1128) still returns ENOSYS before the observed select wait;
that has not been fatal on the tested path, but timer behavior needs its own
contract. The syscall identity is confirmed by the BSD-licensed historical
NetBSD IRIX table at `5aca2679d78276864d2980a08314887b2058fb2c`.

The user-requested PNG is retained privately at
`.work/irix-siocnread/screenshots/toolchest-netbsd-xorg.png`, with adjacent JSON
provenance. Its source XWD SHA-256 is
`a248dc5b5986c4afb5d4101c3bc3ba01f8e88ed46dde47e78e8cef40f68497da`.
No vendor image is added to the public repository.

The fresh xclock recheck uses this same SIOCNREAD kernel, analog/digital modes
and both identities. All four still stop at libXmu SGI_ELFMAP ENOMEM before
opening an X socket. A native xclock is viewable on the same Xvfb. The earlier
[live loader capture](2026-10-31-irix-xclock-elfmap.md) established the libXmu/libXaw
address collision; this ioctl change does not implement relocation.

The first rendered Toolchest prompted another review of the user's
[IRIX Interactive Desktop User Interface Guidelines](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/index.html).
The [desktop acceptance plan](../ROADMAP.md#milestone-3-original-desktop-proof)
now links the relevant chapters and separates menu interaction, window/focus
behavior, component launch, services and session restoration. Those are planned
comparisons derived from the manual, not claims of full desktop compatibility.

## Validation

Both kernels were built sequentially from clean source with two compiler jobs.
Focused runs pass 840 checks: 336 LP64 CI, 336 LP64 ordinary and 168 o32 CI.
Of these, 720 match original IRIX exactly; 120 check the documented unsupported
command policy. Native and vendor controls bracket each focused workload.
The select regression passes all 552 records on the new LP64 kernel. Transport
regressions pass 1,284 LP64 and 641 o32 observations, for 2,477 regression
observations in total. The [machine-readable report](2026-10-31-irix-siocnread.json)
rechecks raw records, hashes, controls and cleanup.

The initial reference diagnostic used a mode-0644 input file, preventing uid
1234 from opening its write modes. It is excluded. Its cleanup command timed
out and the guest was stopped. The corrected mode-0666 reference run checks all
336 cases and shuts down cleanly. No group-dependent permission inference is
made: IRIX supplementary groups are not normalized, but world permissions
remove them from these descriptor-setup tests.

The first longer-window attempt lacked X headers and halted cleanly before
running its observer. The corrected run installs the hash-verified NetBSD 11.0
`xcomp.tgz` development set in its disposable guest and passes both native
controls and both vendor checks. All final test guests halt cleanly; a final
host process audit finds no IRIS or iris-ci processes.

Vendor binaries, disk images, raw vendor traces and framebuffer captures remain
private under ignored `.work`. Public artifacts contain synthetic fixtures,
metadata and findings. At most four IRIS guests run concurrently; each harness
owns and stops its guest.
