# Private IRIX libc locks on Xiri

The NetBSD IRIX module implements the n32 `usync_cntl` calls used by SGI
libpthread for private locks. Trap 1223 previously returned ENOSYS on both
Indys. The module from NetBSD `1cf737772c6` loads at securelevel 1 on the
same Indy kernel used for the threaded heap qualification. All 212 module
imports resolve against that kernel. The
[original IRIX comparison](2026-11-25-irix-event-workers.md) records the
baseline for 6.5.22f and 6.5.30f.

## What an unlock does

A wait and a wake can pass different request records. The shared key is the
address of the lock word in the process. A wake hands one grant to a waiter
on that word. If nobody is waiting, the module saves one grant for the next
wait on the word. A later caller cannot take a grant already handed to a
sleeping thread. The process mutex protects the queue and counts, and the
native interruptible wait releases the mutex while the LWP sleeps.

SGI's two libpthread builds write queue policy 1 on the wait path. Their
unlock routine sets the version, address and flags but leaves the policy
field unset. The first candidate checked that field on both calls. It
passed the original probe and still rejected a real 6.5.22f Mozilla
unlock. The trace showed wait policy 1 and wake policy 4021 on the same
address, followed by EOPNOTSUPP. The corrected module validates the policy
only for a wait.

The module accepts version 1002, zero flags and a readable private lock
word. It keeps up to 256 distinct addresses with unused grants per process.
A fork child starts empty, and exec or exit frees the table. Process-shared
locks, other operations and a comparison of signal interruption with
original IRIX remain open.

## Reproducing the lock tests

Build `waitwake` and `waitpair` using the [n32 probe instructions](../../lab/irix-pthread/README.md#event-workers-address-based-waits-and-stack-guards).
Run both as an ordinary user. The binaries and the test interpretation are
the same on the original systems and on Xiri.

| Probe | Passing observation |
| --- | --- |
| `waitwake` | Two early wakes on a second word leave the waiter on the first word asleep. They satisfy exactly two later waits on the second word. The third wait needs a fresh wake. |
| `waitpair` | A wake before the first worker is created survives. With two workers waiting on the same word, exactly one returns after the first wake and both return zero after the second. The probe uses wake policy fields of 65535 and 0. |
| SGI libpthread `create-join` | The ordinary user's worker writes 42 and returns the expected pointer. Root can also create and join a system-scope worker. |

The new two-waiter probe passed on both original IRIX donors. Both Xiri
Indys passed both lock probes as `xiritest`, including five consecutive
repeats on each release. The host suite passed all 96 tests.

## Mozilla on the Indy

| Direct launch as `xiritest` | IRIX 6.5.22f payload | IRIX 6.5.30f payload |
| --- | --- | --- |
| Local test document | Browser process started. Four X window queries found no Mozilla window. | Browser process started. Three X queries found an unnamed 10×10 window. A fourth timed out. |
| Lock evidence | No lock failure was logged. The bounded trace captured no lock calls. | The wait and wake on `0x1004d6c0` both returned zero, including the wake with policy 4021. |
| Remaining diagnostics | Two stack-guard warnings. The loader also reported failures for `libucvibm.so` and `libucvko.so`. | Three stack-guard warnings. |

In Icon Catalog, double-clicking lowercase `mozilla` started
`mozilla-bin` as `xiritest` on both Indys. On 6.5.30f it created an
additional 200×200 window before the next query stalled. For uppercase
`Mozilla`, the guest observer timed out after the double-click on each
release. The previous module had a confirmed process for that entry on
both releases. The longer browser runs required stopping the disposable
emulators after guest shutdown was requested.

Neither release displayed the local document. With a live worker, the
standalone stack-guard probe reproducibly returned IRIX EOPNOTSUPP on
both Indys when changing a private page to `PROT_NONE` and back. That
operation passed on both original donors and is the next compatibility
change to test. The separate `PR_EVENT` worker probe still returns
EOPNOTSUPP on both Indys.

## Reproducing the browser test

Use a private overlay of the corresponding v5 Indy CHD for a browser test.
Install the matching development kernel and module plus that release's
optional Mozilla payload. The tested local kernel/module archive is
`.work/modules/irix-private-usync-20261125/indy-kernel-module.tar.xz`.
The [previous qualification](2026-11-25-threaded-break.md#reproduce-on-an-indy)
gives the installation paths. Cold boot, log into xdm as `xiritest`, open
the Applications tab and double-click each Mozilla entry separately. The
visible acceptance target is a local HTML document with a distinctive
title. [Release pins and observations](2026-11-25-irix-usync.json).
