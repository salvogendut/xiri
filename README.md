# Xiri

Xiri is a project to give real SGI workstations a maintained operating system while preserving the IRIX desktop and selected IRIX applications.

The agreed target is the full original IRIX desktop on NetBSD and X.org, supported by an IRIX binary compatibility layer. Modern applications would run natively on NetBSD. Preserving the desktop includes its behavior and integration, beyond window decorations. Running the original desktop on this foundation remains to be demonstrated.

## Project status

Planning and feasibility research started 2026-10-14. Milestone 0 setup began 2026-10-29 with a [pinned IRIS CLI build](lab/iris/README.md). NetBSD 11.0 now installs and boots to multiuser on an emulated R4400 Indy, including a [host-built kernel with a distinct identifier](docs/results/2026-10-30-netbsd-kernel.md). The fork now runs [unmodified vendor o32 asa and n32 echo](docs/results/2026-10-30-irix-lp64.md) through their original runtimes on an LP64 kernel, with bounded ELF loading, syscall dispatch, mappings and heap growth. The [Toolchest session diagnosis](docs/results/2026-10-31-irix-toolchest-session.md) identifies its subsequent SIGSEGV as a missing `HOME` environment variable. An explicit session wrapper avoids that crash. The [qualified select subset](docs/results/2026-10-31-irix-select.md) supplies measured readiness and timeout behavior on both kernels; version-2 `xstat` remains the next configuration boundary. General IRIX application compatibility, the original desktop, and hardware validation remain pending.

The candidate build host has been [inventoried](docs/results/2026-10-29-host-inventory.md), and [NetBSD 11.0 sgimips inputs](lab/netbsd-11.0/README.md) have been downloaded and verified. The [guest lab](lab/indy-netbsd/README.md), [installation record](docs/results/2026-10-29-indy-netbsd-install.md), and [debugger/probe results](docs/results/2026-10-30-netbsd-debugger-probe.md) retain the configuration, commands, evidence, and unresolved emulator issues. Use the [development setup checklist](docs/ROADMAP.md#development-setup-checklist) for the remaining work.

Confirmed project requirements:

- Run on real SGI hardware.
- Use Indy emulation for initial implementation and testing, then qualify physical machines.
- Use NetBSD as the underlying operating system.
- Preserve the IRIX desktop.
- Support selected legacy IRIX applications alongside maintained software.
- Keep planning and execution documents in this repository.

Hardware available for testing: Indy, Indigo2, and Octane. Exact CPU, graphics, RAM, and installed IRIX versions remain to be inventoried. Fuel is a possible later target; access to one has not been established.

## Planning documents

- [Feasibility and platform choice](docs/FEASIBILITY.md): comparison of approaches, existing work, hardware support, and sources.
- [Proposed architecture](docs/ARCHITECTURE.md): compatibility boundaries, original desktop preservation, graphics, and application integration.
- [Execution roadmap](docs/ROADMAP.md): experiments, dependencies, acceptance criteria, and unresolved choices.
- [Indy emulation environment](docs/EMULATION.md): IRIS versus MAME, build and image prerequisites, development loop, and qualification gates.

## First milestone

The NetBSD development loop now reaches an automated probe: installer, installed guest, host-built kernel, debugger breakpoints, and a bounded smoke test. The [kernel build script](scripts/build-netbsd-kernel.sh) retains debug symbols; the [probe harness](scripts/probe-netbsd.py) uses fresh disk copies and passes in CI and ordinary IRIS execution with the R4400 profile. [Repeated disk and network integrity tests](docs/results/2026-10-30-netbsd-io.md) also pass in both modes, using the IRIS fork. [Snapshot tests](docs/results/2026-10-30-netbsd-snapshots.md) now pass in both modes after a RAM-map restore fix on `xiri/netbsd-snapshots`. The current transfer profile uses HTTP or 1024-byte NFS requests; fragmented NFS corruption and the earlier installer HTTP stall remain open. [NetBSD X/Newport display and input](docs/results/2026-10-30-netbsd-x11.md) now pass in both modes with software rendering and an IRIS keyboard-controller fix. XAA acceleration and full display geometry remain open. MAME provides an independent comparison and fallback and has not yet been tested by this project.

The [historical `COMPAT_IRIX` audit](docs/results/2026-10-30-irix-compat-audit.md) led to an opt-in personality on the NetBSD fork. Bounded ELF loading, runtime queries, and mapping now support the first successful unmodified vendor application: [IRIX asa runs its filter](docs/results/2026-10-30-irix-o32-dispatch.md), using the original libc and rld. The `xiri/irix-o32-dispatch` branch adds checked indirect calls, the actual page-size query, and non-fixed mapping hints. The [lab](lab/irix-o32/README.md#vendor-asa-execution) checks the output against original IRIX, as root and as an ordinary user, alongside the earlier runtime and static regressions in both emulator modes. This is a bounded o32 application path. A separate [64-bit native baseline](docs/results/2026-10-30-netbsd64-native.md) now boots the LP64 kernel and tests native o32/n32/n64 execution after firmware-call and emulator TLB fixes. The [LP64 personality extension](docs/results/2026-10-30-irix-lp64.md) now runs unmodified n32 echo alongside o32 asa, using explicit ABI marshalling, ELF32 auxiliary data and bounded heap growth. Both programs retain their original libc/rld and pass as root and an ordinary user. The [dual-ABI lab](lab/irix-lp64/README.md) retains loader, dispatch, heap, native and original-IRIX comparisons; the same source also preserves the established 32-bit-kernel regression route.

The [desktop startup audit](docs/results/2026-10-30-irix-desktop-startup.md) resolved their library closures and recorded the first blockers: an unsupported TCP socket call for Toolchest, and a 4 KiB-aligned library mapping plus relocation requirements for 4Dwm. The [initial TCP implementation](docs/results/2026-10-30-irix-tcp.md) now creates sockets, sets options, transfers data and reproduces connection refusal. The [getsockname](docs/results/2026-10-31-irix-sockname.md) and [getpeername](docs/results/2026-10-31-irix-peername.md) extensions now let Toolchest query both addresses after connecting to native Xvfb. The [X-client startup interfaces](docs/results/2026-10-31-irix-xconnect.md) now let unmodified Toolchest complete X setup and send processed requests.

The [legacy recvmsg checkpoint](docs/results/2026-10-31-irix-recvmsg.md) now receives a 32-byte X reply and preserves the measured IRIX buffer-fault behavior. The [follow-up diagnosis](docs/results/2026-10-31-irix-toolchest-session.md) proves that the empty environment causes Toolchest to pass a null `HOME` value to `strcpy`. Supplying `HOME` avoids that fault. The [select checkpoint](docs/results/2026-10-31-irix-select.md) adds distinct-descriptor counting, guarded fd sets and timeouts, including delayed TCP data/EOF. It has two explicit limits: nfds above 1024 is rejected, and invalid selected descriptors receive EBADF even where IRIX ignores the tested high bit. Version-2 `xstat` still blocks the menu configuration check even with supplied resources installed. A usable window and event handling remain unqualified. Once IRIX X applications work, the [desktop acceptance plan](docs/ROADMAP.md#milestone-3-original-desktop-proof) uses the supplied SGI interface guidelines to qualify the complete environment.

The user-provided [IRIX 6.5.22m reference](lab/irix-reference/README.md) now boots to a shell and runs native asa/echo probes. Its 4Dwm and Toolchest are n32; native ldd confirms the inventoried library paths, and both programs reach a controlled TCP connection refusal on IRIX. Reference XFS alerts, a clean graphical session, later runtime modules and session services still need investigation. See the [prerequisites](docs/EMULATION.md#prerequisites-and-current-gaps).

NetBSD is the chosen foundation. The experiments will determine the required compatibility work and supported configurations. Octane requires a NetBSD porting effort, using existing open-source implementations as hardware references. See the [platform decision](docs/FEASIBILITY.md#platform-choice).
