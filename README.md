# Xiri

Xiri is a project to give real SGI workstations a maintained operating system while preserving the IRIX desktop and selected IRIX applications.

The agreed target is NetBSD underneath, an IRIX binary compatibility layer, and the existing IRIX desktop. Modern applications would run natively on NetBSD. Preserving the desktop includes its behavior and integration, beyond window decorations. Running the original desktop on this foundation remains to be demonstrated.

## Project status

Planning and feasibility research, started 2026-10-14 and updated 2026-10-15. No kernel, compatibility layer, desktop port, emulator boot validation, or hardware validation has been implemented in this repository.

Environment setup and testing are pending resource provisioning. Use the [development setup checklist](docs/ROADMAP.md#development-setup-checklist) to prepare the build host and required inputs.

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

Establish a reproducible NetBSD development loop on an emulated Indy: installer, installed guest, host-built kernel, and automated probe. IRIS is the preferred initial harness, subject to NetBSD qualification; MAME provides an independent comparison and fallback. Neither has been boot-tested by this project.

Characterize the original IRIX desktop's dependencies once reference media is available. The user has no local PROM or IRIX image yet. IRIS documents an embedded PROM fallback, allowing the first NetBSD experiment to proceed without a separate PROM file; the IRIX reference and desktop experiments still require an IRIX installation. See the [prerequisites](docs/EMULATION.md#prerequisites-and-current-gaps).

NetBSD is the chosen foundation. The experiments will determine the required compatibility work and supported configurations. Octane requires a NetBSD porting effort, using existing open-source implementations as hardware references. See the [platform decision](docs/FEASIBILITY.md#platform-choice).
