# Mozilla and Netscape on the Indy Applications page

The 6.5.22f original-media donor ships Mozilla 1.0.1. The 6.5.30f donor
ships Mozilla 1.7.12. Their launchers, shared libraries and browser data
are release-specific. The optional profiles record the donor and file
digests for each installation.

## Build the matching payload

For example, from the Xiri checkout on a host with guestfish and chdman:

```sh
release=6.5.22f
./xiri import \
    --profile "profiles/irix-${release}-mozilla-v1.json" \
    --source ".work/donors/irix-${release}-original-media/irix-donor.chd" \
    --output ".work/imports/irix-${release}-mozilla-v1"
```

Use `release=6.5.30f` for the other donor. The importer checks the source
and computes the ELF dependency closure. It emits a normalized
`payload.tar.gz` and a manifest of guest paths and hashes. The browser
data goes under `/emul/irix/var/netscape/mozilla`, and the vendor private
libraries go under `/emul/irix/usr/lib32/internal/mozilla`.
The import includes `libsocket.so` on both lines and `libz.so` on 6.5.30f.
The external Java plug-in and SDK utilities are outside these profiles.

## Install on a private v5 Indy copy

Use the same release as the installed desktop. Put the resulting archive on
guest-readable media. As root, extract it relative to the guest root:

```sh
tar xzpf /cdrom/payload.tar.gz -C /
ls -l /emul/irix/usr/bin/X11/mozilla
```

The expected link text is `../../../var/netscape/mozilla/mozilla`. The
vendor shell launcher follows it to locate `run-mozilla.sh`. Copying the
launcher as a regular file loses that information. The two original catalog
entries point to the launcher directory and the alias, respectively.

The R5000 also needs the updated NetBSD `compat_irix_o32` module.
Mozilla 1.7.12 is an n32 MIPS IV executable. The v5 kernel module rejects
it with `ENOEXEC` before the dynamic loader starts. Build the module from
the NetBSD fork’s `xiri` branch with the matching sgimips 11.99.11 tools:

```sh
sh lab/ip28-kernel/build-module.sh ../NetBSD-xiri /path/to/netbsd-tools /tmp/xiri-mozilla
```

Install `module/compat_irix_o32.kmod` from that build in the guest at
`/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod`
and reboot. The 6.5.22f browser is n32 MIPS III. The executable admission
change is NetBSD `xiri` commit `524cb15e140`.

## What the two Mozilla icons do now

With the release-matched payload, both the uppercase and lowercase launchers
reach the real browser process under xdm as `xiritest`. The 6.5.30f browser
created a 10×10 X window. Neither release displayed a usable Navigator
window or the requested local HTML page. Direct launch with an explicit
`file://` URL reached the same wait.

The foreign syscall trace captured the same sequence on both guests.
IRIX libc invokes `nsproc` (trap 1204) with flags `0x020000ff`.
The module returns IRIX `ENOSYS` (89). The browser then calls
`sginap` (1082) and retries, with successively longer delays. This accounts
for the live PID and the NetBSD `nanoslp` wait channel. GTK also logged a
failed `shmget` while starting up. Execution continued past that warning.

The mask combines `PR_SALL`, `PR_THREADS` and `PR_NOLIBC`. The existing
installer compatibility code implements a restricted two-process sproc
share group. A browser worker needs IRIX thread creation, a private PRDA
for each concurrent thread, and the thread lifecycle expected by libpthread.
A useful next regression is an original n32 program that creates a worker,
exchanges a value with it and joins it on both original IRIX and Xiri.

The [admission regression](../../lab/irix-mips4/README.md) passed all 24
cases. In the live R4400 guest, the 6.5.30f MIPS IV executable continued
to return `ENOEXEC`. The R5000 loaded the same executable and reached
the thread call. All 96 host tests passed. The [four decoded traces](2026-11-24-indy-browser-traces.json)
include the private payload and base image hashes. Local HTML rendering in
Mozilla remains unverified on the original donors as well.

## Netscape Messenger on 6.5.22f

`AboutNetscapeMessenger` and `NetscapeMail` are SGI WebJumper documents.
Only 6.5.22f has these two catalog entries. Build and extract the separate
[`irix-6.5.22f-communicator-v1` profile](../../profiles/irix-6.5.22f-communicator-v1.json)
using the import and guest extraction commands above. It includes SGI's
`launchWebJumper`, the local HTML documents, the Netscape wrapper and
the Communicator executable. The profile maps the donor's `/usr/bsd/head`
to `/emul/irix/usr/bin/head`. WebJumper reads the third line of the catalog
document with `head -3`. NetBSD's native utility could not open that path in
the IRIX filesystem.

With the original helper and the IRIX utility installed, tracing each
double-click recorded the final Netscape arguments. About passed
`file:/var/netscape/communicator/docs/AboutNetscapeMessenger.html` and Mail
passed `mailbox:`. Communicator created a user profile and 1×1 helper windows.
Before interval-timer support, its diagnostic was
`nspr: can't set interval timer: 89`. Both the browser and its DNS helper
were sampled inside `_PR_PutOnSleepQ`, called from `_PR_CondWait`. Disabling
asynchronous DNS alone produced the same timer diagnostic.

### Interval-timer results

NetBSD `xiri` commit `1d7a8b42efb` implements IRIX `getitimer` and
`setitimer` using NetBSD's process timers. We booted the two original
IRIX donors and the two Xiri Indys and ran the same o32 and n32 executables.
All four Xiri comparisons matched the 57 original output rows and the
one-shot SIGALRM termination status of 142. The checks include arming and
reading all three timer kinds, disarming, previous-value reporting, and
preserving state on errors. [Reproduction and reference output](../../lab/irix-time/README.md#interval-timers).

The tested module includes both the executable admission and timer changes.
Its SHA-256 is `f759f450b9a8fdab95b25f1e915764e3ae3d88b317a940b8347c80c8382f8b9b`.
The retained local build is `.work/modules/irix-browsers-20261125/compat_irix_o32.kmod`.
These experiments used private overlays of the published v5 CHDs.

On an independent graphical login on the original 6.5.22f Indy, SGI's
WebJumper opened its local page in a 720×892 Navigator window. The
screenshot shows the text and links under **About Netscape Messenger**.
[Original IRIX reference screenshot](2026-11-25-native-irix-netscape-about.png).

### What the Xiri user sees with the timer fix

| 6.5.22f icon | Cold-boot result |
| --- | --- |
| AboutNetscapeMessenger | Netscape starts with the correct local URL. The catalog retest allowed 96 guest seconds for the Navigator window. Only a 1×1 helper remained, with the browser and DNS helper each consuming about 50 CPU seconds. The local document did not appear. |
| NetscapeMail | The click creates a 475×600 **Netscape Message Center** window in the X tree and Netscape error dialogs. On screen, the dialogs are blank and the mailbox is unusable. [Xiri screenshot](2026-11-25-xiri-netscape-mail.png). |

A fresh direct launch with asynchronous DNS disabled confirmed that
`setitimer(ITIMER_REAL, …)` now returns success. Later in that same trace
the process repeatedly called `getpid` and sent itself IRIX signal 10
(SIGBUS). On the catalog launch, the browser sampled in libc's `_sigtramp`
and its DNS helper sampled in the NSPR sleep queue. A short trace of that
catalog process captured repeated SIGALRM deliveries and `sigreturn`. The
first cause of the direct launch’s SIGBUS remains open. The application also reported a failing `uname()` and
missing optional media plug-ins. The donor's Netscape X resource files
were already present in the base desktop import.
