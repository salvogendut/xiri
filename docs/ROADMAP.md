# Xiri execution roadmap

Status: proposed work, updated 2026-10-15. All implementation milestones below are pending.

The agreed target is NetBSD with an IRIX personality and the existing IRIX desktop. Initial implementation and testing use an emulated Indy. The first deliverable is a reproducible NetBSD development loop, followed by desktop feasibility and physical Indy qualification. Expand to additional machines and applications after those results.

## Requirements established

- Real hardware is the primary execution target.
- Indy emulation is the initial development and test environment; IRIS is preferred pending qualification, with MAME for comparison and fallback.
- NetBSD is the underlying OS; the IRIX personality supplies selected binary compatibility.
- Indy, Indigo2, and Octane are available for testing.
- Preserve the IRIX desktop as well as selected legacy applications.
- Support maintained software alongside the preserved environment.
- Keep planning, decisions, and reproducible execution records in this repository.

## Milestone 0 Emulator and software baseline

- [ ] Provision build tools and sufficient host storage as described in the [emulation plan](EMULATION.md).
- [ ] Pin an IRIS source revision, exact Rust toolchain, dependency resolution and debug-capable build options.
- [ ] Record the emulated Indy CPU, RAM, Newport configuration, PROM, NVRAM and disk layout.
- [ ] Obtain the NetBSD sgimips installer, sets, checksums and matching source baseline.
- [ ] Obtain appropriate Indy firmware for MAME comparison; record IRIS's embedded fallback separately if used.
- [ ] Select a reference IRIX installation and record its desktop package versions.
- [ ] Identify two or three additional legacy applications and representative tasks for each.
- [ ] Inventory the desktop executables' ABIs, interpreters, libraries, resources, and supporting services.
- [ ] Record exact upstream revisions for NetBSD, historical compatibility code, MAME, and relevant drivers.

Acceptance for starting NetBSD work: a pinned emulator build, guest configuration and NetBSD input manifest. The user has no local PROM or IRIX image yet; IRIS's documented embedded PROM fallback permits the first boot attempt without an external PROM file. Original-IRIX reference acceptance additionally requires a desktop dependency manifest and a reproducible reference session. These inputs need not block the NetBSD bootstrap.

Parallel hardware preparation: inventory each physical machine's CPU, memory, graphics, firmware, storage, Ethernet and installed IRIX release. Establish serial capture and an alternate boot/storage setup for the Indy before physical testing; preserve its existing installation.

## Milestone 1 Host boot and desktop feasibility

The NetBSD boot and desktop experiments can be performed independently as their inputs become available. Both determine the implementation work needed on the first platform. Use the [emulator qualification gate](EMULATION.md#qualification-gate) to record each result.

- [ ] Boot the NetBSD installation kernel in IRIS, install to a disposable disk, and cold-boot to multiuser.
- [ ] Capture serial logs and verify persistent storage, network transfer and reboot integrity.
- [ ] Cross-build a modified kernel on the modern host and verify its build identifier in a fresh guest boot.
- [ ] Demonstrate debugger attachment, a breakpoint, and continued execution.
- [ ] Automate a probe with output, exit status, timeout and clean-state repetition; compare ordinary and CI execution.
- [ ] Qualify snapshots separately, keeping changed-kernel tests on cold boots.
- [ ] Repeat key boot and probe results in MAME when firmware is available; use it as primary if it passes a stage IRIS fails.
- [ ] Establish a usable NetBSD X display and input on emulated Newport, or record the precise driver gap.
- [ ] Run selected original desktop clients on IRIX against a dedicated modern X server.
- [ ] Record required visuals, X extensions, fonts, libraries, and helper processes; distinguish confirmed requirements from suspected ones.
- [ ] Compare historical `COMPAT_IRIX` code with current kernel interfaces and document the smallest execution experiment.

Acceptance: a repeatable installer-to-modified-kernel loop, an automated probe, and a desktop compatibility report. Record emulator failures separately from guest failures. Identify required kernel and display changes and the first desktop component to execute. A failed desktop probe should produce an actionable dependency finding.

Decision gate: if the display or desktop exposes a major feasibility obstacle, document it and revise the implementation plan before expanding the compatibility layer. Changing the NetBSD foundation or replacing original desktop components would require an explicit revision of the agreed target.

## Milestone 2 Native IRIX execution

- [ ] Execute a minimal static IRIX-format program with verified output and exit status.
- [ ] Implement the loader and runtime path behavior needed by a dynamically linked probe.
- [ ] Validate files, allocation, fork and exec, signals, and synchronization against original IRIX.
- [ ] Add the ABI coverage required by the desktop manifest; do not defer n32 if selected desktop components require it.
- [ ] Record unsupported calls and operations explicitly rather than masking them as successful.

Acceptance: repeatable static and dynamic execution, meaningful behavioral probes, and at least one useful IRIX command-line program on NetBSD in the emulated Indy. Retain the same probes for physical qualification.

## Milestone 3 Original desktop proof

- [ ] Launch the original window manager through compatibility against the host X server.
- [ ] Add Toolchest and the chosen file and session components incrementally.
- [ ] Implement required service adapters, including the measured file-notification and launch behavior.
- [ ] Show a host-native graphical application and an IRIX application in the same local session.
- [ ] Verify normal window operations, file navigation, desktop updates, and saved preferences.
- [ ] Repeat logout and login, checking process cleanup and restoration of expected state.
- [ ] Compare behavior with the reference installation and list component-level differences.

Acceptance: an original desktop session executing inside the emulated Indy on NetBSD, with working native and compatible application launch and a reproducible demonstration. A screenshot or themed substitute alone does not satisfy this milestone. The physical desktop remains required for the first hardware release.

## Milestone 4 Usable first release

- [ ] Boot the qualified build on the physical Indy and repeat ABI and desktop acceptance there.
- [ ] Validate real storage, networking, cache/DMA behavior, input and local display; record differences from emulation.
- [ ] Package a reproducible installation for the first supported configuration.
- [ ] Provide an import workflow for the selected original runtime and desktop files.
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
| Reference IRIX version and desktop package set | Milestone 0 reference work, once media is available |
| Priority applications beyond the desktop | Milestone 0 |
| Required 3D performance and graphics APIs | Before committing to an acceleration effort |
| Qualified emulator and NetBSD build baseline | Milestones 0–1; proposed versions in the emulation plan |
| Required original components versus acceptable replacements | For any component that fails preservation feasibility |
| Native browser target and acceptable performance | Milestone 4 feasibility investigation |

Begin with host capacity, the pinned emulator build and the NetBSD boot loop. Inventory hardware and acquire reference media in parallel. These results will support credible effort estimates and a concrete implementation backlog.
