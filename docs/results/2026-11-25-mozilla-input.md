# Restoring Mozilla keyboard and menu input on IRIX 6.5.22f under Xiri

Mozilla 1.0.1 could finish drawing the welcome page on the R4400 Indy and
then ignore the keyboard and mouse. The missing operation was delivery of
SGI's private pthread interrupt, `SIGPTINTR` (47), to Mozilla's event worker.
Updating the NetBSD compatibility module restored the File menu and address
bar. The browser, SGI libraries and profile were kept in place.
[File menu on the second typed document](2026-11-25-mozilla-repaired-6.5.22f.png).

## What the traces showed

On the stock November 25 catalog module, Navigator froze with both the saved
6.5.22f session and a fresh profile. Two threads sent `PR_THREAD_KILL` to
IRIX worker ID 3 with signal 47. Xiri returned `EOPNOTSUPP` (IRIX errno
122). The receiver was sleeping in `__sigpoll` with mask words
`00000000 00004000 00000000 00000000`, waiting for that signal alone.
The main thread then slept in `PR_THREAD_BLOCK`. The browser still had a
PID and a polling thread. [Original freeze and screenshot](2026-11-25-indy-interaction.md#where-6522f-mozilla-stopped).

On the original-media IRIX 6.5.22f Indy, the same browser opened File and
accepted a typed local URL. SGI's `par` recorded the browser installing a
`SA_SIGINFO` action for 47 before its first worker was created. The following
sequence was observed repeatedly during input. Times are relative to one
capture attached to the working browser.

| Time | Thread | Observed call |
| --- | --- | --- |
| 5160 ms | Event worker | Enters `sigpoll([47], info, NULL)` |
| 5161 ms | Sender | `PR_THREAD_KILL(3, 47)` returns 0, then enters `PR_THREAD_BLOCK` |
| 5177 ms | Event worker | Wait returns 47, with `info.signo = 47`. Starts a 13.8 ms timed wait |
| 5192 ms | Event worker | Timed wait returns EAGAIN. Starts waiting again |

Five small n32 programs established which behavior to implement. On
original 6.5.22f and both updated Xiri Indys, the default disposition
accepted the send and both waits timed out. With the handler installed and
47 blocked in the target, an early send remained pending for the worker.
A delayed send also delivered exactly once. The traditional SIGUSR1 control
still returned 16 once. All five programs exited zero on all three machines.
[Probe sources, build flags and expected results](../../lab/irix-pthread/README.md#event-workers-address-based-waits-and-stack-guards).

## What changed and how it was tested

NetBSD `xiri` commit `18746c8d997` maps SGI's directed pthread interrupt to
a native realtime signal. The module checks the target ID, honors the
disposition and uses NetBSD's per-LWP signal delivery. It carries bit 47
through IRIX signal sets, the worker's private PRDA mask and signal frames.
The browser's synchronous event-worker path was exercised here. General
asynchronous handler behavior and thread-control operation 8 remain open.

We booted private copies of both November 25 catalog disks, installed the
same module, rebooted, logged in as `xiritest` through xdm and launched SGI
Mozilla from winterm. In each browser we opened File, entered two distinct
local URLs and verified both document titles. On the R5000, typing once
went to the page's find function. Ctrl+L focused the address bar and the
second document loaded. On 6.5.22f we also quit the browser, double-clicked
**Mozilla** in the Applications tab and repeated both URL changes. The File
menu opened over the second page. The 98 Xiri host tests passed. Internet
connections, TLS and long browsing sessions remain untested.
[6.5.22f menu and document](2026-11-25-mozilla-repaired-6.5.22f.png) ·
[6.5.30f menu and document](2026-11-25-mozilla-repaired-6.5.30f.png).

## Apply the update to a November 25 catalog Indy

The local update ISO contains the tested module and the five test programs.
It works with the **6.5.22f R4400** and **6.5.30f R5000** November 25 catalog
bundles running NetBSD **11.99.11**. Both base CHDs still have their original
module. From the Xiri checkout, with your guest powered off, start it with
the update CD. Substitute `6.5.30f` for the other Indy.

```sh
.work/images/xiri-indy-6.5.22f-catalog-20261125/run-iris.sh --cdrom5 "$PWD/.work/modules/irix-mozilla-input-20261125/mozilla-input.iso"
```

In the guest, run the following as NetBSD root. The original module is
backed up alongside the replacement on the first installation. Reboot to
load it.

```sh
(
    set -e
    mod=/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod
    mkdir -p /mnt/mozilla
    mount -r -t cd9660 /dev/cd1a /mnt/mozilla
    test "$(sha256 -q /mnt/mozilla/compat_irix_o32.kmod)" = 38873c2f84ef23bf50e263b833ebf6ce3077482ed770d061ffdc7ee83fcddcb4
    test -f "$mod.pre-mozilla-input" || cp -p "$mod" "$mod.pre-mozilla-input"
    install -m 444 /mnt/mozilla/compat_irix_o32.kmod "$mod.new"
    mv "$mod.new" "$mod"
    umount /mnt/mozilla
    reboot
)
```

At xdm, log in as `xiritest`. In **Icon Catalog → Applications**, double-click
**Mozilla**. Open **File**, press Escape, then press **Ctrl+L**, type
`about:mozilla` and press Return. On 6.5.22f this displayed **The Book of
Mozilla, 3:31**. [Screenshot](2026-11-25-mozilla-book-6.5.22f.png).

To roll back, copy `compat_irix_o32.kmod.pre-mozilla-input` back over `compat_irix_o32.kmod` in
the same module directory and reboot.

The ISO SHA-256 is `169f8a6519626a2c177772a7ad98f080fd391841e08c98fb2246d39497e6eaf4`.
A fresh build from the NetBSD checkout produced identical executable
`.text`. The module on the ISO is the exact binary loaded by both guests.
[Build helper](../../lab/ip28-kernel/build-module.sh) · [Base disk hashes](2026-11-25-webjumper-homepage.md#try-the-prepared-images).
