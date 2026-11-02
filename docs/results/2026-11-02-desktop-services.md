# Desktop services, catalog contents and original Toolchest menus

Original Icon Catalog now discovers **18 visible pages** and lists the
**21 Freeware entries** from the supplied installation. Original FileManager
lists native files and folders. The unwanted Trusted Path panel is absent.
Native Xorg remains the display server. At the user's request, the custom
Toolchest Applications menu is removed; Desktop → Open Unix Shell and
Find → Icon Catalog retain their native launch bridges.

The [diagnostic PNG](images/2026-11-02-freeware-labels.png) shows the populated
Freeware labels with FileManager behind it; icon artwork is visibly missing.
The [machine-readable evidence](2026-11-02-desktop-services.json) records
the exact kernel, native daemon, trace calls, screenshot hash and clean halt.

The [kernel qualification](2026-11-02-irix-desktop-fs.md) covers the necessary
directory records, link metadata, readlink, poll and MAC query. Userspace also
needed a working File Alteration Monitor. The [native FAM build](../../lab/native-fam/README.md)
uses public FAM 2.7.0 and pinned pkgsrc patches, without changing vendor clients.
The original clients use TCP directly with RPC program/version **391002.1**;
version 2 negotiates an unsupported Unix-domain socket.

The first daemon crashed on its first polling pass. An old BTree iterator
called a child method through null, then checked `this` inside the method;
modern optimization removes that check. A local patch checks the child
before the call. The optimized host regression crashes before the patch and
passes afterward; the native NetBSD regression also passes. The second local
correction prints 64-bit `time_t` with the correct format.

Native FAM evaluates watch paths outside the IRIX emulation namespace.
Creating `/usr/lib/desktop -> /emul/irix/usr/lib/desktop` before starting the
clients makes the imported catalog visible to both sides. An already failed
watch does not recover merely when the alias appears: restarting Icon Catalog
was necessary in the diagnostic run. FAM logs then show `Exists`/`EndExist`
for the Freeware entries. Creating and deleting a native test file in the
desktop state directory produces real `Created` and `Deleted` notifications.

The development configuration binds FAM to loopback and maps untrusted
clients to the explicit native `xiritest` account at UID/GID 1234, with
`insecure_compatibility = false`. This is a single-user integration setup.
The persistent launcher owns FAM and any rpcbind it starts, and reaps them
when its reserved-UID desktop session ends. FAM's temporary effective UID
means it can also be killed by that existing session cleanup guard.

The [bitmap import](../../lab/irix-desktop-bitmaps/README.md) adds the observed
SGI toolbar resource directory as a separate payload delta. Its 48 files,
six aliases and destination modes are recorded without replacing the old
qualified application payload. Source media is mounted read-only. Fresh desktop observation confirms that
these assets restore the catalog toolbar glyphs; application artwork remains
a separate issue.

The [FileManager PNG](images/2026-11-02-fm-toolbar.png) shows the same restored
toolbar resources alongside the native `Examples` directory and `Readme.txt`.
The original Toolchest has its six menu headings and no custom Applications
entry. The diagnostic launch and cleanup evidence is hashed in the JSON record.

The complete upgrade run `ordinary-b02m61p7` passes two repeated Toolchest
shell launches with typed proof files, the original Find → Icon Catalog
action, Freeware discovery, FileManager startup, and native create/delete
notifications. Native execution and X controls pass, as do final hashes for
**1,749 staged regular files and ten installed native/configuration files**.
The reserved-UID guard reports `absent=1 valid=1`; session-owned FAM/rpcbind
and the launcher lock are removed. The guest halts cleanly and its base seed
is unchanged.

Earlier upgrade attempts remain failed harness runs: one incorrectly sent
a NULL RPC request to FAM's non-RPC wire protocol, and two checked the catalog
title before asynchronous discovery finished. Readiness now checks the
portmapper registration and waits for the actual page title after both
startup and reopening. Diagnostic follow-ups in those guests confirmed the
menu and file notifications, but do not relabel the failed automated runs.

Current display PNGs use IRIS's software framebuffer capture, retaining its
two PROM overscan columns. The big-endian XWD-to-PNG path reverses red/blue
relative to the composed display (an observed background pixel changes from
84,102,118 to 118,102,84). Raw XWD captures remain diagnostic artifacts; the
new image qualification preserves the framebuffer PNG byte for byte.

The promoted bundle is
`.work/images/xiri-netbsd-desktop-20261102-services/netbsd-xiri.chd`
(480,153,720 bytes, SHA-256
`fb0b8f3146a54800950e573ef204fd49f707aba9e0107c2b37e6eecab012ee48`).
Its complete 8 GiB extraction matches the stopped, qualified guest. The
[cold-boot qualification](2026-11-02-desktop-services-image.json) boots from
the CHD, verifies both kernel forms and persistent support files, observes
the 18-page catalog, checks native execution and cleanup, and halts cleanly.
The [PNG](images/2026-11-02-desktop-services-image.png) is an unchanged software
framebuffer capture. The first cold boot also passed its runtime checks but
produced a black capture because the compositor was selected before boot;
that image qualification was rejected. Selecting it after multiuser startup
fixes the capture, and the repeated cold-boot qualification passes.

The reusable raw seed is `.work/xiri-image/prepared-seed-20261102-services`.
The previous CHD and seed are retained. See the [manual guide](../XIRI-IMAGE.md)
for IRIS/Prismatic settings, boot switching and remaining desktop limits.
All owned IRIS test instances are stopped at completion.

Filetype artwork is **still absent**. A fresh 633,794-byte fm trace contains
2,417 foreign calls. It repeatedly opens `/usr/lib/filetype/desktop.otr`, then
calls `fcntl(fd, 13, ...)`, which Xiri rejects with EINVAL. The public historic
NetBSD compatibility header names command 13 `F_SETBSDLKW`. No database read
or iconlib lookup follows these opens. This is the next concrete compatibility
boundary to measure against the original system; treating the lock as a no-op
would not establish correct sharing or lifetime behavior. Other observed
unsupported calls remain in the trace and may become relevant afterward.

The fixed-width [ktrace reader](../../scripts/read-irix-ktrace.py) correlates
foreign entry/return records and pathname lookups. It handles indirect syscall
numbers explicitly; the guest o32 kdump cannot safely decode every native
LP64 structured user record.

Earlier bounded Xsgi investigation is deferred at the user's request. Valid
startup reached a 16 MiB shared AUTOGROW mapping after `.XsgiShmInfo9` and
exited on EINVAL. No graphics-device access was observed before that boundary.
The diagnostic guest halted cleanly with the source image unchanged. This
does not establish Xsgi suitability or replace the native Xorg path.
