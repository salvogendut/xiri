# Bringing Xiri support into NetBSD

[Back to README](../README.md) · [Architecture](ARCHITECTURE.md) ·
[Fork workflow](FORKS.md) · [Module build](../lab/irix-module/README.md)

Audit date: 2026-11-14. **The loadable module works on our fork, but it still
depends on three changes to the core kernel.** Upstreaming those interfaces,
the relevant native fixes and the module would make a standard compatible
NetBSD/MIPS kernel a realistic delivery target. It would not make IRIX MIPS
binaries run directly on an x86 or ARM NetBSD machine.

NetBSD's development branch is `trunk`/NetBSD-current. Its GitHub `src`
repository is a CVS mirror and directs patches to GNATS. We should prepare
reviewable patch series for the relevant maintainers; merging our Git branch
into the GitHub mirror is not the submission procedure.
[Official source mirror](https://github.com/NetBSD/src),
[contribution instructions](https://www.netbsd.org/contrib/).

## Audited sources and scope

The audit compares NetBSD `xiri` at
`8bf86afce2afede752c0eae37852e2f2472d91cb` with the common upstream base
`da076c20ff0f5e9b8940891552eddf1a4f99dbac`. The official `upstream/trunk`
reference was refreshed to `df656f186a9c7c00fe9a9aa8b3f7325871fd008b`.
The accompanying [audit ledger](results/2026-11-14-netbsd-upstream-audit.json)
lists the changed paths. This cycle's additional `symlink`/`utimets` work is
inside `sys/compat/irix_o32/irix_o32.c`; it adds no core interface. The subsequent
Keyboard-panel work also stays in this file: n32 executable data on a 4 KiB
boundary uses NetBSD's existing `vmcmd_map_readvn` implementation. It adds no
change to the native ELF loader or to the core dependencies listed below.

There are 176 changed paths in the committed fork delta, dominated by the
separate XFS work. Among the core files discussed below, newer upstream
changes also move `p_pgrp` within `struct proc` in `sys/sys/proc.h`.
A source audit does not establish that a rebased kernel builds or runs.
Keep the qualified artifacts pinned and test a separate current-tree build.

All `sys/`, `tests/`, `share/` and `usr.sbin/` paths below are relative to
`../NetBSD-xiri`. Xorg driver paths belong to the separate NetBSD **xsrc**
tree. The [current image pointer](../lab/irix-installed-desktop/image.json)
distinguishes the installed core, module and emulator: a module's newer
source revision does not mean every core change in that branch is installed.

## The three required core interfaces

These are the direct dependencies of the present personality implementation.
Each needs upstream acceptance or an alternative implementation before the
module can be delivered for an otherwise standard kernel.

| Interface | Exact files and functions | Why Xiri needs it | Upstream work |
| --- | --- | --- | --- |
| Select over kernel-owned masks | `sys/kern/sys_select.c`: `selcommon_kern()`; declaration in `sys/sys/select.h` | IRIX has different fd-set copyout, timeout and ready-descriptor counting rules. The module prepares its own masks, uses the native scan/wait protocol, then applies IRIX result semantics. | Review the helper's ownership, sizing and timeout contract; test native select regressions and foreign alias/error cases. Keep IRIX ABI translation in the module. |
| Refresh an emulation-managed signal mask before returning to userspace | `sys/sys/proc.h`: `struct emul.e_sigmask`; `sys/kern/kern_lwp.c`: `lwp_userret()` | IRIX pthread initialization lets libc update its hold mask in the user PRDA without a syscall. The callback `irix_prda_sigmask()` copies and translates that mask before native pending-signal delivery. | Review callback placement, locking, user-memory faults and cost. This changes `struct emul` layout: rebuild affected modules and test other emulations and minimal-emulation configurations. Agree the API with kernel maintainers. |
| Personality-specific continued-child notification policy | `sys/sys/proc.h`: `EMUL_NOCLDSTOP_CONT`; `sys/kern/kern_sig.c`: `child_psignal()` | For IRIX, `SA_NOCLDSTOP` suppresses continued-child notifications as well as stops. The flag applies this before queuing a signal; discarding it later would still cause wakeups or overwrite pending status. | Review the opt-in policy and test stop/continue/exit combinations. Preserve native NetBSD behavior for personalities without the flag. |

The module already uses existing `exec_add()`/`exec_remove()`, `execsw`,
`e_syscall_intern` and native VFS/socket/VM interfaces. Its syscall table,
ELF recognition, argument conversion, signal frames, PRDA and sproc support
live in the personality. **There is no current need to patch the global
native syscall table or introduce an IRIX desktop daemon into the kernel.**

The MIPS kernel-object loader at `sys/arch/mips/mips/kobj_machdep.c` is audited
by our build, but it has no Xiri patch in this comparison. Its existing N64
restriction is why module delivery currently targets `mips64eb`. A 32-bit
kernel uses the built-in personality; 32-bit module loading would be a
separate loader project.

## Native fixes and platform support

These are ordinary NetBSD changes exposed by the workloads. They belong in
independent fixes, with native reproducers, rather than being hidden inside
the IRIX module.

| Change | Source locations | Role and current evidence |
| --- | --- | --- |
| MIPS FPU state after signal return | `sys/arch/mips/mips/mips_fpu.c`, `fpu_discard()` | Retain valid replacement FPU state after discarding live registers. Fixes native X server Type1 font failures. [Register, conversion and font evidence](results/2026-11-05-type1-scaler.md). |
| Child wait accounting and scanning | `sys/kern/kern_exit.c`, `find_stopped_child()`; regressions in `tests/lib/libc/sys/t_wait.c` | Consuming continuation must not decrement the stopped-child count; scans must still find continued children when that count is zero. [Native wait evidence](results/2026-11-05-native-wait.json). This is separate from the IRIX SIGCHLD flag above. |
| NetBSD32 CD9660 mount arguments | `sys/compat/netbsd32/netbsd32.h`, `netbsd32_fs.c`, `netbsd32___mount50()` | Translate UID/GID and file/directory masks, preserving old argument lengths and GETARGS behavior. Fixes inaccessible CD files for ordinary users. [158 CD ABI checks](results/2026-11-04-system-stability.md). |
| Contiguous-page allocation lower bound | `sys/uvm/uvm_pglist.c`, `uvm_pglistalloc_contig_aggressive()` | Reject an alignment-rounded start below the usable lower bound. [Allocator reproduction](results/2026-11-03-uvm-pglist.md). |
| LP64 calls into o32 ARCS firmware | `sys/dev/arcbios/arcbios_calls.S` | Save full N64 registers and use low-memory KSEG0 aliases for the IP2x firmware stack/arguments. Needed by the tested 64-bit Indy platform. The implementation assumes low RAM below 512 MiB; review machine/firmware gating and test other ARCS users before upstreaming. |
| Swap-encryption boolean sysctl | `sys/uvm/uvm_swap.c`, `sysctl_kern_uvm_swap_encrypt()` | Use correctly sized boolean storage and an atomic read on the big-endian path. [Native controls](results/2026-11-05-native-paging.md). |
| Speculative pageout scheduling | `sys/uvm/uvm_pdaemon.c`, `uvmpd_scan_queue()` | Let other LWPs run between batches once free/pending pages meet the target. This is a scheduling policy change requiring broader review, not a module prerequisite. [Measured results and unresolved candidate limits](results/2026-11-05-native-paging-image.md). |

The selected desktop uses the qualified native-wait core. The later pageout
policy/swap-sysctl candidate remains unselected; its source being on `xiri`
does not turn it into a release prerequisite or close its recorded limits.

Native userland also has a small independent fix in
`usr.sbin/rpcbind/rpcbind.c`: `init_transport()` avoids adding a duplicate
loopback address when `-h` already names it. That removes the duplicate-bind
messages seen during desktop startup. It is not a kernel dependency.

## What must be prepared for the module submission

The implementation is in `sys/compat/irix_o32/`:

| Files | Responsibility |
| --- | --- |
| `irix_o32.c` | ELF/ABI admission, exec lifecycle, private syscall table and adapters, PRDA initialization, module registration |
| `irix_signal.c`, `irix_signal.h` | Foreign signal delivery and return |
| `irix_sproc.c`, `irix_sproc.h` | Bounded shared-process groups, fork/exit state and private PRDA behavior |
| `irix_tty.c`, `irix_tty.h` | Terminal attributes, session and process-group translation |
| `irix_errno.h`, `irix_errno_map.h`, `irix_stat.h` | Foreign errors and measured data layouts |

Existing build wiring adds `COMPAT_IRIX_O32` and its source files to
`sys/arch/mips/conf/files.mips`, adds the module to `sys/modules/Makefile`
for `mips64eb`, and builds it through
`sys/modules/compat_irix_o32/Makefile`. Registration uses
`MODULE_CLASS_EXEC`, with `exec_elf32` and `compat_netbsd32` dependencies
on N64. The name supports **both o32 and n32 applications**; agree the
public module/option naming during review.

Before proposing inclusion:

1. Agree a maintained compatibility scope. The working subset is measured
   against IRIX 6.5.22m; it is not complete IRIX, full sproc semantics,
   arbitrary IRIX versions or foreign N64 application support.
2. Review the large adapter file and syscall definitions against NetBSD's
   compatibility-code conventions. Decide the appropriate split and generated
   metadata with maintainers. Replace the historical lab diary in the kernel
   README with a concise implementation/support description.
3. Add normal documentation, including a proposed
   `share/man/man8/compat_irix.8` and the option description in
   `share/man/man4/options.4`. Document required native configuration and
   unsupported behavior.
4. Add module distribution-set entries: inspect
   `distrib/sets/lists/modules/ad.mips` and the appropriate machine list, with
   gating that matches big-endian N64 support. The current fork has the
   Makefile wiring but no IRIX entry in those lists. Validate an actual
   release/sets build, not only a standalone `.kmod` build.
5. Keep matching kernel/module builds and verify exported imports and
   relocations. The lab's `COPY_SYMTAB` setting supplies symbols for its
   direct-PROM boot path; review normal bootloader symbol delivery separately.
   It is not a new IRIX loader hook.
6. Port suitable independent probes into the NetBSD test tree. Keep original
   IRIX binaries and disk images out of the source/test distribution. Retain
   measured reference records and make vendor-runtime tests explicitly optional.

## Display, XFS and session work have separate destinations

- **Newport Xorg acceleration/text fixes:**
  `xsrc/external/mit/xf86-video-newport/dist/src/newport_accel.c`.
  Our [texture patch](../lab/newport-xaa/texture-coordinates.patch) and
  [fallback-refresh patch](../lab/newport-text/shadow-fallback.patch) are
  maintained here as patches against a pinned xsrc revision. They are **not
  included by merging the NetBSD src branch**. They need their own xsrc/driver
  review and native rendering tests. [Driver guide](NEWPORT.md).
- **Console themes/frame and GR2:** `sys/arch/sgimips/gio/newport.c`,
  `newport_frame.h`, `files.gio`, `grtwo.c`, `grtworeg.h`; shared
  `sys/dev/wscons/{wsconsio.h,wsdisplay.c,wsdisplayvar.h,wsdisplay_vcons.c,wsdisplay_vconsvar.h}`;
  `usr.sbin/wsdecorctl/`, `etc/rc.d/wsdecor`, associated configuration,
  set lists, documentation and artwork. The module does not depend on these.
  Review genuine driver fixes separately from optional console appearance
  and new wscons ioctls; do not require a decorated console to run Xiri.
- **XFS/PUFFS:** `external/gpl2/xfs/` and
  `lib/libpuffs/dispatcher.c` form separate filesystem/userland work.
  The PUFFS changes translate access bits and reserve buffers for extended
  attributes. The desktop runs from ordinary files on FFS and does not require
  an XFS kernel filesystem. Audit this much larger series on its own.
- **Services and sessions:** [`runtime/`](../runtime/README.md), native FAM,
  xdm configuration, the IRIX runtime importer and desktop resources belong
  in userland packaging. A pkgsrc-based package is a possible delivery route;
  deciding that does not require additional kernel hooks. Native authentication
  and per-user HOME/group handling remain outside the personality.
- **IRIS and Prismatic:** emulator/frontend changes stay in their own
  repositories. They support development and testing; physical compatible
  MIPS hardware would not need these host programs.

## Acceptance work and submission order

First resolve contribution provenance and the submission route. NetBSD's
current commit guidelines require **prior written approval from core for
LLM-generated code**. This project has AI-assisted implementation, so that
requirement needs explicit handling; successful tests or human review alone
do not constitute that approval. Retain original source/license notices and
document historical NetBSD derivation and independent ABI observations.
[NetBSD commit guidelines](https://www.netbsd.org/developers/commit-guidelines.html),
[our historical source audit](results/2026-10-30-irix-compat-audit.md).

Then prepare small series in this order:

1. Native bug fixes with self-contained failing/passing tests: FPU state,
   child waits, CD arguments, allocator bounds, rpcbind and the sysctl fix.
   Keep pageout scheduling policy in its own discussion.
2. The three emulation interfaces and the required sgimips firmware support,
   reviewed with the relevant kernel/port maintainers.
3. The personality, build/sets integration, manual page and independent tests.
4. Xsrc driver fixes and userland packaging; optional console/XFS series can
   proceed independently.

For each accepted series, rebuild against current NetBSD sources. Test
native behavior on an unaffected architecture as well as MIPS; exercise
kernel configurations with and without the personality. For the generic
signal hooks, include other emulations and native stop/continue behavior.
For the module, repeat absent-module execution failure, boot loading at
normal securelevel, genuine busy-unload refusal, unload/reload, o32/n32 ABI
probes, native controls, both IRIX accounts and a native ctwm login. Add
physical Indy/compatible-hardware validation before broad hardware claims.

Our lab gives useful regressions, but it does not yet prove a complete
current-tree release build, cross-architecture regression coverage, physical
hardware acceptance or upstream approval. Existing lab tests should become
repeatable upstream tests where possible; native tests must not require
proprietary IRIX installation media.

The first concrete upstream deliverable should be a small native-fix series
plus an interface proposal for the three hooks. The desired end state remains
a boot-loaded IRIX module, separately installed userland services/runtime,
and an ordinary authenticated X session on a compatible standard NetBSD system.
