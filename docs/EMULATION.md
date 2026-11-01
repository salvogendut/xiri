# Indy emulation development environment

Initial decision and research date: 2026-10-15; implementation strategy reviewed on 2026-10-19. Execution started on 2026-10-29: the pinned IRIS build installs and boots NetBSD 11.0 on the R4400 profile. A [host-built custom kernel](results/2026-10-30-netbsd-kernel.md) also cold-booted to multiuser on 2026-10-30, followed by [debugger and automated probe checks](results/2026-10-30-netbsd-debugger-probe.md). Later [I/O](results/2026-10-30-netbsd-io.md), [snapshot](results/2026-10-30-netbsd-snapshots.md), [X display/input](results/2026-10-30-netbsd-x11.md) and [LP64 native](results/2026-10-30-netbsd64-native.md) checkpoints extend that baseline. The [Toolchest session lab](../lab/irix-toolchest/README.md) isolates the empty-environment crash using native ptrace controls. The [select lab](../lab/irix-select/README.md) compares guarded records with original IRIX, runs delayed-readiness peers, repeats Toolchest with HOME/resources and native X controls, and checks the previous transport suite on the new kernels. The [xstat lab](../lab/irix-xstat/README.md) adds an independent native metadata observer, paired IRIX layouts, page-boundary copy checks, namespace shadow/fallback tests and staged Toolchest window-tree observations. Its fault follow-up reuses the validated native ptrace controls. The [fxstat lab](../lab/irix-fxstat/README.md) adds descriptor metadata, a native fstat observer, shared-serializer xstat regressions, and frame captures during staged Toolchest launches. The [SIOCNREAD lab](../lab/irix-siocnread/README.md) adds a paired TCP byte-count/EOF oracle, exact four-byte copyout guards, and staged Toolchest rendering captures. Its longer window observer measures X map state and Expose redraws against an independent native control. The [xclock lab](../lab/irix-xclock/README.md) adds a simpler original client, native clock control, window-state samples and paired framebuffer captures. A [loader trace lab](results/2026-10-31-irix-xclock-elfmap.md) uses controlled native breakpoints to capture actual SGI_ELFMAP headers and occupied memory, confirming the libXmu/libXaw collision. The [relocation lab](../lab/irix-elfmap-relocation/README.md) now compares o32/n32 synthetic layouts with original IRIX, checks both NetBSD kernels and captures original xclock windows in both modes. The [winterm fault capture](results/2026-10-31-irix-winterm-fault.md) validates a null-font delay-slot fault and actual access/seek arguments with native ptrace/font controls. The [access lab](../lab/irix-access/README.md) adds six real/effective identity combinations and exact permission/path records, including namespace shadow denial. Its winterm observer verifies original resource reads and the later PTY boundary against native controls. The [PTY lab](../lab/irix-pty/README.md) adds paired allocation-interface records, the original libc helper, native bidirectional PTY controls and xwsh traces through its later fork boundary. Its disposable namespace uses native ptyfs plus a nullfs view inside the foreign root. The current user-authorized limit is four independent IRIS instances at once; track every instance and stop it after its run. Kernel builds remain sequential with at most two compiler jobs. Trace text is compressed on the guest and transferred over the existing serial console. A separate syscall-timing run isolates select entry/return intervals from launch and drain overhead. It decodes LP64 timestamp fields explicitly: the installed o32 kdump displays their fractional seconds as zero. Broader hardware qualification and emulator speed comparisons remain pending.

## Decision

Use **IRIS as the preferred initial development environment, conditional on passing the NetBSD qualification below**. Keep **MAME as an independent comparison environment and fallback**. Begin development on an emulated Indy; the physical Indy, Indigo2, and Octane remain the deployment targets.

IRIS offers the more convenient documented development loop: a control socket, serial capture, integrated network services, disk overlays, and machine snapshots. MAME provides a separate implementation with a mature debugger and Lua automation. This recommendation concerns workflow, not a demonstrated difference in emulation speed or correctness.

IRIS explicitly says that NetBSD guests are not regularly tested. Its reported IRIX desktops do not prove that a current NetBSD kernel works. MAME's IRIX boot instructions do not establish that either. If IRIS fails a qualification stage that MAME passes, use MAME for that stage and retain a minimal IRIS reproducer. If both fail, investigate the boot image, firmware, and guest support before starting compatibility-layer work. [IRIS README][iris-readme], [MAME Indy source][mame-indy].

Additional reference recorded on 2026-10-16: [SGIEmu](FEASIBILITY.md#sgiemu-emulator), particularly its Newport implementation, device tests and tracing runner. Its inspected documentation lists Windows-only operation and missing Ethernet emulation. NetBSD has not been qualified by Xiri, so this addition does not change the initial harness choice.

Additional reference recorded on 2026-10-19: [irix-emu](FEASIBILITY.md#irix-emu-emulator), an R5000/Newport implementation with graphics tracing and device tests. Ethernet is documented as unimplemented and NetBSD remains unqualified. Its glpass library uses emulator hypercalls and a macOS host GPU; evaluate that separately from hardware-driver correctness and original-IRIX reference runs. The initial IRIS/MAME choice remains in place.

Additional reference recorded on 2026-10-19: [qemu-sgi-ip22](FEASIBILITY.md#qemu-sgi-ip22-emulator), a QEMU Indy/R4400 model with device-trace comparison notes, reported IRIX/Linux boot and preliminary Newport support. Its documented ARCS firmware boot path, TAP networking and incomplete graphics need separate qualification; Xiri has not tested NetBSD on it. Use it as another source for device behavior and test methods while retaining the initial IRIS/MAME choice.

## Recommended implementation strategy

Use an existing full-system Indy emulator and develop Xiri inside NetBSD/sgimips. Keep the emulator changes limited to defects and instrumentation exposed by the workload, with small patches suitable for upstream submission. The project's deliverable remains NetBSD plus IRIX compatibility on physical SGI hardware; developing a new emulator would add a separate CPU and device implementation to maintain.

### Roles for the available implementations

| Implementation | Recommended role | Condition for expanding that role |
| --- | --- | --- |
| IRIS | First candidate for everyday NetBSD development and original-IRIX reference sessions | Pass the boot, I/O, debugger and repeatability gates below |
| MAME | Independent reproduction of key failures and fallback development environment | Demonstrate the relevant NetBSD stage with a recorded configuration |
| qemu-sgi-ip22 | Additional kernel/device investigation candidate and source of differential-tracing methods | Qualify NetBSD, its firmware path and required devices; partial graphics must be assessed before desktop use |
| SGIEmu and irix-emu | Focused device and graphics research references | Demonstrate the required guest behavior before depending on either as a harness |

This division follows the [source assessments](FEASIBILITY.md#existing-work). QEMU's broader infrastructure makes its SGI fork interesting for future automation, but the inspected fork's reported IRIX/Linux boots do not establish NetBSD or desktop readiness. Do not require every emulator to be operational before beginning Xiri work. Select a fallback because it passes a needed test, and retain the failing case for the other implementation.

### One machine configuration, two guest installations

Begin with the proposed Indy IP24/R5000/Newport configuration below. Once the physical Indy is inventoried, align the CPU instruction set, RAM and graphics variant where supported, and record any differences. Keep an original-IRIX reference disk and a separate NetBSD/Xiri development disk, each with its own writable state. They can run sequentially when host resources are limited.

Cross-build NetBSD kernels and test programs on the modern host. Run the same behavioral probes on original IRIX and Xiri, comparing outputs, errors, signals and desktop operations. Preserve the original IRIX libraries and rendering path for reference runs. Emulator-specific host-call or host-GPU bridges belong to separate experiments; they add interfaces unavailable on the physical machine.

Keep the test procedure independent of any one emulator: launch, capture serial output, wait for an explicit guest marker, transfer a probe, collect its result and reset the guest. Implement only the first required backend adapter, then add others when a comparison is useful. Retain guest tests and expected behavior across backends, while recording differences in CPU, firmware and device configuration.

### Order of work

1. Boot an unmodified NetBSD installation kernel in IRIS, install it and reach multiuser over serial. Establish this baseline before changing the compatibility layer.
2. Verify disk persistence, networking and a changed host-built kernel. Demonstrate a debugger breakpoint and an automated probe with a timeout. Use the debug-capable interpreter profile first; assess optimized profiles against that baseline later.
3. Reproduce a failure in MAME or another suitable implementation before attributing it to NetBSD. If a broad emulator blocker prevents progress, qualify an alternative instead of making Xiri depend on an emulator-specific workaround.
4. Add ABI and desktop tests incrementally. Use a dedicated external X display to isolate client/ABI problems when useful, and qualify the NetBSD X server on emulated Newport separately for the local desktop.
5. Run a physical Indy boot and I/O smoke test as soon as hardware access permits, then repeat ABI and desktop milestones there. Full hardware-release acceptance still follows the [roadmap](ROADMAP.md). Early physical checks reduce the risk of depending on inaccurate cache, DMA or interrupt behavior.

For graphics research, start with one operation and compare the original driver's accesses with emulator traces, then verify the proposed behavior on hardware. A successful host-GPU demo or agreement between two emulators is supporting evidence, not a physical-driver acceptance result. Extend to Indigo2 and Octane after the Indy execution path is established.

## Comparison for Xiri

| Need | IRIS | MAME | Consequence |
| --- | --- | --- | --- |
| Common machine | Indy IP24, R4400 or R5000, Newport | Indy R4600 variants and R5000 `indy_5015`, Newport | Start with R5000/Newport; record RAM and firmware separately |
| Current NetBSD guest | BSD-related fixes and settings exist; regular testing is not claimed | Must qualify the selected release and driver | A successful boot and I/O test decide suitability |
| Kernel investigation | Monitor, memory/register inspection, breakpoints, GDB stub in suitable builds | CPU debugger, breakpoints, watchpoints, scripting | Preserve guest kernel symbols and test debugger attachment early |
| Automation | Control socket, `iris-ci`, serial logging, offscreen display capture | Lua scripting and command-line configuration | IRIS has less harness plumbing, but its supplied guest helpers assume IRIX |
| Network boot and transfer | Integrated NAT, BOOTP/DHCP, TFTP and NFS services | Configure the networking provider available in the selected build and external services as needed | IRIS is the preferred first network-boot experiment |
| Reset between tests | Raw-image COW, CHD sidecars, documented Newport machine snapshots | Disk-image workflows; Indy driver does not advertise `MACHINE_SUPPORTS_SAVE` | Use cold boots as the baseline; do not promise MAME snapshot restoration |
| Firmware | Embedded PROM fallback documented | Matching external ROM set required | No separate PROM file is technically needed to attempt the first IRIS boot |
| Hardware validation | Emulator-specific behavior must be checked | Useful second implementation, also imperfect graphics/sound flags | Neither replaces physical qualification |

Sources: [IRIS options and build features][iris-features], [storage and automation][iris-storage], [networking][iris-networking], [MAME release driver][mame-indy], [MAME debugger][mame-debugger], [Lua interface][mame-lua].

## Baselines to record

The inspected IRIS revision is `21c0ecb024b3a7dc9e11514fa1b5302363071bf6`. MAME source was inspected at release tag `mame0289`. These are research baselines, not qualified Xiri releases. Pin the actual source revision and build options when creating the lab; record any changes from these baselines.

Guest configuration:

- The working IRIS baseline uses `indy_ip24`/`r4400`/`newport`. The originally proposed R5000 profile panicked in the NetBSD 11.0 installer with `r5k picache line size 16`. The proposed MAME `indy_5015` comparison remains untested; select and record its CPU configuration before comparing results. Physical Indy inventory is still pending.
- Use a RAM size supported by both configurations, recording the actual amount each reports. Start with IRIS's default 256 MiB and inspect MAME's configuration before claiming equivalence.
- NetBSD 11.0/sgimips, big-endian MIPS, initially the 32-bit `INSTALL32_IP2x` and `GENERIC32_IP2x` kernels. A 64-bit-capable CPU does not require starting with a 64-bit kernel. [NetBSD installation notes][netbsd-install].
- Separate NetBSD and original-IRIX disks; separate working copies, NVRAM, sockets, ports, and logs for each emulator instance. Record MAC addresses and PROM settings.
- A minimal NetBSD installation first, adding X sets for display tests. The supplied reference is now IRIX 6.5.22m with 6.5.22 desktop packages; its limited native session and unresolved XFS alerts are recorded in the [vendor baseline](results/2026-10-30-irix-vendor-baseline.md).

The NetBSD release establishes an unmodified baseline. Pin matching source before cross-building; upgrading the guest or emulator becomes an explicit regression test.

## Prerequisites and current gaps

Milestone 0 provisioning began on 2026-10-29. A [candidate build host was inventoried](results/2026-10-29-host-inventory.md), a [pinned IRIS CLI build completed](results/2026-10-29-iris-build.md), and [NetBSD inputs were verified](results/2026-10-29-netbsd-inputs.md). The [installed R4400 guest](results/2026-10-29-indy-netbsd-install.md) boots to multiuser, including with the [custom kernel built on the host](results/2026-10-30-netbsd-kernel.md). The [development setup checklist](ROADMAP.md#development-setup-checklist) records the remaining actions.

| Item | Why it is needed | Current status |
| --- | --- | --- |
| Host build environment and storage | Emulator, cross-toolchain, source/object trees, guest disks | Fedora 44 host, IRIS build environment, and NetBSD cross-tools provisioned; installed guest checkpoint and kernel test disk retained |
| IRIS source and Rust toolchain | Debug-capable emulator build | Initial [build record](results/2026-10-29-iris-build.md) retained; current [fork revision](../lab/iris/README.md) adds the NFS fix. R4400 install, kernel debugging, smoke, and bounded I/O tests passed; smoke and I/O comparisons include ordinary execution |
| NetBSD sgimips installer, sets, checksums and matching source | Boot baseline and modified-kernel loop | Inputs verified; guest installed; all four source sets extracted; host-built `XIRI_INDY` kernel and cross-GDB support the tested build/debug/probe loop |
| Indy PROM | Firmware baseline and MAME ROM verification | Supplied Indy PROM matches the recorded SHA-1 and boots IRIS; MAME verification remains pending |
| IRIX installation media or an image from the user's machine | Original behavior, libraries, desktop and application inventory | IRIX 6.5.22m image extracted read-only; native commands and vendor ABI inventory recorded |
| MAME executable and matching ROM configuration | Independent reproduction of failures | Not installed |
| Physical Indy configuration and serial access | Later hardware qualification | Machine available; CPU, graphics and connection details pending |

The IRIS fallback supplied firmware for the NetBSD bootstrap. The user has now supplied an installed IRIX 6.5.22m image and matching Indy PROM; see the [reference lab](../lab/irix-reference/README.md). A clean filesystem/desktop reference qualification is still pending. Keep original firmware, OS images, and imported desktop binaries outside Git; retain manifests, hashes, acquisition notes, configurations, and test logs here.

For MAME's R5000 Indy, the inspected driver names `ip24prom.070-9101-011.bin` (512 KiB; SHA-1 `ac663a4db68528e400487e98cbf901f620fb30ce`). Verify the installed build's requirements with `mame indy_5015 -listroms` and `-verifyroms`; use its media/slot listings to derive attachment options. Obtain the appropriate firmware from an available machine or another authorized source rather than assuming any Indy dump matches. [MAME ROM declarations][mame-indy].

### Inspected session environment

Read-only inspection of the session environment on 2026-10-15 found Debian 12 on x86_64, glibc 2.36, four logical CPUs, about 6.4 GiB RAM, and about **4 GiB free workspace storage**. GCC, CMake, Make, Python and GitHub CLI were available; Rust/Cargo and either emulator were not found in the checked locations. These measurements describe that session environment; recheck the selected build host before provisioning.

IRIS's inspected release workflow builds Linux x64 on Ubuntu 24.04 and documents glibc 2.39 for its Linux packages. It also builds the distributed executables with `lightning`, which removes interactive debugging. Plan a source build on the selected build host; check its dependencies and library compatibility. The packaged executable is not assumed to work in the inspected Debian 12 session. [IRIS release workflow][iris-release].

Reserve roughly **30–50 GiB of free storage** for source, toolchains, object files, two guest environments and snapshots. This is a planning allowance, not a measured minimum. The inspected session's 4 GiB is insufficient for that complete lab. Select build parallelism from the build host's measured RAM and CPU capacity; two jobs was the conservative starting point for the inspected session.

## IRIS build and execution profiles

Build the CLI and automation client first. The intended starting command, from the pinned source checkout after dependencies are installed, is:

```sh
cargo build --release --bin iris --bin iris-ci
```

This command was executed on 2026-10-29 with an exact nightly and locked dependencies; see the [build record](results/2026-10-29-iris-build.md). The source selects a rolling `nightly` toolchain by default, so retain the recorded toolchain, lockfile, native dependency versions and build features when reproducing it. The full GUI packaging dependency list is broader than this CLI build. [Cargo manifest][iris-cargo], [toolchain selection][iris-toolchain], [release build dependencies][iris-release].

Use these rules for the initial profile:

- Keep `lightning` and instruction fusion off so breakpoints remain usable. Leave experimental CPU `jitv2` off until the baseline passes; measure optimized builds separately.
- Keep private `hostcall` services and `hostgl` off. Compatibility probes must exercise the interfaces that the physical SGI will have.
- Retain the documented default `scsi_deferred_int = true` for BSD compatibility.
- Test ordinary execution first. `--ci` enables automation but also documented fidelity shortcuts; compare ordinary and CI runs before accepting CI results as representative.
- For unattended graphics tests, use `--ci` with Newport still enabled. **Explicit `--headless` disables Newport graphics**; it is unsuitable for desktop acceptance. `--ci-display` exposes the window during harness development.
- Run emulator qualification suites sequentially, shut down each guest, and verify that no `iris` or `iris-ci` processes remain after the batch. Limit kernel builds to two jobs on this host.
- Capture serial output and assign each instance its own CI socket and ports. Confirm the NetBSD console channel; documentation names such as `/dev/ttyd1` refer to IRIX.

These distinctions come from [IRIS build/runtime options][iris-features] and the [automation guide][iris-storage]. The `iris-ci boot`, `login`, `run`, `put` and `get` examples target IRIX prompts and device paths. Qualify or adapt them for NetBSD rather than treating them as an existing NetBSD harness.

## Boot and development loop

1. **Reach the PROM and installer.** Start with serial capture. Serve the uncompressed NetBSD installation kernel using IRIS's `--tftp-dir`; test its BOOTP/TFTP path. Use the PROM-supported ELF or ECOFF format. If networking blocks bootstrap, try the official sgimips bootable CD image. An ordinary ISO is insufficient: the SGI boot path requires a volume header. [IRIS TFTP options][iris-features], [NetBSD boot instructions][netbsd-install].
2. **Install to a disposable guest disk.** Use the installer to establish the SGI volume header, boot loader and native filesystem. Verify disk boot, multiuser operation, network transfer and filesystem integrity after reboot. Preserve a clean base image before enabling per-run overlays.
3. **Build on the modern host.** Use NetBSD's `build.sh` cross-tools for `sgimips`/`mipseb`, then the `GENERIC32_IP2x` kernel and small probes. Keep object/tool directories separate from source and retain a symbol-bearing kernel for debugging. Compilation on the host is the main way to shorten iteration; do not depend on building the OS inside the MIPS guest. [NetBSD cross-build guide][netbsd-build].
4. **Boot a changed kernel.** Transfer through the qualified TFTP path or guest networking. Prove that a distinct kernel build identifier appears in the boot log. Keep local disk root initially; NFS-root adds another service to qualify. IRIS's NFS export is a candidate for artifact transfer after ordinary guest networking works.
5. **Run and collect probes.** Capture output, exit status, kernel messages and host elapsed time. Later run the same behavioral probes on the original-IRIX guest and compare results with Xiri. Add the desktop's X and service tests once the necessary runtime is available.
6. **Check independent execution.** Reproduce key milestones in MAME, then on the physical Indy before claiming hardware support. Investigate differences rather than changing tests to fit one emulator.

The [qualified snapshot profile](results/2026-10-30-netbsd-snapshots.md) supports repeated userspace tests, including fresh-process restore after the RAM-map fix. A restored RAM snapshot resumes the old kernel, so **cold-boot each changed kernel**. Couple snapshot state with its disk overlay, NVRAM, configuration, emulator revision and guest build. External NFS writes are not rolled back with guest RAM. Do not share live writable disks between emulator instances or assume their snapshot/overlay formats are interchangeable. [IRIS storage model][iris-storage].

MAME automation should use Lua, console capture and an external wall-clock timeout. `-seconds_to_run` counts emulated time and does not replace a host timeout for a stalled guest. Verify the selected build's network backend before specifying a TAP/pcap setup. [MAME command-line options][mame-cli], [Lua scripting][mame-lua].

## Qualification gate

Firmware, installation, and persistent-guest checks have execution evidence in the [2026-10-29 run record](results/2026-10-29-indy-netbsd-install.md), using the R4400 profile with CI enabled. The [kernel record](results/2026-10-30-netbsd-kernel.md) adds a host cross-build and verified changed-kernel boot. The [debugger/probe record](results/2026-10-30-netbsd-debugger-probe.md) establishes debugger attachment, breakpoint continuation, unattended probes, failure/timeout handling, and repeated cold starts, with matching smoke-test outcomes in CI and ordinary execution. The [I/O record](results/2026-10-30-netbsd-io.md) adds repeated 96 MiB disk writes, checksum verification after a cold start, and 96 MiB of network transfers in both modes. The pinned fork fixes NetBSD NFS mount negotiation. The [snapshot tests](results/2026-10-30-netbsd-snapshots.md) pass repeated full restores, CI rollback, fresh-process restore, timers, and final cold-boot integrity after the fork's RAM-map fix. They also found an intermittent integrity failure with fragmented NFS; the current profile uses HTTP or 1024-byte NFS requests. That corruption and the earlier installer HTTP stall remain open. The [X11 tests](results/2026-10-30-netbsd-x11.md) pass a software-rendered 1024×768, 24-bit Newport display, PS/2 input, and a twm/xterm session in both modes after an IRIS keyboard-controller fix. XAA colors and full framebuffer geometry remain open. Comparison with MAME and hardware gates remain pending. Store small run records under `docs/results/`, including commands, versions, configuration, input hashes, logs and outcomes; keep large images separately.

| Stage | Required evidence |
| --- | --- |
| Firmware and installation | PROM output, installer shell, recognized CPU/RAM/SCSI devices |
| Persistent NetBSD guest | Install, cold boot to multiuser, clean shutdown and another successful cold boot |
| I/O | Repeated disk read/write with checksum comparison; network transfer and integrity check; no unexplained kernel errors |
| Development loop | Host cross-build, boot of the changed kernel, verified build identifier, debugger breakpoint and continued execution |
| Automation | Unattended start, known probe output and exit status, hang timeout, logs retained, repeat from clean disk state |
| CI and snapshots | Compare ordinary/CI outcomes; restore a snapshot and verify guest state, disk consistency and relevant timers |
| Display | NetBSD X server, Newport output and input verified; original desktop tests tracked separately |
| Comparison and hardware | Key boot/probe results repeated in MAME and later physical Indy; differences documented |

Measure cold-boot time, incremental build-to-result time, probe runtime, memory and reset time under recorded configurations. Those measurements will decide whether optimized builds or more emulator work are useful. Emulator results cannot establish real cache, DMA, interrupt timing or graphics performance.

The first deliverable is a reproducible **NetBSD installer → installed guest → changed kernel → automated probe** sequence. A first original-IRIX shell session now runs the asa/echo reference checks; XFS alerts and graphical reference behavior remain to be qualified. This separates the immediate lab work from the larger desktop preservation experiment without changing the project target.

[iris-readme]: https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/README.md
[iris-features]: https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/FEATURES.md
[iris-storage]: https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/STORAGE.md
[iris-networking]: https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/NETWORKING.md
[iris-cargo]: https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/Cargo.toml
[iris-toolchain]: https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/rust-toolchain.toml
[iris-release]: https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/.github/workflows/release.yml
[mame-indy]: https://github.com/mamedev/mame/blob/mame0289/src/mame/sgi/indy_indigo2.cpp
[mame-debugger]: https://docs.mamedev.org/debugger/index.html
[mame-lua]: https://docs.mamedev.org/luascript/index.html
[mame-cli]: https://docs.mamedev.org/commandline/commandline-all.html
[netbsd-install]: https://cdn.netbsd.org/pub/NetBSD/NetBSD-11.0/sgimips/INSTALL.html
[netbsd-build]: https://www.netbsd.org/docs/guide/en/chap-build.html


## Original image resource staging

Use the [resource checklist](IRIX-RESOURCES.md) and linked manifests when a
client requests another IRIX asset. Read-only guestfish extraction keeps vendor
bytes under ignored `.work`; public files retain metadata and findings. Install
explicit readable resource/environment modes and executable program/library
modes in disposable guests, since the guest umask can otherwise make a root-only
test look successful. Capture frames during interaction and transfer them after
the bounded client exits. Server fonts belong in X.org's font path; client
locale files belong in the foreign namespace. The [font-import experiment](results/2026-10-31-irix-winterm-resources.md)
checks those paths separately. Keep the global four-IRIS limit and verify all
owned guests have stopped after testing.

Original-IRIX reference runs use an in-memory disk overlay. Transfer records
before quitting; the stopped raw image does not contain those guest writes.
The access harness keeps archive argument lists small for IRIX and runs
packaging inside a script so a failure cannot log out the interactive shell.


## Process checkpoint

The [process lab](../lab/irix-process/README.md) adds paired original-IRIX
fork/mask/wait measurements, full LP64 CI/ordinary and o32 matrices, independent
native KERN_PROC2 mask/identity snapshots, and process-group cleanup controls.
At that historical checkpoint, original xwsh forks and opens the slave in its
child, then reaches unsupported execve. The observer retains all child trace events and signals plus the first
2,000 parent events, avoiding repeated serial transfer of the parent's loop
after command failure. The full-trace hash/count and capture scope are recorded.
The subsequent [shell lab](../lab/irix-shell/README.md) measures descriptor,
session and exec interfaces and verifies native shell commands through original
winterm. It stages the pinned NetBSD X development set, explicitly makes the
session environment readable by the test UID, and generates the final Return
character inside the guest shell so serial-console multiline editing cannot
corrupt the typed command. A native helper reopens the verified native PTY
before controlling-terminal setup; direct acquisition through the nullfs view
triggered a captured `exit1 -> layer_revoke -> vrelel` panic on teardown.
The reserved-UID guard tracks and cleans up descendants across setsid and
launcher exit. Native controls cover detached descendants, tty hangup and X
keyboard input. Foreign signal handlers, resize and normal app exit remain open;
4Dwm evaluation follows this working shell baseline.

The [4Dwm loader checkpoint](results/2026-11-01-irix-elfmap-subpage.md) now handles the two 4 KiB data boundaries and passes 750 mapping/limit checks. The [fixed/local mmap checkpoint](results/2026-11-01-irix-mmap-local.md) now also clears GL initialization, with 660 mapping cases and native page-zero controls. The [measured PRDA checkpoint](results/2026-11-01-irix-prda.md) now clears that libc fault, with 80 executions / 180 records plus fork and native-exec controls. The [4Dwm session](results/2026-11-01-irix-4dwm.md) now passes reparenting, pointer focus, key delivery and dragging alongside Toolchest and a working winterm shell. Session saving is explicitly disabled; desks, restoration and complete desktop services remain open.

The [expanded desktop attempt](results/2026-11-01-irix-desktop-components.md)
uses those unchanged pins to investigate fm, bgicons and Icon Catalog. It finds
a fatal unsupported pthread resource-limit query and a separate executable
alignment rejection. Its observation record preserves baseline-check failures
and component failures; it does not replace the accepted 4Dwm interaction matrix
or qualify the recently merged IRIS upstream build for these guests.

The [resource-limit checkpoint](results/2026-11-01-irix-rlimit.md) uses isolated
LP64/o32 kernel outputs and original-IRIX measurements. Both LP64 emulator
modes and the o32 regression pass query/loader qualification. The
[desktop follow-up](results/2026-11-01-irix-desktop-startup-fixes.md) clears the
initial exec/query failures and records `MAP_AUTORESRV` rejection during pthread
table allocation. A bounded native focus diagnostic logs actual pointer
coordinates without assigning focus; terminal input remains a separate check.
The subsequent [AUTORESRV checkpoint](results/2026-11-01-irix-mmap-autoresrv.md)
clears that mapping rejection and reaches `prctl(PR_INIT_THREADS)`. The new
fixtures cover the actual allocation size, protection changes, private fork
inheritance and the existing mapping/page-zero controls. These runs retain
the previously qualified IRIS binaries. The latest upstream
revision was already integrated into fork `xiri`; no emulator change was needed.

The [pthread initialization checkpoint](results/2026-11-01-irix-init-threads.md)
now passes the LP64 CI/ordinary and o32 CI matrices, including asynchronous
signal holds. The [desktop retry](results/2026-11-01-irix-desktop-init-threads.md)
advances to session-directory creation; Icon Catalog renders its fatal dialog.
The ordinary run also exposed a 72-pixel-high terminal and failed its keyboard
geometry gate; an unchanged ordinary repeat passes. Retain the failure
separately from those successful interactions; startup repeatability remains
unqualified.

The [mkdir checkpoint](results/2026-11-01-irix-mkdir.md) passes the same native
kernel/mode matrix and verifies actual filesystem effects independently of
foreign xstat. Its [desktop follow-up](results/2026-11-01-irix-desktop-mkdir.md)
opens Icon Catalog with a blank page. Original assets remain unchanged;
content enumeration and application interaction require separate checks.

Active emulator and kernel development now uses the consolidated
[`xiri` branches](FORKS.md). Existing guest qualification remains tied to its
recorded commits and binaries; consolidation does not silently update those
pins.


The [pipe checkpoint](results/2026-11-01-irix-pipe.md) adds native pipe dispatch
with exactly matching V0/V1 returns, flags, data flow, fork/EOF and allocation
rollback. The matrix passes 220 native records and 44 controls across LP64
CI/ordinary and o32 CI. The new desktop observer uses a separate guard with a
180-second ceiling and an initial native guard control; previous failed
captures and qualified guard sources remain unchanged.

The [installer/home experiment](results/2026-11-01-irix-installer.md) uses one
disposable CI guest at a time, followed by clean shutdown. Native account and
shared-home file checks survive a cold boot. Original inst startup is blocked
by the captured shared/autogrow mmap request; both native controls and the
known-fault tracer controls pass. The separate full-desktop CI capture timeout
remains unresolved; this smaller passing harness does not clear it.

The [shared-mapping cycle](results/2026-11-01-irix-mmap-shared.md) uses at most
four concurrent IRIS guests, with sequential two-job kernel builds. Its final
reference, three native matrices and installer retry all halt cleanly. The
first uncompressed reference export failed and is retained as an unclean
non-seed diagnostic; three initial native captures halted cleanly but lacked
backing-file evidence due to a harness working-directory error. Corrected
captures use compressed reference export and explicit native archive paths.
The unchanged reference image's XFS alerts remain outside this qualification.

The [sproc reference cycle](results/2026-11-01-irix-sproc-reference.md) uses
two disposable original-IRIX guests, with at most two briefly overlapping
during shutdown/startup. Both halt cleanly and all 112 full-matrix process
groups are absent after cleanup, including 24 deliberate watchdog cases.
No IRIS instance remains running. The reference and NetBSD guest binaries
stay pinned while the separate [upstream integration](results/2026-11-01-iris-upstream-sproc.md)
passes workspace and JIT/idle host checks.


The [native sproc cycle](results/2026-11-01-irix-sproc.md) uses at most four
owned guests and sequential two-job kernel builds. Its final lifecycle
matrices pass 340 executions / 600 records with all groups absent, including
40 specifically expected blocked-case watchdogs. A resource-ceiling fixture
was corrected from 128 to 192 MiB to accommodate LP64's 120 MiB reserved main
stack; earlier runs are retained as diagnostics. The
[installer retry](results/2026-11-01-irix-installer-sproc.md) also retains an
earlier serial-marker setup failure, then captures successful child/shell
handoff and the later descriptor/time boundary with whole-group cleanup.
The qualified emulator and previous guest artifacts remain unchanged.

The final shared-mapping regressions on the sproc kernel pass 1,180 records,
1,180 backing files and 44 controls across the same three kernel/mode pairs.
All accepted and diagnostic guests halt cleanly; the final host check finds
no IRIS processes. The four-instance ceiling was respected throughout.


The [F_DUPFD cycle](results/2026-11-01-irix-dupfd.md) uses at most four owned
guests with sequential two-job builds. The original reference passes 168
records; native matrices pass 420 records and 44 controls, and pipe
regressions pass another 220 records and 44 controls. The original guest,
all six native matrix/regression guests and installer retry halt cleanly.
The installer attempt retains its bounded timeout and whole-group cleanup.
No guest artifact from an earlier checkpoint was changed.


The [time cycle](results/2026-11-01-irix-time.md) uses 192 original records,
480 native records and 44 controls, followed by eight bounded xclock launches
and the installer retry. Builds are sequential with two jobs; no more than
four guests run concurrently. ABI fixtures must exit normally; interactive
xclock uses an intentional 18-second watchdog with group cleanup. Original
and native guests halt cleanly. XWD captures are converted losslessly to PNG;
clock/date semantics are checked independently of pixel changes. Existing
qualified emulators, worktrees and kernels remain pinned.
