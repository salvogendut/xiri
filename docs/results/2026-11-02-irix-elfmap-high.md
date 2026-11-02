# Freeware library addresses and desktop launch follow-up

The user reproduced GIMP's loader error in winterm on the icons CHD. The
same invocation on a disposable copy reports:

```
gimp: rld: Error: elfmap: couldn't map /usr/freeware/lib32/libgtk-1.2.so.1: (null)
gimp: rld: Fatal Error: Cannot Successfully map soname 'libgtk-1.2.so.1' ...
```

The original loader writes these messages to `/dev/tty`, so redirecting
stderr alone missed them. Raw ktrace retains the writes. The library is
already imported with executable permission. Its RX address is `0x5fe70000`
and RW address is `0x5ffd4000`; the mapper's previous 1 GiB admission limit
rejected the layout before mapping it.

NetBSD `xiri` commit `ac4423d4657c4664898dfcab44b9f19c66f46f3b` admits
preferred library addresses throughout the 32-bit user range. Segment-end,
file-range, size, alignment, protection, permission and rollback checks stay
in force. A collision still relocates the complete layout into the existing
`0x04000000..0x40000000` search window. It never replaces existing mappings.
Main executable/interpreter admission is a separate contract and is unchanged.

## Validation

The [machine-readable result](2026-11-02-irix-elfmap-high.json) qualifies
700 mapping executions and 32 native/vendor controls on clean builds:
LP64 CI, LP64 ordinary execution and o32 CI. The fixtures retain all 57
lower-window cases and add 13 high-address cases: code execution, data/BSS,
repeat mapping, RX/RW collisions, competing mappings, write/gap faults,
the 1 GiB boundary, a stack collision and requests outside the user range.
Original IRIX 6.5.22m supplies 280 matching fixture executions. All final
guests halt cleanly.

Two differences are explicit. IRIX relocates requests above the user limit;
this bounded NetBSD implementation rejects them with ENOEXEC. IRIX accepts
`0x7f000000` directly, while NetBSD relocates it because its compat stack
reserves that area. The first two native runs exposed an incorrect checker
expectation for this stack reservation; their raw records remain preserved
and they are excluded from qualification. The corrected complete reruns
include the before/after controls. The older original-IRIX 960 MiB occupant
setup limitation also remains explicitly excluded from mapper conclusions.

## GIMP retry

On the new kernel, the same winterm command completes all 11 observed
ELFMAP calls, including GTK at `0x5fe70000`, and communicates with Xorg.
It then exits with:

```
LibGimp-ERROR **: unable to set handler for signal 1
aborting...
```

The trace records `sigaction(1, ...)` returning IRIX EOPNOTSUPP (122).
Earlier registrations for signals 47 and 48 also return that error. The
current signal adapter explicitly excludes realtime signals and action masks
containing unsupported bits. The exact action payload for signal 1 still
needs measurement; the trace alone does not identify which guard rejected it.
This clears the reported loader failure, not full GIMP startup or plug-ins.

Before: `.work/catalog-actions/diagnose-wmkppqs6/gimp.ktrace`.
After: `.work/catalog-actions/gimp-high-lmxc2zwx/gimp.ktrace`.
Both use the original installed GIMP and libraries, with no vendor patches.

## Icon Catalog and xosview

A recognized double-click and the keyboard Open action both fork a catalog
child, then attempt `/emul/irix/bin/sh`; exec returns ENOEXEC. That original
shell is a static n32 ELF (flags `0x20000020`), outside the current marked
static-probe and dynamic-vendor loader contracts. The trace also exposes
unimplemented `chdir` and `setpgrp` calls in the launch child. Those need
proper ABI work; a mouse-timing adjustment alone cannot repair launch.
A separate retry with `SHELL=/usr/local/libexec/xiri/command-shell` still
executes the original `/bin/sh` and fails with ENOEXEC; that environment
override does not redirect this catalog action.

The imported xmahjongg FTR already contains `CMD OPEN $LEADER $REST` and
both normal and opened artwork. There is no need to invent a Freeware
registration. Opened-state behavior remains unqualified until application
launch and its lifecycle work. The trace also checks `/usr/lib/desktop/launcheffect`
and `/usr/lib/desktop/waitmap`; both are absent from the staged tree and
return ENOENT. Check their presence and purpose on the source image before
adding them to the copy ledger.

xosview reproduces `sysinfo scall interface not supported`. Its trace
requests `sysmp` commands 1 and 9 (the latter with subselectors 1 and 8),
plus `syssgi` selector 5. These return ENOSYS; current `sysmp` supports only
the page-size query. Statistics support needs measured layouts and native
NetBSD data, independently of X and library loading.

## Starting directory

The desktop launcher previously changed into its temporary session directory
and every child inherited it, despite `HOME=/usr/people/xiritest`. The native
session script now resolves its log directory first and starts applications
from HOME. Log, readiness, handoff and logout paths remain absolute under
the session directory. Typed `pwd` in both the initial winterm and a fresh
Toolchest Open Unix Shell reports `/usr/people/xiritest`, with UID/GID 1234
and valid native controlling-terminal handoffs. A [PNG capture](images/2026-11-02-winterm-home.png)
shows the corrected terminal directory. Toolchest logout then removed the
supervisor, X lock, desktop lock and all UID 1234 clients. The [application evidence](2026-11-02-desktop-applications.json)
pins those terminal responses and the raw application traces. The change applies to the
session's configured HOME; it does not invent a `/root` home for IRIX root.

The published `20261102-icons` CHD remains unchanged. These source changes
are not yet a newly qualified manual image. On that existing image, plain
`cd` moves the terminal to the configured home.

Both application diagnostic guests halted cleanly. A final host process check
found no remaining IRIS instances. The source and documentation changes are
pushed; no existing qualified image or pinned emulator was replaced.
