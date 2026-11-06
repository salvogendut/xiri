# Xiri execution roadmap

Status: updated 2026-11-06. The current image runs the original 4Dwm desktop,
Toolchest, Icon Catalog, File Manager, winterm and xclock on NetBSD/Xorg with
accelerated Newport. Catalog launching, running-icon feedback, backdrop,
desktop icons and logout pass bounded checks; the latest xmahjongg texture
repair passes native pixel comparisons and desktop interaction checks.
Compatibility and desktop behavior remain incomplete. See the
[current overview](../README.md), [rendering evidence](results/2026-11-03-newport-xmahjongg.md)
and [historical checkpoints](HISTORY.md).

The [desktop-preferences cycle](results/2026-11-06-desktop-preferences.md)
restores each user's backdrop, colour scheme, focus policy and window movement
settings. Two distinct profiles pass logout/login and reboot checks, including
native pointer tests and matching backdrop pixels. Xmahjongg now launches on
demand. Next qualify saved application sessions and File Manager/Dumpster
behavior; other control panels and backdrop formats remain separate.

The agreed target remains the full original IRIX desktop on NetBSD and X.org,
with modern software running natively. The [repository/workflow cleanup](results/2026-11-03-workflow-cleanup.md) is
complete: the maintained `./xiri` commands and both desktop checks are qualified.
The [first module milestone](results/2026-11-03-irix-module.md) now passes
on the Xiri fork, including a desktop without built-in IRIX support. The
[new manual CHD](results/2026-11-03-irix-module-image.md) packages that kernel
and module and passes graphical boot, repeated desktop/logout, accelerated
rendering and a fresh catalog launch from disk. The maintained
[service/session runtime](../runtime/README.md) now passes its
[qualification](results/2026-11-03-xiri-session.md), and native
[xdm integration](results/2026-11-03-xiri-xdm.md) now passes normal xiritest
login and a separate native user's standard ctwm session. The [xdm CHD](results/2026-11-03-xiri-xdm-image.md)
now packages both runtime cycles and passes direct-disk login, logout/relogin
and catalog checks. Earlier images remain regression baselines.

The [winterm reliability cycle](results/2026-11-03-winterm-reliability.md)
adds measured PTY window sizing and SIGCHLD NOCLDSTOP handling to the module,
plus a native shell handoff that preserves the terminal's dimensions. Paired
original-IRIX/NetBSD checks pass 248 ioctl observations and 24 child-exit
signal/frame controls. Foreground resize and normal terminal exit now work;
the intermittent font collapse now reproduces in both native and IRIX Xlib
against Xorg's scalable IBM Courier face. A session resource default selects
the existing SGI Screen bitmap font; later font cycles below select bitmap
Courier and fix the native Type1 cause. The later job-control cycle qualifies
continued-child notification policy, IRIX nanosleep and real shell jobs;
broader terminal workloads remain open. The extended font
diagnostic also captured repeated characters during XTest input; investigate
that separately without attributing it to concurrency before a controlled
comparison. Its failed input attempts are excluded from terminal acceptance.

The [GIMP cycle](results/2026-11-03-irix-gimp.md) adds full-mask signal
registration with paired o32/n32 checks and imports the original setup/data/
plug-in resources. GIMP now paints, saves/reopens matching XCF and PNG files,
quits normally and launches from Freeware as xiritest. Follow-ups are the
larger images/tile swapping and
individual plug-ins. Shared-memory transport currently uses its fallback.
The replacement manual CHD has separate boot/session acceptance.

The [catalog startup survey](results/2026-11-03-irix-catalog.md) now attempts
all 124 distinct program targets selected from the 166-entry inventory.
The [application checklist](ICON-CATALOG.md) preserves all 17 system pages
and the empty user Blank page. The bottom-right page menu exposes all 18.
Nine launch targets reproduce busy processes without a window; three invoke
GNOME Terminal. Acrobat initially lacked its Reader installation, while Freeware NEdit
launches through the catalog and accepts text but fails to save. These remain
separate from functional passes. Interrupted X queries and compview's failed
cleanup tracking are retained explicitly; all disposable guests are stopped.

The [GNOME follow-up](results/2026-11-04-irix-gnome.md) identifies gedit's
ORBit Unix-listener loop. The candidate module implements the measured
pathname-stream subset; original GNOME VFS modules and editor resources then
let gedit edit, save/reopen and overwrite a document and launch through the
catalog. Image decoding/help and broader plug-ins remain open. Preference
persistence is covered by the later cycle below.
All eight other formerly busy targets now reach windows/dialogs and become
idle in the repeated bounded check. Evolution needs its default-user tree;
the three terminal routes fail during child/login setup; Balsa setup is
partly blank; Glade opens with OAF/preferences warnings; Gnumeric needs its
GNOME print fonts; XChat reaches a first-run notice. None is a functional
pass merely because a window now appears.

The [terminal cycle](results/2026-11-04-irix-terminal.md) traces that generic
login error through missing socketpair, the absent original PTY helper,
PTY ownership and libc's master check. The candidate adds one-descriptor
legacy transfers and reaches the original IRIX shell. Basic typed commands,
home-directory file creation and `exit` work. The subsequent
[termios cycle](results/2026-11-04-irix-termios.md) qualifies 864 attribute
observations and 64 controlling-terminal/session observations against original
IRIX. Its original shell recognizes an interactive terminal and passes prompt,
command, Ctrl-C, foreground resize and normal-exit checks. The later
job-control cycle also qualifies stop/resume and background jobs. The glynx and
Midnight Commander wrappers still need their missing `lynx` and `mc` program
trees; their shared terminal startup is not application support.

The [preference cycle](results/2026-11-04-irix-preferences.md) now qualifies
256 paired rename observations and 16 namespace controls. GNOME Terminal,
gedit and GIMP settings survive normal exit/relaunch; GIMP preserves an exact
backup. The [Acrobat cycle](results/2026-11-04-irix-acrobat.md) imports the
complete original package and supports its measured legacy ELF layout, with
514 loader/mapping executions. Reader displays a PDF, changes page/zoom,
reopens it and exits normally; catalog launching works but its running-icon
feedback remains unresolved. The [cumulative CHD](results/2026-11-04-irix-acrobat-image.md)
now packages these changes and passes cold application, full-screen xdm,
both user desktops, recovery, catalog and clean-shutdown checks.

Per the user's 2026-11-04 priority change, defer individual application repairs
and first qualify system stability. The [native stability probe](../lab/system-stability/README.md)
repeats X input, child supervision, both user desktops, logout and clean halt
with diagnostics that distinguish transport, process and kernel failures.
Preserve the survey's native child-control stalls, failed batch halt and the
Acrobat image's transient native input timeout as evidence; require a
reproduced cause and tested correction before closing each observation.
The [system cycle](results/2026-11-04-system-stability.md) has also reproduced
and corrected native NetBSD32 CD9660 ownership/mask translation; that cause is
separate from the earlier stalls. The corrected core passes 158 CD checks.
Two cold boots pass 1,200 native input cycles, 160 child-launch cases, both
user desktops and active-desktop shutdown, including a candidate run with
96 MiB held by an independent process and measured paging. The intermittent
older failures were not reproduced in that first cycle. The
[replacement-image cycle](results/2026-11-04-system-stability-image.md) now
packages the corrected core and passes full-screen xdm, both desktops,
recovery, rendering, catalog and clean halt. Its application gate reproduces
the native XTest timeout at `button-sync`, including a shorter capture/click
test. A stopped-client diagnostic also reaches that alarm, but native GDB
crashes during inspection; later procfs reads do not establish the earlier
cause. The [follow-up](results/2026-11-04-xorg-scheduling.md) now captures that
state at the alarm: the release is ready, while a higher-priority client
continues QueryPointer requests. Round-robin Xorg dispatch avoids the stall.
The selected replacement passes 60 native query-loop controls, six complete
Acrobat sequences, GNOME Terminal, CD9660 and both-user session/shutdown gates;
a separate reduced replay passes 60 capture/focus cycles. Keep the original
failures, fixture exclusions and normal shell-zombie observation distinct.
Native child-control stalls and the earlier catalog halt remain open system
work. The Type1 cause is addressed by the later cycle below.

The [2026-11-05 font/menu cycle](results/2026-11-05-newport-text.md) reproduces
blank disabled Toolchest labels and native Xft/Render glyphs as a Newport
software-fallback refresh failure. The corrected xsrc driver passes all
69 native text cases and the existing texture regression with XAA enabled.
Explicit NetBSD bitmap Courier restores larger winterm text close to IRIX's
original appearance, without importing another font. That cycle retained the
separate scalable Type1 failure. Its image passes cold xdm,
both users, three winterm starts/resizes, 345 text comparisons, catalog launch
and clean halt. A separate menu replay shows all 93 labels in the six top
menus and four cascades, including 41 disabled labels. The preceding scheduler
image and manual state remain preserved.

The [Type1 follow-up](results/2026-11-05-type1-scaler.md) now fixes native
MIPS signal-return FPU state loss. All sixteen signal cases fail on the old
core and pass with the correction, alongside eight no-signal controls.
The corrected core also passes 200,000 arithmetic conversions, 560 font
operations, 24 original IRIX FPU records and an explicit Type1 winterm
input/resize/exit check. The IRIX module, font libraries and bitmap desktop
default remain unchanged. Other scalable faces, native n64 and physical
hardware remain separate qualification work. The
[replacement CHD](results/2026-11-05-type1-image.md) now passes cold xdm,
both desktops, 345 text comparisons, winterm, catalog and clean halt, and is
selected for manual testing. The preceding fonts image and state are retained.

Other shared-system candidates are common IRIX filesystem/timing/job-control
interfaces and general
deployment beyond the current test account and custom core hooks. Select the
following cycle from measured impact after the font/menu and FPU results. Keep NEdit file
creation and the missing Lynx/Midnight Commander payloads queued for the later
application pass. Keep Acrobat's
wrapper execution feedback, broader PDF use and print/browser integration
as separate follow-ups.
For each repaired entry qualify catalog double-click, running-icon feedback,
a useful operation, persistence and normal exit with child cleanup. Continue
through the document/web handlers and unresolved registrations. Keep missing
resources, unsupported interfaces, hardware requirements, slow startup and
crashes distinct; startup UI alone does not qualify application support.
Investigate the survey's native child-control stalls and batch shutdown
failure alongside compview's tracking failure; retain the failing runs rather
than attributing these symptoms to an individual application without evidence.

The completed process/job-control cycle follows the user's 2026-11-05 order:
first measure and implement IRIX stop/continue notifications, child waiting
and nanosleep; then qualify real shell foreground/background jobs and cleanup;
finally revisit the retained native child-control stalls and catalog-batch
shutdown failure on the corrected baseline. Successful bounded tests do not
close an earlier unexplained hang without evidence of its cause.
The [sleep/wait/group interfaces and real terminal jobs](results/2026-11-05-irix-job-control.md)
now pass their focused qualification, including the original IRIX shell,
logout with active jobs and a separate native-user login. The final-module
regressions also pass. Paired old/new 22-target catalog batches complete with
verified cleanup and clean halt; the historical stalls remain unreproduced.
A separate native multi-child test reproduced a shared NetBSD wait-accounting
defect; its fix and before/after tests are isolated in the
[native wait lab](../lab/native-wait/README.md). The new native tests fail on
the unfixed core and pass unchanged on the fixed core under both identities.
The [final CHD](results/2026-11-05-native-wait-image.md) passes cold desktop,
font, shell-job and cleanup checks plus the same 22-target catalog batch,
and is now selected for manual testing. The earlier Type1 and intermediate
job-control images remain preserved.

The [process-tracking follow-up](results/2026-11-05-process-tracking.md)
passes 3,072 independent native child lifecycles and 16 installed-supervisor
scenarios across the old GIMP and current native-wait images. Compview's
paired replays now verify cleanup and halt, while the first X query still
times out and later queries recover. This separates the current query symptom
from the historical tracking failure without explaining that earlier failure.
The maintained fixture requires orphan reparenting and compares events with
pipe-published identities. No kernel/runtime change or new image is warranted
by these passes. Keep the historical tracking/bootstrap/shutdown observations
open; a recurrence needs simultaneous notification, identity and teardown
evidence. Individual application fixes remain deferred.

The [cleanup-deadline cycle](results/2026-11-05-cleanup-deadline.md) now
reproduces a separate runtime defect: a delayed signal return can leave a
real child-exit notification queued when the guard declares failure. A final
nonblocking event/reap check corrects five measured false failures without
extending the grace period. Seven deadline scenarios, 1,536 native child
lifecycles and eight existing supervisor scenarios pass. A deliberately live
child still fails cleanup, and unrelated same-user processes survive.
Remaining-identity, queue and native-state diagnostics are now recorded on
deadline failure. The historical compview/bootstrap/halt observations remain
unexplained; this injection does not establish their cause.

The [cleanup candidate image](results/2026-11-05-cleanup-image.md) passes
cold desktop, font, job-control, both-user logout and clean-halt checks.
It remains unselected because the added 96 MiB pressure gate fails. Native
sleep timeouts occur on both candidate and preceding images; the latter
captures the correct 200 ms request at native libc's nanosleep return.
A separate candidate run reports valid 25-descendant cleanup, then fails
a shell postcheck. The [native paging investigation](results/2026-11-05-native-paging.md)
now traces that assertion, controls its exit/reap race, and locates long
software-encrypted pageout batches in the native page daemon. A separate
big-endian swap-encryption sysctl defect is corrected and tested before/after.
The final candidate passes the full pressure workload and forced encrypted
swap readback with the original watchdog and exact ownership requirements.
A separate startup kernel crash keeps its CHD unselected; evidence is retained
and further investigation is deferred at the user's request. A traced capture also reproduces
a stale greeter frame that an explicit frame wait refreshes to the actual
desktop; the separate cold-image visual gate remains required.
That cold gate now passes from the packaged candidate, including fonts,
native ctwm, IRIX sessions, shell jobs, catalog launch and clean shutdown.

The [multi-user cycle](results/2026-11-05-multiuser.md) now removes FAM's single
configured IRIX-user restriction. Two ordinary IRIX accounts pass xdm login
switching with private homes/session state, while a separate native account
retains ctwm. Concurrent FAM clients use their own native UID and groups,
including supplementary groups. Boot-generated IRIX lookup tables follow
native account administration without copying passwords. The selected CHD
retains the native-wait core/module and needs no new kernel hooks.
Individual application fixes and native IRIX clogin integration remain later
work.

## Next packaging phase

The user requested these deployment changes on 2026-11-03. The implementation
order was updated to prioritize the kernel module at the user’s request:

1. **Loadable IRIX personality: qualified on our fork.** The
   [module cycle](results/2026-11-03-irix-module.md) follows `compat_linux`
   for registration, dependencies and lifecycle. Boot loading, busy-unload
   refusal, unload/reload, the desktop and o32/n32 regressions pass on a
   kernel without the built-in personality. The export/relocation audit
   passes. Stock-kernel delivery still needs upstreaming or replacing
   `selcommon_kern`, `emul.e_sigmask` and `EMUL_NOCLDSTOP_CONT`. Newport and
   other native platform drivers remain separate NetBSD components.
2. **Service/session ownership: qualified.** The maintained
   [`runtime/`](../runtime/README.md) packages boot services with rc.d and
   configuration, plus an unprivileged session on an existing X display.
   Its NetBSD descendant tracker replaces reserved-UID cleanup. Four desktops,
   both menu logouts, existing-X-server reuse, independent shell survival,
   groups/X authority, failed startup and service restart pass the
   [cycle checks](results/2026-11-03-xiri-session.md).
   The [multi-user extension](results/2026-11-05-multiuser.md) now replaces the
   original one-account FAM mapping with native client identities. The current
   image packages that extension; the earlier module image retains its old launcher.
3. **Ordinary-user login through native xdm: runtime and image qualified.** The
   [xdm checks](results/2026-11-03-xiri-xdm.md) preserve the authenticated UID,
   groups, HOME `/usr/people/xiritest`, working directory and native X authority.
   Three successful IRIX sessions, both logout menus, failed startup recovery,
   independent same-user shell survival and a separate native ctwm login pass.
   Xorg uses the explicit 1280×1024 accelerated Newport configuration.
   Native xdm owns the display; the client session leaves system services alive.
   The [Newport text correction](NEWPORT.md) now restores Xft glyphs with
   normal greeter resources, superseding the earlier rendering workaround.
4. **Original IRIX clogin later.** Once the xdm/session boundary is established,
   investigate clogin's authentication and service interfaces against original
   IRIX. Reuse the qualified session startup; do not assume the login binary is
   already compatible.

Acceptance requires repeatable installation/configuration and a fresh manual
CHD for the resulting deployment. The first module milestone is complete
on our fork and its [replacement manual image](results/2026-11-03-irix-module-image.md)
is qualified. The [xdm replacement CHD](results/2026-11-03-xiri-xdm-image.md)
now packages service/session integration and normal native login. It boot-loads
the module, starts system services and authenticates the desktop account through
xdm. A separate account retains the standard native ctwm desktop.
Continue application/desktop fixes alongside packaging without losing the
established regression coverage.

Active fork work is consolidated on [`xiri` in IRIS and NetBSD](FORKS.md).
Historical lab revisions remain pinned in detached worktrees.

The desired final delivery target, agreed on 2026-11-01, is a **loadable NetBSD
kernel module for the IRIX personality, modeled after `compat_linux`**. Use
NetBSD's Linux compatibility module as the reference for module structure,
registration, dependency handling, load/unload lifecycle and separation from
the foreign runtime. Xiri's runtime importer and desktop/session packages
remain separate user-space components. Both built-in and module builds now
have qualification on our fork. Aim to work with an otherwise standard,
compatible NetBSD/MIPS kernel by upstreaming or removing required core changes;
that stock-kernel deployment is not yet demonstrated. See the
[module deployment boundary](ARCHITECTURE.md#components-and-deployment).

The user-reported display responsiveness gap is tracked in [Newport performance](NEWPORT.md). The IRIS RGB24 plane correction and Xorg texture correction now pass bounded accelerated rendering checks. The user reports a more responsive desktop; controlled performance measurements and broader graphics coverage remain open.

The [original-shell checkpoint](results/2026-11-02-irix-vendor-shell.md) and
[published shell image](results/2026-11-02-irix-shell-image.md) now run the
catalog command path and start winterm in HOME. The
[desktop behavior cycle](results/2026-11-02-irix-desktop-behavior.md) addresses
running-icon feedback, granite and filesystem/home/Dumpster icons before
xdm integration. Next desktop work includes Dumpster actions, launch animation,
preferences and persistence; broader GIMP behavior and xosview statistics
remain application-specific work. The
[new manual CHD](results/2026-11-02-desktop-behavior-image.md) packages the
session/FAM changes and clearly labels xiritest as the desktop user, with
root retained as service launcher. Intermittent winterm startup/font-metric
behavior also needs investigation.

## Development setup checklist

The candidate host inventory, pinned IRIS CLI build, verified NetBSD inputs, guest installation, and host kernel build are complete. The R4400 guest reaches multiuser after a cold boot with the custom kernel, supports debugger breakpoints, and passes an automated probe. Repeated disk writes, cold-read integrity, and bidirectional network transfers pass in both execution modes; see the [I/O results](results/2026-10-30-netbsd-io.md). See the [installation record](results/2026-10-29-indy-netbsd-install.md), [kernel build record](results/2026-10-30-netbsd-kernel.md), and [debugger/probe results](results/2026-10-30-netbsd-debugger-probe.md).

Before starting implementation:

1. Sync this repository and inventory the selected build host's OS, CPU architecture, RAM, free storage and installed tools. Recheck capacity rather than relying on the earlier session measurements in the [emulation plan](EMULATION.md#inspected-session-environment).
2. Arrange storage for source, toolchains, object files, guest disks and snapshots. Retain the 30–50 GiB planning allowance and adjust it from actual usage.
3. Provision a debug-capable IRIS source build with a recorded Rust toolchain and native dependencies, plus NetBSD cross-build tools. Check the selected host's library compatibility before choosing any packaged emulator.
4. Use the [verified NetBSD 11.0 input baseline](../lab/netbsd-11.0/README.md) for the installer, sets, checksums and matching source. Use the supplied Indy PROM and [IRIX 6.5.22m reference image](results/2026-10-30-irix-vendor-baseline.md) for vendor and desktop experiments. The first native shell session works; investigate its XFS alerts and qualify MAME and graphics separately.
5. Preserve the [qualified o32/n32 application paths](results/2026-10-30-irix-lp64.md) while expanding toward the supplied n32 desktop. The LP64 kernel now runs unmodified asa and echo through their original runtimes, with 8 KiB page checks and the established 32-bit-kernel regressions. The [TCP path](results/2026-10-30-irix-tcp.md) and [socket-address queries](results/2026-10-31-irix-peername.md) now reach a controlled native X connection and both endpoint queries. The [startup-interface checkpoint](results/2026-10-31-irix-xconnect.md) now reaches completed X setup and processed requests. The [legacy recvmsg checkpoint](results/2026-10-31-irix-recvmsg.md) now receives an X reply and reaches a later SIGSEGV. The [session diagnosis](results/2026-10-31-irix-toolchest-session.md) now identifies a null `HOME` value passed to `strcpy`; an explicit environment avoids the fault. The [select checkpoint](results/2026-10-31-irix-select.md) implements the measured readiness and timeout subset, including unique descriptor counts and copyout faults, with an explicit 1024-descriptor cap and stricter invalid-descriptor policy. The [xstat checkpoint](results/2026-10-31-irix-xstat.md) adds measured pathname metadata for both ABIs and versions 2/3, including guards, permissions, namespace fallback and partial faults. The [fxstat checkpoint](results/2026-10-31-irix-fxstat.md) adds measured descriptor metadata and shares the serializer with xstat. With supplied resources, Toolchest now reads the correct app-defaults size and full menu without the earlier allocator SIGSEGV. The [SIOCNREAD subset](results/2026-10-31-irix-siocnread.md) is measured and implemented; Toolchest now renders its menu and remains alive in bounded tests. Sustained visibility and Expose redraw now pass under both identities. The [resource/input follow-up](results/2026-10-31-irix-toolchest-input.md) now separates color/keysym inputs and menu navigation. Next qualify supported application launches and broader timing/session behavior. The [winterm and font experiments](results/2026-10-31-irix-winterm-resources.md) establish native SGI font import and an original xwsh startup fault; the [fault capture](results/2026-10-31-irix-winterm-fault.md) now identifies a null font object and unsupported access to staged locale/defaults. The [access adapter](results/2026-10-31-irix-access.md) now permits those resource reads and removes the null-font failure. The [process checkpoint](results/2026-11-01-irix-process.md) follows native PTY allocation with bounded fork, masks and exit waits. The [shell checkpoint](results/2026-11-01-irix-shell.md) now verifies descriptor duplication, session creation and native exec with paired probes, then real keyboard input and command execution through original winterm/xwsh. Native handoff and a reserved-UID supervisor cover controlling-terminal setup and session descendants. The initial 4Dwm session now passes native-window interaction alongside Toolchest and winterm with session saving disabled; retain foreign signal handlers, resize, normal terminal exit and broader shell behavior as explicit follow-ups. Reassess seek when a later workload requires it. The subpage and relocation mappers now cover the observed library boundaries; the fixed/local mmap and measured PRDA checkpoints now clear GL initialization and the following libc fault. Qualify window management and the remaining session paths. Complete runtime resource/service qualification and a clean graphical reference session. Add the required behavior with paired original-IRIX probes. Keep the [X11 limits](results/2026-10-30-netbsd-x11.md) explicit and compare CI with ordinary execution for each new workload.
6. Inventory the physical Indy, Indigo2 and Octane, and arrange Indy serial capture for later hardware qualification.

Keep large images and original runtimes outside Git; save configurations, manifests, commands and small result logs in the repository. This checklist prepares Milestones 0–1.

## Requirements established

- Real hardware is the primary execution target.
- Indy emulation is the initial development and test environment; IRIS is preferred pending qualification, with MAME for comparison and fallback.
- NetBSD is the underlying OS; the IRIX personality supplies selected binary compatibility.
- Indy, Indigo2, and Octane are available for testing.
- Preserve the IRIX desktop as well as selected legacy applications.
- Use reverse engineering to establish missing graphics-driver behavior and other proprietary interfaces, corroborating binary analysis with observed behavior.
- Support maintained software alongside the preserved environment.
- Keep planning, decisions, and reproducible execution records in this repository.

## Milestone 0 Emulator and software baseline

- [x] Provision build tools and sufficient host storage as described in the [emulation plan](EMULATION.md). See the [host inventory](results/2026-10-29-host-inventory.md) and [cross-build record](results/2026-10-30-netbsd-kernel.md).
- [x] Pin an IRIS source revision, exact Rust toolchain, dependency resolution and debug-capable build options. See the [build record](results/2026-10-29-iris-build.md).
- [x] Record the emulated Indy CPU, RAM, Newport configuration, PROM, NVRAM and disk layout. See the [guest lab](../lab/indy-netbsd/README.md) and [run record](results/2026-10-29-indy-netbsd-install.md).
- [x] Obtain the NetBSD sgimips installer, sets, checksums and matching source baseline. See the [input record](results/2026-10-29-netbsd-inputs.md).
- [x] Obtain appropriate Indy firmware for MAME comparison; record IRIS's embedded fallback separately if used. The supplied PROM matches the recorded SHA-1 and boots the IRIX reference in IRIS. MAME verification remains part of the separate comparison gate.
- [x] Select a reference IRIX installation and record its desktop package versions. The [supplied image](results/2026-10-30-irix-vendor-baseline.md) reports IRIX 6.5.22m; desktop_base, eoe, and x_eoe report 6.5.22.
- [ ] Identify two or three additional legacy applications and representative tasks for each.
- [x] Inventory the static library closures and initial resource/session requirements of 4Dwm and Toolchest. The [desktop inventory](../lab/irix-desktop/manifest.json) resolves 25 and eight libraries respectively, verified by native ldd, and pins 101 resource/service candidates.
- [ ] Complete desktop runtime dependency qualification, including delayed/dlopen modules, fonts, user resources, helpers and session services. The static inventory does not establish a working desktop.
- [ ] Record exact upstream revisions for NetBSD, historical compatibility code, MAME, and relevant drivers. NetBSD release/fork and historical IRIX/SVR4 removal revisions are now pinned in the [source audit](results/2026-10-30-irix-compat-audit.md); MAME and later driver baselines remain pending.

Acceptance for starting NetBSD work: a pinned emulator build, guest configuration and NetBSD input manifest. IRIS's embedded PROM supplied the initial bootstrap; the user-provided PROM and IRIX 6.5.22m image now support reference work. Original-IRIX reference acceptance additionally requires a desktop dependency manifest and a reproducible reference session. These inputs need not block the NetBSD bootstrap.

Parallel hardware preparation: inventory each physical machine's CPU, memory, graphics, firmware, storage, Ethernet and installed IRIX release. Establish serial capture and an alternate boot/storage setup for the Indy before physical testing; preserve its existing installation.

## Milestone 1 Host boot and desktop feasibility

The NetBSD boot and desktop experiments can be performed independently as their inputs become available. Both determine the implementation work needed on the first platform. Use the [emulator qualification gate](EMULATION.md#qualification-gate) to record each result.

- [x] Boot the NetBSD installation kernel in IRIS, install to a disposable disk, and cold-boot to multiuser. Passed with R4400 and CI enabled; R5000 panicked during cache initialization.
- [x] Capture serial logs and verify persistent storage, network transfer and reboot integrity. Repeated 96 MiB disk writes, 32 MiB cold-read verification, and 96 MiB of NFS/HTTP/TCP transfers passed in CI and ordinary execution. The [I/O record](results/2026-10-30-netbsd-io.md) documents those runs. Later snapshot stress found intermittent corruption with fragmented NFS; current work uses HTTP or 1024-byte NFS requests. The installer HTTP stall is also unresolved.
- [x] Cross-build a modified kernel on the modern host and verify its build identifier in a fresh guest boot. `XIRI_INDY_20261030` reached multiuser over TFTP with SCSI root; see the [build and boot record](results/2026-10-30-netbsd-kernel.md).
- [x] Demonstrate debugger attachment, a breakpoint, and continued execution. Cross-GDB stopped at `main` and `cpu_rootconf`; the guest resumed to multiuser. See the [debugger record](results/2026-10-30-netbsd-debugger-probe.md).
- [x] Automate a probe with output, exit status, timeout and clean-state repetition; compare ordinary and CI execution. The [harness](../scripts/probe-netbsd.py) passed the file/swap/kernel smoke test in both modes and verified deliberate exit and timeout failures. This is a workload-specific comparison.
- [x] Qualify snapshots separately, keeping changed-kernel tests on cold boots. Repeated restores, CI rollback, fresh-process restore, timers, and final cold-boot integrity pass in both execution modes with the RAM-map fix. The [snapshot record](results/2026-10-30-netbsd-snapshots.md) limits the NFS profile to 1024-byte requests and retains the fragmented-transfer failure.
- [ ] Repeat key boot and probe results in MAME when firmware is available; use it as primary if it passes a stage IRIS fails.
- [ ] When hardware access permits, run an early physical Indy boot and I/O smoke test to expose differences from emulation; retain full ABI and desktop hardware acceptance for Milestone 4.
- [x] Establish a usable NetBSD X display and input on emulated Newport, or record the precise driver gap. [Software-rendered Xorg at 1024×768, depth 24](results/2026-10-30-netbsd-x11.md) passes pixel, keyboard/mouse, twm/xterm, and clean-shutdown checks in both modes after an IRIS keyboard-controller fix. The [framed-console/XAA cycle](results/2026-11-02-newport-framed-acceleration.md) later qualifies RGB24 drawing and partial masks at 1280×1024 after an IRIS plane-encoding correction; both accelerated and software screenshots match.
- [ ] Run selected original desktop clients on IRIX against a dedicated modern X server.
- [ ] Record required visuals, X extensions, fonts, libraries, and helper processes; distinguish confirmed requirements from suspected ones.
- [x] Compare historical `COMPAT_IRIX` code with current kernel interfaces and document the smallest execution experiment. The [audit](results/2026-10-30-irix-compat-audit.md) records recognition bugs, removed dependencies, o32/n32 boundaries, and an implementation acceptance matrix. The synthetic native control and two `ENOEXEC` checks pass in both modes.
- [ ] Evaluate [REA](FEASIBILITY.md#rea-reverse-engineering-tools) as optional analysis tooling on representative big-endian MIPS/IRIX artifacts; record provider capabilities and gaps before relying on its output.

Acceptance: a repeatable installer-to-modified-kernel loop, an automated probe, and a desktop compatibility report. Record emulator failures separately from guest failures. Identify required kernel and display changes and the first desktop component to execute. A failed desktop probe should produce an actionable dependency finding.

Decision gate: if the display or desktop exposes a major feasibility obstacle, document it and revise the implementation plan before expanding the compatibility layer. Changing the NetBSD foundation or replacing original desktop components would require an explicit revision of the agreed target.

## Milestone 2 Native IRIX execution

- [x] Execute a minimal static IRIX-format program with verified output and exit status. The [explicitly marked synthetic o32 fixture](results/2026-10-30-irix-o32-execution.md) prints 15 exact bytes and exits 37 using IRIX calls 1004/1001. All 33 execution, error, rejection, and cleanup cases pass in both modes. This covers the constrained test image, not general unbranded IRIX ELF files or vendor applications.
- [x] Expand static o32 coverage for argv/envp, file operations, memory mappings, and meaningful partial/error returns before dynamic-runtime work. The [bounded subset](results/2026-10-30-irix-o32-basics.md) passes 44 cases in both modes, including static auxv, translated open flags, file effects, partial/nonblocking transfers, private mappings, and protection faults. Native paths/VM policy are used; original-IRIX behavioral comparison remains pending.
- [x] Extend the static ELF loader for writable data and zero-filled BSS, with segment bounds and permission checks, before interpreter support. The [marked two-load-segment subset](results/2026-10-30-irix-o32-segments.md) passes 89 cases in both modes, including partial-page and pure BSS, adjacent segments, fresh contents after repeated execs, immutable executable files, and text/unmapped-page faults. General ELF layouts and non-executable-data enforcement remain unqualified.
- [x] Establish bounded o32 interpreter loading, runtime lookup, and dynamic auxiliary data. The [runtime experiment](results/2026-10-30-irix-o32-runtime.md) passes 37 runtime and 89 static cases per mode. Unmodified asa enters libc and stops at an unsupported capability-configuration query; the synthetic interpreter verifies auxv, data/BSS, and the main-entry handoff.
- [x] Implement bounded runtime configuration, capability, and identity queries, with the same direct-trap probe on original IRIX. The [query extension](results/2026-10-30-irix-o32-queries.md) passes 42 runtime and 89 static cases per mode, including four real/effective identity profiles, guarded copyout, pointer faults, and name-length boundaries. Xiri explicitly advertises traditional superuser permissions; IRIX capability enforcement is not implemented.
- [x] Implement bounded `SGI_ELFMAP` and enter the original rld. The [mapping experiment](results/2026-10-30-irix-o32-elfmap.md) covers linked RX/RW mappings, private initialized data, partial/whole BSS, protections, file/mount checks, and rollback without replacing old mappings. It passes 86 runtime and 89 static scenarios per mode, with 43 original-IRIX mapping observations. Relocation and broader layouts remain outside the subset.
- [x] Implement checked indirect dispatch, `sysmp(MP_PGSIZE)`, and non-fixed mmap hints. [Unmodified asa completes its filter](results/2026-10-30-irix-o32-dispatch.md) using the original libc/rld, with seven input cases compared against original IRIX and root/user execution on NetBSD. Earlier mapping/query/static checks remain in the qualification; broader vendor relocation and runtime behavior remain unqualified.
- [ ] Validate files, allocation, fork and exec, signals, and synchronization against original IRIX.
- [x] Establish a separate LP64 GENERIC64_IP2x/COMPAT_NETBSD32 boot/native baseline. The [qualification](results/2026-10-30-netbsd64-native.md) covers installed o32 userland and native n32/n64 probes in both modes, with firmware-call and emulator TLB fixes. This kernel has no IRIX personality.
- [x] Port the bounded o32 personality to LP64 and qualify IRIX n32 dispatch/loading, with unmodified echo before 4Dwm and Toolchest. The [dual-ABI qualification](results/2026-10-30-irix-lp64.md) runs echo and asa with original libc/rld, tests 8 KiB page layouts and heap growth, and retains native controls and the same-source 32-bit regressions. Foreign 64-bit syscall arguments/returns remain outside this subset.
- [x] Capture reproducible desktop startup boundaries with native and asa/echo controls in both emulator modes. The [audit](results/2026-10-30-irix-desktop-startup.md) distinguishes Toolchest’s unsupported socket call from original IRIX’s successful TCP connection attempt, and identifies 4Dwm’s library mapping boundary.
- [x] Qualify the initial IRIX TCP transport for Toolchest, then test a controlled native X connection and record later startup requirements. The [TCP checkpoint](results/2026-10-30-irix-tcp.md) reaches successful connect followed by unsupported getsockname, with paired probes and native/vendor regressions.
- [x] Qualify getsockname output address/length translation and repeat Toolchest’s X connection. The [getsockname checkpoint](results/2026-10-31-irix-sockname.md) matches paired output/guard observations and reaches unsupported getpeername.
- [x] Qualify getpeername output translation and unconnected-socket errors, then repeat Toolchest’s X connection. The [getpeername checkpoint](results/2026-10-31-irix-peername.md) matches 152 returning paired records and records later gethostname/fcntl/sendmsg/shutdown failures.
- [x] Qualify those hostname, descriptor-control and message-transfer interfaces against original IRIX, then repeat Toolchest. The [startup-interface checkpoint](results/2026-10-31-irix-xconnect.md) reaches successful X setup and processed requests, followed by unsupported recvmsg.
- [x] Qualify legacy recvmsg output structures, vector lengths, received bytes and error behavior with paired IRIX probes, then repeat Toolchest. The [receive checkpoint](results/2026-10-31-irix-recvmsg.md) adds 268 exact returning pairs, checks queue consumption/peeking and read-only header output, and advances Toolchest through a successful 32-byte X receive.
- [x] Isolate Toolchest’s subsequent SIGSEGV with validated native ptrace controls and an environment-only comparison. The [session checkpoint](results/2026-10-31-irix-toolchest-session.md) proves a missing `HOME` value reaches `strcpy` unchecked; the explicit wrapper avoids that fault.
- [x] Qualify the bounded `select` subset against original IRIX, including guarded sets, unique counts, copyout faults and waits measured inside the syscall. The [select checkpoint](results/2026-10-31-irix-select.md) passes both LP64 modes and the o32 kernel, with two explicit descriptor-policy differences and unchanged transport regressions. All 24 HOME Toolchest launches reach the version-2 xstat boundary.
- [x] Qualify versions 2/3 of `xstat` against original IRIX: 648 reference executions and 1,620 guarded NetBSD records across LP64 CI/ordinary and o32. The [xstat checkpoint](results/2026-10-31-irix-xstat.md) also repeats the supplied resource stages and captures the later allocator fault.
- [x] Qualify descriptor-based [fxstat](results/2026-10-31-irix-fxstat.md): 520 original-IRIX records, 1,300 matching NetBSD records, shared xstat and transport/select regressions. Toolchest reads the correct app-defaults size and full menu without the observed allocator SIGSEGV.
- [x] Measure and implement [SIOCNREAD](results/2026-10-31-irix-siocnread.md), then rerun Toolchest with native X controls. The menu renders and the client survives the bounded launch tests.
- [x] Check sustained visibility and Expose redraw using an independent native control: root and uid 1234 both restore the rendered menu during 60-second runs.
- [x] Qualify the [bounded resource/menu sequence](results/2026-10-31-irix-toolchest-input.md): original XKeysymDB, numeric SGI colors, mouse posting, keyboard traversal, submenus, Escape and redraw.
- [ ] Qualify supported application launches, spring-loaded dragging, timers and broader event/session behavior.
- [x] Try [original winterm/xwsh](results/2026-10-31-irix-winterm.md), distinguish launcher success from child execution, and verify native terminal controls.
- [x] Evaluate [original SGI Screen font import](results/2026-10-31-irix-winterm-resources.md): 22 indexed fonts, four native render controls and paired font/locale/account staging.
- [x] Locate the [xwsh null-font fault and resource-lookup boundary](results/2026-10-31-irix-winterm-fault.md) with actual access/seek arguments and native controls.
- [x] Implement the [bounded access subset](results/2026-10-31-irix-access.md): 4,020 checks with explicit native-policy differences. Eight original xwsh starts now read locale/default resources and pass the earlier null-font crash.
- [x] Measure and implement the bounded [PTY allocator interfaces](results/2026-10-31-irix-pty.md), including native ownership/namespace setup and original libc slave opens. Original xwsh advances to unsupported fork.
- [x] Measure and implement the [bounded process subset](results/2026-11-01-irix-process.md): fork/getpid, traditional signal masks and positive-child exit waits, with independent native identity/mask/COW/file-offset and process-group cleanup checks. Original xwsh reaches child execve after opening its slave.
- [x] Run a native interactive shell through [original winterm/xwsh](results/2026-11-01-irix-shell.md), with paired descriptor/session/exec probes, real keyboard input, a PNG and bounded descendant cleanup.
- [x] Qualify [winterm resize and normal terminal exit](results/2026-11-03-winterm-reliability.md), including measured NOCLDSTOP child-exit handlers, preserved nondefault dimensions and foreground SIGWINCH delivery.
- [x] Correct the reproduced [native Type1 collapse](results/2026-11-05-type1-scaler.md) through MIPS FPU signal-return preservation, with independent register, font and original winterm controls.
- [x] Qualify IRIX sleep, stop/continue notifications, process groups and real foreground/background terminal jobs, including logout with active jobs.
- [ ] Extend beyond the qualified shell sequences to arbitrary nested pipelines and general layered-tty revoke. Terminal defaults retain the verified NetBSD bitmap Courier face.
- [x] Qualify the [4 KiB data mapping extension](results/2026-11-01-irix-elfmap-subpage.md): 750 mapping/limit checks; original 4Dwm passes its previous library boundary.
- [x] Resolve [4Dwm’s fixed/local GL mapping](results/2026-11-01-irix-mmap-local.md): 660 cases, 30 controls and 32 native page-zero checks.
- [x] Provide [measured PRDA process data](results/2026-11-01-irix-prda.md): 80 executions / 180 records, fork COW/PID updates, exec reset, damaged-state policy and native-exec controls.
- [x] Demonstrate [4Dwm window interaction and a combined shell session](results/2026-11-01-irix-4dwm.md): real reparenting, pointer focus, key delivery, dragging and typed winterm commands alongside Toolchest. Session saving is explicitly disabled.
- [ ] Resolve remaining 4Dwm session file/service dependencies and feature queries, then qualify broader menus, minimize/maximize, desks and restoration. Preserve the qualified terminal resize/exit and both desktop logout routes.
- [x] Capture the [actual libXmu mapping failure](results/2026-10-31-irix-xclock-elfmap.md): unchanged libXmu headers request two addresses already occupied by libXaw text, and the mapper returns ENOMEM. Native breakpoint controls and clean shutdown pass.
- [x] Add [bounded collision relocation](results/2026-10-31-irix-elfmap-relocation.md): 576 mapper/limit checks, both ABIs, unchanged headers, alignment/gap/sentinel checks, and eight original analog/digital xclock windows. The later subpage checkpoint separately qualifies 4Dwm's 4 KiB data boundaries.
- [x] Measure and implement [time/gettimeofday](results/2026-11-01-irix-time.md): 192 original records, 480 native records and 44 controls. Eight bounded original analog/digital xclock launches show current UTC time, advance and redraw; PNGs are retained. Longer sessions and timezone/DST remain follow-ups.
- [ ] Record unsupported calls and operations explicitly rather than masking them as successful.

Acceptance: repeatable static and dynamic execution, meaningful behavioral probes, and at least one useful IRIX command-line program on NetBSD in the emulated Indy. Retain the same probes for physical qualification.

## Milestone 3 Original desktop proof

The target is a complete original IRIX desktop session on NetBSD and X.org.
The first rendered, live Toolchest client now establishes the entry point for
component-level checks. The user-supplied [IRIX Interactive Desktop User Interface Guidelines,
007-2167-006](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/index.html)
was revisited on 2026-10-31 after that rendering. The comparisons below are our
acceptance plan derived from its desktop, window/session, service, data exchange
and menu chapters; they are not claims that the complete desktop already works.

| Manual coverage | Planned desktop comparison |
| --- | --- |
| [Chapters 1](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch01.html)–[2](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch02.html): components, icons and file-type rules | Toolchest, Icon Catalog, file manager and desktop icons; launch applications and open files through their assigned actions |
| [Chapter 3](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch03.html): windows, focus, desks and sessions | Move, resize, minimize, focus and switch desks; restore application state across logout/login |
| [Chapter 4](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch04.html): services and settings | Apply preferences, observe file changes from native and IRIX programs, and qualify each required helper or host-service adapter |
| [Chapter 5](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch05.html) and [7](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch07.html): exchange and interaction | Clipboard/selection exchange, keyboard navigation and drag-and-drop between selected native and IRIX applications |
| [Chapter 8](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch08.html): menus | Open, traverse and dismiss menus with mouse and keyboard; distinguish menu rendering from launching a supported application |

Use the manual as a behavior reference and measure version-specific details
on the selected installation. The existing resource/service inventory supplies
dependency candidates; a visible window alone does not complete these checks.

- [x] Revisit the supplied manual after the first rendered Toolchest client and map its relevant chapters to the comparisons above.
- [x] Maintain the [image-resource checklist](IRIX-RESOURCES.md) and [ledger](../lab/irix-desktop/resource-ledger.json), distinguishing extracted assets, observed use, remaining artwork/catalog/service gaps and native session state.
- [x] Qualify opened-icon feedback after catalog double-click, the granite backdrop, and filesystem/home/Dumpster icons before graphical-login integration. The [desktop behavior result](results/2026-11-02-irix-desktop-behavior.md) passes launch/exit artwork restoration and desktop directory opening; broader actions remain below.
- [x] Integrate native NetBSD xdm in the maintained runtime. The [qualification](results/2026-11-03-xiri-xdm.md) covers full-screen login → desktop → logout → login, identity/HOME/groups/X authority, failed startup, both IRIX logout menus and a separate user's standard ctwm session. The [replacement CHD](results/2026-11-03-xiri-xdm-image.md) passes direct-disk checks; native IRIX clogin follows later.
- [x] Replace reserved-UID cleanup in the maintained runtime with a native descendant supervisor. The [session qualification](results/2026-11-03-xiri-session.md) preserves independent same-user activity, groups, HOME and X authority. The current xdm CHD packages this supervisor; the previous module image keeps its older reserved-UID launcher as a control. The xiritest home remains `/usr/people/xiritest`; an actual IRIX root session should use `/`.
- [ ] Turn the remaining comparisons into reproducible desktop acceptance cases against the original installation.
- [x] Launch original 4Dwm against native Xvfb and demonstrate reparenting, focus, key delivery and dragging in the [combined shell session](results/2026-11-01-irix-4dwm.md); Newport/physical display qualification remains separate.
- [x] Add original Toolchest and a working winterm shell to the same 4Dwm session.
- [x] Qualify [1280×1024 Newport geometry and supported Toolchest launches](results/2026-11-02-desktop-launch.md): two menu-created native shells accept typed commands; Applications opens original xclock, Icon Catalog and xmahjongg. Imported vendor menus and shells remain unchanged, with explicit native launch overrides.
- [x] Resolve Newport RGB24 XAA fast-clear colors and write masks using the REX3/RB2 documentation catalogued in `../sgi`. [Renderer and native Xorg checks](results/2026-11-02-newport-framed-acceleration.md) pass with IRIS `xiri` 819c682; the requested framed-console kernel matches NetBSD feature commit a536d8c4da2.
- [x] Resolve the reproduced XAA xmahjongg artwork corruption: the [Xorg Newport texture correction](results/2026-11-03-newport-xmahjongg.md) passes the focused Render regression and matches all 617,684 software-rendered game-window pixels. Broader Render and 32-bit core drawing remain separate qualification work.
- [ ] Measure native Xorg fill/copy/text and window-movement performance with acceleration enabled/disabled; compare equivalent IRIX and Xiri setups. Correctness-run elapsed times do not establish a speedup.
- [ ] Diagnose xwsh retaining its window after native shell exit and producing PTY write EIO when further input reaches it. The menu test explicitly removes that closed-shell client; automatic terminal closure is not yet qualified.
- [x] Attempt the original file manager, background icons and Icon Catalog in the [expanded session](results/2026-11-01-irix-desktop-components.md); retain startup failures and inventory the next resources.
- [x] Clear the initial `getrlimit(RLIMIT_PTHREAD)` and bgicons executable-alignment blockers with [measured limit/loader support](results/2026-11-01-irix-rlimit.md): 4,760 NetBSD limit records and 280 loader executions pass.
- [x] Clear the observed `mmap(MAP_AUTORESRV)` boundary with [private demand mappings](results/2026-11-01-irix-mmap-autoresrv.md), preserving fixed/local and native controls.
- [x] Measure and implement initial `prctl(PR_INIT_THREADS)` state and native signal holds: [260 executions / 860 records and 32 asynchronous-signal checks](results/2026-11-01-irix-init-threads.md) pass. Thread creation remains separate.
- [x] Implement [measured mkdir support](results/2026-11-01-irix-mkdir.md): 3,200 records, 1,540 independently verified directory creations and 44 controls pass. Native group ownership remains explicit policy.
- [x] Record the [user-supplied original desktop reference](IRIX-DESKTOP-REFERENCE.md), with a pixel-preserving PNG and explicit appearance/content targets.
- [x] Implement [measured pipe support](results/2026-11-01-irix-pipe.md): 220 exact records and 44 native/vendor controls, including descriptor exhaustion/rollback and forked writers.
- [ ] Complete usable file/icon clients. The [desktop service repair](results/2026-11-02-desktop-services.md) supersedes the earlier empty catalog/select startup boundary: system pages and entry labels now appear, FileManager lists native files, and FAM delivers changes. The [icon repair](results/2026-11-02-desktop-icons.md) qualifies Freeware artwork and FileManager folder/document icons. The [xdm CHD](results/2026-11-03-xiri-xdm-image.md) also qualifies catalog double-click launching. Broader file operations and intermittent terminal geometry/startup failures remain. Session saving remains disabled.
- [x] Inventory the supplied [May 2004 freeware sets](results/2026-11-01-irix-freeware.md): four CDs, 489 distinct packages; record zero-filled ncurses/nedit metadata separately.
- [x] Establish [native /usr/people account creation and shared-file access](results/2026-11-01-irix-installer.md), including cold-boot persistence.
- [x] Measure and implement the installer's [shared zero-device mapping](results/2026-11-01-irix-mmap-shared.md): 472 original records, 1,180 native records/backing files and 44 controls. Regular-file AUTOGROW remains separate.
- [x] Measure the specific `sproc(PR_SADDR|PR_BLOCK|PR_NOLIBC)` child lifecycle reached by [original inst](results/2026-11-01-irix-installer-shared.md): [112 executions / 200 original records](results/2026-11-01-irix-sproc-reference.md) establish entry, shared data/new mappings, private PRDA/LOCAL pages, descriptor ownership and parent release.
- [x] Implement and qualify the [bounded two-member sproc lifecycle](results/2026-11-01-irix-sproc.md): 340 executions / 600 records and 44 controls, including group-aware guards, repeated creation, LOCAL replacement and exec/exit cleanup. Parent-death races, general multi-member updates and exhaustion failure injection remain separate.
- [x] Retry [original inst with sproc](results/2026-11-01-irix-installer-sproc.md): child creation, armed parent release and native shell exec now succeed. F_DUPFD fails during stdout/stderr pipe setup; the dry run later reaches its watchdog.
- [x] Measure and implement [F_DUPFD](results/2026-11-01-irix-dupfd.md): 168 original records, 420 matching native records, 220 pipe regressions and two sets of 44 controls. The [installer retry](results/2026-11-01-irix-installer-dupfd.md) now connects stdout/stderr successfully but still times out amid gettimeofday ENOSYS.
- [x] Implement time/gettimeofday and capture ticking xclock PNGs. The [installer retry](results/2026-11-01-irix-installer-time.md) confirms successful time calls but still reaches its watchdog.
- [x] Capture [installer helper arguments, output and exit](results/2026-11-01-irix-installer-helpers.md). Four native utility aliases let the embedded bootstrap exit zero in CI and ordinary runs; the parent leaves it a zombie and still times out.
- [x] Measure [foreign signal registration, delivery and return](results/2026-11-01-irix-signal-reference.md): 480 original-IRIX executions, including 120 deliveries, 24 FPU restoration checks and 16 handler reaps using waitsys `P_ALL`/`0x43`. The previously predicted wait call now has an original-runtime reference.
- [x] Implement and qualify the measured traditional-signal subset and wait-any: [1,216 native records and 76 controls](results/2026-11-01-irix-signal.md), with explicit o32/n32 frames, FPU restoration, fork inheritance and invalid-context checks.
- [ ] Extend signal qualification for nested delivery, alternate stacks, restart, broader lifecycle/wait behavior and actual GUI callbacks. Installer retries are deferred for installed-image import; no installer callback has yet completed on NetBSD.
- [ ] Qualify the bootstrap's IRIX `stat -qd` device lookup using the original utility or a measured native adapter; the existing fallback zero is insufficient. System/hardware information, umask and creat remain other observed gaps.
- [x] Inventory already installed applications and their complete catalog registration trees in the supplied disk: [166 entries in 17 tabs](results/2026-11-01-irix-installed-desktop.md), including xmahjongg in Freeware, filetype icons/rules and game data.
- [x] Import the installed payload and observe xmahjongg rendering under 4Dwm, with native controls and cleanup. Record all copies and permission changes in the [import ledger](IRIX-IMPORT.md).
- [x] Build a reusable CHD and verify its full raw-disk round trip and direct disk boot. Provide [manual IRIS instructions](XIRI-IMAGE.md) and a reusable raw automation seed.
- [x] Measure and implement desktop link metadata, readlink, directory enumeration, polling and the MAC capability query: [6,500 guest records and 32 controls](results/2026-11-02-irix-desktop-fs.md). The Trusted Path panel is removed.
- [x] Connect original Icon Catalog and FileManager to native FAM v1, fix the daemon's optimized tree-iterator crash, and expose the imported desktop paths to its native namespace. Observe 18 catalog pages, 21 Freeware entries, native files/folders and live file notifications.
- [x] Prioritize original IRIX `/bin/sh`: [bounded static n32 admission, directory/process-group adapters and shell execution](results/2026-11-02-irix-vendor-shell.md), with 772 checks and two xmahjongg launches through the catalog's original action.
- [x] Package the shell kernel, native null device and winterm HOME fix in a [new manual CHD](results/2026-11-02-irix-shell-image.md); verify graphical boot/logout and a fresh catalog launch from the CHD.
- [ ] Qualify a complete xmahjongg game, later-login persistence, Dumpster operations and transient launch animation. Bounded accelerated hint/take, undo and resize/restore now pass. The **Freeware** double-click launch and opened/closed artwork cycle now pass. Evaluate the located original `launcheffect`/`waitmap` helpers separately; keep unresolved links and additional application runtime data explicit.
- [ ] Later resume original IRIX `inst`, then Software Manager, to install **xmahjongg 3.6.1** from distribution media. Its original hooks must create the **Freeware** entry and icon/type rules; qualify installation history, upgrade and removal separately from file import. See the [software plan](IRIX-SOFTWARE.md).
- [x] Qualify persistent native accounts under `/usr/people/<username>` with shared native/IRIX access, generated desktop state and logout/login persistence. The [multi-user result](results/2026-11-05-multiuser.md) covers two accounts. Original root sessions use `HOME=/`; avoid a second emulation-root copy of user homes.
- [ ] Implement required service adapters, including the measured file-notification and launch behavior.
- [x] Exercise native X test windows under original 4Dwm in the same native Xvfb session used by Toolchest and winterm.
- [ ] Show a maintained host-native graphical application and an IRIX application in the same local session; qualify physical display output separately.
- [x] Restore separate users' backdrop, colour scheme, focus and window-movement preferences across logout/login and reboot. [Preference result](results/2026-11-06-desktop-preferences.md).
- [ ] Resolve SGI colour names under Xorg and qualify the Solid backdrop colour picker; its default `sgiLightBlue` currently renders black.
- [ ] Complete file navigation, desktop updates, remaining window operations and other preference panels.
- [ ] Repeat logout and login, checking process cleanup and restoration of expected state.
- [x] Qualify the development session's graphical console login, repeated desktop start, both logout menus and client/service cleanup. [Usability result](results/2026-11-02-desktop-usability.md); IRIX session saving/restoration remains open.
- [ ] Compare behavior with the reference installation and list component-level differences.
- [ ] Qualify later IRIX releases separately from the current **6.5.22 / 6.5.22m** reference. Retain release-specific image/resource pins and behavior results; record differences as they are encountered.

Acceptance: an original desktop session executing inside the emulated Indy on NetBSD, with working native and compatible application launch and a reproducible demonstration. A screenshot or themed substitute alone does not satisfy this milestone. The physical desktop remains required for the first hardware release.

## Milestone 4 Usable first release

- [x] Package the IRIX personality as a loadable kernel module modeled after `compat_linux`, with a reproducible build/install path and explicit kernel-version/architecture dependencies. [First milestone on our fork](results/2026-11-03-irix-module.md); stock-kernel delivery remains below.
- [ ] Audit core dependencies, including `selcommon_kern`, the pthread-initialization `emul.e_sigmask` hook and the opt-in `EMUL_NOCLDSTOP_CONT` policy; upstream or remove them to enable deployment on a compatible standard NetBSD kernel.
- [x] Qualify module load, dependency resolution, refusal to unload while in use, unload/reload after exit, and the application regressions on a kernel without the built-in IRIX personality. Normal boot and the desktop also pass in the [module cycle](results/2026-11-03-irix-module.md).
- [x] Deliver a reusable [module-based manual CHD](results/2026-11-03-irix-module-image.md), with matching kernel/module hashes, boot configuration, graphical login/logout and direct-CHD desktop qualification.
- [ ] Boot the qualified build on the physical Indy and repeat ABI and desktop acceptance there.
- [ ] Validate real storage, networking, cache/DMA behavior, input and local display; record differences from emulation.
- [ ] Package a reproducible installation for the first supported configuration.
- [ ] Provide an import workflow for the selected original runtime and desktop files.
- [ ] Deliver the original IRIX installers with qualified dependency/conflict reporting, installation history, catalog hooks and repeatable upgrade/removal. Keep the runtime-bootstrap import distinct from ongoing installation through inst/Software Manager.
- [ ] Build a small maintained native software set, starting with networking and development tools.
- [ ] Qualify the selected legacy applications using representative work, not just startup.
- [ ] Measure desktop responsiveness, application startup, memory use, and any software rendering.
- [ ] Evaluate native browser feasibility separately; document any remote browser option as remote execution.
- [ ] Demonstrate a host update followed by the compatibility and desktop checks.

Acceptance: another tester can install the system on the named physical Indy configuration, reproduce the local desktop demonstration, run the named applications, and repeat the checks after an update. An emulator-only result does not satisfy hardware-release acceptance.

## Milestone 5 Indigo2 and Octane expansion

- [ ] Classify the available Indigo2 by CPU and graphics; identify reusable support and additional port work.
- [ ] Map the missing NetBSD Octane board support using historical OpenBSD and current Linux implementations as references.
- [ ] Implement and validate Octane boot, memory, interrupts, and essential I/O under NetBSD.
- [ ] Add the available Octane's display and input support, keeping graphics acceleration separately scoped.
- [ ] Qualify each added configuration through boot, I/O, X display, desktop, and applications.
- [ ] Investigate one graphics family for acceleration only after basic desktop operation is stable.
- [ ] Apply the [reverse-engineering workflow](ARCHITECTURE.md#reverse-engineering-workflow) to missing graphics initialization, command submission and synchronization behavior; retain probes and physical observations for each implemented interface.

Acceptance: per-configuration support records and repeatable desktop results. Fuel remains outside the execution queue until hardware access and a port assessment exist.

## Evidence to retain

Each completed experiment should record the following in this repository, with large disk images and imported runtimes kept separately:

| Field | Required information |
| --- | --- |
| Environment | Emulator/version/build features or physical machine; CPU, graphics, memory, firmware, OS and runtime versions |
| Build | Source revisions, toolchain, configuration, patch set, artifact checksums |
| Procedure | Commands, inputs, expected outcome, cold boot or snapshot origin, recovery steps where applicable |
| Result | Logs, observed behavior, failures, and relevant timing or resource measurements |
| Interpretation | Which capability passed, which remains unresolved, and the next decision |

Use small reproducible programs for ABI differences. Use original IRIX as the behavioral reference and hardware runs for device claims. Record a desktop component as original, adapted, replaced, or unsupported so the preservation result remains clear.

## Outstanding decisions

| Question | When to resolve |
| --- | --- |
| Exact physical CPU and graphics configurations | Inventory alongside Milestone 0; required before hardware qualification |
| Reference IRIX version and desktop package set | Selected: IRIX 6.5.22m, desktop packages 6.5.22; complete dependency and clean-reference qualification next |
| Priority applications beyond the desktop | Milestone 0 |
| Required 3D performance and graphics APIs | Before committing to an acceleration effort |
| Qualified emulator and NetBSD build baseline | Milestones 0–1; proposed versions in the emulation plan |
| Required original components versus acceptable replacements | For any component that fails preservation feasibility |
| Native browser target and acceptable performance | Milestone 4 feasibility investigation |

Begin with the development setup checklist, the pinned emulator build and the NetBSD boot loop. Inventory hardware and qualify the supplied reference media alongside implementation. These results will support credible effort estimates and a concrete implementation backlog.
