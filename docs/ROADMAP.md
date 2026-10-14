# Xiri execution roadmap

Status: proposed work, 2026-10-14. All implementation milestones below are pending.

The agreed target is NetBSD with an IRIX personality and the existing IRIX desktop. The first deliverable is a measured feasibility result on one SGI workstation. Expand to additional machines and applications after that result.

## Requirements established

- Real hardware is the primary execution target.
- NetBSD is the underlying OS; the IRIX personality supplies selected binary compatibility.
- Indy, Indigo2, and Octane are available for testing.
- Preserve the IRIX desktop as well as selected legacy applications.
- Support maintained software alongside the preserved environment.
- Keep planning, decisions, and reproducible execution records in this repository.

## Milestone 0 Hardware and software baseline

- [ ] Record each machine's CPU, memory, graphics option, firmware, storage, Ethernet, and installed IRIX release.
- [ ] Select a reference IRIX installation and record its desktop package versions.
- [ ] Identify two or three additional legacy applications and representative tasks for each.
- [ ] Inventory the desktop executables' ABIs, interpreters, libraries, resources, and supporting services.
- [ ] Establish serial capture and a recoverable alternate boot or storage setup for the first machine.
- [ ] Record exact upstream revisions for the host OS, historical compatibility code, emulator, and relevant drivers.

Acceptance: a configuration inventory, a named test machine, a desktop dependency manifest, and a reproducible original-IRIX reference session. Preserve the existing installation as the comparison environment.

## Milestone 1 Host boot and desktop feasibility

The NetBSD boot and desktop experiments can be performed independently; both determine the implementation work needed on the first platform.

- [ ] Cross-build or obtain an appropriate maintained NetBSD image for the chosen Indy configuration.
- [ ] Capture a boot log and demonstrate serial console, storage, networking, and input.
- [ ] Exercise storage and networking sufficiently to expose basic DMA or cache failures.
- [ ] Establish a usable host X display on the actual graphics board, or record the precise driver gap.
- [ ] Run selected original desktop clients on IRIX against a dedicated modern X server.
- [ ] Evaluate [IRIS](FEASIBILITY.md#iris-emulator) for repeatable IRIX desktop and ABI reference runs; compare results with physical machines and qualify NetBSD guest boot separately.
- [ ] Record required visuals, X extensions, fonts, libraries, and helper processes; distinguish confirmed requirements from suspected ones.
- [ ] Compare historical `COMPAT_IRIX` code with current kernel interfaces and document the smallest execution experiment.

Acceptance: a NetBSD boot and I/O record plus a desktop compatibility report. Identify required kernel and display changes and the first desktop component to execute. A failed desktop probe should produce an actionable dependency finding.

Decision gate: if the display or desktop exposes a major feasibility obstacle, document it and revise the implementation plan before expanding the compatibility layer. Changing the NetBSD foundation or replacing original desktop components would require an explicit revision of the agreed target.

## Milestone 2 Native IRIX execution

- [ ] Execute a minimal static IRIX-format program with verified output and exit status.
- [ ] Implement the loader and runtime path behavior needed by a dynamically linked probe.
- [ ] Validate files, allocation, fork and exec, signals, and synchronization against original IRIX.
- [ ] Add the ABI coverage required by the desktop manifest; do not defer n32 if selected desktop components require it.
- [ ] Record unsupported calls and operations explicitly rather than masking them as successful.

Acceptance: repeatable static and dynamic execution, meaningful behavioral probes, and at least one useful IRIX command-line program on the maintained host. Run these on the real first target.

## Milestone 3 Original desktop proof

- [ ] Launch the original window manager through compatibility against the host X server.
- [ ] Add Toolchest and the chosen file and session components incrementally.
- [ ] Implement required service adapters, including the measured file-notification and launch behavior.
- [ ] Show a host-native graphical application and an IRIX application in the same local session.
- [ ] Verify normal window operations, file navigation, desktop updates, and saved preferences.
- [ ] Repeat logout and login, checking process cleanup and restoration of expected state.
- [ ] Compare behavior with the reference installation and list component-level differences.

Acceptance: a locally running original desktop session on the SGI, with working native and compatible application launch and a reproducible demonstration. A screenshot or themed substitute alone does not satisfy this milestone.

## Milestone 4 Usable first release

- [ ] Package a reproducible installation for the first supported configuration.
- [ ] Provide an import workflow for the selected original runtime and desktop files.
- [ ] Build a small maintained native software set, starting with networking and development tools.
- [ ] Qualify the selected legacy applications using representative work, not just startup.
- [ ] Measure desktop responsiveness, application startup, memory use, and any software rendering.
- [ ] Evaluate native browser feasibility separately; document any remote browser option as remote execution.
- [ ] Demonstrate a host update followed by the compatibility and desktop checks.

Acceptance: another tester can install the system, reproduce the desktop demonstration, run the named applications, and repeat the checks after an update.

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
| Environment | Machine, CPU, graphics, memory, firmware, OS and runtime versions |
| Build | Source revisions, toolchain, configuration, patch set, artifact checksums |
| Procedure | Commands, inputs, expected outcome, recovery steps where applicable |
| Result | Logs, observed behavior, failures, and relevant timing or resource measurements |
| Interpretation | Which capability passed, which remains unresolved, and the next decision |

Use small reproducible programs for ABI differences. Use original IRIX as the behavioral reference and hardware runs for device claims. Record a desktop component as original, adapted, replaced, or unsupported so the preservation result remains clear.

## Outstanding decisions

| Question | When to resolve |
| --- | --- |
| Exact CPU and graphics configurations | Milestone 0 |
| Reference IRIX version and desktop package set | Milestone 0 |
| Priority applications beyond the desktop | Milestone 0 |
| Required 3D performance and graphics APIs | Before committing to an acceleration effort |
| NetBSD branch, kernel configuration, and patch baseline | Milestone 1 |
| Required original components versus acceptable replacements | For any component that fails preservation feasibility |
| Native browser target and acceptable performance | Milestone 4 feasibility investigation |

Begin with the inventory and the two Milestone 1 experiments. Their results will support credible effort estimates and a concrete implementation backlog.
