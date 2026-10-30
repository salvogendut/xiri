# Xiri feasibility and platform choice

Research started on 2026-10-14. The emulator development assessment was updated on 2026-10-15; additional references were added through 2026-10-19. Individual entries record their inspection dates and source revisions where available.

The agreed Xiri target is NetBSD plus an IRIX personality and the existing IRIX desktop, running on real SGI machines. Recreating the whole IRIX kernel would add substantial work without removing the need for hardware drivers, application ports, or graphics compatibility.

Preserving the original desktop makes this a systems compatibility project as well as an OS distribution project. Its feasibility must be tested early.

## Comparison of approaches

| Approach | Main benefit | Main limitation for Xiri | Proposed role |
| --- | --- | --- | --- |
| Extend original IRIX with new packages | Retains the original desktop, applications, and graphics drivers | Leaves the kernel and platform interfaces unchanged; software ports still need maintenance | Reference environment and possible interim use |
| Emulate a complete SGI workstation | Runs original IRIX for reference and NetBSD/Xiri for development on a modern host | Emulating original IRIX alone does not modernize it; hardware still needs qualification | Initial implementation and regression environment, plus reference testing |
| Reimplement IRIX as a complete OS | Potential control over every interface | Requires kernel, drivers, userland, desktop, and continuing maintenance | Outside the initial scope |
| Maintained kernel with IRIX compatibility | Reuses networking, VM, storage, and native software infrastructure | Requires SGI drivers and precise compatibility for chosen programs | Preferred direction |

Emulation and compatibility operate at different boundaries. A hardware emulator implements the machine that IRIX expects. A personality implements the OS interfaces that an IRIX program expects. On a compatible SGI CPU, that program's ordinary instructions can execute directly; its system calls and other OS interactions still need translation.

Hardware reverse engineering remains necessary where drivers are missing. The advantage is that Xiri can target the interfaces needed by its own drivers instead of reproducing every device behavior exercised by the original IRIX kernel.

## Existing work

NetBSD previously implemented `COMPAT_IRIX`, but retired it in NetBSD 6.0. Historical source includes probes for both o32 and n32 executables. This is useful reference code, not an available modern compatibility feature or proof that the desktop will work. [NetBSD 6.0 release notes](https://www.netbsd.org/releases/formal-6/NetBSD-6.0.html), [historical ELF loader](https://github.com/NetBSD/src/blob/netbsd-5/sys/compat/irix/irix_exec_elf32.c).

The [2026-10-30 source audit](results/2026-10-30-irix-compat-audit.md) pins the pre-removal implementation and compares it with the release kernel and current fork. It found incorrect success returns on ELF ABI mismatches, dependencies on the removed SVR4 code, and process/VM integration gaps. The subsequent [o32 implementation](results/2026-10-30-irix-o32-execution.md) executes an explicitly marked static `write`/`exit` fixture in both emulator modes. Native regressions, rejected files, explicit errors, and cleanup also pass. This establishes a small syscall boundary; it does not demonstrate vendor IRIX applications or their runtimes.

The [argument, file, and memory extension](results/2026-10-30-irix-o32-basics.md) passes 44 cases in each mode. It validates a bounded static subset with explicit flag translation, partial transfers, private mappings, and protection faults. The subsequent [data/BSS extension](results/2026-10-30-irix-o32-segments.md) passes 89 cases per mode and qualifies bounded static segments, zero-fill, and text write protection. Interpreter loading and original-IRIX behavioral comparison remain pending. These results support continuing the loader work without establishing general application compatibility.

The current NetBSD SGI port page lists Indy, some Indigo2 configurations, and O2 among its supported machines. It lists Octane and R10000 Power Indigo2 as unsupported; Fuel is absent from its supported model list. Its old explanation mentioning a required mips64 toolchain should not be read as a current diagnosis: NetBSD 6.0 already introduced broader 64-bit MIPS support. Board support requires a fresh source and boot audit. [NetBSD SGI port](https://wiki.netbsd.org/ports/sgimips/), [NetBSD 6.0 MIPS changes](https://www.netbsd.org/releases/formal-6/NetBSD-6.0.html).

OpenBSD historically supported Octane and Fuel, but discontinued its SGI port after 6.9. That code provides a significant hardware reference. The published `impact` and `odyssey` manuals establish console support, not an IRIX-equivalent accelerated desktop. [OpenBSD SGI port](https://www.openbsd.org/sgi.html), [Impact driver](https://man.openbsd.org/OpenBSD-6.9/sgi/impact.4), [VPro driver](https://man.openbsd.org/OpenBSD-6.9/sgi/odyssey.4).

Linux currently has an upstream `SGI_IP30` configuration for Octane and Octane2. Its implementation is a hardware reference for the NetBSD port; a kernel configuration entry does not establish complete graphics support or a ready-to-install distribution. [Linux MIPS configuration](https://github.com/torvalds/linux/blob/master/arch/mips/Kconfig).

MAME contains an Indy/Indigo2 implementation with IRIX boot instructions. Its Octane implementation is explicitly a nonworking skeleton, including a placeholder CPU. Octane emulation is therefore unfinished in that implementation, rather than fundamentally impossible. This finding does not establish the status of every emulator. [Indy and Indigo2 implementation](https://github.com/mamedev/mame/blob/master/src/mame/sgi/indy_indigo2.cpp), [Octane implementation](https://github.com/mamedev/mame/blob/master/src/mame/sgi/octane.cpp).

SGUG RSE already provides a package environment and development tools for IRIX. Its work is relevant to toolchain bootstrapping and application ports, though it does not supply a replacement kernel. [SGUG RSE](https://github.com/sgidevnet/sgug-rse).

### IRIS emulator

[techomancer/iris](https://github.com/techomancer/iris) is an additional hardware and testing reference. Its README reports IRIX 5.3 and 6.5 operation, an Indy IP24 desktop, and Indigo2 IP22/IP28 emulation, including an R10000/IP28 desktop. These are upstream results; Xiri has not yet reproduced them. Reference revision: [21c0ecb024b3](https://github.com/techomancer/iris/tree/21c0ecb024b3a7dc9e11514fa1b5302363071bf6), inspected on 2026-10-14. [IRIS README at that revision](https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/README.md).

Useful starting points for Xiri:

- [REX3 graphics notes](https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/docs/rex3.md): register and drawing behavior to compare with drivers and physical hardware.
- [Testing guide](https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/TESTING.md) and [CPU test suite](https://github.com/techomancer/iris/tree/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/cpu-tests): candidate methods for repeatable execution and hardware comparison.
- [Hardware documentation index](https://github.com/techomancer/iris/blob/21c0ecb024b3a7dc9e11514fa1b5302363071bf6/README.md#documentation): machine profiles, interrupts, SCSI, and audio references.

Initial implementation and testing will use Indy emulation. IRIS is the preferred development harness because its documented control socket, serial capture, network services, overlays and snapshots fit repeated kernel and ABI experiments. MAME supplies an independent implementation and fallback. This is a workflow recommendation, not a measured speed or correctness result. IRIS's README notes that NetBSD guests are not regularly tested, so current NetBSD boot and I/O must be qualified first. Hardware behavior inferred from emulation must later be checked on the available SGI machines.

The [emulation assessment](EMULATION.md) compares both tools, pins inspected sources, records the missing images and host prerequisites, and defines the initial acceptance tests. It also identifies two important IRIS configuration constraints: packaged `lightning` builds disable debugging, and explicit `--headless` disables Newport graphics. No emulator boot has been demonstrated by Xiri.

### SGIEmu emulator

[RenatoTarabella/SGIEmu](https://github.com/RenatoTarabella/SGIEmu) is another hardware and graphics research reference. Its README reports Indy IP24/R4400 emulation with Newport XL graphics, IRIX 5.3/6.5 desktops and GL demos, using an x86-64 JIT with an interpreter fallback. Reference revision: [5870980dc1f3](https://github.com/RenatoTarabella/SGIEmu/tree/5870980dc1f38b40bcdcabd7cfacb0b410d96ac8), inspected on 2026-10-16. These are upstream claims; Xiri has not built or tested it. [Pinned README](https://github.com/RenatoTarabella/SGIEmu/blob/5870980dc1f38b40bcdcabd7cfacb0b410d96ac8/README.md).

Useful starting points:

- [Newport implementation](https://github.com/RenatoTarabella/SGIEmu/blob/5870980dc1f38b40bcdcabd7cfacb0b410d96ac8/src/indy/newport.c) and [device tests](https://github.com/RenatoTarabella/SGIEmu/blob/5870980dc1f38b40bcdcabd7cfacb0b410d96ac8/tests/test_devices.c): additional material for investigating register behavior and drawing operations.
- [Headless runner](https://github.com/RenatoTarabella/SGIEmu/blob/5870980dc1f38b40bcdcabd7cfacb0b410d96ac8/tools/indy_boot.c): documented serial output, scripted input, screenshots, tracing and an in-memory disk-write mode. Its `--snapshot` option should not be assumed to provide full machine-state restoration.
- [Preliminary Octane implementation](https://github.com/RenatoTarabella/SGIEmu/blob/5870980dc1f38b40bcdcabd7cfacb0b410d96ac8/src/octane/octane.c): HEART, XBOW, BRIDGE and IOC3 work to examine during later board-support research; its presence does not establish a working Octane guest.

The inspected README documents Windows-only operation, no Ethernet or audio emulation, graphics limitations, and a requirement for external PROM and IRIX images. NetBSD operation remains unqualified. Use this as an additional implementation to investigate and compare with traces and physical hardware; the initial IRIS/MAME development plan remains in place.

### irix-emu emulator

[geoffroyvergne/irix-emu](https://github.com/geoffroyvergne/irix-emu) implements an Indy IP24/R5000 with Newport XL8 graphics in C++23 with an SDL3 frontend. Its README reports IRIX 6.5 installation and desktop operation. Reference revision: [5914d75bdadc](https://github.com/geoffroyvergne/irix-emu/tree/5914d75bdadc402b1367026d8b3158fb49581c9e), inspected on 2026-10-19. Xiri has not built or boot-tested it. [Pinned README](https://github.com/geoffroyvergne/irix-emu/blob/5914d75bdadc402b1367026d8b3158fb49581c9e/README.md).

Useful starting points:

- [Newport implementation](https://github.com/geoffroyvergne/irix-emu/blob/5914d75bdadc402b1367026d8b3158fb49581c9e/src/graphics/Newport.cpp) and [core tests](https://github.com/geoffroyvergne/irix-emu/blob/5914d75bdadc402b1367026d8b3158fb49581c9e/tests/CoreTests.cpp): register behavior, DCB, rasterization, cursor and device interactions. The README documents graphics/DMA tracing, scripted input and screenshots for investigations.
- [glpass documentation](https://github.com/geoffroyvergne/irix-emu/blob/5914d75bdadc402b1367026d8b3158fb49581c9e/glpass/README.md): a replacement IRIX `libGL.so` sends calls through emulator hypercalls to a macOS OpenGL backend. Its GLX, colour-index, window-tracking and threading work may inform graphics compatibility research. Applying those ideas on real SGI hardware would require a suitable renderer and integration in Xiri; the host-GPU results do not establish an accelerated SGI driver.

The inspected README lists Ethernet and audio as unimplemented and CPU caches as unmodeled. Its fault policy also allows skipping unimplemented instructions and returning zero for unemulated registers, which must be considered when interpreting successful tests. NetBSD operation remains unqualified. Keep glpass separate from original-IRIX behavioral baselines because it replaces the graphics library and uses emulator-specific services. Treat this project as an additional research implementation while retaining the initial IRIS/MAME harness plan.

### qemu-sgi-ip22 emulator

[dsheffie/qemu-sgi-ip22](https://github.com/dsheffie/qemu-sgi-ip22) adds a full-system Indy machine model (`-M indy`) with an R4400 CPU to QEMU. Its [SGI guide](https://github.com/dsheffie/qemu-sgi-ip22/blob/e24b3c7fe0b969eebdcc7e538ce490adefa73ddd/docs/index.md) reports IRIX 6.5 reaching an interactive root shell and IP22 Linux reaching userspace. Reference revision: [e24b3c7fe0b96](https://github.com/dsheffie/qemu-sgi-ip22/tree/e24b3c7fe0b969eebdcc7e538ce490adefa73ddd), inspected on 2026-10-19. Xiri has not built or boot-tested it; NetBSD remains unqualified.

Useful starting points:

- [Device-trace comparison notes](https://github.com/dsheffie/qemu-sgi-ip22/blob/e24b3c7fe0b969eebdcc7e538ce490adefa73ddd/QEMU_IP22_HANDOFF.md): comparisons against `interp_mips` that exposed byte-lane, SCSI DMA, interrupt, serial and RTC problems. These are useful methods for our reverse-engineering probes; confirm inferred hardware behavior on physical machines.
- [Newport implementation](https://github.com/dsheffie/qemu-sgi-ip22/blob/e24b3c7fe0b969eebdcc7e538ce490adefa73ddd/hw/display/sgi_newport.c) and [latest commit notes](https://github.com/dsheffie/qemu-sgi-ip22/commit/e24b3c7fe0b969eebdcc7e538ce490adefa73ddd): optional `-M indy,newport=on` graphics and an 8042 keyboard/mouse controller. The commit reports graphical console and X11 startup, with missing overlay/popup/display-ID planes, retrace timing and drawing features. The guide and handoff still describe graphics/input as absent, so use the commit and source to resolve that documentation gap; a complete desktop is not established.
- [Board and device models](https://github.com/dsheffie/qemu-sgi-ip22/tree/e24b3c7fe0b969eebdcc7e538ce490adefa73ddd/hw/mips): follow `ip22.c` into the MC, HPC3, IOC2, WD33C93 and Seeq implementations for additional hardware comparisons.

The documented boot path uses supplied ARCS/FSBL firmware, an extracted IRIX kernel and an installed disk image. This boot path needs separate qualification from real SGI PROM boot. The guide reports working IRIX networking over TAP and unresolved user-mode/slirp networking. Record firmware and network backend with any future run. Retain this as an additional emulation and device-research source while qualifying the initial IRIS/MAME setup.

### REA reverse-engineering tools

[morluto/rea](https://github.com/morluto/rea) provides MCP and CLI workflows for binary analysis through providers such as Ghidra, Hopper and IDA. Its README describes access to disassembly, pseudocode, symbols, strings and cross-references. Reference revision: [7d1e4d0e2bfb](https://github.com/morluto/rea/tree/7d1e4d0e2bfb77bd47203b4f962e4f034678dc75), inspected on 2026-10-15. [README at that revision](https://github.com/morluto/rea/blob/7d1e4d0e2bfb77bd47203b4f962e4f034678dc75/README.md).

Potential uses for Xiri include investigating original graphics drivers, firmware and other proprietary interfaces: locating register accesses, command construction, initialization sequences and synchronization paths. Desktop library dependencies and IRIX ABI behavior are additional candidates. These are proposed uses, not demonstrated REA results on SGI software.

REA is an optional analysis tool, not a prerequisite for the first NetBSD boot. It requires a supported Node.js/npm environment and a configured native-analysis provider. Before adoption, verify the provider's handling of representative big-endian MIPS/IRIX binaries and relevant o32/n32 layouts. Xiri has not installed or validated it. Treat recovered pseudocode as a hypothesis; corroborate findings with instruction-level evidence, emulator traces and physical-machine observations. See the [reverse-engineering workflow](ARCHITECTURE.md#reverse-engineering-workflow).

### irix-work desktop reverse engineering

[gazecube/irix-work](https://github.com/gazecube/irix-work) targets reverse engineering of the IRIX desktop stack for x86-64 Linux. Its `irix-re` branch and [desktop handoff dated 2026-10-11](https://github.com/gazecube/irix-work/blob/irix-re/IRIX-HANDOFF-2026-10-11.md) were reviewed on 2026-10-19. The handoff describes recompiled native runners and host bridges, with component-specific progress and unresolved failures. Xiri has not built or run this work.

Particularly relevant research leads:

- X11 resource handling and window-manager behavior: observations about `4Dwm`, X resource parsing, drawing synchronization and extension handling.
- Desktop integration: session launch/logout, file monitoring through FAM, Icon Catalog data generated from installation metadata, and host application launch experiments.
- Compatibility details: executable initialization, null-page behavior, pseudo-terminal handling and runtime memory corruption investigations involving desktop libraries.

The [desktop integration tree](https://github.com/gazecube/irix-work/tree/irix-re/desktop-integration) and handoff provide starting points for the desktop dependency manifest and focused behavioral probes. The inspected notes also report incomplete Icon Catalog behavior, file-manager instability and terminal shell-launch problems; they do not establish a fully working desktop.

Use these findings to inform Xiri's NetBSD personality and service adapters. The Linux/x86-64 execution approach has different CPU, ABI and host-service boundaries, so validate each proposed behavior against original IRIX before adopting it for native MIPS execution. The agreed NetBSD foundation and original-desktop preservation target remain in place.

### IRIXKernel build research

[shawlucas/IRIXKernel](https://github.com/shawlucas/IRIXKernel) describes itself as an incomplete attempt to compile the IRIX kernel on modern Linux. Reference revision: [3e9c861567ce](https://github.com/shawlucas/IRIXKernel/tree/3e9c861567cef1243127e4aaa1cf44e61f3b2e4c), inspected on 2026-10-19; that commit is dated 2020-06-21. [Pinned README](https://github.com/shawlucas/IRIXKernel/blob/3e9c861567cef1243127e4aaa1cf44e61f3b2e4c/README.md).

The inspected tree includes [libc math material](https://github.com/shawlucas/IRIXKernel/tree/3e9c861567cef1243127e4aaa1cf44e61f3b2e4c/lib/libc/src/math), [SGI-related headers](https://github.com/shawlucas/IRIXKernel/tree/3e9c861567cef1243127e4aaa1cf44e61f3b2e4c/include) and [assembler work](https://github.com/shawlucas/IRIXKernel/tree/3e9c861567cef1243127e4aaa1cf44e61f3b2e4c/as). These are possible leads for runtime conventions, floating-point behavior and historical build/toolchain investigations. Compare any relevant findings with original-IRIX probes before relying on them.

Xiri has reviewed the README and repository layout only. Kernel buildability, graphics-driver coverage and applicability to NetBSD remain unverified; no code has been imported into Xiri or built. Keep this as an exploratory source alongside the other compatibility and reverse-engineering references.

### IRIX-Simulator desktop appearance and interaction

[Sergutsu/IRIX-Simulator](https://github.com/Sergutsu/IRIX-Simulator) is a web-based recreation of the IRIX desktop. Its README describes 4Dwm-style windows, SGI Motif widgets, Toolchest, desktop icons, workspace switching and session persistence. Reference revision: [6eb3406f7c79](https://github.com/Sergutsu/IRIX-Simulator/tree/6eb3406f7c7991e3a67e55945c933066a355b379), inspected on 2026-10-19. [Pinned README](https://github.com/Sergutsu/IRIX-Simulator/blob/6eb3406f7c7991e3a67e55945c933066a355b379/README.md).

Its role in Xiri is limited to **desktop look and feel and interaction mechanics**, as requested. Useful starting points include:

- [Desktop components](https://github.com/Sergutsu/IRIX-Simulator/tree/6eb3406f7c7991e3a67e55945c933066a355b379/src/components) and [styles](https://github.com/Sergutsu/IRIX-Simulator/blob/6eb3406f7c7991e3a67e55945c933066a355b379/src/styles/irix.css): window decoration, focus, minimized tiles, menus, icon interaction and Desks Overview.
- [Screenshot reference catalog](https://github.com/Sergutsu/IRIX-Simulator/blob/6eb3406f7c7991e3a67e55945c933066a355b379/src/reference/irixScreenshots.ts) and [desktop specifications](https://github.com/Sergutsu/IRIX-Simulator/blob/6eb3406f7c7991e3a67e55945c933066a355b379/docs/IRIX_6.5_SPECIFICATIONS.md): leads for visual comparison and interaction checklists.

Treat the simulator's choices as secondary references and verify them against SGI documentation and the selected original-IRIX installation. This reference supplies no evidence of IRIX binary compatibility, kernel or hardware behavior, or completion of Xiri's original-desktop preservation goal. Xiri has reviewed its README and repository layout only; the simulator has not been run or its fidelity validated here.

## Platform choice

NetBSD was selected as the underlying OS on 2026-10-14. Development starts on an emulated Indy, followed by physical qualification. The following hardware order is based on the available machines and published support, pending actual boot tests.

| Machine | Proposed investigation | Decision condition |
| --- | --- | --- |
| Indy | First NetBSD platform, preferably a configuration with supported Newport graphics | Confirm CPU, graphics board, stable networking, storage, and usable display |
| Indigo2 | Second platform if its CPU and graphics match existing support | R4x00, R8000, and R10000 machines must be treated separately |
| Octane | Port the required board and device support to NetBSD | Use historical OpenBSD and current Linux as references; validate I/O and display on the available machine |
| Fuel | Later research target | Requires access to hardware and a dedicated port assessment |

The target is one NetBSD foundation across the supported machines. Its advantages are a common compatibility implementation and one maintained OS base. The cost is additional board support, especially for Octane. Linux as a replacement foundation and revival of the retired OpenBSD SGI port were considered alternatives; they are outside the agreed implementation plan.

## Preserving the desktop

The preservation target includes window management, Toolchest, file and desktop icons, desks, application launching, and saved preferences. SGI's desktop guide documents these as interacting parts of the environment. The initial implementation strategy is to run the original programs through compatibility and adapt the services they depend on. [SGI Desktop User's Guide](https://tech-pubs.net/SGI_EndUser/books/Desktop_UG/sgi_html/ch13.html).

A working `4Dwm` window is only an early milestone. Required X extensions, shared libraries, file notification, session management, and system administration operations need individual investigation. SGI's package inventory separately identifies desktop libraries, file alteration monitoring, and desktop services. Dependencies must be established for the actual installed IRIX release. [SGI software subsystem inventory](https://tech-pubs.net/SGI_Admin/books/ChallS_OG/sgi_html/ch07.html).

If an original component proves impractical to retain, a compatible replacement can be proposed with an explicit account of the lost behavior. Such a replacement would change the preservation strategy; it should not silently redefine completion.

## Graphics and modern software

Graphics is the largest technical uncertainty. Console output, a usable X server, accelerated 2D, OpenGL, and older IRIS GL are distinct capabilities. Reusing an original desktop program does not make the original IRIX kernel graphics driver usable under a different kernel.

The proposed first target is a usable 2D desktop. Hardware 3D acceleration should follow a separately scoped investigation of one graphics family. Software rendering can establish correctness for selected programs, but its performance must be measured on the real machines.

A maintained OS improves the basis for modern software; it does not guarantee a current browser build. The exact CPU instruction set, endianness, compiler and runtime support, memory, and rendering costs still matter. For example, Rust's published NetBSD target list includes a little-endian MIPS target requiring MIPS32, which does not establish support for these older big-endian SGI CPUs. [Rust NetBSD platform documentation](https://doc.rust-lang.org/rustc/platform-support/netbsd.html).

Native maintained command-line tools and modest graphical applications are sensible early targets. A current full browser remains an independent feasibility item. A browser running on a modern companion machine and displayed on the SGI is a practical optional bridge; it would not count as native browser support.

## Scope and effort

A prototype on one machine with selected binaries is a bounded feasibility project. A reliable desktop across three machine families, with broad legacy compatibility and acceleration, is a much larger continuing effort. Calendar estimates should follow the first boot, desktop dependency, and ABI experiments.

First establish the emulated NetBSD development loop, then determine whether the original desktop can be separated from enough IRIX-specific kernel and display behavior to coexist with a maintained host. A user-provided [IRIX 6.5.22m image](results/2026-10-30-irix-vendor-baseline.md) now supplies the original runtime and n32 desktop binaries. Selected native command probes pass. Xiri’s bounded o32 loader, runtime queries, ELF mapping, and [indirect dispatch](results/2026-10-30-irix-o32-dispatch.md) now run unmodified asa through its original libc and rld. Its filter completes with output checked against original IRIX, as root and as an ordinary user. This proves one vendor application path; broader runtime, terminal, and dynamic-linking behavior remain unqualified. The [LP64 native baseline](results/2026-10-30-netbsd64-native.md) removes the kernel-boot obstacle, and the [dual-ABI personality](results/2026-10-30-irix-lp64.md) now runs unmodified n32 echo alongside o32 asa on the 8 KiB kernel. Exact command outputs match original IRIX; malformed loader layouts, dispatch widths, heap growth and native regressions are tested. This establishes two vendor command paths. The [desktop startup audit](results/2026-10-30-irix-desktop-startup.md) now resolves the static library closures and records initial resource/session requirements. The [initial TCP subset](results/2026-10-30-irix-tcp.md) now lets Toolchest connect to a native X server, where unsupported getsockname is the next blocker; 4Dwm stops at an unaligned library mapping and also requires library relocation. Original IRIX loads both and attempts TCP connections to the controlled unused display. Live X interaction, later modules, resources, services and session behavior remain to be qualified. Reference XFS alerts and graphical-session qualification remain open. Answer that feasibility question before investing in a full Octane or Fuel port; physical Indy inventory can proceed alongside the emulated work.
