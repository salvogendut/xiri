# Xiri

Xiri is a project to give real SGI workstations a maintained operating system while preserving the IRIX desktop and selected IRIX applications.

The agreed target is the full original IRIX desktop on NetBSD and X.org, supported by an IRIX binary compatibility layer. Modern applications would run natively on NetBSD. Preserving the desktop includes its behavior and integration, beyond window decorations. Running the original desktop on this foundation remains to be demonstrated.

The desired final delivery form for the compatibility layer is a **loadable
NetBSD kernel module modeled after `compat_linux`**, with separate runtime-import
and desktop/session packages. Current qualification uses a built-in personality
in our custom kernel; module packaging and resolution of remaining core dependencies are
tracked in the [roadmap](docs/ROADMAP.md#milestone-4-usable-first-release).

## Project status

Planning and feasibility research started 2026-10-14. Milestone 0 setup began 2026-10-29 with a [pinned IRIS CLI build](lab/iris/README.md). NetBSD 11.0 now installs and boots to multiuser on an emulated R4400 Indy, including a [host-built kernel with a distinct identifier](docs/results/2026-10-30-netbsd-kernel.md). The fork now runs [unmodified vendor o32 asa and n32 echo](docs/results/2026-10-30-irix-lp64.md) through their original runtimes on an LP64 kernel, with bounded ELF loading, syscall dispatch, mappings and heap growth. The [Toolchest session diagnosis](docs/results/2026-10-31-irix-toolchest-session.md) identifies its subsequent SIGSEGV as a missing `HOME` environment variable. An explicit session wrapper avoids that crash. The [qualified select subset](docs/results/2026-10-31-irix-select.md) supplies measured readiness and timeout behavior on both kernels. The [xstat checkpoint](docs/results/2026-10-31-irix-xstat.md) adds measured o32/n32 metadata layouts and pathname behavior. The [fxstat checkpoint](docs/results/2026-10-31-irix-fxstat.md) supplies descriptor metadata and removes the observed app-defaults allocator crash. The [SIOCNREAD checkpoint](docs/results/2026-10-31-irix-siocnread.md) removes the following XIO failure: Toolchest now renders its menu and passes 60-second visibility/Expose-redraw checks as root and uid 1234. Original [xclock now draws analog and digital windows](docs/results/2026-10-31-irix-elfmap-relocation.md) after bounded library relocation, with timekeeping still unsupported. The [access follow-up](docs/results/2026-10-31-irix-winterm-access.md) clears the earlier xwsh locale/font crash: it now reads the staged resources and reaches PTY setup, and the [PTY allocator checkpoint](docs/results/2026-10-31-irix-pty.md) advances it through native master allocation and slave permissions. The [process checkpoint](docs/results/2026-11-01-irix-process.md) adds bounded fork, signal masks and child-exit waits; xwsh now draws its terminal window and opens the slave in its child. The [shell checkpoint](docs/results/2026-11-01-irix-shell.md) adds descriptor/session queries and native exec: the original winterm launcher now opens xwsh with NetBSD’s interactive shell and accepts typed commands. A native helper supplies controlling-terminal setup and avoids the observed layered-tty teardown panic. Foreign signal handlers, resize and normal application exit remain open. General IRIX application compatibility, the original desktop, and hardware validation remain pending.

The candidate build host has been [inventoried](docs/results/2026-10-29-host-inventory.md), and [NetBSD 11.0 sgimips inputs](lab/netbsd-11.0/README.md) have been downloaded and verified. The [guest lab](lab/indy-netbsd/README.md), [installation record](docs/results/2026-10-29-indy-netbsd-install.md), and [debugger/probe results](docs/results/2026-10-30-netbsd-debugger-probe.md) retain the configuration, commands, evidence, and unresolved emulator issues. Use the [development setup checklist](docs/ROADMAP.md#development-setup-checklist) for the remaining work.

Confirmed project requirements:

- Run on real SGI hardware.
- Use Indy emulation for initial implementation and testing, then qualify physical machines.
- Use NetBSD as the underlying operating system.
- Preserve the IRIX desktop.
- Support selected legacy IRIX applications alongside maintained software.
- Use the original IRIX installers and package hooks to add applications to Icon Catalog.
- Give ordinary users native homes under `/usr/people/<username>`; IRIX root sessions use `/`.
- Keep planning and execution documents in this repository.

Hardware available for testing: Indy, Indigo2, and Octane. Exact CPU, graphics, RAM, and installed IRIX versions remain to be inventoried. Fuel is a possible later target; access to one has not been established.

## Planning documents

- [Feasibility and platform choice](docs/FEASIBILITY.md): comparison of approaches, existing work, hardware support, and sources.
- [Proposed architecture](docs/ARCHITECTURE.md): compatibility boundaries, original desktop preservation, graphics, and application integration.
- [Execution roadmap](docs/ROADMAP.md): experiments, dependencies, acceptance criteria, and unresolved choices.
- [Fork development](docs/FORKS.md): the consolidated IRIS and NetBSD `xiri` branches, pinned worktrees and reproduction rules.
- [IRIX software and user homes](docs/IRIX-SOFTWARE.md): original installers, xmahjongg/Freeware acceptance and the native account layout.
- [IRIX resource checklist](docs/IRIX-RESOURCES.md): extracted image assets, runtime evidence, remaining resources and native session state.
- [Indy emulation environment](docs/EMULATION.md): IRIS versus MAME, build and image prerequisites, development loop, and qualification gates.

## First milestone

The NetBSD development loop now reaches an automated probe: installer, installed guest, host-built kernel, debugger breakpoints, and a bounded smoke test. The [kernel build script](scripts/build-netbsd-kernel.sh) retains debug symbols; the [probe harness](scripts/probe-netbsd.py) uses fresh disk copies and passes in CI and ordinary IRIS execution with the R4400 profile. [Repeated disk and network integrity tests](docs/results/2026-10-30-netbsd-io.md) also pass in both modes, using the IRIS fork. [Snapshot tests](docs/results/2026-10-30-netbsd-snapshots.md) now pass in both modes after a RAM-map restore fix on `xiri/netbsd-snapshots`. The current transfer profile uses HTTP or 1024-byte NFS requests; fragmented NFS corruption and the earlier installer HTTP stall remain open. [NetBSD X/Newport display and input](docs/results/2026-10-30-netbsd-x11.md) now pass in both modes with software rendering and an IRIS keyboard-controller fix. XAA acceleration and full display geometry remain open. MAME provides an independent comparison and fallback and has not yet been tested by this project.

The [historical `COMPAT_IRIX` audit](docs/results/2026-10-30-irix-compat-audit.md) led to an opt-in personality on the NetBSD fork. Bounded ELF loading, runtime queries, and mapping now support the first successful unmodified vendor application: [IRIX asa runs its filter](docs/results/2026-10-30-irix-o32-dispatch.md), using the original libc and rld. The `xiri/irix-o32-dispatch` branch adds checked indirect calls, the actual page-size query, and non-fixed mapping hints. The [lab](lab/irix-o32/README.md#vendor-asa-execution) checks the output against original IRIX, as root and as an ordinary user, alongside the earlier runtime and static regressions in both emulator modes. This is a bounded o32 application path. A separate [64-bit native baseline](docs/results/2026-10-30-netbsd64-native.md) now boots the LP64 kernel and tests native o32/n32/n64 execution after firmware-call and emulator TLB fixes. The [LP64 personality extension](docs/results/2026-10-30-irix-lp64.md) now runs unmodified n32 echo alongside o32 asa, using explicit ABI marshalling, ELF32 auxiliary data and bounded heap growth. Both programs retain their original libc/rld and pass as root and an ordinary user. The [dual-ABI lab](lab/irix-lp64/README.md) retains loader, dispatch, heap, native and original-IRIX comparisons; the same source also preserves the established 32-bit-kernel regression route.

The [desktop startup audit](docs/results/2026-10-30-irix-desktop-startup.md) resolved their library closures and recorded the first blockers: an unsupported TCP socket call for Toolchest, and a 4 KiB-aligned library mapping plus relocation requirements for 4Dwm. The [initial TCP implementation](docs/results/2026-10-30-irix-tcp.md) now creates sockets, sets options, transfers data and reproduces connection refusal. The [getsockname](docs/results/2026-10-31-irix-sockname.md) and [getpeername](docs/results/2026-10-31-irix-peername.md) extensions now let Toolchest query both addresses after connecting to native Xvfb. The [X-client startup interfaces](docs/results/2026-10-31-irix-xconnect.md) now let unmodified Toolchest complete X setup and send processed requests.

The [legacy recvmsg checkpoint](docs/results/2026-10-31-irix-recvmsg.md) now receives a 32-byte X reply and preserves the measured IRIX buffer-fault behavior. The [follow-up diagnosis](docs/results/2026-10-31-irix-toolchest-session.md) proves that the empty environment causes Toolchest to pass a null `HOME` value to `strcpy`. Supplying `HOME` avoids that fault. The [select checkpoint](docs/results/2026-10-31-irix-select.md) adds distinct-descriptor counting, guarded fd sets and timeouts, including delayed TCP data/EOF. It has two explicit limits: nfds above 1024 is rejected, and invalid selected descriptors receive EBADF even where IRIX ignores the tested high bit. The [xstat adapter](docs/results/2026-10-31-irix-xstat.md) supplies pathname metadata. The [fxstat adapter](docs/results/2026-10-31-irix-fxstat.md) now supplies descriptor metadata: Toolchest requests the correct app-defaults size, reads the full menu, and avoids the earlier allocator SIGSEGV. The [SIOCNREAD adapter](docs/results/2026-10-31-irix-siocnread.md) now supplies measured byte-count/EOF behavior, and resource-enabled Toolchest renders its menu and passes 60-second visibility/Expose-redraw checks under both identities. The [resource/input checkpoint](docs/results/2026-10-31-irix-toolchest-input.md) adds original keysyms and explicit SGI colors, with mouse posting, keyboard traversal, submenus and Escape checks. Application launches and broader event/session behavior remain unqualified.

The [ELF-map relocation checkpoint](docs/results/2026-10-31-irix-elfmap-relocation.md) clears the libXmu/libXaw collision: original analog and digital xclock windows now render under both identities in CI and ordinary IRIS. The mapper passes 576 focused checks. Clock time remains at the epoch because `time`/`gettimeofday` are unsupported.

The [winterm fault capture](docs/results/2026-10-31-irix-winterm-fault.md) identifies a null font object in `tuFont::getWidth` and actual unsupported `access` calls for staged locale/app-defaults files. The [access adapter](docs/results/2026-10-31-irix-access.md) now clears this failure. The subsequent [PTY checkpoint](docs/results/2026-10-31-irix-pty.md) supplies native allocation, device identities and slave permissions. The [process checkpoint](docs/results/2026-11-01-irix-process.md) adds fork and child waits. The [shell checkpoint](docs/results/2026-11-01-irix-shell.md) now runs NetBSD `/bin/sh` inside original xwsh through the unchanged winterm launcher, with real X keyboard input, a command-created marker, native session checks and descendant cleanup. [The PNG](docs/results/images/2026-11-01-irix-winterm-shell.png) shows the prompt and command output. The [4Dwm follow-up](docs/results/2026-11-01-irix-4dwm.md) now manages windows alongside Toolchest and the working terminal, with session saving disabled. Complete desktop services precede xclock timekeeping.

The [resource checklist](docs/IRIX-RESOURCES.md) tracks required image assets and remaining gaps; the [user-supplied original desktop capture](docs/IRIX-DESKTOP-REFERENCE.md) supplies our visual reference. With Toolchest rendering observed, the [desktop acceptance plan](docs/ROADMAP.md#milestone-3-original-desktop-proof) uses the supplied SGI interface guidelines to qualify the complete environment.

The [expanded desktop attempt](docs/results/2026-11-01-irix-desktop-components.md)
adds original fm, bgicons and Icon Catalog to the session. The
[limit-query and executable-alignment fixes](docs/results/2026-11-01-irix-rlimit.md)
now clear their initial startup blockers, with 4,760 NetBSD limit records and
280 loader executions passing. The [AUTORESRV follow-up](docs/results/2026-11-01-irix-mmap-autoresrv.md)
now clears pthread-table allocation through native demand mappings.
[Measured pthread initialization](docs/results/2026-11-01-irix-init-threads.md)
also passes, including native signal-mask synchronization and fork/exec state.
[Measured directory creation](docs/results/2026-11-01-irix-mkdir.md) now clears
the following session-directory blocker, with 3,200 records and 1,540 native
filesystem effects verified. The [desktop retry](docs/results/2026-11-01-irix-desktop-mkdir.md)
opens Icon Catalog's empty fallback page; system page data is not staged, so
emptiness alone is not a compatibility failure. `bgicons` exits zero. The subsequent [pipe adapter](docs/results/2026-11-01-irix-pipe.md) passes
220 exact reference comparisons and 44 native/vendor controls. The
[desktop retry](docs/results/2026-11-01-irix-desktop-pipe.md) now renders a
FileManager window, but it loops on select EINVAL; file browsing and actions
remain unqualified. Ordinary shell checks pass; CI desktop capture times out.
The static closure and resource locations are inventoried; full desktop
startup, file operations and services remain pending.

The user-provided [IRIX 6.5.22m reference](lab/irix-reference/README.md) now boots to a shell and runs native asa/echo probes. Its 4Dwm and Toolchest are n32; native ldd confirms the inventoried library paths, and both programs reach a controlled TCP connection refusal on IRIX. Reference XFS alerts, a clean graphical session, later runtime modules and session services still need investigation. See the [prerequisites](docs/EMULATION.md#prerequisites-and-current-gaps).

NetBSD is the chosen foundation. The experiments will determine the required compatibility work and supported configurations. Octane requires a NetBSD porting effort, using existing open-source implementations as hardware references. See the [platform decision](docs/FEASIBILITY.md#platform-choice).

The [4Dwm loader checkpoint](docs/results/2026-11-01-irix-elfmap-subpage.md) now handles the two 4 KiB data boundaries and passes 750 mapping/limit checks. The [fixed/local mmap checkpoint](docs/results/2026-11-01-irix-mmap-local.md) now also clears GL initialization, with 660 mapping cases and native page-zero controls. The [measured PRDA checkpoint](docs/results/2026-11-01-irix-prda.md) now clears that libc fault, with 80 executions / 180 records plus fork and native-exec controls. The [4Dwm session](docs/results/2026-11-01-irix-4dwm.md) now passes reparenting, pointer focus, key delivery and dragging alongside Toolchest and a working winterm shell. Session saving is explicitly disabled; desks, restoration and complete desktop services remain open.

The [4Dwm PNG](docs/results/images/2026-11-01-irix-4dwm-shell.png) shows
original decorations, Toolchest and the working winterm shell. This is an
initial session: saving/restoration and startup repeatability remain open.

The supplied [May 2004 Freeware media](docs/results/2026-11-01-irix-freeware.md)
contains four CD sets and 489 distinct package names. The selected first
installation target is xmahjongg 3.6.1, using original `inst` and its own
`iconcatalogedit` hooks for the **Freeware** page. The [software plan](docs/IRIX-SOFTWARE.md)
also defines persistent `/usr/people` homes shared by native and IRIX programs.

The [installer/home probe](docs/results/2026-11-01-irix-installer.md) now verifies
native and IRIX access to one `/usr/people` home, including cold-boot
persistence. The [shared-mapping checkpoint](docs/results/2026-11-01-irix-mmap-shared.md)
clears the installer's failed-map crash. The [bounded sproc checkpoint](docs/results/2026-11-01-irix-sproc.md)
now passes 340 executions, 600 records and 44 controls across both kernels.
The [installer retry](docs/results/2026-11-01-irix-installer-sproc.md) creates
its subcommand and executes native `/bin/sh`; the next concrete failure is
`fcntl(F_DUPFD)` returning EINVAL during pipe setup. Repeated unsupported
gettimeofday calls and IRIX-style helper paths also remain. Distribution
reading, installation, the Freeware catalog action and graphical login
persistence remain open.
