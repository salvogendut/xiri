# Why the two Mozilla releases stall on Xiri

Mozilla 1.0.1 and 1.7.12 both rendered a local HTML document on the Xiri
4Dwm desktop with two diagnostic changes. The first let libpthread start
its event worker. The second let Mozilla query its local X socket for
unread bytes. Both release-matched original IRIX donors rendered the same
page. A separate missing signal wait explains why a live browser thread
can consume CPU during startup.

| Startup evidence | IRIX 6.5.22f / Mozilla 1.0.1 | IRIX 6.5.30f / Mozilla 1.7.12 |
| --- | --- | --- |
| Native IRIX, ordinary user | 610×450 document window on Indy R4400 | 610×450 document window on O2 R5000 |
| Xiri Indy, production stack-guard module | 20,847 rejected event-worker requests in the previous trace | 31,320 rejected requests |
| Xiri Indy, diagnostic module admitting event workers | Two ordinary workers and one event worker started | Two ordinary workers and one event worker started |
| Signal waits returning IRIX ENOSYS on one browser thread | 166,590 at libc PC `0x0fa4f8b8` | 80,588 at libc PC `0x0fa426f4` |
| Main thread querying its connected local socket | `SIOCNREAD` on fd 3 returned IRIX EAFNOSUPPORT (124) | Same selector, descriptor and error |
| Document with event-worker change alone | No titled window. The 120-second launch reached its timeout. | Only startup windows. The browser exited 1 with and without tracing. |
| Document after enabling byte counts on the local X socket | 610×450 Navigator rendered the heading | 610×450 Navigator rendered the heading |
| Cold-boot repeat with the same module and `DISPLAY=127.0.0.1:0` | Rendered the same page | Rendered the same page |

[Xiri 6.5.22f screenshot](2026-11-25-mozilla-xiri-6.5.22f.png) ·
[Xiri 6.5.30f screenshot](2026-11-25-mozilla-xiri-6.5.30f.png).

The counts describe bounded trace captures with different durations.
The first 6.5.22f capture ended before event-worker creation. The longer
capture recorded it. On both releases the GDK log reported fatal I/O error
124 on display `:0.0`. Independent authenticated display queries returned
1280×1024 before and after the launch, with the same Xorg PID. The 6.5.22f
loader also reported failures mapping `libucvibm.so` and `libucvko.so`.
Both warnings recurred during the successful 6.5.22f page load. Both
releases also rendered the page despite GDK's `shmget` warning.

[Original 6.5.22f document screenshot](2026-11-25-mozilla-native-6.5.22f.png) ·
[Original 6.5.30f document screenshot](2026-11-25-mozilla-native-6.5.30f.png) ·
[Production module comparison](2026-11-25-irix-stack-guard.md).

On native 6.5.22f the observer found the document, then failed to find
`head` for its trailing diagnostics. On 6.5.30f the host timed out waiting
for the shell completion marker. Both serial logs captured the titled
document and both framebuffer captures show the heading. Both donors shut
down cleanly.

## Worker and signal behavior

The production `irix_nsproc` adapter in `sys/compat/irix_o32/irix_thread.c`
accepts flags `0x020000ff`. Both browsers also set the `PR_EVENT` bit
(`0x04000000`) in the syscall and in the worker descriptor. The descriptor
had a zero length and the scheduling pointer was null. A diagnostic build
accepted that combination and logged it in a user ktrace record. The
ordinary create/join, contended wait and stack-guard controls passed on
both Indys. The separate worker-lifetime probe returned IDs 1, 2, 3 and 4
on Xiri. Original IRIX reused ID 2 for the replacement worker.

Both vendor libcs implement `__sigpoll` with the instructions
`li v0,1166` and `syscall`. Each failing PC points to that second
instruction. Xiri's foreign syscall dispatch lacks an entry for 1166.
On 6.5.30f the waiting thread alternates it with successful time queries.
There are also unsupported thread-control calls, including
`PR_THREAD_KILL`. The traces identify the wait without revealing the
contents of the browser's signal mask.

The freestanding `sigpoll` probe blocks IRIX SIGUSR1, waits with a 10 ms
timeout, sends SIGUSR1 to itself and polls twice with a zero timeout.

| Probe result | Both original IRIX releases | Both Xiri Indys with the event diagnostic |
| --- | --- | --- |
| No signal pending | EAGAIN (11) | ENOSYS (89) |
| SIGUSR1 pending | Returned 16 and wrote signal 16 to siginfo | ENOSYS, signal field remained zero |
| Poll again after the successful native wait | EAGAIN | ENOSYS |

This measures timeout, receipt and consumption in a single thread. Directed
delivery to a worker and worker ID lifetime require separate controls.
[Signal and worker probes](../../lab/irix-pthread/README.md#event-workers-address-based-waits-and-stack-guards).

## The local X connection

The n32 trace on each Indy shows a successful `socket(1, 2, 0)` and
`connect` on fd 3. Mozilla later calls `ioctl(3, 0x4004730a, ...)` from
its main thread. This is IRIX `SIOCNREAD`, which reports the number of
unread bytes. The adapter in `sys/compat/irix_o32/irix_o32.c` admits
IPv4 TCP streams. The local X connection uses a Unix-domain stream and
takes the EAFNOSUPPORT branch. [Original TCP byte-count qualification](../../lab/irix-siocnread/README.md).

The second diagnostic build also admitted Unix-domain stream sockets in
the existing byte-count adapter. On both original releases and on both
modified Xiri Indys, a connected socket pair reported 0, 3, 2 and 0 queued
bytes as the probe wrote and read three bytes. All four guests returned
IRIX ECONNRESET (131) after the peer closed and the reader consumed EOF.
The real browsers then painted the local document on `:0`. This isolates
the socket error from the missing signal wait, which the second build
still lacks. [Local-stream probe](../../lab/irix-siocnread/README.md#connected-unix-streams).

The xdm session normally sets `DISPLAY=127.0.0.1:0`. Both browsers also
rendered the document when launched on that display after a cold boot.
The event-only failure comparison used `:0`, so the evidence for needing
the local socket change applies to the Unix-domain path. The successful
launches called the vendor launcher directly as `xiritest`. Qualifying
the two catalog clicks and CPU use after the page loads remains open.
[xdm session configuration](../../runtime/etc/xdm.xsession).

The [subsequent production-module check](2026-11-25-mozilla-sigpoll.md) records
worker ID reuse, directed signals, timed waits and the two catalog launchers.

## Reproducing the comparison

Start from NetBSD `e380016ff914a4010bfeb5b3736fd1223c3ad29b` and the
release-specific Indy v5 browser payload. Use disposable overlays and the
kernel and boot file from the stack-guard qualification. In a disposable
NetBSD source checkout, apply the event patch and build the module. For
the local socket comparison, also apply the second patch and rebuild.

```sh
git -C "$src" apply "$PWD/lab/irix-pthread/event-creation-diagnostic.patch"
sh lab/ip28-kernel/build-module.sh "$src" "$tools" "$out/event"
git -C "$src" apply "$PWD/lab/irix-siocnread/local-stream-diagnostic.patch"
sh lab/ip28-kernel/build-module.sh "$src" "$tools" "$out/event-local"
```

Install the chosen `module/compat_irix_o32.kmod` in the guest module
directory and cold-boot the overlay. Log into xdm as `xiritest` and run
the following in its terminal. This selects the Unix-domain display used
for the local socket comparison. The window title and rendered heading
identify a successful load even when the browser first creates unnamed
startup windows.

```sh
cd "$HOME"
export DISPLAY=:0
printf '%s\n' '<title>Xiri event worker test</title><h1>Xiri event worker test</h1>' >event.html
/emul/irix/bin/sh /usr/bin/X11/mozilla "file://$HOME/event.html"
```

For the syscall comparison, run the same command under NetBSD
`ktrace -i -t u -f event.ktr` and stop tracing after startup.
Pair `irix_o32` and `irix_ret` by process and LWP using
[the LP64 trace decoder](../../scripts/irix-lp64-ktrace.py).
Both diagnostic modules resolved all 212 imported symbols against the
matching kernel. The 96 host tests passed. The records and screenshots
use private overlays of the two release lines. The patches are lab
inputs. The production module and installer CHDs retain their previously
qualified versions.

The local lab archive `.work/modules/irix-mozilla-diagnostics-20261125/`
retains the module that displayed both pages and the two compressed
event-only ktraces. The matching kernel and boot file are in the
[stack-guard archive](2026-11-25-irix-stack-guard.md).

[Release hashes and measured results](2026-11-25-mozilla-event-diagnosis.json) ·
[Indy installation paths](2026-11-25-threaded-break.md#reproduce-on-an-indy).
