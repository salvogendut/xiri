# Threaded heap resizing on the two Indy releases

The baseline module returned IRIX EOPNOTSUPP on the first heap resize after
a successful `nsproc` on both the 6.5.22f R4400 and the 6.5.30f R5000.
The same executable grew and shrank its heap before starting the worker.
This isolates the failure from Mozilla and its loader.

The module now serializes threaded `break` with non-fixed `mmap` and
`SGI_ELFMAP` in the same process. Native `obreak` performs the page
rounding, allocation, release and data-limit check. The compatibility
module also checks address-space headroom before growth. Threaded shrink
stops at the break captured during first worker initialization because older
heap pages can contain fixed mappings installed by the application.

## What the guests verified

On both releases, the ordinary user passed the occupied-page test and
five additional untraced repetitions passed. The worker wrote into a page
it had added, the parent read that value, then shrank and regrew the heap.
The discarded pages read as zero. The preserved heap page and the separate
mapping still held their markers after rejected requests. SGI libpthread
also passed create/join for the desktop user and for root using system scope.

With the default 256 MiB data limit and unlimited address space, the occupied
guard rejected growth with ENOMEM. With a 4 MiB data cap, growth into an
otherwise free 5 MiB interval also returned ENOMEM. A 36 MiB address-space
cap prevented even the initial guard mapping. Repeating at 122–126 MiB
allowed guard and worker setup, then rejected that 5 MiB request. At 128 MiB,
132 MiB and unlimited, the limit fixture instead reported growth. A final
control wrote the last word of the 5 MiB allocation at 128 MiB and
confirmed ENOMEM at 124 MiB and with the 4 MiB data cap on each release.

The production module at NetBSD revision `aeb037b5865` loaded at securelevel
1 on both guests. All 211 module imports resolved against the existing
Indy kernel, and all 96 host tests passed. The tested pair is available
locally at `.work/modules/irix-threaded-break-20261125/indy-kernel-module.tar.xz`.

## Mozilla under xdm

Both original catalog entries launched the release-matched Mozilla process
as `xiritest`. No launch displayed the titled local document. On 6.5.22f
the lowercase launcher was still consuming CPU after 130 seconds with no
browser window in the sampled X tree. On 6.5.30f the lowercase launcher
still had small startup windows at 135 seconds. We stopped those two
catalog processes after observation.

| Indy browser | Successful threaded `break` calls in the direct-launch trace | Outcome of the direct local URL |
| --- | ---: | --- |
| 6.5.22f, Mozilla 1.0.1 | 495, zero rejected | The 120-second guest timeout ended the launch (124). The two converter libraries still failed to load. |
| 6.5.30f, Mozilla 1.7.12 | 2,014, zero rejected | The browser created 200×200 startup windows. The guest kernel recorded an out-of-swap kill for the matching browser PID (137). |

Direct-launch counts come from the initial trace interval. After that
interval the browsers continued with tracing disabled. In the separate
uppercase catalog traces, the two releases respectively made 774 and
12,640 successful threaded heap requests with zero rejected. This resolves
the heap rejection seen in the [preceding tests](2026-11-25-threaded-elfmap.md).

Both vendor runtimes reported failure to protect a worker stack guard and
failure to block or wake a libc lock. The uppercase traces on both guests
contain the supported `nsproc` flags `0x020000ff` and a second request
using `0x060000ff`. The current adapter rejects the latter. The 6.5.22f
trace recorded 5,027 unsupported `nsproc` returns and 112,114 unimplemented
trap 1223 returns. On 6.5.30f those counts were 100,125 and 82. The next
comparison is one contended worker pair on original IRIX using the second
flag combination and the observed block/wake operations. That will let us
test the contract independently of Mozilla's retry loop.

[Release hashes, observed windows and trace counts](2026-11-25-threaded-break.json).

## Reproduce on an Indy

Use a private overlay of the appropriate v5 Indy CHD and its pinned IRIS
binary. Install the matching development kernel and `netbsd.boot`, the
production module in `/stand/sgimips/11.99.11/modules/compat_irix_o32/`,
and the release-specific optional browser import. Cold boot before testing.
The [module build script](../../lab/ip28-kernel/build-module.sh) takes the
NetBSD source, NetBSD cross-tool directory and a fresh output directory.
The [heap probe](../../lab/irix-thread-break/README.md) gives the build
commands and exit-status key.

For the browser test, log into xdm as `xiritest`, select Applications in
Icon Catalog and double-click `Mozilla` and `mozilla` separately. For a
direct run from winterm, create a local HTML file with a distinctive title
under the user's home, then run

```sh
/emul/irix/bin/sh /usr/bin/X11/mozilla file:///usr/people/xiritest/thread-break.html
```

Each qualification guest also set its release-matched browser's startup
homepage to that local file so the catalog clicks had the same visible
target. Each release used a disposable overlay. The qualified CHD, NVRAM
and emulator passed their original hash checks after testing.
