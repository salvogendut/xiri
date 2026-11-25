# Mozilla worker startup on original IRIX and Xiri

Three small n32 programs reproduce the worker, lock and stack-guard operations
seen during Mozilla startup. Each ran as `guest` on original IRIX 6.5.22f
(Indy R4400) and 6.5.30f (O2 R5000), and as `xiritest` on the corresponding
Xiri Indys (R4400 and R5000). Both Xiri boots used the threaded heap module
from NetBSD `aeb037b5865`. [Probe and build instructions](../../lab/irix-pthread/README.md#event-workers-address-based-waits-and-stack-guards).

| Operation | Both original IRIX releases | Both Xiri release lines |
| --- | --- | --- |
| `nsproc` with `PR_EVENT` | An ordinary worker got ID 1. Two event workers got IDs 2 and 3 and both entered their supplied routines. After their exit, a replacement got ID 2 while worker 1 remained alive. | The ordinary worker entered. The first event creation returned EOPNOTSUPP (122). |
| `usync_cntl` interruptible block and wake | An outstanding wait slept until its matching wake. Two earlier wakes for a second address satisfied exactly two subsequent waits there. A third wait needed a fresh wake. | Trap 1223 returned ENOSYS (89) for both operations. The worker returned from the purported waits before the matching wake. |
| `mprotect` for a private stack guard | With a worker alive, a new private mapping accepted `PROT_NONE`, then read/write. Its original value, 37, survived. | Both protection changes returned EOPNOTSUPP (122). |

The IRIX SDK names the extra bit in `0x060000ff` **PR_EVENT** (`0x04000000`).
SGI's `par` showed child return zero and distinct positive parent returns on
successful worker creation. The creation probe measures worker lifetime and
ID reuse. Delivery of asynchronous events to those workers remains unmeasured.

For the lock test, the worker and parent passed separate argument records
that referred to the same lock word. Both lock words occupied the same
page. An early wake for the second word left the first word's waiter asleep.
The trace names operations 2 and 4 `USYNC_INTR_BLOCK` and `USYNC_UNBLOCK`.
The tested n32 request carries version 1002, a 64-bit address, policy 1 and
flags zero. This test establishes the behavior for these private words in
one process. Cross-process sharing, waiter ordering and signal interruption
remain open.

## Browser check

On each private Xiri overlay, we logged into 4Dwm through xdm, set a local
test page as the browser homepage and double-clicked both original
Applications entries. We also passed the local file URL directly to the
vendor launcher. Both browsers started under the ordinary user. Neither
release displayed the document during these bounded checks. The direct
launches reproduced the stack-guard and lock diagnostics. We stopped the
test browsers after sampling them. The [longer heap qualification](2026-11-25-threaded-break.md)
records the previous timeout and guest out-of-swap outcomes.

The first implementation target is the measured private, address-keyed
block/wake pair. It has a small regression test for contention, address
isolation and counted early wakes. Event-worker creation and stack-guard
protection can then be tested independently. Keep the visible local
document as the browser acceptance check on each release.
[Release pins and guest results](2026-11-25-irix-event-workers.json).

The subsequent module implements the two private lock operations and passes
both the address-isolation probe and a two-waiter check on each Indy.
[Implementation and browser retest](2026-11-25-irix-usync.md).
