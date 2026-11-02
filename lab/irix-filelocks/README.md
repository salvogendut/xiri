# IRIX record-lock lab

The [result](../../docs/results/2026-11-02-irix-filelocks.md) records the
IRIX 6.5.22m measurements, NetBSD qualification, reproduction commands and
link to the completed desktop artwork repair.

`probe.c` observes guarded o32/n32 structures, access modes and validation
errors. `behavior.c` uses pipe barriers to observe process ownership,
conflicts, waiting and release. The `interop-*` pair tests the shared native
and foreign vnode lock state. Reference JSON contains original-system
records and fixture/source hashes; both baseline files pin clean-source
NetBSD kernels. Proprietary files and disk images remain in ignored `.work`.

The explicit comparator preserves the known preliminary directory-read
difference while checking every lock-result and buffer byte. Do not turn
lock acquisition into a successful no-op: the cross-process and native-peer
checks must continue to pass.
