# Mozilla input, SGI Clock and the two system meters

We cold-booted private copies of the November 25 catalog disks and their saved
desktop overlays. We logged in through xdm as `xiritest`. The two images use
different CPUs, vendor browsers and user profiles, so this comparison does
not isolate which difference causes the freeze. [Disk hashes and launchers](2026-11-25-webjumper-homepage.md#try-the-prepared-images).

| Program | 6.5.22f Indy R4400 | 6.5.30f Indy R5000 |
| --- | --- | --- |
| Mozilla, Applications tab | The welcome page painted. The File menu did not appear and the address bar still showed the homepage after typing a different URL. [Capture after input](2026-11-25-mozilla-input-6.5.22f.png) | The saved catalog opened on DesktopTools. Selecting Applications revealed **Mozilla**, **jot**, **mozilla** and **nedit**. Double-clicking **Mozilla**, typing a local URL and then opening File displayed the second document and its menu. [Menu and document](2026-11-25-mozilla-input-6.5.30f.png) |
| SGI `clock`, DesktopTools | Working in the user's manual test. | Running `/emul/irix/usr/sbin/clock` in winterm opened a 100×100 analog clock at the upper left. Its hands advanced. The larger clock at the upper right was the session's `xclock`. [Both clocks](2026-11-25-clock-manual-6.5.30f.png) |
| SGI `gr_osview`, DesktopTools | Exited with `can't open memory special file`. No window. | Same diagnostic and no window. On both releases the launch returned status zero. |
| SGI Freeware `xosview`, winterm | Absent on the disk. After installation the CPU and memory bars appeared. [Meters](2026-11-25-xosview-cd4-6.5.22f.png) | Absent on the disk. The installed program displayed both meters. [Meters](2026-11-25-xosview-cd4-6.5.30f.png) |

## Where 6.5.22f Mozilla stopped

The saved Navigator window was 1042×738. We clicked File and sent Escape,
Ctrl+L, a local file URL and Return through the emulator. After 40 seconds
the welcome page and its address were still visible. We repeated the check
with XTEST focus and key events, using a second document placed alongside the
welcome page. The frame still showed the original document. On 6.5.30f the
same second URL changed the title to **Xiri Input One - Mozilla**. Clicking
File displayed choices including **Open File** and **Print**.

On 6.5.22f the main thread was sleeping on `irixth` before the keystrokes.
The trace recorded activity on one worker and no system calls on the main
thread during input. On 6.5.30f the main thread was in `poll` and read 192
bytes during input. In the NetBSD fork, `sys/compat/irix_o32/irix_thread.c`
uses that condition variable for `PR_THREAD_BLOCK`. The next comparison is
the last block and its matching wake on original 6.5.22f. This run does not
identify a missed wake or qualify Internet browsing.

## Install Freeware xosview

The catalog bundle's first CD carries a subset of the May 2004 disc. The
original `fw_xosview` product is on full Freeware CD 4. A private supplementary
ISO is available at `.work/irix-freeware/xosview-cd4.iso` in the lab
checkout. Its SHA-256 is `0a3017566726579dbdb0f44e2a10752349658d72b0ec86ce57c8d76d5fa0d884`.
To recreate it from an owned disc, see the [installer recipe](../../lab/irix-installer/README.md#build-the-xosview-supplement).

From the checkout, launch the desired stopped guest with the supplement
as its second CD. Use `6.5.22f` in the launcher path for the R4400.

```sh
.work/images/xiri-indy-6.5.30f-catalog-20261125/run-iris.sh --cdrom5 "$PWD/.work/irix-freeware/xosview-cd4.iso"
```

As NetBSD root in the guest, run the following once per image.

```sh
mkdir -p /mnt/xosview
mount -r -t cd9660 /dev/cd1a /mnt/xosview
sh /mnt/xosview/xosview.sh /mnt/xosview
umount /mnt/xosview
```

In the logged-in desktop user's winterm, run:

```sh
xosview -xrm 'xosview*load: False' -xrm 'xosview*gfx: False'
```

The installer selects `fw_xosview.sw.xosview` in SGI `inst`. On both release
lines `inst` reported no conflicts, `versions` recorded the subsystem and the
installed executable had SHA-256 `0fd6a1f98b7dfdfeba2780d483edbe14eff930d8a936f1c4565bb8bc29434a22`.
The package installs the executable and X resources. It has no Icon Catalog
registration. The default load-average meter still requires RPC support.
[Earlier CPU and memory workload measurements](2026-11-24-indy-xosview.md).
