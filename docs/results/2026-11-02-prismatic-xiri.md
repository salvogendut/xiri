# Prismatic boots the Xiri CHD

The existing `../prismatic/target/release/prismatic` release binary boots a
disposable copy of the prepared NetBSD CHD to multiuser. The native o32
control prints its expected marker and exits 37. The installed launcher
opens original IRIX windows on native Xorg/Newport, including a visible
winterm native-shell prompt. No emulator or kernel source change was needed.

[The result](2026-11-02-prismatic-xiri.json) records the binary/configuration
hashes and raw evidence. The checkout context was Prismatic `main`
`7b9f8e563ab865022b6de93543232d5dd512a331` and its existing IRIS dependency
`perf/sgiemu-port` at `66f5a59be8b455eaaaa5299947a97ab59d17919f`. The existing
binary was tested without rebuilding; checkout revisions are context, not
a new build provenance claim. Neither source checkout was changed.

The test used Indy IP24, R4400, 256 MiB, Newport, SCSI ID 1, interrupt
deferral, separate NVRAM and a disposable CHD overlay. An isolated X11
host display ran the actual SDL frontend. The first harness attempt could
not identify its window; that PROM-only instance was stopped. The corrected
attempt explicitly selected SDL's X11 driver and completed the boot.

The user independently booted the image in Prismatic after changing only:

```text
setenv osloader boot
setenv osloadfilename netbsd.boot
setenv osloadoptions auto
boot
```

The existing partition variables already selected the correct disk. A
missing-sash error therefore identified stale IRIX PROM settings, not a
missing NetBSD bootloader. Prismatic has its own configuration/state files;
selecting a CHD does not load the accompanying standalone `iris.toml` or
NVRAM. The [image guide](../XIRI-IMAGE.md) now includes both the short fix and
full partition setup, a Prismatic configuration, and instructions to return
to IRIX. Direct volume-header inspection of the supplied IRIX disk confirms
its loader name is `sash` and its boot file is `/unix`.

The [frontend PNG](images/2026-11-02-prismatic-xiri.png) preserves the PPM's
pixels. It shows the native shell prompt and an Icon Catalog warning that
customization panels cannot communicate with it. Unused framebuffer borders
and incomplete/overlapping repaint are also visible. This is a boot and
startup observation, not a clean desktop/display acceptance result; the
catalog warning needs separate investigation.

After the bounded session, no reserved-UID clients remained. NetBSD synced
and unmounted its filesystems and returned to the PROM; Prismatic exited
zero through its quit dialog. The harness waited for the wrong literal
`halted`, while this kernel prints `halting...`, so its raw Boolean is false.
The qualification explicitly checks the complete shutdown transcript rather
than silently rewriting that observation. The base CHD was unchanged.
Only the owned test instance was stopped; the user's independent instance
was left running.
