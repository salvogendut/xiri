# Desktop filesystem and RPC compatibility

The NetBSD `xiri` branch now supplies the link inspection, directory enumeration
and polling interfaces reached by the original desktop clients. It also reports
MAC support as absent, matching the supplied original IRIX system and preventing
4Dwm's unwanted Trusted Path panel. Xorg remains the display server; the user
has deferred further Xsgi investigation.

Source commits are `10335af3bb3` (link/MAC adapters), `8d8ca8a0e2c` (directory
records, poll and complete dispatch), and `9c8bd4e328f` (readlink fault handling).
The final kernel pin is **9c8bd4e328f**. Exact source and artifact hashes are in
the [machine-readable qualification](2026-11-02-irix-desktop-fs.json).

All **6,500 guest records and 32 native/vendor controls pass**. The LP64 matrix
runs in both CI and ordinary IRIS execution; the o32 kernel runs the matching
o32 matrix. All three guests halt cleanly. The pre-existing xstat regression
is included alongside the new interfaces.

| Suite | LP64 CI | LP64 ordinary | o32 CI |
| --- | ---: | ---: | ---: |
| lxstat | 672 | 672 | 336 |
| readlink and feature queries | 240 | 240 | 120 |
| poll | 240 | 240 | 120 |
| directory enumeration | 800 | 800 | 400 |
| xstat regression | 648 | 648 | 324 |

The original IRIX oracle contains 1,952 new observations, spanning o32/n32,
direct/indirect traps, and root/UID 1234. Directory conversion selects the
64-bit layout for n32 even through the old syscall numbers. Short buffers
preserve the next unreturned entry. Required ngetdents EOF-pointer faults occur
after successful record/cursor updates. Native observers independently provide
filesystem metadata and directory order.

The first link build omitted the explicit dispatch allowlist entries; its
runs were cancelled and do not qualify those adapters. The next matrix found
that native FFS fast-symlink reads discard uiomove errors. Xiri now reads the
link into a bounded kernel buffer and owns the user copyout, restoring EFAULT
and partial-prefix behavior. A separate LP64 harness failure came from staging
directory permissions; explicit umask/modes corrected the fixture setup.

Compatibility limits remain explicit. Native pipe poll readiness differs from
IRIX for POLLOUT on the read end and unrequested POLLRDNORM at hangup: 60 records
across the three matrices exercise these declared differences. Directory padding
is unspecified; Xiri avoids the occasional IRIX partial-byte write when a
requested directory buffer crosses an unmapped span. Native inode numbers,
cookies, ordering and page sizes remain native values. Unix-domain sockets and
union-mount directory traversal are not qualified by this work.

The [lab guide](../../lab/irix-lxstat/README.md) contains reproduction commands.
The [native FAM experiment](../../lab/native-fam/README.md) is a separate
userspace requirement: syscall success alone does not qualify desktop icons,
file monitoring or application actions. The older 20261102 CHD retains its
signal kernel; the separately [qualified service image](2026-11-02-desktop-services.md)
now packages this filesystem/poll kernel and native FAM.
