# Xiri execution roadmap

Status: execution started, updated 2026-10-31. Host inventory, the pinned IRIS build, verified NetBSD inputs, the installed R4400 guest, and a host-built custom kernel boot are complete. Debugger breakpoints and an automated smoke probe now pass, including comparison of CI and ordinary execution. Bounded disk and network integrity tests also pass in both modes. Snapshot restore, CI rollback, and post-restore cold boots now pass with the fork's RAM-map fix. NetBSD X/Newport display and input now pass in both modes with software rendering and a keyboard-controller fix. The historical IRIX source audit, fork kernel baseline, marked static o32 execution, bounded argument/file/memory probes, and writable ELF data/BSS are complete. Supplied IRIX 6.5.22m media provides native asa/echo observations and an unmodified vendor rejection baseline. Bounded o32 interpreter loading, runtime queries, SGI_ELFMAP, indirect dispatch, and allocation now run unmodified vendor asa through its original libc/rld. Its output and the interface probes are compared with original IRIX. The separate LP64 kernel/native baseline passes after firmware-call and emulator TLB fixes. The bounded dual-ABI personality now runs n32 echo alongside o32 asa, with explicit argument widths, ELF32 auxiliary data and heap growth. Desktop library closure and initial resource/session inventory identify 4Dwm’s alignment/relocation requirements. The initial TCP subset and getsockname output translation now let Toolchest connect to a native X server and query its local address; getpeername is its next blocker. XAA acceleration, full display geometry, fragmented NFS corruption, and the earlier installer HTTP stall remain open; original desktop and later implementation milestones are pending.

The agreed target is NetBSD with an IRIX personality and the existing IRIX desktop. Initial implementation and testing use an emulated Indy. The development loop now supports [unmodified vendor asa/echo and bounded o32/n32 probes](results/2026-10-30-irix-lp64.md) on the NetBSD fork. Broader ABI coverage, desktop feasibility, and physical Indy qualification follow before expanding to additional machines and applications.

## Development setup checklist

The candidate host inventory, pinned IRIS CLI build, verified NetBSD inputs, guest installation, and host kernel build are complete. The R4400 guest reaches multiuser after a cold boot with the custom kernel, supports debugger breakpoints, and passes an automated probe. Repeated disk writes, cold-read integrity, and bidirectional network transfers pass in both execution modes; see the [I/O results](results/2026-10-30-netbsd-io.md). See the [installation record](results/2026-10-29-indy-netbsd-install.md), [kernel build record](results/2026-10-30-netbsd-kernel.md), and [debugger/probe results](results/2026-10-30-netbsd-debugger-probe.md).

Before starting implementation:

1. Sync this repository and inventory the selected build host's OS, CPU architecture, RAM, free storage and installed tools. Recheck capacity rather than relying on the earlier session measurements in the [emulation plan](EMULATION.md#inspected-session-environment).
2. Arrange storage for source, toolchains, object files, guest disks and snapshots. Retain the 30–50 GiB planning allowance and adjust it from actual usage.
3. Provision a debug-capable IRIS source build with a recorded Rust toolchain and native dependencies, plus NetBSD cross-build tools. Check the selected host's library compatibility before choosing any packaged emulator.
4. Use the [verified NetBSD 11.0 input baseline](../lab/netbsd-11.0/README.md) for the installer, sets, checksums and matching source. Use the supplied Indy PROM and [IRIX 6.5.22m reference image](results/2026-10-30-irix-vendor-baseline.md) for vendor and desktop experiments. The first native shell session works; investigate its XFS alerts and qualify MAME and graphics separately.
5. Preserve the [qualified o32/n32 application paths](results/2026-10-30-irix-lp64.md) while expanding toward the supplied n32 desktop. The LP64 kernel now runs unmodified asa and echo through their original runtimes, with 8 KiB page checks and the established 32-bit-kernel regressions. The [TCP path](results/2026-10-30-irix-tcp.md) and [getsockname extension](results/2026-10-31-irix-sockname.md) now reach a controlled native X connection and local-address query; qualify getpeername output translation next, then observe subsequent X requirements. Handle 4Dwm’s unaligned libraries and overlapping linked addresses separately. Complete runtime resource/service qualification and a clean graphical reference session. Add the required behavior with paired original-IRIX probes. Keep the [X11 limits](results/2026-10-30-netbsd-x11.md) explicit and compare CI with ordinary execution for each new workload.
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
- [x] Establish a usable NetBSD X display and input on emulated Newport, or record the precise driver gap. [Software-rendered Xorg at 1024×768, depth 24](results/2026-10-30-netbsd-x11.md) passes pixel, keyboard/mouse, twm/xterm, and clean-shutdown checks in both modes after an IRIS keyboard-controller fix. XAA colors and full framebuffer geometry remain open.
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
- [ ] Qualify getpeername output translation and unconnected-socket errors, then repeat Toolchest’s X connection and measure later handshake/event-loop requirements.
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
