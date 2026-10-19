# Indy emulation development environment

Decision and research date: 2026-10-15. This is a proposed setup based on upstream documentation and source inspection. Neither emulator has been built or boot-tested by Xiri; no speed comparison has been measured.

## Decision

Use **IRIS as the preferred initial development environment, conditional on passing the NetBSD qualification below**. Keep **MAME as an independent comparison environment and fallback**. Begin development on an emulated Indy; the physical Indy, Indigo2, and Octane remain the deployment targets.

IRIS offers the more convenient documented development loop: a control socket, serial capture, integrated network services, disk overlays, and machine snapshots. MAME provides a separate implementation with a mature debugger and Lua automation. This recommendation concerns workflow, not a demonstrated difference in emulation speed or correctness.

IRIS explicitly says that NetBSD guests are not regularly tested. Its reported IRIX desktops do not prove that a current NetBSD kernel works. MAME's IRIX boot instructions do not establish that either. If IRIS fails a qualification stage that MAME passes, use MAME for that stage and retain a minimal IRIS reproducer. If both fail, investigate the boot image, firmware, and guest support before starting compatibility-layer work. [IRIS README][iris-readme], [MAME Indy source][mame-indy].

Additional reference recorded on 2026-10-16: [SGIEmu](FEASIBILITY.md#sgiemu-emulator), particularly its Newport implementation, device tests and tracing runner. Its inspected documentation lists Windows-only operation and missing Ethernet emulation. NetBSD has not been qualified by Xiri, so this addition does not change the initial harness choice.

Additional reference recorded on 2026-10-19: [irix-emu](FEASIBILITY.md#irix-emu-emulator), an R5000/Newport implementation with graphics tracing and device tests. Ethernet is documented as unimplemented and NetBSD remains unqualified. Its glpass library uses emulator hypercalls and a macOS host GPU; evaluate that separately from hardware-driver correctness and original-IRIX reference runs. The initial IRIS/MAME choice remains in place.

Additional reference recorded on 2026-10-19: [qemu-sgi-ip22](FEASIBILITY.md#qemu-sgi-ip22-emulator), a QEMU Indy/R4400 model with device-trace comparison notes, reported IRIX/Linux boot and preliminary Newport support. Its documented ARCS firmware boot path, TAP networking and incomplete graphics need separate qualification; Xiri has not tested NetBSD on it. Use it as another source for device behavior and test methods while retaining the initial IRIS/MAME choice.

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

Proposed guest configuration:

- Indy IP24 with an R5000 and Newport graphics: IRIS `indy_ip24`/`r5000`/`newport`, MAME `indy_5015`. This is an emulated reference configuration, pending inventory of the user's physical Indy.
- Use a RAM size supported by both configurations, recording the actual amount each reports. Start with IRIS's default 256 MiB and inspect MAME's configuration before claiming equivalence.
- NetBSD 11.0/sgimips, big-endian MIPS, initially the 32-bit `INSTALL32_IP2x` and `GENERIC32_IP2x` kernels. A 64-bit-capable CPU does not require starting with a 64-bit kernel. [NetBSD installation notes][netbsd-install].
- Separate NetBSD and original-IRIX disks; separate working copies, NVRAM, sockets, ports, and logs for each emulator instance. Record MAC addresses and PROM settings.
- A minimal NetBSD installation first, adding X sets for display tests. Select the IRIX reference release after media and desktop package inventory become available.

The NetBSD release establishes an unmodified baseline. Pin matching source before cross-building; upgrading the guest or emulator becomes an explicit regression test.

## Prerequisites and current gaps

Provisioning and testing are pending. Inventory the selected build host before choosing build settings or installing dependencies. The [development setup checklist](ROADMAP.md#development-setup-checklist) records the next actions.

| Item | Why it is needed | Current status |
| --- | --- | --- |
| Host build environment and storage | Emulator, cross-toolchain, source/object trees, guest disks | Selected build host to inventory and provision; earlier session measurements below |
| IRIS source and Rust toolchain | Debug-capable emulator build | Not installed; select an exact nightly and retain resolved dependencies |
| NetBSD sgimips installer, sets, checksums and matching source | Boot baseline and modified-kernel loop | To obtain from the official release distribution |
| Indy PROM | Firmware baseline and MAME ROM verification | User has no local image yet; IRIS documents an embedded fallback |
| IRIX installation media or an image from the user's machine | Original behavior, libraries, desktop and application inventory | User has no local image yet; required for the IRIX reference experiments |
| MAME executable and matching ROM configuration | Independent reproduction of failures | Not installed |
| Physical Indy configuration and serial access | Later hardware qualification | Machine available; CPU, graphics and connection details pending |

The IRIS fallback supplies firmware behavior; it does not supply an installed IRIX filesystem. We can attempt the NetBSD bootstrap before obtaining IRIX media. Keep original firmware, OS images, and imported desktop binaries outside Git; retain manifests, hashes, acquisition notes, configurations, and test logs here.

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

This command has not been executed here. The source selects a rolling `nightly` toolchain; record an exact working nightly date, `rustc -Vv`, the resolved lockfile, native dependency versions and build features. Linux dependencies include native audio/video/windowing libraries and C/Clang tooling; resolve the CLI's requirements from its manifest and upstream build instructions. The full GUI packaging dependency list is broader than this first build. [Cargo manifest][iris-cargo], [toolchain selection][iris-toolchain], [release build dependencies][iris-release].

Use these rules for the initial profile:

- Keep `lightning` and instruction fusion off so breakpoints remain usable. Leave experimental CPU `jitv2` off until the baseline passes; measure optimized builds separately.
- Keep private `hostcall` services and `hostgl` off. Compatibility probes must exercise the interfaces that the physical SGI will have.
- Retain the documented default `scsi_deferred_int = true` for BSD compatibility.
- Test ordinary execution first. `--ci` enables automation but also documented fidelity shortcuts; compare ordinary and CI runs before accepting CI results as representative.
- For unattended graphics tests, use `--ci` with Newport still enabled. **Explicit `--headless` disables Newport graphics**; it is unsuitable for desktop acceptance. `--ci-display` exposes the window during harness development.
- Capture serial output and assign each instance its own CI socket and ports. Confirm the NetBSD console channel; documentation names such as `/dev/ttyd1` refer to IRIX.

These distinctions come from [IRIS build/runtime options][iris-features] and the [automation guide][iris-storage]. The `iris-ci boot`, `login`, `run`, `put` and `get` examples target IRIX prompts and device paths. Qualify or adapt them for NetBSD rather than treating them as an existing NetBSD harness.

## Boot and development loop

1. **Reach the PROM and installer.** Start with serial capture. Serve the uncompressed NetBSD installation kernel using IRIS's `--tftp-dir`; test its BOOTP/TFTP path. Use the PROM-supported ELF or ECOFF format. If networking blocks bootstrap, try the official sgimips bootable CD image. An ordinary ISO is insufficient: the SGI boot path requires a volume header. [IRIS TFTP options][iris-features], [NetBSD boot instructions][netbsd-install].
2. **Install to a disposable guest disk.** Use the installer to establish the SGI volume header, boot loader and native filesystem. Verify disk boot, multiuser operation, network transfer and filesystem integrity after reboot. Preserve a clean base image before enabling per-run overlays.
3. **Build on the modern host.** Use NetBSD's `build.sh` cross-tools for `sgimips`/`mipseb`, then the `GENERIC32_IP2x` kernel and small probes. Keep object/tool directories separate from source and retain a symbol-bearing kernel for debugging. Compilation on the host is the main way to shorten iteration; do not depend on building the OS inside the MIPS guest. [NetBSD cross-build guide][netbsd-build].
4. **Boot a changed kernel.** Transfer through the qualified TFTP path or guest networking. Prove that a distinct kernel build identifier appears in the boot log. Keep local disk root initially; NFS-root adds another service to qualify. IRIS's NFS export is a candidate for artifact transfer after ordinary guest networking works.
5. **Run and collect probes.** Capture output, exit status, kernel messages and host elapsed time. Later run the same behavioral probes on the original-IRIX guest and compare results with Xiri. Add the desktop's X and service tests once the necessary runtime is available.
6. **Check independent execution.** Reproduce key milestones in MAME, then on the physical Indy before claiming hardware support. Investigate differences rather than changing tests to fit one emulator.

Snapshots can shorten repeated userspace tests after qualification. A restored RAM snapshot resumes the old kernel, so **cold-boot each changed kernel**. Couple snapshot state with its disk overlay, NVRAM, configuration, emulator revision and guest build. External NFS writes are not rolled back with guest RAM. Do not share live writable disks between emulator instances or assume their snapshot/overlay formats are interchangeable. [IRIS storage model][iris-storage].

MAME automation should use Lua, console capture and an external wall-clock timeout. `-seconds_to_run` counts emulated time and does not replace a host timeout for a stalled guest. Verify the selected build's network backend before specifying a TAP/pcap setup. [MAME command-line options][mame-cli], [Lua scripting][mame-lua].

## Qualification gate

Every row is pending. Store small run records under `docs/results/` when execution starts; include full commands, versions, configuration, input hashes, logs and outcomes. Store large images separately.

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

The first deliverable is a reproducible **NetBSD installer → installed guest → changed kernel → automated probe** sequence. Original-IRIX reference sessions follow when media becomes available. This separates the immediate lab work from the larger desktop preservation experiment without changing the project target.

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
