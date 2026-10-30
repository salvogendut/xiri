# Xiri

Xiri is a project to give real SGI workstations a maintained operating system while preserving the IRIX desktop and selected IRIX applications.

The agreed target is NetBSD underneath, an IRIX binary compatibility layer, and the existing IRIX desktop. Modern applications would run natively on NetBSD. Preserving the desktop includes its behavior and integration, beyond window decorations. Running the original desktop on this foundation remains to be demonstrated.

## Project status

Planning and feasibility research started 2026-10-14. Milestone 0 setup began 2026-10-29 with a [pinned IRIS CLI build](lab/iris/README.md). NetBSD 11.0 now installs and boots to multiuser on an emulated R4400 Indy, including a [host-built kernel with a distinct identifier](docs/results/2026-10-30-netbsd-kernel.md). The compatibility layer, desktop port, and hardware validation remain pending.

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

The NetBSD development loop now reaches an automated probe: installer, installed guest, host-built kernel, debugger breakpoints, and a bounded smoke test. The [kernel build script](scripts/build-netbsd-kernel.sh) retains debug symbols; the [probe harness](scripts/probe-netbsd.py) uses fresh disk copies and passes in CI and ordinary IRIS execution with the R4400 profile. [Repeated disk and network integrity tests](docs/results/2026-10-30-netbsd-io.md) also pass in both modes, using the IRIS fork. [Snapshot tests](docs/results/2026-10-30-netbsd-snapshots.md) now pass in both modes after a RAM-map restore fix on `xiri/netbsd-snapshots`. The current transfer profile uses HTTP or 1024-byte NFS requests; fragmented NFS corruption and the earlier installer HTTP stall remain open. [NetBSD X/Newport display and input](docs/results/2026-10-30-netbsd-x11.md) now pass in both modes with software rendering and an IRIS keyboard-controller fix. XAA acceleration and full display geometry remain open. The next source-only step is auditing historical `COMPAT_IRIX` and defining the smallest execution experiment. MAME provides an independent comparison and fallback and has not yet been tested by this project.

Characterize the original IRIX desktop's dependencies once reference media is available. The user has no local PROM or IRIX image yet. IRIS documents an embedded PROM fallback, allowing the first NetBSD experiment to proceed without a separate PROM file; the IRIX reference and desktop experiments still require an IRIX installation. See the [prerequisites](docs/EMULATION.md#prerequisites-and-current-gaps).

NetBSD is the chosen foundation. The experiments will determine the required compatibility work and supported configurations. Octane requires a NetBSD porting effort, using existing open-source implementations as hardware references. See the [platform decision](docs/FEASIBILITY.md#platform-choice).
