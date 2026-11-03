# Development history through 2026-11-03

This is the former README, retained as a chronological evidence index. Its
status statements describe individual checkpoints and may be superseded by
later entries. Use the [current README](../README.md), [development guide](DEVELOPMENT.md)
and [selected image](../lab/irix-installed-desktop/image.json) for current work.

The [2026-11-03 GIMP cycle](results/2026-11-03-irix-gimp.md) adds full action
mask registration and preserves explicit self-masks with NODEFER. It passes
80 paired signal records, 80 existing regressions and four native controls.
Original GIMP setup, paintbrush editing, XCF/PNG save and reopen, normal exit
and catalog launch now work with the additional original resources. Missing
preference-backup rename and broader plug-in behavior remain explicit limits.
The replacement CHD carries these resources and the module update; separate
fresh GIMP and xdm/desktop checks precede promotion. The next systematic
application pass is recorded in the [catalog checklist](ICON-CATALOG.md).

The [2026-11-03 winterm reliability cycle](results/2026-11-03-winterm-reliability.md)
adds PTY window sizing and SIGCHLD NOCLDSTOP support in the loadable module.
The native shell handoff preserves initial dimensions; foreground jobs receive
SIGWINCH and typing `exit` closes an extra terminal normally. Paired original
IRIX/NetBSD checks cover both ABIs and dispatch paths under root and UID 1234.
Earlier statements below about missing terminal resize/exit are historical.
The intermittent collapsed-font case reproduces in native and IRIX Xlib on
the same Xorg Type1 face. Terminal defaults now use the verified SGI Screen
bitmap font; the native Type1 failure, continued-child notifications and
IRIX nanosleep remain separate gaps. The replacement CHD passes three IRIX
login/resize cycles, normal terminal exit and the separate native ctwm login;
all owned test guests halt cleanly.


Xiri is a project to give real SGI workstations a maintained operating system while preserving the IRIX desktop and selected IRIX applications.

The agreed target is the full original IRIX desktop on NetBSD and X.org, supported by an IRIX binary compatibility layer. Modern applications would run natively on NetBSD. Preserving the desktop includes its behavior and integration, beyond window decorations. Running the original desktop on this foundation remains to be demonstrated.

Our working IRIX reference is **IRIX 6.5.22**, confirmed by the user on
2026-11-02. The installed reference image is recorded as **6.5.22m** in the
[baseline provenance](results/2026-10-30-irix-vendor-baseline.md).
Current application and desktop results apply to that reference release;
other IRIX releases need their own qualification.

The desired final delivery form for the compatibility layer is a **loadable
NetBSD kernel module modeled after `compat_linux`**, with separate runtime-import
and desktop/session packages. Current qualification uses a built-in personality
in our custom kernel; module packaging and resolution of remaining core dependencies are
tracked in the [roadmap](ROADMAP.md#milestone-4-usable-first-release).

## Project status

Planning and feasibility research started 2026-10-14. Milestone 0 setup began 2026-10-29 with a [pinned IRIS CLI build](../lab/iris/README.md). NetBSD 11.0 now installs and boots to multiuser on an emulated R4400 Indy, including a [host-built kernel with a distinct identifier](results/2026-10-30-netbsd-kernel.md). The fork now runs [unmodified vendor o32 asa and n32 echo](results/2026-10-30-irix-lp64.md) through their original runtimes on an LP64 kernel, with bounded ELF loading, syscall dispatch, mappings and heap growth. The [Toolchest session diagnosis](results/2026-10-31-irix-toolchest-session.md) identifies its subsequent SIGSEGV as a missing `HOME` environment variable. An explicit session wrapper avoids that crash. The [qualified select subset](results/2026-10-31-irix-select.md) supplies measured readiness and timeout behavior on both kernels. The [xstat checkpoint](results/2026-10-31-irix-xstat.md) adds measured o32/n32 metadata layouts and pathname behavior. The [fxstat checkpoint](results/2026-10-31-irix-fxstat.md) supplies descriptor metadata and removes the observed app-defaults allocator crash. The [SIOCNREAD checkpoint](results/2026-10-31-irix-siocnread.md) removes the following XIO failure: Toolchest now renders its menu and passes 60-second visibility/Expose-redraw checks as root and uid 1234. Original [xclock now draws analog and digital windows](results/2026-10-31-irix-elfmap-relocation.md) after bounded library relocation, with [timekeeping now qualified](results/2026-11-01-irix-time.md) in bounded UTC runs. The [access follow-up](results/2026-10-31-irix-winterm-access.md) clears the earlier xwsh locale/font crash: it now reads the staged resources and reaches PTY setup, and the [PTY allocator checkpoint](results/2026-10-31-irix-pty.md) advances it through native master allocation and slave permissions. The [process checkpoint](results/2026-11-01-irix-process.md) adds bounded fork, signal masks and child-exit waits; xwsh now draws its terminal window and opens the slave in its child. The [shell checkpoint](results/2026-11-01-irix-shell.md) adds descriptor/session queries and native exec: the original winterm launcher now opens xwsh with NetBSD’s interactive shell and accepts typed commands. A native helper supplies controlling-terminal setup and avoids the observed layered-tty teardown panic. Signal handlers, resize and normal application exit in xwsh remain to qualify. General IRIX application compatibility, the original desktop, and hardware validation remain pending.

The [signal implementation](results/2026-11-01-irix-signal.md) now passes
1,216 native records and 76 controls, covering measured traditional-signal
registration, o32/n32 delivery/return, FPU restoration and wait-any reaping.
The [installed-image import](results/2026-11-01-irix-installed-desktop.md)
now includes 166 catalog entries across 17 tabs, with xmahjongg rendering
under 4Dwm. That first import still showed Icon Catalog's Blank fallback.
The [reusable CHD guide](XIRI-IMAGE.md) covers manual IRIS testing and
automated reuse; the [copy ledger](IRIX-IMPORT.md) records every source
and destination, including persistent fonts and executable library modes.
Original-installer retries are deferred; copying files does not qualify
installation or every application's runtime behavior.

The [desktop launch qualification](results/2026-11-02-desktop-launch.md)
adds a 1280×1024 Newport screen and working Toolchest actions for the
supported applications. Open Unix Shell starts original xwsh with a native
NetBSD shell; two repeated menu launches accept typed commands. The initial
Applications menu opened xclock, Icon Catalog and xmahjongg. The
current configuration removes that custom menu at the user's request and
retains Desktop → Open Unix Shell and Find → Icon Catalog.

The [desktop repair checkpoint](results/2026-11-02-desktop-services.md)
adds measured directory/link/poll support and native FAM. Icon Catalog now
discovers 18 pages and lists the 21 Freeware entries; FileManager lists native
files and folders. Reporting MAC support as absent removes the Trusted Path
panel. The [icon repair](results/2026-11-02-desktop-icons.md) now restores
application-specific Freeware artwork and FileManager folder/document icons.
It adds measured record locks and seek offsets, and gives native FAM the
imported pathname view. Broader catalog application behavior remains to be qualified.
Intermittent xwsh startup failures and automatic closure after shell exit
also remain open. Xorg stays in use;
further Xsgi experiments are deferred.

The [application follow-up](results/2026-11-02-irix-elfmap-high.md) fixes
GIMP's high-address GTK library mapping failure (700 mapping checks and
32 controls). GIMP now reaches Xorg, then stops at signal-handler registration;
it is not yet usable. That investigation identified Catalog Open's static
IRIX shell boundary, and xosview needs kernel statistics interfaces. Desktop sessions now start
applications in the configured home, with `pwd` verified in initial and
Toolchest-launched winterm windows.

The [original-shell checkpoint](results/2026-11-02-irix-vendor-shell.md)
now runs unmodified IRIX `/bin/sh`, with 772 checks across LP64 CI/ordinary
and o32 regression guests. Icon Catalog successfully launches xmahjongg on
two double-click attempts. Full interactive job control remains to qualify;
winterm keeps its native shell default. A native
null-device binding also fixes shell redirection inside the emulation tree.
The [shell image](results/2026-11-02-irix-shell-image.md) packages these
changes, with fresh graphical boot/logout and actual CHD catalog-launch checks.

The [desktop behavior update](results/2026-11-02-irix-desktop-behavior.md)
adds FAM execution feedback for running/closed application icons, the original
granite backdrop and filesystem/home/Dumpster desktop icons. It uses existing
vendor artwork and one additional bitmap; the kernel is unchanged. The
[new manual CHD](results/2026-11-02-desktop-behavior-image.md) includes
these changes and labels the ordinary desktop user as `xiritest`; root
remains the service launcher. Dumpster
operations, transient launch animation, preferences and session restoration
remain separate work. Native xdm integration is deferred until the desktop
behavior is more complete.

The [desktop usability update](results/2026-11-02-desktop-usability.md)
adds graphical console boot/login, working Toolchest and desktop-menu logout,
window-manager readiness before starting clients, and native rpcbind's
duplicate-loopback fix. Two desktop sessions return to the console with
clients/services removed. Session restoration remains separate work.

The reported responsiveness gap and the supplied SGI driver guide are tracked
in [Newport performance](NEWPORT.md). The [framed-console/XAA cycle](results/2026-11-02-newport-framed-acceleration.md)
fixes RGB24 fast-clear colors and plane masks in IRIS. Accelerated and software
native drawing checks now produce identical screenshots. The
[xmahjongg follow-up](results/2026-11-03-newport-xmahjongg.md) corrects XAA
texture coordinates in the Xorg Newport driver: all 617,684 game-window pixels
now match software rendering with Composite enabled. Performance measurements
and broader Render support remain open. Separate [manual images](XIRI-IMAGE.md)
retain the framed kernel and corrected emulator for comparison.

The candidate build host has been [inventoried](results/2026-10-29-host-inventory.md), and [NetBSD 11.0 sgimips inputs](../lab/netbsd-11.0/README.md) have been downloaded and verified. The [guest lab](../lab/indy-netbsd/README.md), [installation record](results/2026-10-29-indy-netbsd-install.md), and [debugger/probe results](results/2026-10-30-netbsd-debugger-probe.md) retain the configuration, commands, evidence, and unresolved emulator issues. Use the [development setup checklist](ROADMAP.md#development-setup-checklist) for the remaining work.

Confirmed project requirements:

- Run on real SGI hardware.
- Use Indy emulation for initial implementation and testing, then qualify physical machines.
- Use NetBSD as the underlying operating system.
- Preserve the IRIX desktop.
- Support selected legacy IRIX applications alongside maintained software.
- Use the original IRIX installers and package hooks to add applications to Icon Catalog.
- Bootstrap the desktop by importing already installed applications and their existing Icon Catalog registration from the user's IRIX image; qualify installer support afterward.
- Give ordinary users native homes under `/usr/people/<username>`; IRIX root sessions use `/`.
- Keep planning and execution documents in this repository.

Hardware available for testing: Indy, Indigo2, and Octane. Exact CPU, graphics, RAM, and installed IRIX versions remain to be inventoried. Fuel is a possible later target; access to one has not been established.

## Planning documents

- [Feasibility and platform choice](FEASIBILITY.md): comparison of approaches, existing work, hardware support, and sources.
- [Proposed architecture](ARCHITECTURE.md): compatibility boundaries, original desktop preservation, graphics, and application integration.
- [Execution roadmap](ROADMAP.md): experiments, dependencies, acceptance criteria, and unresolved choices.
- [Fork development](FORKS.md): the consolidated IRIS and NetBSD `xiri` branches, pinned worktrees and reproduction rules.
- [IRIX software and user homes](IRIX-SOFTWARE.md): original installers, xmahjongg/Freeware acceptance and the native account layout.
- [IRIX resource checklist](IRIX-RESOURCES.md): extracted image assets, runtime evidence, remaining resources and native session state.
- [Indy emulation environment](EMULATION.md): IRIS versus MAME, build and image prerequisites, development loop, and qualification gates.

## First milestone

The NetBSD development loop now reaches an automated probe: installer, installed guest, host-built kernel, debugger breakpoints, and a bounded smoke test. The [kernel build script](../scripts/build-netbsd-kernel.sh) retains debug symbols; the [probe harness](../scripts/probe-netbsd.py) uses fresh disk copies and passes in CI and ordinary IRIS execution with the R4400 profile. [Repeated disk and network integrity tests](results/2026-10-30-netbsd-io.md) also pass in both modes, using the IRIS fork. [Snapshot tests](results/2026-10-30-netbsd-snapshots.md) now pass in both modes after a RAM-map restore fix on `xiri/netbsd-snapshots`. The current transfer profile uses HTTP or 1024-byte NFS requests; fragmented NFS corruption and the earlier installer HTTP stall remain open. [NetBSD X/Newport display and input](results/2026-10-30-netbsd-x11.md) now pass in both modes with software rendering and an IRIS keyboard-controller fix. The later framed-console/XAA cycle qualifies RGB24 drawing at 1280×1024; performance measurements remain open. MAME provides an independent comparison and fallback and has not yet been tested by this project.

The [historical `COMPAT_IRIX` audit](results/2026-10-30-irix-compat-audit.md) led to an opt-in personality on the NetBSD fork. Bounded ELF loading, runtime queries, and mapping now support the first successful unmodified vendor application: [IRIX asa runs its filter](results/2026-10-30-irix-o32-dispatch.md), using the original libc and rld. The `xiri/irix-o32-dispatch` branch adds checked indirect calls, the actual page-size query, and non-fixed mapping hints. The [lab](../lab/irix-o32/README.md#vendor-asa-execution) checks the output against original IRIX, as root and as an ordinary user, alongside the earlier runtime and static regressions in both emulator modes. This is a bounded o32 application path. A separate [64-bit native baseline](results/2026-10-30-netbsd64-native.md) now boots the LP64 kernel and tests native o32/n32/n64 execution after firmware-call and emulator TLB fixes. The [LP64 personality extension](results/2026-10-30-irix-lp64.md) now runs unmodified n32 echo alongside o32 asa, using explicit ABI marshalling, ELF32 auxiliary data and bounded heap growth. Both programs retain their original libc/rld and pass as root and an ordinary user. The [dual-ABI lab](../lab/irix-lp64/README.md) retains loader, dispatch, heap, native and original-IRIX comparisons; the same source also preserves the established 32-bit-kernel regression route.

The [desktop startup audit](results/2026-10-30-irix-desktop-startup.md) resolved their library closures and recorded the first blockers: an unsupported TCP socket call for Toolchest, and a 4 KiB-aligned library mapping plus relocation requirements for 4Dwm. The [initial TCP implementation](results/2026-10-30-irix-tcp.md) now creates sockets, sets options, transfers data and reproduces connection refusal. The [getsockname](results/2026-10-31-irix-sockname.md) and [getpeername](results/2026-10-31-irix-peername.md) extensions now let Toolchest query both addresses after connecting to native Xvfb. The [X-client startup interfaces](results/2026-10-31-irix-xconnect.md) now let unmodified Toolchest complete X setup and send processed requests.

The [legacy recvmsg checkpoint](results/2026-10-31-irix-recvmsg.md) now receives a 32-byte X reply and preserves the measured IRIX buffer-fault behavior. The [follow-up diagnosis](results/2026-10-31-irix-toolchest-session.md) proves that the empty environment causes Toolchest to pass a null `HOME` value to `strcpy`. Supplying `HOME` avoids that fault. The [select checkpoint](results/2026-10-31-irix-select.md) adds distinct-descriptor counting, guarded fd sets and timeouts, including delayed TCP data/EOF. It has two explicit limits: nfds above 1024 is rejected, and invalid selected descriptors receive EBADF even where IRIX ignores the tested high bit. The [xstat adapter](results/2026-10-31-irix-xstat.md) supplies pathname metadata. The [fxstat adapter](results/2026-10-31-irix-fxstat.md) now supplies descriptor metadata: Toolchest requests the correct app-defaults size, reads the full menu, and avoids the earlier allocator SIGSEGV. The [SIOCNREAD adapter](results/2026-10-31-irix-siocnread.md) now supplies measured byte-count/EOF behavior, and resource-enabled Toolchest renders its menu and passes 60-second visibility/Expose-redraw checks under both identities. The [resource/input checkpoint](results/2026-10-31-irix-toolchest-input.md) adds original keysyms and explicit SGI colors, with mouse posting, keyboard traversal, submenus and Escape checks. Application launches and broader event/session behavior remain unqualified.

The [ELF-map relocation checkpoint](results/2026-10-31-irix-elfmap-relocation.md) clears the libXmu/libXaw collision: original analog and digital xclock windows now render under both identities in CI and ordinary IRIS. The mapper passes 576 focused checks. The [time checkpoint](results/2026-11-01-irix-time.md) now supplies both calls: analog/digital clocks show current time, advance and redraw in both modes. [The PNG](results/images/2026-11-01-irix-xclock-time.png) shows the digital clock.

The [winterm fault capture](results/2026-10-31-irix-winterm-fault.md) identifies a null font object in `tuFont::getWidth` and actual unsupported `access` calls for staged locale/app-defaults files. The [access adapter](results/2026-10-31-irix-access.md) now clears this failure. The subsequent [PTY checkpoint](results/2026-10-31-irix-pty.md) supplies native allocation, device identities and slave permissions. The [process checkpoint](results/2026-11-01-irix-process.md) adds fork and child waits. The [shell checkpoint](results/2026-11-01-irix-shell.md) now runs NetBSD `/bin/sh` inside original xwsh through the unchanged winterm launcher, with real X keyboard input, a command-created marker, native session checks and descendant cleanup. [The PNG](results/images/2026-11-01-irix-winterm-shell.png) shows the prompt and command output. The [4Dwm follow-up](results/2026-11-01-irix-4dwm.md) now manages windows alongside Toolchest and the working terminal, with session saving disabled. Broader desktop services remain open; the later time checkpoint also qualifies bounded xclock updates.

The [resource checklist](IRIX-RESOURCES.md) tracks required image assets and remaining gaps; its [information sources](IRIX-RESOURCES.md#irix-information-sources) include the IRIX7 technical-publications archive and SGI desktop manuals. The [user-supplied original desktop capture](IRIX-DESKTOP-REFERENCE.md) supplies our visual reference. With Toolchest rendering observed, the [desktop acceptance plan](ROADMAP.md#milestone-3-original-desktop-proof) uses the supplied SGI interface guidelines to qualify the complete environment.

The [expanded desktop attempt](results/2026-11-01-irix-desktop-components.md)
adds original fm, bgicons and Icon Catalog to the session. The
[limit-query and executable-alignment fixes](results/2026-11-01-irix-rlimit.md)
now clear their initial startup blockers, with 4,760 NetBSD limit records and
280 loader executions passing. The [AUTORESRV follow-up](results/2026-11-01-irix-mmap-autoresrv.md)
now clears pthread-table allocation through native demand mappings.
[Measured pthread initialization](results/2026-11-01-irix-init-threads.md)
also passes, including native signal-mask synchronization and fork/exec state.
[Measured directory creation](results/2026-11-01-irix-mkdir.md) now clears
the following session-directory blocker, with 3,200 records and 1,540 native
filesystem effects verified. The [desktop retry](results/2026-11-01-irix-desktop-mkdir.md)
opens Icon Catalog's empty fallback page; system pages were not staged in that test, so
emptiness alone is not a compatibility failure. `bgicons` exits zero. The subsequent [pipe adapter](results/2026-11-01-irix-pipe.md) passes
220 exact reference comparisons and 44 native/vendor controls. The
[earlier desktop retry](results/2026-11-01-irix-desktop-pipe.md) rendered a
FileManager window but looped on select EINVAL, while CI capture timed out.
The later [desktop service repair](results/2026-11-02-desktop-services.md)
now lists native files and catalog entries. Full file operations, actions and
desktop/session behavior remain pending.

The user-provided [IRIX 6.5.22m reference](../lab/irix-reference/README.md) now boots to a shell and runs native asa/echo probes. Its 4Dwm and Toolchest are n32; native ldd confirms the inventoried library paths, and both programs reach a controlled TCP connection refusal on IRIX. Reference XFS alerts, a clean graphical session, later runtime modules and session services still need investigation. See the [prerequisites](EMULATION.md#prerequisites-and-current-gaps).

NetBSD is the chosen foundation. The experiments will determine the required compatibility work and supported configurations. Octane requires a NetBSD porting effort, using existing open-source implementations as hardware references. See the [platform decision](FEASIBILITY.md#platform-choice).

The [4Dwm loader checkpoint](results/2026-11-01-irix-elfmap-subpage.md) now handles the two 4 KiB data boundaries and passes 750 mapping/limit checks. The [fixed/local mmap checkpoint](results/2026-11-01-irix-mmap-local.md) now also clears GL initialization, with 660 mapping cases and native page-zero controls. The [measured PRDA checkpoint](results/2026-11-01-irix-prda.md) now clears that libc fault, with 80 executions / 180 records plus fork and native-exec controls. The [4Dwm session](results/2026-11-01-irix-4dwm.md) now passes reparenting, pointer focus, key delivery and dragging alongside Toolchest and a working winterm shell. Session saving is explicitly disabled; desks, restoration and complete desktop services remain open.

The [4Dwm PNG](results/images/2026-11-01-irix-4dwm-shell.png) shows
original decorations, Toolchest and the working winterm shell. This is an
initial session: saving/restoration and startup repeatability remain open.

The supplied [May 2004 Freeware media](results/2026-11-01-irix-freeware.md)
contains four CD sets and 489 distinct package names. The selected first
application is xmahjongg 3.6.1. The [installed-image path](results/2026-11-01-irix-installed-desktop.md)
now takes priority: import its existing executable, game data and **Freeware**
registration. Original `inst` and its `iconcatalogedit` hooks remain later
installation work. The [software plan](IRIX-SOFTWARE.md)
also defines persistent `/usr/people` homes shared by native and IRIX programs.

The [installer/home probe](results/2026-11-01-irix-installer.md) now verifies
native and IRIX access to one `/usr/people` home, including cold-boot
persistence. The [shared-mapping checkpoint](results/2026-11-01-irix-mmap-shared.md)
clears the installer's failed-map crash. The [bounded sproc checkpoint](results/2026-11-01-irix-sproc.md)
now passes 340 executions, 600 records and 44 controls across both kernels.
The [F_DUPFD checkpoint](results/2026-11-01-irix-dupfd.md) adds the
installer's missing descriptor allocation, with 420 exact records and 220 pipe
regressions passing. The [installer retry](results/2026-11-01-irix-installer-dupfd.md)
connects its helper's stdout/stderr. The [time checkpoint](results/2026-11-01-irix-time.md)
now passes 480 ABI records and advances original xclock. The [installer time retry](results/2026-11-01-irix-installer-time.md)
receives successful time calls but still times out. The
[helper trace](results/2026-11-01-irix-installer-helpers.md) identifies its
embedded bootstrap and qualifies four native utility aliases in the lab.
The bootstrap then exits zero, while the parent leaves it unreaped at that
checkpoint. The [signal follow-up](results/2026-11-01-irix-signal.md)
now qualifies the measured handler and wait-any subset, but the installer
has not been retried. Native `stat -qd` remains incompatible.
Distribution reading,
installation, the Freeware catalog action and graphical login persistence remain open.
