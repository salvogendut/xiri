# Loading a library with a live IRIX pthread

Both original Mozilla icons on the 6.5.30f Indy now load
`/var/netscape/mozilla/components/libnsappshell.so`. The previous module
returned IRIX EOPNOTSUPP (122) on that call. On the same guest and kernel,
the new module maps it at `0x04758000`. The browser still exits before
displaying the local page. [Release pins and measurements](2026-11-25-threaded-elfmap.json).

## Kernel change and regression checks

A per-process lock serializes ELF placement, address-space limit accounting
and rollback with other ELF loads and ordinary mmap insertions. A worker
can load libraries in its own process. Fixed replacement, unmapping, heap
changes and the separate sproc share-group rules retain their existing guards.
NetBSD commit `8ace81118ab` changes the IRIX module and uses the kernel from the
[worker qualification](2026-11-25-nsproc.md).

On both the R4400 with 6.5.22f and the R5000 with 6.5.30f, a freestanding
n32 parent and worker requested the same two-segment image eight times.
All eight calls received EOPNOTSUPP on the baseline module. On the candidate,
one received the preferred address and the rest relocated. Each mapping
executed the expected code and had its own writable data and zero BSS.
A rejected request preserved all eight private markers. Five additional
untraced runs passed on each Indy. The SGI pthread create/join controls
also passed for xiritest and for root with explicit system scope.

A separate qualification build returned EIO while reading the data tail,
after the kernel had mapped the text and allocated the tail. The next
valid load obtained the same requested address, and the eight existing
markers survived. The regular o32 and n32 single-thread controls also passed
on each candidate for partial data, repeat loading, an occupied gap and an
occupied writable segment. [Fixture and reproduction](../../lab/irix-elfmap-relocation/README.md#mapping-while-an-n32-worker-runs).

## Mozilla under xdm

Each guest used its own release-matched browser payload and a normal xiritest
login. We double-clicked both original entries on Applications, observed the
X window tree, and traced their descendants. A separate launch through the
SGI shell requested a local file titled **Xiri local ELF map test**.

| Browser | Catalog launches | Direct local URL |
| --- | --- | --- |
| 6.5.30f, Mozilla 1.7.12 | Both mapped `libnsappshell.so` after thread creation. The uppercase and lowercase launches recorded six and seven successful ELF maps respectively after the worker started, including the app shell. A 10×10 startup window appeared briefly. | Six successful maps after worker creation. Eleven `break` requests returned EOPNOTSUPP. The wrapper reported a memory fault and exited 139. |
| 6.5.22f, Mozilla 1.0.1 | Both launched and retained the ENOEXEC failures for `libucvibm.so` and `libucvko.so` before worker creation. | Sixteen `break` requests returned EOPNOTSUPP. The wrapper reported a memory fault and exited 139. |

The local page did not appear on either line. The kernel still requires a
single, unshared mapping for IRIX `break` (trap 1017). A small worker-live
heap-growth test can isolate that rejection and verify resource limits and
mapping preservation. The traces establish the ordering of the rejected
calls and the later faults. Their causal relationship remains open.

For an Indy lab update, use the same v5 release-specific private copy, kernel
and optional browser payload as in the worker qualification. Build the current
module using `lab/ip28-kernel/build-module.sh`, install it in
`/stand/sgimips/11.99.11/modules/compat_irix_o32/` and cold boot. Both guests
loaded the production module at securelevel 1. All 210 module imports resolved
against the matching kernel, and all 96 host tests passed. The tested
production pair is available locally at
`.work/modules/irix-threaded-elfmap-20261125/indy-kernel-module.tar.xz`.
The release-specific v5 CHDs and NVRAM passed their original hash checks
after the private overlays were shut down.
