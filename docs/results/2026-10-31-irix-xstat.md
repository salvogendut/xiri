# IRIX xstat contract and Toolchest follow-up

## Measured contract

The user's original IRIX 6.5.22m installation ran 324 original static fixtures
under root and uid/gid 1234: 648 complete 576-byte records. Every fixture checks
return registers, identity, output guards and a mapped-page boundary. Both
ABIs use the same executable bytes on IRIX and NetBSD, through direct and
indirect syscall dispatch. The reference guest halted cleanly.

Version 2 selects a 136-byte structure for o32 and a 152-byte structure for
n32. Version 3 selects the 152-byte structure for either ABI. The
[layout table](../../lab/irix-xstat/abi.json) gives every field offset. The
BSD-licensed historical NetBSD definitions provided a starting point, but
measurement corrected the n32 version-2 selection and small size conversion.
No leaked proprietary source was consulted.

The reference establishes these details:

- Path lookup occurs before version or output validation. Missing paths and
  invalid path pointers retain their errors even with an invalid version.
- Versions 0, 1, 4 and -1 return EINVAL after a successful lookup. A path can
  contain 1023 bytes plus NUL; longer paths return IRIX ENAMETOOLONG (78).
- Symlinks are followed. A trailing slash on a regular file is accepted.
  Native directory search permissions still apply; file read access is not
  required to obtain metadata.
- Unaligned output is accepted. A copy crossing the end of a mapping writes
  the complete accessible prefix and then returns EFAULT. Read-only and
  inaccessible output pointers fail. All padding and reserved bytes are zero.
- The o32 version-2 size field saturates at `INT32_MAX` for the sparse
  2 GiB + 1024 byte file. The wide layout preserves its full size.
- Device values encode 14 major bits above 18 minor bits. Character/block
  fixtures verify the encoding. Return register v1 and the tested n32 saved
  register retain their sentinels.

The host decoder reconstructs all 648 reference records, including guard
areas and fault prefixes. Four deliberate corruption controls confirm that
changed guards, padding, return flags and a short-copy byte are rejected.

## Implementation and comparison

The NetBSD wrapper uses native pathname lookup, credentials and vnode stat,
then serializes fixed-width fields into a zeroed foreign structure. It applies
the measured pathname length limit before removing trailing slashes. Existing
`/emul/irix` lookup and native fallback apply. A distinct shadow-file fixture
checks that policy; another file exists only in the native namespace.

An independent native `stat` observer records identities, modes, sizes,
timestamps and allocation. Every byte of each foreign record is compared
against these named native values packed into the measured IRIX layout. This
avoids comparing unrelated native and XFS inode numbers or silently ignoring
filesystem-dependent fields.

The filesystem string is deliberately `unknown` rather than `xfs`; project ID
is zero. The implementation does not provide XFS attributes or project
accounting. Inode/block/time/device overflow beyond the tested widths,
concurrent namespace mutation, other stat-family calls and general application
compatibility remain unqualified. The [lab](../../lab/irix-xstat/README.md)
contains the commands, pinned inputs and complete scope.

## Validation record

The bounded xstat subset passes on the clean NetBSD source revision
`3f309d17fc5e6ea9ccc3b774e8cc1ca8ef277979`, branch `xiri/irix-xstat`.
Both kernels were built sequentially with two jobs. The emulator remains at
`9df1df14334838a989253efefe26f0547e6da592`.

| Kernel and emulator mode | xstat records | Native/vendor controls | HOME Toolchest attempts |
| --- | ---: | ---: | ---: |
| LP64, CI | 648 | 12 | 12 |
| LP64, ordinary | 648 | 12 | 12 |
| o32, CI | 324 | 8 | 0 |

All 1,620 records match the measured contract with independently observed
native filesystem fields and the explicit filesystem/project differences.
All three focused guests halt cleanly. The 24 Toolchest attempts reproduce
12 library-only configuration errors and 12 installed-resource SIGSEGVs.
Native X controls pass before and after each LP64 workload.

The [machine-readable report](2026-10-31-irix-xstat.json) pins the run hashes,
inputs, counts and observed boundaries. Its qualifier rechecks all records
offline and re-decodes the raw Toolchest traces. The transport harness gained
an explicit desktop-expectations option during the focused runs; the qualifier
therefore re-decodes that helper's output instead of requiring identical whole
transport-script hashes. Other focused sources remain pinned byte-for-byte.

The first reference attempt produced 520 complete records but exceeded IRIX's
argument limit when collecting them with one wildcard-expanded tar command.
The archive was recovered in batches; that run did not finish clean shutdown
and is diagnostic evidence only. The final harness batches archive additions,
synchronizes the console before shutdown and collected the expanded 648-record
matrix with a clean power-off. One host-side launch attempted to run the entire
harness inside the toolbox, where `genisoimage` is absent; it failed before any
emulator started. Run the harness on the host, which launches IRIS through its
existing toolbox wrapper.

## Toolchest resource boundary

With libraries alone, Toolchest still reports the absent menu configuration.
Installing the supplied menu, app-defaults and locale indexes takes an earlier
resource-loading path: xstat succeeds for
`/usr/lib/X11/app-defaults/Toolchest`, open succeeds, and fxstat(1160) returns
ENOSYS. The subsequent read requests `0xffffffff` bytes and returns the
4,281-byte app-defaults file. The installed-resource run faults before opening
`system.chestrc`; the 6,460-byte menu is not the file in that read.

Two initial root ptrace captures agree on PC `0x0fa56b6c`, a load through
register 8 plus eight bytes, with bad address `0x740a0a5c`. The return address
`0x0fa511b8` is inside libc's malloc entry. The corrupted base value
`0x740a0a54` matches bytes at offset 48 of the app-defaults file. This is strong
evidence of allocator metadata overwritten by resource input. Unsupported
fxstat and the unchecked read length are the immediate leads; no general
allocator or fxstat fix is claimed here.

The initial diagnostic guest passed native exec/fault PC controls and captured
the two root faults, then failed its non-root attempt: `PT_TRACE_ME` rejected
the credential transition and the child exited 124. It halted cleanly, but that
run remains a partial diagnostic. The final diagnostic restricts ptrace to
root; ordinary-user behavior remains covered by repeated untraced launches.

A 1×1 Toolchest window appears in some library-only samples. It is not a usable
menu or event loop. Window-tree samples in the installed-resource stage show
no remaining child window. These samples do not rule out a transient window
between observations.


The first xstat-kernel transport run retained the old desktop signatures.
All 1,272 synthetic fixture records, native/vendor outputs and five peers
matched, but two closed-display Toolchest trace checks changed: successful
xstat adds a six-call path through getpid, sysinfo, open, fcntl, fxstat and
close, with one additional successful fcntl return. The display-error output
and both 4Dwm boundaries are unchanged. That run remains a failed comparison;
`lab/irix-xstat/desktop.json` records the reviewed signatures for fresh runs
without changing historical transport expectations.

Fresh transport regressions pass 1,284 LP64 cases and 641 o32 cases, including
fixture bytes, peers, native controls and reviewed desktop boundaries. A
separate LP64 run passes all 552 select records, retaining its existing explicit
descriptor-policy differences. These three regression guests halt cleanly.

The [xclock experiment](2026-10-31-irix-xclock.md) completes the root fault
capture in a fully controlled run and tests a simpler original X client.
Its independent loader failure does not change the xstat qualification.
The [fxstat follow-up](2026-10-31-irix-fxstat.md) now supplies descriptor
metadata: Toolchest requests exactly the app-defaults size, reads the complete
menu, and reaches an X I/O error at unsupported SIOCNREAD without the observed
allocator fault. The [libXmu capture](2026-10-31-irix-xclock-elfmap.md) separately
confirms a collision with mapped libXaw text. The results above remain pinned
to the earlier xstat kernel.
