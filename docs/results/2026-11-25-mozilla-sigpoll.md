# Mozilla on the Xiri Indy desktop

Both **Mozilla** and **mozilla** in the Applications catalog rendered a local
HTML document on each Indy release. Across four 24-second samples the
browser used 0.00 to 0.35 seconds of guest CPU time after the page appeared.

## Signal waits and event workers

The n32 compatibility module implements IRIX `__sigpoll` (trap 1166) using
NetBSD’s signal queues and timed wait. The v5 diagnostic runs had recorded
166,590 missing-syscall returns on Mozilla 1.0.1 and 80,588 on 1.7.12.
Those captures used different time limits. The following tests ran identical
n32 executables as ordinary users on two original IRIX donors and on two
cold-booted Xiri Indys. [Earlier traces](2026-11-25-mozilla-event-diagnosis.md).

| Observation | Original 6.5.22f | Xiri 6.5.22f | Original 6.5.30f | Xiri 6.5.30f |
| --- | ---: | ---: | ---: | ---: |
| Elapsed time for a 200 ms empty wait | 207 ms | 219 ms | 216 ms | 209 ms |
| Pending IRIX SIGUSR1, followed by an immediate poll | 16, EAGAIN | 16, EAGAIN | 16, EAGAIN | 16, EAGAIN |
| Invalid timeout of one billion nanoseconds | EINVAL | EINVAL | EINVAL | EINVAL |
| SIGUSR1 sent to a named event worker, received once | 16 | 16 | 16 | 16 |
| Private signal 47 send | 0 | EOPNOTSUPP | 0 | EOPNOTSUPP |
| Subsequent 500 ms wait for 47 | EAGAIN | EAGAIN | EAGAIN | EAGAIN |

The worker blocks its signal before the parent sends. It starts polling
after the send returns. Each SIGUSR1 wait wrote IRIX signal number 16 into
the 128-byte result structure. Both native donors accepted the private
send but did not return signal 47 through this wait. Asynchronous handling
of this private signal and thread-control operation 8 remain open.

Event-worker creation now accepts the vendor `PR_EVENT` flags and reserves
the lowest available positive thread ID. With ordinary worker 1 still live,
both Xiri Indys assigned IDs 2 and 3 to two concurrent event workers and
reused 2 after they exited. Vendor pthread create/join, private stack guard
protection and counted lock wakeups passed on both. The Unix-stream
`SIOCNREAD` fixture measured 0, 3, 2 and 0 queued bytes and ECONNRESET
after reading EOF on each final module. [Worker and signal probes](../../lab/irix-pthread/README.md) ·
[Socket control](../../lab/irix-siocnread/README.md#connected-unix-streams).

NetBSD `xiri` commit `547482bf0e21f7bb44c1417b119a12a4da687a4e`
contains the implementation. All 215 imported module symbols resolved
against the [matching Indy kernel](2026-11-25-irix-stack-guard.md).
The local module archive is
`.work/modules/irix-mozilla-sigpoll-20261125/compat_irix_o32.kmod`.
Both guests loaded the filesystem module at securelevel 1. All 96 host
tests passed. The IRIS fork at `39ef6dff` already contained the checked
upstream revision `057ba095`.

## Launch and idle CPU checks

On each release, the stock vendor launcher opened Navigator under the
`xiritest` xdm account. Its original web homepage led to a DNS alert in
the offline guest. For the measurements, the test set a local HTML file
as the homepage in that user's existing Mozilla profile. Each real
Applications icon received an XTEST double-click. The other browser
processes had exited before each launch. The launcher path, X title and
visible heading identify the result.

| Indy vendor release | Catalog icon | Browser PID | Guest CPU / elapsed | Mean guest CPU | Screen |
| --- | --- | ---: | ---: | ---: | --- |
| 6.5.22f | `Mozilla` | 2839 | 0.00 s / 24 s | 0.00% | [PNG](2026-11-25-mozilla-sigpoll-6.5.22f-upper.png) |
| 6.5.22f | `mozilla` | 3992 | 0.00 s / 24 s | 0.00% | [PNG](2026-11-25-mozilla-sigpoll-6.5.22f-lower.png) |
| 6.5.30f | `Mozilla` | 2456 | 0.00 s / 24 s | 0.00% | [PNG](2026-11-25-mozilla-sigpoll-6.5.30f-upper.png) |
| 6.5.30f | `mozilla` | 3156 | 0.35 s / 24 s | 1.46% | [PNG](2026-11-25-mozilla-sigpoll-6.5.30f-lower.png) |

Sampling used the change in cumulative browser-process CPU time across
three guest-clock readings. The final LWP snapshots include a sleeping
`sigwait` worker. These measurements cover the static document after
startup. Each rate uses CPU seconds divided by elapsed guest seconds. The
instantaneous `ps` percentage also reflects recent startup work. Web access, extended browsing
and plug-ins remain unqualified.

## Launch the test images

Run one of these commands from the Xiri repository. Each bundle has its
own standalone CHD, firmware state, pinned IRIS binary and matching
Freeware CD 4. IRIS creates a writable overlay at launch. Both images retain the vendor's stock
preferences. The test user's profile, local document, launcher logging
and measurement tools lived on disposable overlays.

```sh
.work/images/xiri-cd4-indy-6.5.22f-mozilla-20261125/run-iris.sh
.work/images/xiri-cd4-indy-6.5.30f-mozilla-20261125/run-iris.sh
```

Both standalone images passed `chdman verify` and were cold-booted on the
matching Indy. The previous v5 images remain available separately.
[Machine settings and original v5 images](2026-11-24-indy-v5-clock.md) ·
[Exact disk, module, payload and screenshot hashes and raw measurements](2026-11-25-mozilla-sigpoll.json).

## Open a local page on the manual image

The vendor's first-run homepage contacts www.mozilla.org. In a guest without
DNS it can stop at an alert. For a repeatable offline check, log in through
xdm as `xiritest` and run these commands in winterm. The explicit file URL
also gives a new account a local page on its first launch.

```sh
cd "$HOME"
printf '%s\n' '<title>Xiri Mozilla catalog test</title><h1>Xiri Mozilla catalog test</h1>' >ok.html
/emul/irix/bin/sh /usr/bin/X11/mozilla "file://$HOME/ok.html"
```

To make the same file the homepage for catalog launches, exit Mozilla.
In the same account, append these preferences to the profile you use.
On **6.5.22f**, first run `milestone=rv:1.0.2`. Its browser compares
the stored milestone to the HTTP handler's version string from the
vendor's `general.useragent.misc` preference. The value `ignore` still
took this release to the external first-run page. On **6.5.30f**, run
`milestone=ignore`. Then apply the settings to the default profile.
If you have several profiles, select the one you want.

```sh
for prefs in "$HOME"/.mozilla/default/*.slt/prefs.js; do
    test -f "$prefs" || continue
    printf '%s\n' \
        "user_pref(\"browser.startup.homepage\", \"file://$HOME/ok.html\");" \
        'user_pref("browser.startup.page", 1);' \
        "user_pref(\"browser.startup.homepage_override.mstone\", \"$milestone\");" \
        >>"${prefs%/*}/user.js"
done
```

Double-click **Mozilla** or **mozilla** in the Applications tab. Both icons
lead to the matching SGI browser. The uppercase icon points into
`/var/netscape/mozilla` and the lowercase one uses `/usr/bin/X11/mozilla`.

## Rebuild from a v5 Indy

Use a writable overlay of the CD 4 v5 Indy for the chosen release and
extract that release’s optional Mozilla payload at the guest root.
Install the stack-guard pair’s native `/netbsd` and `/netbsd.boot` and
the signal-wait module at
`/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod`.
Cold-boot and verify the module hash in the qualification record. After
a clean halt, flatten the overlay with
`chdman copy -i overlay.chd -ip parent.chd -o standalone.chd -c zlib -np 2` and run `chdman verify -i standalone.chd`.
Use a fresh writable overlay for the browser tests. [Browser import procedure](2026-11-24-indy-mozilla.md#build-the-matching-payload) ·
[Matching kernel and boot file](2026-11-25-irix-stack-guard.md) ·
[Module build helper](../../lab/ip28-kernel/build-module.sh).
