# Private pthread stack guards on the Indy

The Xiri n32 module now lets IRIX libpthread protect a private anonymous
page while another thread is running. The previous module rejected every
`mprotect` after the first worker started. Both original IRIX releases
accepted the same calls. [Original IRIX comparison](2026-11-25-irix-event-workers.md).

## What changed

The threaded adapter checks the whole page-rounded range before calling
NetBSD's native `mprotect`. The range must be mapped, private and anonymous.
It may span several adjacent VM entries. A request overlapping the fixed
PRDA page, where Xiri switches the current worker's thread data, returns
EOPNOTSUPP. The same error applies to mixed private/shared ranges and
requests for execute permission. The per-process VM lock serializes this
check and the protection change with mapping, heap resizing and ELF loading.
UVM enforces the protections on the actual pages.

## What the two releases verified

On the 6.5.22f R4400 and 6.5.30f R5000 Indys, `xiritest` ran the same
`guard` executable that had passed on the original donors. Both protection
calls returned zero and the page retained its marker, 37. Both Xiri guests
also passed the following enforcement checks, including five repeat runs.

| Operation with a live worker | Result on both Indys |
| --- | --- |
| Protect one byte of a private page with `PROT_NONE` | A read from `/dev/zero` into that page returned EFAULT. The adjacent page still accepted one byte. |
| Restore the protected page to read/write | The same read succeeded. |
| Protect a range crossing from a private page into a shared page | The request returned EOPNOTSUPP. Both pages still accepted writes. |
| Protect the fixed PRDA page | The request returned EOPNOTSUPP. |

Both private lock probes passed. SGI libpthread created and joined a
default-scope worker as `xiritest` and a system-scope worker as root.
The separate event-worker probe still returned EOPNOTSUPP for `PR_EVENT`.
[Probe sources and build instructions](../../lab/irix-pthread/README.md#event-workers-address-based-waits-and-stack-guards).

The production module from NetBSD `e380016ff91` loaded at securelevel 1
on each Indy. All 212 imported symbols resolved against the matching
kernel and all 96 host tests passed. The local archive
`.work/modules/irix-threaded-stack-guard-20261125/indy-kernel-module.tar.xz`
contains `netbsd`, `netbsd.boot` and `compat_irix_o32.kmod`. To reproduce
the run, use a disposable v5 overlay and install the matching browser
payload for the release. [Indy installation paths](2026-11-25-threaded-break.md#reproduce-on-an-indy).

## Mozilla under xdm

On each release we logged into xdm as `xiritest` and passed a local HTML
file titled **Xiri stack guard test** to the vendor launcher. A short run
used a 22-second guest timeout. A second run gave the browser 75 guest
seconds, with tracing limited to startup. The longer runs captured the
local URL in the browser's argument list on both releases.

| Longer direct launch | IRIX 6.5.22f, Mozilla 1.0.1 | IRIX 6.5.30f, Mozilla 1.7.12 |
| --- | --- | --- |
| Guard requests in the trace | Four 8 KiB `PROT_NONE` calls succeeded. Zero failed. | Four 8 KiB `PROT_NONE` calls succeeded. Zero failed. |
| X windows | No Mozilla window in the successful queries. One query timed out. | 10×10 and 200×200 startup windows. |
| Browser outcome | The timeout ended the launch. No titled document appeared. | The timeout ended the launch. No titled document appeared. |
| `nsproc` returning EOPNOTSUPP in the trace | 20,847 | 31,320 |

On 6.5.22f, two guard calls followed successful worker creation in the
trace. On 6.5.30f the host observer timed out while the guest was printing
the trace summary. The serial log contains all four successful returns.
Their order relative to worker creation was not recorded for that run.

Neither browser repeated its previous stack-guard warning. Both still
logged the GDK `shmget` warning. The 6.5.22f loader also reported the
two known converter failures for `libucvibm.so` and `libucvko.so`.
The remaining shared reproducible failure is the `PR_EVENT` worker
request. The [original comparison](2026-11-25-irix-event-workers.md)
records how both donors created those workers and reused their IDs.
Event delivery needs a separate reference check.

A subsequent [Mozilla startup comparison](2026-11-25-mozilla-event-diagnosis.md)
admitted the event worker on disposable Indys and traced the signal wait
and local X socket that both browsers use next.

[Release hashes, test outputs and sampled browser windows](2026-11-25-irix-stack-guard.json).
