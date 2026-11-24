# xosview CPU and memory meters on the two Indy releases

The original SGI Freeware n32 xosview opens on the R4400 Indy with IRIX
6.5.22f userspace and the R5000 Indy with 6.5.30f userspace. Each ran its
own release libraries and xdm desktop. The NetBSD `xiri` module at
`a38466f4ead2` supplies real CPU time and memory counts. The Freeware
binary was staged for the tests. The published CD 4 v5 images still use
their previous module and package selection.

To reproduce on a private v5 copy, build the module with
`sh lab/ip28-kernel/build-module.sh ../NetBSD-xiri /path/to/netbsd-tools /tmp/xiri-meter-build`.
Copy `module/compat_irix_o32.kmod` from the build directory to
`/stand/sgimips/11.99.11/modules/compat_irix_o32/compat_irix_o32.kmod`
in the guest and reboot. Run the original Freeware executable in the
logged-in desktop session.

| Guest | User CPU, idle → busy | Free RAM lost under load | Free RAM recovered after exit | Captures |
| --- | --- | --- | --- | --- |
| 6.5.22f, Indy R4400 | 2.7% → 91.9% | 24.7 MiB | 23.8 MiB | [Idle](2026-11-24-xosview-6.5.22f-idle.png) · [Busy](2026-11-24-xosview-6.5.22f-busy.png) · [Desktop](2026-11-24-xosview-6.5.22f-desktop.png) |
| 6.5.30f, Indy R5000 | 2.5% → 93.7% | 24.7 MiB | 23.9 MiB | [Idle](2026-11-24-xosview-6.5.30f-idle.png) · [Busy](2026-11-24-xosview-6.5.30f-busy.png) · [Desktop](2026-11-24-xosview-6.5.30f-desktop.png) |

The native workload touched 24 MiB and kept one CPU busy for 40 seconds.
We sampled the same mapped window and the IRIX counters before, during
and after it ran. On both releases, more than 5,000 CPU graph pixels and
816 memory bar pixels changed from idle to busy. Both bars changed again
after exit. The percentages above use the user-time delta divided by the
total CPU-time delta over six-second sampling intervals.

## What the original systems returned

The same [syscall probes](../../lab/irix-sysmp/README.md) ran as o32 and
n32 executables on the installed IRIX 6.5.22f Indy (128 MiB) and IRIX
6.5.30f O2 (256 MiB). Both returned 280 bytes for system activity and 48
for real memory. Reads accepted short prefixes, capped oversized copies
at the record boundary and left a zero-length destination untouched.
An invalid CPU or a per-CPU real-memory request returned `EINVAL`.
A negative length returned `EFAULT`.

Xiri reproduces these checks for both ABIs. CPU counters use 100 Hz IRIX
units. User time includes nice time. The memory record uses NetBSD's own
page size, 8192 bytes on these Indys, for free, physical, available and
file-cache page counts. The original IRIX machines used 4096-byte pages.
IRIX-specific activity fields without a NetBSD equivalent are zero.

The binary also calls the IRIX hardware inventory interface for the total
memory used to scale its graph. Both vendor ABIs use 24-byte inventory
records. Xiri supplies the main-memory record and both 256 MiB Indys
reported 256 MiB. The original systems reported a longer device list.

## Remaining meter

With its default resources the original executable mapped a 400×140
window. Its separate load-average meter printed `rstat: Socket type not
supported`. The IRIX socket implementation currently supports stream
sockets. The load-average value in that view is unqualified. We also
opened a CPU-and-memory-only view on each desktop with an empty diagnostic
log using the following X resources.

```sh
xosview -xrm 'xosview*load: False' -xrm 'xosview*gfx: False'
```

Both private images subsequently cold-booted with the new module and
reported clean unmount and halt. That last boot used a fresh monitor
connection because the changing framebuffer had timed out during a
screenshot wait in the graphical run. Both original donors shut down
cleanly, and the published CHD and NVRAM digests still matched.

[Measurements and binary digests](2026-11-24-indy-xosview.json) ·
[Earlier startup failure](2026-11-24-indy-link-clock-xosview.md) ·
[Applications tab results](2026-11-24-indy-applications.md)
