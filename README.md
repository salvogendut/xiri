# Xiri

Xiri is a project to give real SGI workstations a maintained operating system while preserving the IRIX desktop and selected IRIX applications.

The agreed target is NetBSD underneath, an IRIX binary compatibility layer, and the existing IRIX desktop. Modern applications would run natively on NetBSD. Preserving the desktop includes its behavior and integration, beyond window decorations. Running the original desktop on this foundation remains to be demonstrated.

## Project status

Planning and feasibility research, started 2026-10-14. No kernel, compatibility layer, desktop port, or hardware validation has been implemented in this repository.

Confirmed project requirements:

- Run on real SGI hardware.
- Use NetBSD as the underlying operating system.
- Preserve the IRIX desktop.
- Support selected legacy IRIX applications alongside maintained software.
- Keep planning and execution documents in this repository.

Hardware available for testing: Indy, Indigo2, and Octane. Exact CPU, graphics, RAM, and installed IRIX versions remain to be inventoried. Fuel is a possible later target; access to one has not been established.

## Planning documents

- [Feasibility and platform choice](docs/FEASIBILITY.md): comparison of approaches, existing work, hardware support, and sources.
- [Proposed architecture](docs/ARCHITECTURE.md): compatibility boundaries, original desktop preservation, graphics, and application integration.
- [Execution roadmap](docs/ROADMAP.md): experiments, dependencies, acceptance criteria, and unresolved choices.

## First milestone

Establish a reproducible NetBSD boot on a suitable Indy configuration and characterize the original IRIX desktop's dependencies. These two experiments determine whether the proposed foundation can support the project's defining feature.

NetBSD is the chosen foundation. The experiments will determine the required compatibility work and supported configurations. Octane requires a NetBSD porting effort, using existing open-source implementations as hardware references. See the [platform decision](docs/FEASIBILITY.md#platform-choice).
