# Xiri execution roadmap

Status: execution started, updated 2026-11-01. Host inventory, the pinned IRIS build, verified NetBSD inputs, the installed R4400 guest, and a host-built custom kernel boot are complete. Debugger breakpoints and an automated smoke probe now pass, including comparison of CI and ordinary execution. Bounded disk and network integrity tests also pass in both modes. Snapshot restore, CI rollback, and post-restore cold boots now pass with the fork's RAM-map fix. NetBSD X/Newport display and input now pass in both modes with software rendering and a keyboard-controller fix. The historical IRIX source audit, fork kernel baseline, marked static o32 execution, bounded argument/file/memory probes, and writable ELF data/BSS are complete. Supplied IRIX 6.5.22m media provides native asa/echo observations and an unmodified vendor rejection baseline. Bounded o32 interpreter loading, runtime queries, SGI_ELFMAP, indirect dispatch, and allocation now run unmodified vendor asa through its original libc/rld. Its output and the interface probes are compared with original IRIX. The separate LP64 kernel/native baseline passes after firmware-call and emulator TLB fixes. The bounded dual-ABI personality now runs n32 echo alongside o32 asa, with explicit argument widths, ELF32 auxiliary data and heap growth. Desktop library closure and initial resource/session inventory identify 4Dwm’s alignment/relocation requirements. The TCP subset, socket-address queries and measured hostname/descriptor/sendmsg/shutdown interfaces now let Toolchest complete X setup and send processed requests. Measured legacy recvmsg now returns a 32-byte X reply. Toolchest’s later SIGSEGV is now traced to a missing HOME variable and avoided with an explicit session wrapper. The measured select subset passes both LP64 modes and the o32 kernel. The xstat/fxstat adapters now supply measured pathname and descriptor metadata. Toolchest requests the correct app-defaults size, reads its full menu and avoids the earlier allocator SIGSEGV; the [SIOCNREAD checkpoint](results/2026-10-31-irix-siocnread.md) removes the next XIO exit and produces a rendered Toolchest menu with 60-second visibility and Expose-redraw checks under both identities. The [resource/input follow-up](results/2026-10-31-irix-toolchest-input.md) adds bounded mouse/keyboard menu checks with original keysyms and explicit SGI colors. Application launch and full event/session behavior remain unqualified. XAA acceleration, full display geometry, fragmented NFS corruption, and the earlier installer HTTP stall remain open; original desktop and later implementation milestones are pending. Original [xclock windows now render](results/2026-10-31-irix-elfmap-relocation.md) in both styles and identities after bounded relocation; timekeeping remains open. The [access follow-up](results/2026-10-31-irix-winterm-access.md) clears the xwsh locale/font crash. The [PTY checkpoint](results/2026-10-31-irix-pty.md) supplies allocation and slave permissions. The [shell checkpoint](results/2026-11-01-irix-shell.md) follows the process subset with native exec/session/descriptor handling: the unchanged winterm launcher now opens an interactive native shell in xwsh and accepts typed commands. A native PTY handoff avoids the observed layered-tty teardown panic. Foreign signal handlers, resize and normal app exit remain open.

The agreed target is the full original IRIX desktop on NetBSD and X.org, supported by an IRIX personality. The current application order is winterm (including PTY, keyboard input and a native shell), then the original 4Dwm window manager and desktop session. Clock timekeeping is deferred behind those priorities. Initial implementation and testing use an emulated Indy. The development loop now supports [unmodified vendor asa/echo and bounded o32/n32 probes](results/2026-10-30-irix-lp64.md) on the NetBSD fork. Broader ABI coverage, desktop feasibility, and physical Indy qualification follow before expanding to additional machines and applications.

Active fork work is consolidated on [`xiri` in IRIS and NetBSD](FORKS.md).
Historical lab revisions remain pinned in detached worktrees.

The desired final delivery target, agreed on 2026-11-01, is a **loadable NetBSD
kernel module for the IRIX personality, modeled after `compat_linux`**. Use
NetBSD's Linux compatibility module as the reference for module structure,
registration, dependency handling, load/unload lifecycle and separation from
the foreign runtime. Xiri's runtime importer and desktop/session packages
remain separate user-space components. Built-in custom kernels remain the
current development and qualification method. Aim to work with an otherwise standard,
compatible NetBSD/MIPS kernel by upstreaming or removing required core changes;
that stock-kernel deployment is not yet demonstrated. See the
[module deployment boundary](ARCHITECTURE.md#components-and-deployment).

## Development setup checklist

The candidate host inventory, pinned IRIS CLI build, verified NetBSD inputs, guest installation, and host kernel build are complete. The R4400 guest reaches multiuser after a cold boot with the custom kernel, supports debugger breakpoints, and passes an automated probe. Repeated disk writes, cold-read integrity, and bidirectional network transfers pass in both execution modes; see the [I/O results](results/2026-10-30-netbsd-io.md). See the [installation record](results/2026-10-29-indy-netbsd-install.md), [kernel build record](results/2026-10-30-netbsd-kernel.md), and [debugger/probe results](results/2026-10-30-netbsd-debugger-probe.md).

Before starting implementation:

1. Sync this repository and inventory the selected build host's OS, CPU architecture, RAM, free storage and installed tools. Recheck capacity rather than relying on the earlier session measurements in the [emulation plan](EMULATION.md#inspected-session-environment).
2. Arrange storage for source, toolchains, object files, guest disks and snapshots. Retain the 30–50 GiB planning allowance and adjust it from actual usage.
3. Provision a debug-capable IRIS source build with a recorded Rust toolchain and native dependencies, plus NetBSD cross-build tools. Check the selected host's library compatibility before choosing any packaged emulator.
4. Use the [verified NetBSD 11.0 input baseline](../lab/netbsd-11.0/README.md) for the installer, sets, checksums and matching source. Use the supplied Indy PROM and [IRIX 6.5.22m reference image](results/2026-10-30-irix-vendor-baseline.md) for vendor and desktop experiments. The first native shell session works; investigate its XFS alerts and qualify MAME and graphics separately.
5. Preserve the [qualified o32/n32 application paths](results/2026-10-30-irix-lp64.md) while expanding toward the supplied n32 desktop. The LP64 kernel now runs unmodified asa and echo through their original runtimes, with 8 KiB page checks and the established 32-bit-kernel regressions. The [TCP path](results/2026-10-30-irix-tcp.md) and [socket-address queries](results/2026-10-31-irix-peername.md) now reach a controlled native X connection and both endpoint queries. The [startup-interface checkpoint](results/2026-10-31-irix-xconnect.md) now reaches completed X setup and processed requests. The [legacy recvmsg checkpoint](results/2026-10-31-irix-recvmsg.md) now receives an X reply and reaches a later SIGSEGV. The [session diagnosis](results/2026-10-31-irix-toolchest-session.md) now identifies a null `HOME` value passed to `strcpy`; an explicit environment avoids the fault. The [select checkpoint](results/2026-10-31-irix-select.md) implements the measured readiness and timeout subset, including unique descriptor counts and copyout faults, with an explicit 1024-descriptor cap and stricter invalid-descriptor policy. The [xstat checkpoint](results/2026-10-31-irix-xstat.md) adds measured pathname metadata for both ABIs and versions 2/3, including guards, permissions, namespace fallback and partial faults. The [fxstat checkpoint](results/2026-10-31-irix-fxstat.md) adds measured descriptor metadata and shares the serializer with xstat. With supplied resources, Toolchest now reads the correct app-defaults size and full menu without the earlier allocator SIGSEGV. The [SIOCNREAD subset](results/2026-10-31-irix-siocnread.md) is measured and implemented; Toolchest now renders its menu and remains alive in bounded tests. Sustained visibility and Expose redraw now pass under both identities. The [resource/input follow-up](results/2026-10-31-irix-toolchest-input.md) now separates color/keysym inputs and menu navigation. Next qualify supported application launches and broader timing/session behavior. The [winterm and font experiments](results/2026-10-31-irix-winterm-resources.md) establish native SGI font import and an original xwsh startup fault; the [fault capture](results/2026-10-31-irix-winterm-fault.md) now identifies a null font object and unsupported access to staged locale/defaults. The [access adapter](results/2026-10-31-irix-access.md) now permits those resource reads and removes the null-font failure. The [process checkpoint](results/2026-11-01-irix-process.md) follows native PTY allocation with bounded fork, masks and exit waits. The [shell checkpoint](results/2026-11-01-irix-shell.md) now verifies descriptor duplication, session creation and native exec with paired probes, then real keyboard input and command execution through original winterm/xwsh. Native handoff and a reserved-UID supervisor cover controlling-terminal setup and session descendants. The initial 4Dwm session now passes native-window interaction alongside Toolchest and winterm with session saving disabled; retain foreign signal handlers, resize, normal terminal exit and broader shell behavior as explicit follow-ups. Reassess seek when a later workload requires it. The subpage and relocation mappers now cover the observed library boundaries; the fixed/local mmap and measured PRDA checkpoints now clear GL initialization and the following libc fault. Qualify window management and the remaining session paths. Complete runtime resource/service qualification and a clean graphical reference session. Add the required behavior with paired original-IRIX probes. Keep the [X11 limits](results/2026-10-30-netbsd-x11.md) explicit and compare CI with ordinary execution for each new workload.
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
- [x] Qualify getpeername output translation and unconnected-socket errors, then repeat Toolchest’s X connection. The [getpeername checkpoint](results/2026-10-31-irix-peername.md) matches 152 returning paired records and records later gethostname/fcntl/sendmsg/shutdown failures.
- [x] Qualify those hostname, descriptor-control and message-transfer interfaces against original IRIX, then repeat Toolchest. The [startup-interface checkpoint](results/2026-10-31-irix-xconnect.md) reaches successful X setup and processed requests, followed by unsupported recvmsg.
- [x] Qualify legacy recvmsg output structures, vector lengths, received bytes and error behavior with paired IRIX probes, then repeat Toolchest. The [receive checkpoint](results/2026-10-31-irix-recvmsg.md) adds 268 exact returning pairs, checks queue consumption/peeking and read-only header output, and advances Toolchest through a successful 32-byte X receive.
- [x] Isolate Toolchest’s subsequent SIGSEGV with validated native ptrace controls and an environment-only comparison. The [session checkpoint](results/2026-10-31-irix-toolchest-session.md) proves a missing `HOME` value reaches `strcpy` unchecked; the explicit wrapper avoids that fault.
- [x] Qualify the bounded `select` subset against original IRIX, including guarded sets, unique counts, copyout faults and waits measured inside the syscall. The [select checkpoint](results/2026-10-31-irix-select.md) passes both LP64 modes and the o32 kernel, with two explicit descriptor-policy differences and unchanged transport regressions. All 24 HOME Toolchest launches reach the version-2 xstat boundary.
- [x] Qualify versions 2/3 of `xstat` against original IRIX: 648 reference executions and 1,620 guarded NetBSD records across LP64 CI/ordinary and o32. The [xstat checkpoint](results/2026-10-31-irix-xstat.md) also repeats the supplied resource stages and captures the later allocator fault.
- [x] Qualify descriptor-based [fxstat](results/2026-10-31-irix-fxstat.md): 520 original-IRIX records, 1,300 matching NetBSD records, shared xstat and transport/select regressions. Toolchest reads the correct app-defaults size and full menu without the observed allocator SIGSEGV.
- [x] Measure and implement [SIOCNREAD](results/2026-10-31-irix-siocnread.md), then rerun Toolchest with native X controls. The menu renders and the client survives the bounded launch tests.
- [x] Check sustained visibility and Expose redraw using an independent native control: root and uid 1234 both restore the rendered menu during 60-second runs.
- [x] Qualify the [bounded resource/menu sequence](results/2026-10-31-irix-toolchest-input.md): original XKeysymDB, numeric SGI colors, mouse posting, keyboard traversal, submenus, Escape and redraw.
- [ ] Qualify supported application launches, spring-loaded dragging, timers and broader event/session behavior.
- [x] Try [original winterm/xwsh](results/2026-10-31-irix-winterm.md), distinguish launcher success from child execution, and verify native terminal controls.
- [x] Evaluate [original SGI Screen font import](results/2026-10-31-irix-winterm-resources.md): 22 indexed fonts, four native render controls and paired font/locale/account staging.
- [x] Locate the [xwsh null-font fault and resource-lookup boundary](results/2026-10-31-irix-winterm-fault.md) with actual access/seek arguments and native controls.
- [x] Implement the [bounded access subset](results/2026-10-31-irix-access.md): 4,020 checks with explicit native-policy differences. Eight original xwsh starts now read locale/default resources and pass the earlier null-font crash.
- [x] Measure and implement the bounded [PTY allocator interfaces](results/2026-10-31-irix-pty.md), including native ownership/namespace setup and original libc slave opens. Original xwsh advances to unsupported fork.
- [x] Measure and implement the [bounded process subset](results/2026-11-01-irix-process.md): fork/getpid, traditional signal masks and positive-child exit waits, with independent native identity/mask/COW/file-offset and process-group cleanup checks. Original xwsh reaches child execve after opening its slave.
- [x] Run a native interactive shell through [original winterm/xwsh](results/2026-11-01-irix-shell.md), with paired descriptor/session/exec probes, real keyboard input, a PNG and bounded descendant cleanup.
- [ ] Qualify foreign signal handlers, resize, normal terminal exit and broader shell behavior; general layered-tty revoke remains open.
- [x] Qualify the [4 KiB data mapping extension](results/2026-11-01-irix-elfmap-subpage.md): 750 mapping/limit checks; original 4Dwm passes its previous library boundary.
- [x] Resolve [4Dwm’s fixed/local GL mapping](results/2026-11-01-irix-mmap-local.md): 660 cases, 30 controls and 32 native page-zero checks.
- [x] Provide [measured PRDA process data](results/2026-11-01-irix-prda.md): 80 executions / 180 records, fork COW/PID updates, exec reset, damaged-state policy and native-exec controls.
- [x] Demonstrate [4Dwm window interaction and a combined shell session](results/2026-11-01-irix-4dwm.md): real reparenting, pointer focus, key delivery, dragging and typed winterm commands alongside Toolchest. Session saving is explicitly disabled.
- [ ] Resolve 4Dwm session file/service dependencies and feature queries, then qualify menus, minimize/maximize, native resize, desks, restoration and logout. Preserve the working terminal; its foreign signal/resize/normal-exit limits remain explicit.
- [x] Capture the [actual libXmu mapping failure](results/2026-10-31-irix-xclock-elfmap.md): unchanged libXmu headers request two addresses already occupied by libXaw text, and the mapper returns ENOMEM. Native breakpoint controls and clean shutdown pass.
- [x] Add [bounded collision relocation](results/2026-10-31-irix-elfmap-relocation.md): 576 mapper/limit checks, both ABIs, unchanged headers, alignment/gap/sentinel checks, and eight original analog/digital xclock windows. The later subpage checkpoint separately qualifies 4Dwm's 4 KiB data boundaries.
- [ ] After the winterm/4Dwm priorities, measure and implement the time calls used by xclock; qualify clock advancement, redraw and sustained behavior beyond the current epoch-time display.
- [ ] Record unsupported calls and operations explicitly rather than masking them as successful.

Acceptance: repeatable static and dynamic execution, meaningful behavioral probes, and at least one useful IRIX command-line program on NetBSD in the emulated Indy. Retain the same probes for physical qualification.

## Milestone 3 Original desktop proof

The target is a complete original IRIX desktop session on NetBSD and X.org.
The first rendered, live Toolchest client now establishes the entry point for
component-level checks. The user-supplied [IRIX Interactive Desktop User Interface Guidelines,
007-2167-006](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/index.html)
was revisited on 2026-10-31 after that rendering. The comparisons below are our
acceptance plan derived from its desktop, window/session, service, data exchange
and menu chapters; they are not claims that the complete desktop already works.

| Manual coverage | Planned desktop comparison |
| --- | --- |
| [Chapters 1](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch01.html)–[2](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch02.html): components, icons and file-type rules | Toolchest, Icon Catalog, file manager and desktop icons; launch applications and open files through their assigned actions |
| [Chapter 3](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch03.html): windows, focus, desks and sessions | Move, resize, minimize, focus and switch desks; restore application state across logout/login |
| [Chapter 4](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch04.html): services and settings | Apply preferences, observe file changes from native and IRIX programs, and qualify each required helper or host-service adapter |
| [Chapter 5](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch05.html) and [7](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch07.html): exchange and interaction | Clipboard/selection exchange, keyboard navigation and drag-and-drop between selected native and IRIX applications |
| [Chapter 8](https://techpubs.jurassic.nl/library/manuals/2000/007-2167-006/sgi_html/ch08.html): menus | Open, traverse and dismiss menus with mouse and keyboard; distinguish menu rendering from launching a supported application |

Use the manual as a behavior reference and measure version-specific details
on the selected installation. The existing resource/service inventory supplies
dependency candidates; a visible window alone does not complete these checks.

- [x] Revisit the supplied manual after the first rendered Toolchest client and map its relevant chapters to the comparisons above.
- [x] Maintain the [image-resource checklist](IRIX-RESOURCES.md) and [ledger](../lab/irix-desktop/resource-ledger.json), distinguishing extracted assets, observed use, remaining artwork/catalog/service gaps and native session state.
- [ ] Turn the remaining comparisons into reproducible desktop acceptance cases against the original installation.
- [x] Launch original 4Dwm against native Xvfb and demonstrate reparenting, focus, key delivery and dragging in the [combined shell session](results/2026-11-01-irix-4dwm.md); Newport/physical display qualification remains separate.
- [x] Add original Toolchest and a working winterm shell to the same 4Dwm session.
- [x] Attempt the original file manager, background icons and Icon Catalog in the [expanded session](results/2026-11-01-irix-desktop-components.md); retain startup failures and inventory the next resources.
- [x] Clear the initial `getrlimit(RLIMIT_PTHREAD)` and bgicons executable-alignment blockers with [measured limit/loader support](results/2026-11-01-irix-rlimit.md): 4,760 NetBSD limit records and 280 loader executions pass.
- [x] Clear the observed `mmap(MAP_AUTORESRV)` boundary with [private demand mappings](results/2026-11-01-irix-mmap-autoresrv.md), preserving fixed/local and native controls.
- [x] Measure and implement initial `prctl(PR_INIT_THREADS)` state and native signal holds: [260 executions / 860 records and 32 asynchronous-signal checks](results/2026-11-01-irix-init-threads.md) pass. Thread creation remains separate.
- [x] Implement [measured mkdir support](results/2026-11-01-irix-mkdir.md): 3,200 records, 1,540 independently verified directory creations and 44 controls pass. Native group ownership remains explicit policy.
- [x] Record the [user-supplied original desktop reference](IRIX-DESKTOP-REFERENCE.md), with a pixel-preserving PNG and explicit appearance/content targets.
- [x] Implement [measured pipe support](results/2026-11-01-irix-pipe.md): 220 exact records and 44 native/vendor controls, including descriptor exhaustion/rollback and forked writers.
- [ ] Qualify usable file/icon clients after directory creation. The [desktop retry](results/2026-11-01-irix-desktop-mkdir.md) now opens Icon Catalog’s empty fallback page with system page data unstaged, and bgicons exits zero. The [pipe retry](results/2026-11-01-irix-desktop-pipe.md) now renders FileManager, but its select EINVAL loop and the failed CI desktop capture need diagnosis; qualify a catalog page/action for an installed application separately. Preserve intermittent terminal geometry/startup failures. Session saving remains disabled.
- [x] Inventory the supplied [May 2004 freeware sets](results/2026-11-01-irix-freeware.md): four CDs, 489 distinct packages; record zero-filled ncurses/nedit metadata separately.
- [x] Establish [native /usr/people account creation and shared-file access](results/2026-11-01-irix-installer.md), including cold-boot persistence.
- [x] Measure and implement the installer's [shared zero-device mapping](results/2026-11-01-irix-mmap-shared.md): 472 original records, 1,180 native records/backing files and 44 controls. Regular-file AUTOGROW remains separate.
- [x] Measure the specific `sproc(PR_SADDR|PR_BLOCK|PR_NOLIBC)` child lifecycle reached by [original inst](results/2026-11-01-irix-installer-shared.md): [112 executions / 200 original records](results/2026-11-01-irix-sproc-reference.md) establish entry, shared data/new mappings, private PRDA/LOCAL pages, descriptor ownership and parent release.
- [x] Implement and qualify the [bounded two-member sproc lifecycle](results/2026-11-01-irix-sproc.md): 340 executions / 600 records and 44 controls, including group-aware guards, repeated creation, LOCAL replacement and exec/exit cleanup. Parent-death races, general multi-member updates and exhaustion failure injection remain separate.
- [x] Retry [original inst with sproc](results/2026-11-01-irix-installer-sproc.md): child creation, armed parent release and native shell exec now succeed. F_DUPFD fails during stdout/stderr pipe setup; the dry run later reaches its watchdog.
- [ ] Measure and implement F_DUPFD, including allocation/limits, flags, shared offsets and failure behavior; retry unchanged inst. Then qualify the helper command paths (`ls`/`mkdir`) and measured gettimeofday behavior. Signal registration, hardware queries and creat remain additional observed gaps.
- [ ] Run original IRIX `inst`, then Software Manager, to install **xmahjongg 3.6.1**. Its original hooks must create the **Freeware** catalog entry and icon/type rules; qualify launch, persistence after login, upgrade and removal. See the [software plan](IRIX-SOFTWARE.md).
- [ ] Qualify persistent native accounts under `/usr/people/<username>` with shared native/IRIX access, generated desktop state and logout/login persistence. Original root sessions use `HOME=/`; avoid a second emulation-root copy of user homes.
- [ ] Implement required service adapters, including the measured file-notification and launch behavior.
- [x] Exercise native X test windows under original 4Dwm in the same native Xvfb session used by Toolchest and winterm.
- [ ] Show a maintained host-native graphical application and an IRIX application in the same local session; qualify physical display output separately.
- [ ] Verify normal window operations, file navigation, desktop updates, and saved preferences.
- [ ] Repeat logout and login, checking process cleanup and restoration of expected state.
- [ ] Compare behavior with the reference installation and list component-level differences.

Acceptance: an original desktop session executing inside the emulated Indy on NetBSD, with working native and compatible application launch and a reproducible demonstration. A screenshot or themed substitute alone does not satisfy this milestone. The physical desktop remains required for the first hardware release.

## Milestone 4 Usable first release

- [ ] Package the IRIX personality as a loadable kernel module modeled after `compat_linux`, with a reproducible build/install path and explicit kernel-version/architecture dependencies.
- [ ] Audit core dependencies, including `selcommon_kern` and the pthread-initialization `emul.e_sigmask` hook; upstream or remove them to enable deployment on a compatible standard NetBSD kernel.
- [ ] Qualify module load, dependency resolution, refusal to unload while in use, unload/reload after exit, and the application regressions on a kernel without the built-in IRIX personality.
- [ ] Boot the qualified build on the physical Indy and repeat ABI and desktop acceptance there.
- [ ] Validate real storage, networking, cache/DMA behavior, input and local display; record differences from emulation.
- [ ] Package a reproducible installation for the first supported configuration.
- [ ] Provide an import workflow for the selected original runtime and desktop files.
- [ ] Deliver the original IRIX installers with qualified dependency/conflict reporting, installation history, catalog hooks and repeatable upgrade/removal. Keep the runtime-bootstrap import distinct from ongoing installation through inst/Software Manager.
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
