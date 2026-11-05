# Native paging desktop image

The replacement image remains an unselected candidate after the
[native paging investigation](2026-11-05-native-paging.md). Its kernel gives
other processes CPU time between speculative pageout batches once free pages
plus submitted pageouts meet the minimum target. It also corrects the
big-endian `vm.swap_encrypt` boolean handler. Swap encryption remains enabled.

The preparation run `.work/xdm-image/prepare/ordinary-8yqldiep` boots directly
from disk into 1280×1024 xdm, loads `compat_irix_o32` at securelevel 1, verifies
the imported payload, checks native execution and halts cleanly. Against the
held cleanup candidate, its installed-file inventory changes only `/netbsd`
and `/netbsd.boot`; 1,281 other recorded files are unchanged. Relative to the
previous selected native-wait image, it also includes the already qualified
session-guard deadline correction.

The final kernel has passed the full 96 MiB desktop pressure workload in
`boot-wtpd08jl`: 800 native input round trips, 120 child launches, 24 existing
supervisor scenarios, three new process-state controls and 158 CD ABI checks.
Both IRIX sessions log out, the separate native ctwm user passes its input
checks, and the guest halts cleanly with a fresh IRIX session active. Earlier
failed candidates and diagnostic runs remain in the investigation record.

A reduced replay directly from the packaged CHD (`boot-8x8dm2rw`) also
passes: 60 native input round trips, 20 child launches, 16 existing supervisor
scenarios, two postcheck controls and 158 CD ABI checks under the same 96 MiB
allocation. It completes IRIX logout, native ctwm login and active-session
shutdown. Its archive passes the normal TCP transfer's guest/host SHA256 check.
This smaller replay supplements the full gate above.

The [build ledger](../../lab/native-paging/build.json) records the actual
parent revision and dirty patch used for compilation. The core is
`3cd6c8da5c9263b116927978b25b4b6a901dc66216aede41be1e3edb680eede6`;
the boot wrapper is
`5526f57cc6297c2b788b3eb1d15336fc0a863045645024866c0f05a4b68107a6`.
The IRIX module remains
`8e97285b0a2185c0b2b5a2ed6e4202dd9ec568a9ba1514ea45a569a8c4c1b366`.
The emulator remains the qualified IRIS `819c682` build; its newer integration
branch revision does not replace this tested binary.

The [packaging record](2026-11-05-native-paging-packaging.json) verifies an
independent full-disk CHD decode against the halted preparation disk. The
local bundle is `.work/images/xiri-netbsd-desktop-20261105-paging/`; its CHD
contains an 8 GiB disk compressed to 496,159,017 bytes, with SHA256
`921ec9e53f1061b9763ae4ec307d12d9b1f5b3b759734832921c8df7154a8d10`.
Temporary memory storage held the independent decode; the final raw cache
is a hash-verified reflink of the preparation disk. Existing qualified disk
artifacts were preserved. The cache-reclamation ledgers under
`.work/native-sleep/` record regenerable C object files and Rust incremental
compiler caches removed to make room. Removing the latter restored about
9 GiB of free space after the user reported low `/var` space. The subsequent
user-requested cleanup removes Cargo dependency build caches and four older
decoded CHD caches after verifying their hashes against the retained CHDs.
The [cleanup ledger](2026-11-05-workspace-cleanup.json) records the removed
paths and restoration commands. Kernels, modules, emulator binaries, compressed
CHDs, manual overlays, debug symbols, source and test evidence remain intact.

Forced encrypted swap readback passes separately, but a fresh timing run
crashes the kernel during desktop startup under 96 MiB pressure. The
[investigation](2026-11-05-native-paging.md#packaged-image-kernel-crash)
retains the fault and complete emulator snapshot. Both bounded follow-up
comparisons pass; further crash investigation is deferred at the user's request.

The [cold desktop qualification](2026-11-05-native-paging-cold.json) passes
in `ordinary-ym1w5eag`: full-screen xdm, three IRIX sessions, the separate
native ctwm user, both desktop logout routes, failed-start recovery, shell
job control and Icon Catalog double-click launch. All five font phases pass
69 native text cases and six Courier metric cycles each. The CHD is unchanged
and shutdown is clean. The [desktop PNG](2026-11-05-native-paging-cold.png)
shows the successful catalog launch. The Toolchest customization menu capture
also has readable labels during visual review.

Cold qualification is recorded independently of the unresolved pressure
startup fault. This cycle does not promote the candidate or change its bundle
manifest. The current manual image and its user-owned overlay/NVRAM remain
intact. All owned test IRIS instances were stopped at the final checkpoint.
